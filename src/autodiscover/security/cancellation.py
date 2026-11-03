"""Trusted orchestration cancellation context; never supplied by retrieved/model content."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_check: ContextVar[Callable[[], bool] | None] = ContextVar("adl_cancellation", default=None)


@contextmanager
def cancellation_scope(check: Callable[[], bool] | None) -> Iterator[None]:
    token = _check.set(check)
    try:
        yield
    finally:
        _check.reset(token)


def cancellation_requested() -> bool:
    check = _check.get()
    return bool(check and check())


def cancellable_wait(seconds: float, sleeper: Callable[[float], None]) -> bool:
    """Return false on cancellation; preserve the injected sleeper without wall-clock loops."""
    check = _check.get()
    if check is None:
        sleeper(seconds)
        return True
    remaining = seconds
    while remaining > 0:
        if check():
            return False
        interval = min(remaining, 0.05)
        sleeper(interval)
        remaining -= interval
    return not check()
