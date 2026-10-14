"""Counts where the shared reads of one thread got their bytes from."""

from __future__ import annotations

import threading


class _ReadAccount:
    """Shared reads one thread made since the account was reset."""

    def __init__(self) -> None:
        """Starts an account with no reads."""
        self.hits = 0
        self.hit_bytes = 0
        self.loads = 0
        self.load_bytes = 0
        self.load_seconds = 0.0
        self.waits = 0
        self.wait_bytes = 0
        self.wait_seconds = 0.0


_reads = threading.local()


def reset() -> None:
    """Starts a fresh count of shared reads for this thread."""
    _reads.account = _ReadAccount()


def describe() -> str:
    """Describes the shared reads this thread made since `reset`.

    Returns:
        Whether the bytes came from memory, from storage, or from a download
        another reader was already doing.
    """
    account = _account()
    parts: list[str] = []
    if account.loads:
        parts.append(f"loaded {account.load_bytes} B in {account.load_seconds * 1000:.0f} ms")
    if account.waits:
        parts.append(f"waited for {account.wait_bytes} B for {account.wait_seconds * 1000:.0f} ms")
    if account.hits:
        parts.append(f"cache hit {account.hit_bytes} B")
    if not parts:
        return "no chunk read"
    return ", ".join(parts)


def note_hit(byte_count: int) -> None:
    """Counts bytes served from memory."""
    account = _account()
    account.hits += 1
    account.hit_bytes += byte_count


def note_load(byte_count: int, seconds: float) -> None:
    """Counts bytes this thread read from storage."""
    account = _account()
    account.loads += 1
    account.load_bytes += byte_count
    account.load_seconds += seconds


def note_wait(byte_count: int, seconds: float) -> None:
    """Counts bytes this thread waited for while another reader downloaded them."""
    account = _account()
    account.waits += 1
    account.wait_bytes += byte_count
    account.wait_seconds += seconds


def _account() -> _ReadAccount:
    """Returns this thread's read account, creating it on the first read."""
    account = getattr(_reads, "account", None)
    if account is None:
        account = _ReadAccount()
        _reads.account = account
    return account
