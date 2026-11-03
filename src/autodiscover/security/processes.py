"""Bind local coordinator PID and creation time without reading process environments."""

import os
from uuid import uuid4

import psutil


def local_owner() -> str:
    pid = os.getpid()
    return f"local:{pid}:{psutil.Process(pid).create_time()!r}:{uuid4()}"


def coordinator_alive(owner: str | None) -> bool | None:
    if not owner or not owner.startswith("local:"):
        return None  # Legacy/remote identity: only lease expiry can establish abandonment.
    try:
        _prefix, pid, created, _unique = owner.split(":")
        process = psutil.Process(int(pid))
        return process.create_time() == float(created) and process.status() not in (
            psutil.STATUS_ZOMBIE,
            psutil.STATUS_DEAD,
        )
    except psutil.NoSuchProcess:
        return False
    except ValueError:
        return None
    except psutil.AccessDenied:
        return None
