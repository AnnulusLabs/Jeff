"""jeff.pantry.cluster — Distributed compute orchestration.
Bauen rewritten. 5,799 lines C → Pearlman Standard Python.

Discovers Ollama instances on the network, routes inference to best
available node, splits work across heterogeneous hardware, monitors
health. GPU kernels stay in llama.cpp/Ollama — this is pure orchestration.

AnnulusLabs LLC · April 2026
"""

import asyncio
import httpx
import time
import socket
import logging
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("jeff.pantry.cluster")

DISCOVERY_PORT = 7433
HEARTBEAT_SEC = 10
NODE_TIMEOUT_SEC = 30


# ── Node Types ───────────────────────────────────────────────────────

class DeviceType(Enum):
    CPU = "cpu"
    CUDA = "cuda"
    ROCM = "rocm"
    METAL = "metal"
    VULKAN = "vulkan"
    CORAL = "coral"
    HAILO = "hailo"
    JETSON = "jetson"

class NodeStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    DRAINING = "draining"


@dataclass
class Device:
    type: DeviceType
    name: str
    vram_mb: int = 0
    compute_tflops: float = 0.0

    def fits(self, model_mb: int) -> bool:
        return self.vram_mb >= model_mb


@dataclass
class Node:
    id: str
    host: str
    port: int = 11434             # Ollama default
    name: str = ""
    status: NodeStatus = NodeStatus.IDLE
    devices: list[Device] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    last_seen: float = 0.0
    latency_ms: float = 0.0
    tokens_per_sec: float = 0.0

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def total_vram(self) -> int:
        return sum(d.vram_mb for d in self.devices)

    @property
    def alive(self) -> bool:
        return (time.time() - self.last_seen) < NODE_TIMEOUT_SEC

    @property
    def score(self) -> float:
        """Higher = better. Factors: VRAM, speed, freshness, idle preference."""
        s = 0.0
        s += self.total_vram / 1000             # VRAM in GB
        s += self.tokens_per_sec / 10           # Speed
        s += 5.0 if self.status == NodeStatus.IDLE else 0
        s -= self.latency_ms / 100              # Penalize latency
        return max(s, 0.1)


# ── Cluster ──────────────────────────────────────────────────────────

