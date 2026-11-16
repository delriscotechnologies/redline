"""Scope configuration: target, allowlist, limits, minimal credentials."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Scope:
    """Authorized boundary for one run.

    Redline refuses to touch anything outside ``allowlist`` and never executes
    model-provided shell commands.
    """

    target: str
    allowlist: list[str] = field(default_factory=list)
    max_requests: int = 50
    timeout_seconds: int = 60
    credentials: dict = field(default_factory=dict)

    def allows(self, url: str) -> bool:
        if not self.allowlist:
            return url == self.target or url.startswith(self.target)
        return any(url == a or url.startswith(a) for a in self.allowlist)


def demo_scope(target: str = "mock://invoice-agent") -> Scope:
    return Scope(
        target=target,
        allowlist=[target],
        max_requests=10,
        timeout_seconds=30,
    )
