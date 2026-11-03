"""Bounded content-addressed storage with atomic creation and integrity verification."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from autodiscover.orchestrator.durability import canonical


class IntegrityError(ValueError):
    pass


class Artifacts:
    def __init__(self, root: Path, max_bytes: int = 8000000):
        self.root, self.max_bytes = root.resolve(), max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, digest: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise IntegrityError("Invalid content address")
        path = self.root / digest[:2] / digest
        if path.parent.is_symlink() or path.is_symlink():
            raise IntegrityError("Artifact symlink rejected")
        return path

    def put(self, content: bytes) -> str:
        if len(content) > self.max_bytes:
            raise IntegrityError("Artifact exceeds limit")
        digest = hashlib.sha256(content).hexdigest()
        path = self.path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if self.get(digest) != content:
                    raise IntegrityError("Existing content does not match address") from None
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return digest

    def get(self, digest: str) -> bytes:
        path = self.path(digest)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                content = stream.read(self.max_bytes + 1)
        except OSError:
            raise IntegrityError("Artifact missing or unsafe") from None
        if len(content) > self.max_bytes or hashlib.sha256(content).hexdigest() != digest:
            raise IntegrityError("Artifact digest/size mismatch")
        return content

    def put_json(self, value: Any) -> str:
        return self.put(canonical(value).encode())

    def get_json(self, digest: str) -> Any:
        return json.loads(self.get(digest))