class Cluster:
    """Manages a network of Ollama nodes."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self._lock = asyncio.Lock()

    # ── Discovery ────────────────────────────────────────────────────

    async def discover_local(self) -> Node | None:
        """Probe localhost Ollama."""
        return await self._probe("localhost", 11434, "local")

    async def discover_lan(self, subnet: str = "192.168.1", ports: list[int] = None):
        """Scan LAN for Ollama instances. Fast parallel probe."""
        ports = ports or [11434]
        tasks = []
        for i in range(1, 255):
            host = f"{subnet}.{i}"
            for port in ports:
                tasks.append(self._probe(host, port, f"{host}:{port}"))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, Node)]

    async def add_node(self, host: str, port: int = 11434, name: str = ""):
        """Manually add a node."""
        node = await self._probe(host, port, name or f"{host}:{port}")
        if node:
            log.info(f"Added node: {node.name} ({node.host}:{node.port}) "
                     f"VRAM={node.total_vram}MB models={len(node.models)}")
        return node

    async def remove_node(self, node_id: str):
        async with self._lock:
            self.nodes.pop(node_id, None)

    async def _probe(self, host: str, port: int, node_id: str) -> Node | None:
        """Check if an Ollama instance is running and catalog it."""
        url = f"http://{host}:{port}"
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=3) as client:
                # Check alive
                resp = await client.get(f"{url}/api/tags")
                latency = (time.time() - t0) * 1000
                if resp.status_code != 200:
                    return None

                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]

                # Detect devices via running model info
                devices = await self._detect_devices(client, url)

                node = Node(
                    id=node_id, host=host, port=port, name=node_id,
                    models=models, devices=devices,
                    last_seen=time.time(), latency_ms=latency,
                )
                async with self._lock:
                    self.nodes[node_id] = node
                return node
        except Exception:
            return None

    async def _detect_devices(self, client: httpx.AsyncClient, url: str) -> list[Device]:
        """Best-effort device detection from Ollama's ps endpoint."""
        devices = []
        try:
            resp = await client.get(f"{url}/api/ps")
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    details = m.get("details", {})
                    # Infer device from size_vram field
                    vram = m.get("size_vram", 0)
                    if vram > 0:
                        devices.append(Device(
                            type=DeviceType.CUDA,  # Assume GPU if VRAM reported
                            name=details.get("family", "gpu"),
                            vram_mb=vram // (1024 * 1024),
                        ))
        except Exception:
            pass
        if not devices:
            devices.append(Device(type=DeviceType.CPU, name="cpu"))
        return devices

    # ── Health ───────────────────────────────────────────────────────

    async def heartbeat(self):
        """Ping all nodes, update status, prune dead ones."""
        dead = []
        for nid, node in list(self.nodes.items()):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    t0 = time.time()
                    resp = await client.get(f"{node.url}/api/tags")
                    node.latency_ms = (time.time() - t0) * 1000
                    node.last_seen = time.time()
                    if resp.status_code == 200:
                        data = resp.json()
                        node.models = [m["name"] for m in data.get("models", [])]
                        node.status = NodeStatus.IDLE
                    else:
                        node.status = NodeStatus.OFFLINE
            except Exception:
                if not node.alive:
                    dead.append(nid)
                    node.status = NodeStatus.OFFLINE

        async with self._lock:
            for nid in dead:
                log.warning(f"Node {nid} timed out. Removing.")
                self.nodes.pop(nid, None)

    async def heartbeat_loop(self):
        """Background heartbeat worker."""
        while True:
            await self.heartbeat()
            await asyncio.sleep(HEARTBEAT_SEC)

    # ── Routing ──────────────────────────────────────────────────────

    def best_node(self, model: str | None = None) -> Node | None:
        """Pick the best available node, optionally filtered by model."""
        candidates = [
            n for n in self.nodes.values()
            if n.alive and n.status != NodeStatus.OFFLINE
        ]
        if model:
            with_model = [n for n in candidates if model in n.models]
            if with_model:
                candidates = with_model

        if not candidates:
            return None
        return max(candidates, key=lambda n: n.score)

    def nodes_with_model(self, model: str) -> list[Node]:
        return [n for n in self.nodes.values()
                if n.alive and model in n.models]

    def all_models(self) -> dict[str, list[str]]:
        """Map of model → list of node IDs that have it."""
        models: dict[str, list[str]] = {}
        for node in self.nodes.values():
            if not node.alive:
                continue
            for m in node.models:
                models.setdefault(m, []).append(node.id)
        return models

    # ── Distributed Inference ────────────────────────────────────────

    async def chat(self, messages: list[dict], model: str | None = None,
                   system: str | None = None, node_id: str | None = None) -> dict:
        """Route a chat request to the best available node."""
        if node_id:
            node = self.nodes.get(node_id)
        else:
            node = self.best_node(model)

        if not node:
            return {"error": "No available nodes", "content": ""}

        payload = {"model": model or "hermes3:8b", "messages": messages, "stream": False}
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + messages

        try:
            node.status = NodeStatus.BUSY
            async with httpx.AsyncClient(timeout=300) as client:
                t0 = time.time()
                resp = await client.post(f"{node.url}/api/chat", json=payload)
                elapsed = time.time() - t0
                data = resp.json()

                tokens_out = data.get("eval_count", 0)
                if elapsed > 0 and tokens_out > 0:
                    node.tokens_per_sec = tokens_out / elapsed

                node.status = NodeStatus.IDLE
                node.last_seen = time.time()
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "tokens_in": data.get("prompt_eval_count", 0),
                    "tokens_out": tokens_out,
                    "node": node.id,
                    "speed": f"{node.tokens_per_sec:.1f} tok/s",
                }
        except Exception as e:
            node.status = NodeStatus.IDLE
            return {"error": str(e), "content": ""}

    async def consensus(self, messages: list[dict], models: list[str],
                        system: str | None = None) -> list[dict]:
        """BranchialAnalyzer: same prompt to multiple models, return all."""
        tasks = [self.chat(messages, model=m, system=system) for m in models]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # ── Status ───────────────────────────────────────────────────────

    def summary(self) -> str:
        lines = [f"CLUSTER: {len(self.nodes)} nodes"]
        total_vram = 0
        total_models = set()
        for node in self.nodes.values():
            status = "+" if node.alive else "x"
            vram = f"{node.total_vram/1024:.1f}GB" if node.total_vram else "CPU"
            speed = f"{node.tokens_per_sec:.0f}t/s" if node.tokens_per_sec else ""
            lines.append(f"  [{status}] {node.name:<20s} {vram:>8s} {speed:>8s} "
                         f"{len(node.models)} models  {node.latency_ms:.0f}ms")
            total_vram += node.total_vram
            total_models.update(node.models)
        lines.append(f"  Total: {total_vram/1024:.1f}GB VRAM, "
                     f"{len(total_models)} unique models")
        return "\n".join(lines)


