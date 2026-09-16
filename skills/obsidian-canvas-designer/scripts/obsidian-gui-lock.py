#!/usr/bin/env python3
"""Cross-process lease for the shared Obsidian GUI.

The Obsidian application is single-instance shared state. Canvas DOM QA mounts nodes,
forces reflow, and moves the viewport, so two processes must never do that at the same
time. This lease is the harness that makes concurrent Canvas work safe instead of
forbidding it: callers queue for the GUI step, then run one at a time.

The lease is a file created with O_CREAT|O_EXCL under the system temporary directory,
keyed by the vault path, so separate vaults never block each other. It stores the
holder pid, an owner label, and a timestamp. A lease whose pid is gone is stale and is
reclaimed automatically, so a crashed agent cannot wedge the lane.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import socket
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


LOCK_ROOT = Path(tempfile.gettempdir()) / "obsidian-canvas-qa"
DEFAULT_TIMEOUT = 120.0
DEFAULT_POLL = 0.25


class GuiLockError(RuntimeError):
    pass


class GuiLockTimeout(GuiLockError):
    pass


def lock_path(vault_root: Path) -> Path:
    digest = hashlib.sha256(str(vault_root.resolve()).encode("utf-8")).hexdigest()[:16]
    return LOCK_ROOT / f"{digest}.lock"


def default_owner() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def read_holder(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def is_stale(holder: dict | None) -> bool:
    if holder is None:
        return True
    pid = holder.get("pid")
    if not isinstance(pid, int):
        return True
    host = holder.get("host")
    if isinstance(host, str) and host != socket.gethostname():
        return False
    return not _pid_alive(pid)


def _try_create(path: Path, owner: str) -> dict | None:
    record = {
        "pid": os.getpid(),
        "owner": owner,
        "host": socket.gethostname(),
        "acquired_at": time.time(),
    }
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return None
    except OSError as exc:
        raise GuiLockError(f"cannot create GUI lease {path}: {exc}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        path.unlink(missing_ok=True)
        raise GuiLockError(f"cannot write GUI lease {path}: {exc}") from exc
    return record


def acquire(
    vault_root: Path,
    owner: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    poll: float = DEFAULT_POLL,
) -> dict:
    """Block until this process owns the GUI lease, or raise GuiLockTimeout."""
    if timeout < 0:
        raise GuiLockError("timeout must not be negative")
    if poll <= 0:
        raise GuiLockError("poll interval must be positive")
    owner = owner or default_owner()
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    path = lock_path(vault_root)
    deadline = time.monotonic() + timeout
    waited = 0.0
    while True:
        holder = read_holder(path)
        if holder is not None and holder.get("pid") == os.getpid() and holder.get("owner") == owner:
            return {**holder, "reentrant": True, "waited_seconds": 0.0, "path": str(path)}
        if holder is not None and is_stale(holder):
            path.unlink(missing_ok=True)
            holder = None
        created = _try_create(path, owner)
        if created is not None:
            return {**created, "reentrant": False, "waited_seconds": round(waited, 3), "path": str(path)}
        if time.monotonic() >= deadline:
            blocked = read_holder(path) or {}
            raise GuiLockTimeout(
                "timed out waiting for the Obsidian GUI lease "
                f"after {timeout:.0f}s; held by {blocked.get('owner')!r} "
                f"(pid {blocked.get('pid')})"
            )
        time.sleep(poll)
        waited += poll


def release(vault_root: Path, owner: str | None = None) -> bool:
    owner = owner or default_owner()
    path = lock_path(vault_root)
    holder = read_holder(path)
    if holder is None:
        return False
    if holder.get("pid") != os.getpid() or holder.get("owner") != owner:
        return False
    path.unlink(missing_ok=True)
    return True


def status(vault_root: Path) -> dict:
    path = lock_path(vault_root)
    holder = read_holder(path)
    if holder is None:
        return {"held": False, "path": str(path)}
    return {
        "held": not is_stale(holder),
        "stale": is_stale(holder),
        "holder": holder,
        "path": str(path),
    }


@contextmanager
def hold(vault_root: Path, owner: str | None = None, timeout: float = DEFAULT_TIMEOUT):
    lease = acquire(vault_root, owner, timeout)
    try:
        yield lease
    finally:
        release(vault_root, lease.get("owner"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("acquire", "release", "status"))
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--owner", default=None)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()
    try:
        if args.command == "acquire":
            result = acquire(args.vault_root, args.owner, args.timeout)
        elif args.command == "release":
            result = {"released": release(args.vault_root, args.owner)}
        else:
            result = status(args.vault_root)
    except (OSError, GuiLockError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2 if isinstance(exc, GuiLockTimeout) else 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
