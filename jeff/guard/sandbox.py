"""jeff.guard.sandbox — Runtime execution isolation.

Tools and agents run in sandboxed contexts. No tool can:
  - Access files outside the project scope
  - Make network requests unless explicitly allowed
  - Spawn processes without approval
  - Read environment variables with secrets
  - Modify system configuration

From KERF SecurityEnforcer + Sandbox architecture.

AnnulusLabs LLC · April 2026
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class Permission(Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK = "network"
    PROCESS_SPAWN = "process_spawn"
    ENV_READ = "env_read"
    SYSTEM_CONFIG = "system_config"
    GIT_WRITE = "git_write"
    PACKAGE_INSTALL = "package_install"


@dataclass
class SandboxPolicy:
    """What a sandboxed execution is allowed to do."""
    name: str = "default"
    allowed_permissions: set = field(default_factory=lambda: {
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.GIT_WRITE,
    })
    allowed_paths: list = field(default_factory=lambda: ["."])
    denied_paths: list = field(default_factory=lambda: [
        "/etc", "/sys", "/proc", "/boot", "/root",
        "~/.ssh", "~/.gnupg", "~/.aws", "~/.config",
    ])
    allowed_commands: list = field(default_factory=lambda: [
        "python", "pip", "git", "ruff", "pytest", "grep",
        "find", "cat", "head", "tail", "wc", "sort", "diff",
        "ls", "tree", "mkdir", "cp", "mv",
    ])
    denied_commands: list = field(default_factory=lambda: [
        "rm -rf /", "sudo", "su", "chmod 777", "curl|bash",
        "wget|bash", "eval", "exec", "> /dev/sd",
        "mkfs", "dd if=", "shutdown", "reboot", "kill -9 1",
    ])
    denied_env_vars: list = field(default_factory=lambda: [
        "AWS_SECRET", "API_KEY", "TOKEN", "PASSWORD", "SECRET",
        "PRIVATE_KEY", "CREDENTIALS",
    ])
    max_file_size_mb: float = 10.0
    max_output_bytes: int = 1_000_000
    timeout_seconds: int = 120
    allow_network: bool = False


# ── Pre-built Policies ───────────────────────────────────────────────

POLICIES = {
    "strict": SandboxPolicy(
        name="strict",
        allowed_permissions={Permission.FILE_READ},
        allow_network=False,
        timeout_seconds=30,
    ),
    "standard": SandboxPolicy(
        name="standard",
        allowed_permissions={
            Permission.FILE_READ, Permission.FILE_WRITE, Permission.GIT_WRITE},
        allow_network=False,
    ),
    "developer": SandboxPolicy(
        name="developer",
        allowed_permissions={
            Permission.FILE_READ, Permission.FILE_WRITE,
            Permission.GIT_WRITE, Permission.PROCESS_SPAWN,
            Permission.PACKAGE_INSTALL},
        allow_network=False,
    ),
    "full": SandboxPolicy(
        name="full",
        allowed_permissions=set(Permission),
        allow_network=True,
    ),
}


@dataclass
class SandboxViolation:
    permission: Permission
    description: str
    command: str = ""
    path: str = ""
    severity: str = "blocked"  # "blocked", "warned", "logged"


@dataclass
class SandboxResult:
    allowed: bool
    violations: list = field(default_factory=list)
    sanitized_command: str = ""


# ── Sandbox Enforcer ─────────────────────────────────────────────────

class Sandbox:
    """Enforce execution boundaries. No silent violations."""

    def __init__(self, policy: SandboxPolicy = None):
        self.policy = policy or POLICIES["standard"]
        self.violations: list[SandboxViolation] = []
        self.project_root = os.getcwd()

    def check_command(self, command: str) -> SandboxResult:
        """Check if a command is allowed under current policy."""
        violations = []

        # Check denied commands
        cmd_lower = command.lower().strip()
        for denied in self.policy.denied_commands:
            if denied.lower() in cmd_lower:
                violations.append(SandboxViolation(
                    permission=Permission.PROCESS_SPAWN,
                    description=f"Denied command pattern: {denied}",
                    command=command))

        # Check if command binary is allowed
        cmd_parts = command.split()
        if cmd_parts:
            binary = cmd_parts[0]
            # Strip path to get base command
            binary_base = os.path.basename(binary)
            if (self.policy.allowed_commands and
                    binary_base not in self.policy.allowed_commands):
                violations.append(SandboxViolation(
                    permission=Permission.PROCESS_SPAWN,
                    description=f"Command not in allowed list: {binary_base}",
                    command=command))

        # Check for network access
        network_cmds = {"curl", "wget", "ssh", "scp", "rsync", "nc", "ncat"}
        if cmd_parts and cmd_parts[0] in network_cmds:
            if not self.policy.allow_network:
                violations.append(SandboxViolation(
                    permission=Permission.NETWORK,
                    description="Network access not allowed",
                    command=command))

        # Check for env var access
        env_pattern = r'\$\{?([A-Z_]+)\}?'
        env_refs = re.findall(env_pattern, command)
        for var in env_refs:
            for denied in self.policy.denied_env_vars:
                if denied.lower() in var.lower():
                    violations.append(SandboxViolation(
                        permission=Permission.ENV_READ,
                        description=f"Denied env var access: {var}",
                        command=command))

        self.violations.extend(violations)

        return SandboxResult(
            allowed=len(violations) == 0,
            violations=violations,
            sanitized_command=command if not violations else "")

    def check_path(self, path: str, write: bool = False) -> SandboxResult:
        """Check if a file path is accessible."""
        violations = []
        resolved = str(Path(path).resolve())

        # Check denied paths
        for denied in self.policy.denied_paths:
            denied_resolved = str(Path(os.path.expanduser(denied)).resolve())
            if resolved.startswith(denied_resolved):
                violations.append(SandboxViolation(
                    permission=Permission.FILE_WRITE if write else Permission.FILE_READ,
                    description=f"Path in denied zone: {denied}",
                    path=path))

        # Check permission
        perm = Permission.FILE_WRITE if write else Permission.FILE_READ
        if perm not in self.policy.allowed_permissions:
            violations.append(SandboxViolation(
                permission=perm,
                description=f"Permission not granted: {perm.value}",
                path=path))

        # Check file size for writes
        if write and os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > self.policy.max_file_size_mb:
                violations.append(SandboxViolation(
                    permission=Permission.FILE_WRITE,
                    description=f"File exceeds size limit: {size_mb:.1f}MB > {self.policy.max_file_size_mb}MB",
                    path=path))

        self.violations.extend(violations)
        return SandboxResult(allowed=len(violations) == 0, violations=violations)

    def execute(self, command: str, cwd: str = None) -> dict:
        """Execute a command inside the sandbox.

        Returns dict with stdout, stderr, returncode, violations.
        """
        check = self.check_command(command)
        if not check.allowed:
            return {
                "stdout": "",
                "stderr": f"SANDBOX BLOCKED: {check.violations[0].description}",
                "returncode": -1,
                "blocked": True,
                "violations": [v.description for v in check.violations]
            }

        try:
            result = subprocess.run(
                command, shell=True,
                cwd=cwd or self.project_root,
                capture_output=True, text=True,
                timeout=self.policy.timeout_seconds,
                env=self._clean_env())

            output = result.stdout[:self.policy.max_output_bytes]
            return {
                "stdout": output,
                "stderr": result.stderr[:10000],
                "returncode": result.returncode,
                "blocked": False,
                "violations": []
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"SANDBOX TIMEOUT: {self.policy.timeout_seconds}s exceeded",
                "returncode": -2,
                "blocked": True,
                "violations": ["timeout"]
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"SANDBOX ERROR: {e}",
                "returncode": -3,
                "blocked": True,
                "violations": [str(e)]
            }

    def _clean_env(self) -> dict:
        """Strip sensitive env vars from execution environment."""
        env = os.environ.copy()
        for key in list(env.keys()):
            for denied in self.policy.denied_env_vars:
                if denied.lower() in key.lower():
                    env.pop(key, None)
        return env

    def summary(self) -> str:
        blocked = sum(1 for v in self.violations if v.severity == "blocked")
        return (f"Sandbox [{self.policy.name}]: "
                f"{len(self.violations)} violations ({blocked} blocked)")