# ── USB Device Scanner ───────────────────────────────────────────────

KNOWN_ACCELERATORS = {
    (0x1a6e, 0x089a): ("Google", "Coral Edge TPU", 4.0),
    (0x03e7, 0x2485): ("Intel", "Neural Compute Stick 2", 1.0),
    (0x2cce, 0x8001): ("Hailo", "Hailo-8", 26.0),
    (0x03e7, 0xf63b): ("Luxonis", "OAK-D", 4.0),
}

def scan_usb_accelerators() -> list[dict]:
    """Detect known AI accelerators on USB. Linux only (reads /sys)."""
    found = []
    try:
        import os
        usb_path = "/sys/bus/usb/devices"
        if not os.path.exists(usb_path):
            return found
        for dev in os.listdir(usb_path):
            vendor_path = os.path.join(usb_path, dev, "idVendor")
            product_path = os.path.join(usb_path, dev, "idProduct")
            if os.path.exists(vendor_path) and os.path.exists(product_path):
                vid = int(open(vendor_path).read().strip(), 16)
                pid = int(open(product_path).read().strip(), 16)
                if (vid, pid) in KNOWN_ACCELERATORS:
                    mfr, name, tops = KNOWN_ACCELERATORS[(vid, pid)]
                    found.append({"vendor": mfr, "device": name,
                                  "tops": tops, "path": dev})
    except Exception:
        pass
    return found


# ── NAT Traversal (simplified) ───────────────────────────────────────

async def get_public_ip() -> str | None:
    """STUN-like: ask a public service for our external IP."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("https://api.ipify.org")
            return resp.text.strip()
    except Exception:
        return None


async def discover_upnp_gateway() -> str | None:
    """Minimal UPnP discovery for gateway IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        msg = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 2\r\n"
            "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n"
        )
        sock.sendto(msg.encode(), ("239.255.255.250", 1900))
        data, addr = sock.recvfrom(4096)
        sock.close()
        return addr[0]
    except Exception:
        return None


# ── Quick Test ───────────────────────────────────────────────────────

async def _test():
    cluster = Cluster()
    local = await cluster.discover_local()
    if local:
        print(cluster.summary())
        models = cluster.all_models()
        print(f"\nModels available: {list(models.keys())[:10]}")
    else:
        print("No local Ollama found. Start it: ollama serve")

    usb = scan_usb_accelerators()
    if usb:
        print(f"\nUSB accelerators: {usb}")

    pub_ip = await get_public_ip()
    if pub_ip:
        print(f"Public IP: {pub_ip}")

if __name__ == "__main__":
    asyncio.run(_test())
