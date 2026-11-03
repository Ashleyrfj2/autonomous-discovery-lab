"""Conservative sanitization; never pass source bodies or credential objects to logs."""

import re
from collections.abc import Mapping
from typing import Any

_SECRET_KEY = re.compile(
    r"^key$|api[_-]?key|(?:access|refresh|auth|bearer)[_-]?token|"
    r"secret|password|authorization|cookie|credential",
    re.I,
)
_PATTERNS = [
    re.compile(r"\b(?:sk-|gsk_|hf_|AKIA)[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)\b(?:bearer|basic)\s+[^\s,;]+"),
    re.compile(r"(?i)(?:api[_ -]?key|token|password|secret)\s*[=:]\s*[^\s,;]+"),
    re.compile(r"https?://[^\s/@:]+:[^\s/@]+@[^\s]+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]


def sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(k): "[REDACTED]" if _SECRET_KEY.search(str(k)) else sanitize(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        for pattern in _PATTERNS:
            value = pattern.sub("[REDACTED]", value)
        return value[:4096]
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return "[UNSUPPORTED]"


def contains_credential(value: str) -> bool:
    """Detect recognizable credential material without returning or logging it."""
    return any(pattern.search(value) for pattern in _PATTERNS[:-1])
