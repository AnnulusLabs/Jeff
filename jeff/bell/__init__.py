"""jeff.bell — Inter-instance relay status.

Bell is intentionally honest right now: the relay is not implemented yet.
Phase 3.5 is the seam where Bell becomes Jeff's MCP server and instance relay.
Until then, Bell reports status instead of pretending capability exists.
"""


def status() -> dict:
    return {
        "implemented": False,
        "phase": "3.5",
        "planned": "MCP server + inter-instance relay",
        "port": 7331,
    }


def summary() -> str:
    s = status()
    return (f"Bell: pending ({s['planned']}) on port {s['port']}. "
            "Not wired yet.")
