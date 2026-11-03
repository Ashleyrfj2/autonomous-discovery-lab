"""Explicitly authorized, pinned-DNS HTTPS retrieval with bounded bodies and time."""

import hashlib
import http.client
import ipaddress
import json
import queue
import socket
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode, urljoin, urlsplit

from autodiscover.orchestrator.durability import now
from autodiscover.security.redaction import sanitize


class RetrievalError(RuntimeError):
    pass


@dataclass(frozen=True)
class Fetched:
    requested_url: str
    final_url: str
    body: bytes
    content_type: str
    retrieved_at: str

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


class SourceFetcher(Protocol):
    def fetch(self, url: str) -> Fetched: ...


class Fetcher:
    def __init__(
        self,
        *,
        authorized: bool,
        allowed_hosts: tuple[str, ...] = ("api.crossref.org", "www.rfc-editor.org"),
        max_bytes: int = 2000000,
        timeout: float = 15,
        resolver: Callable[..., list] = socket.getaddrinfo,
    ):
        if not 0 < max_bytes <= 8000000 or not 0 < timeout <= 30:
            raise ValueError("Bounded retrieval policy required")
        self.authorized, self.allowed_hosts = authorized, allowed_hosts
        self.max_bytes, self.timeout, self.resolver = max_bytes, timeout, resolver

    def validate(self, url: str, *, deadline: float | None = None) -> tuple[str, str]:
        if not self.authorized:
            raise RetrievalError("RETRIEVAL_NOT_AUTHORIZED")
        if len(url) > 3000 or any(ord(c) < 32 for c in url) or sanitize(url) != url:
            raise RetrievalError("UNSAFE_OR_SENSITIVE_URL")
        parsed = urlsplit(url)
        try:
            port = parsed.port
        except ValueError:
            raise RetrievalError("INVALID_PORT") from None
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.fragment
            or port not in (None, 443)
            or parsed.hostname not in self.allowed_hosts
        ):
            raise RetrievalError("ORIGIN_NOT_ALLOWED")
        host = parsed.hostname
        if host is None:
            raise RetrievalError("ORIGIN_NOT_ALLOWED")
        result: queue.Queue = queue.Queue(maxsize=1)

        def resolve() -> None:
            try:
                result.put(self.resolver(host, 443, type=socket.SOCK_STREAM))
            except OSError:
                result.put(None)

        thread = threading.Thread(target=resolve, daemon=True, name="adl-dns")
        thread.start()
        remaining = (
            self.timeout if deadline is None else min(self.timeout, deadline - time.monotonic())
        )
        try:
            rows = result.get(timeout=max(0.001, remaining))
        except queue.Empty:
            raise RetrievalError("DNS_TIMEOUT") from None
        if rows is None:
            raise RetrievalError("DNS_FAILURE")
        addresses = {row[4][0] for row in rows}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise RetrievalError("PRIVATE_OR_RESERVED_ADDRESS")
        return host, sorted(addresses)[0]

    def _one(self, url: str, deadline: float) -> tuple[int, dict[str, str], bytes]:
        host, address = self.validate(url, deadline=deadline)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RetrievalError("RETRIEVAL_TIMEOUT")
        context = ssl.create_default_context()
        connection = http.client.HTTPSConnection(host, timeout=remaining, context=context)
        # Connect to the already validated numeric address; retain TLS hostname verification.
        # No proxy/env auth, alternate resolver or automatic redirect can bypass the policy.
        sock = socket.create_connection((address, 443), timeout=remaining)
        sock.settimeout(max(0.001, deadline - time.monotonic()))
        connection.sock = context.wrap_socket(sock, server_hostname=host)
        tls_socket = connection.sock

        def interrupt() -> None:
            try:
                tls_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

        timer = threading.Timer(max(0.001, deadline - time.monotonic()), interrupt)
        timer.daemon = True
        timer.start()
        try:
            parsed = urlsplit(url)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            connection.request(
                "GET",
                path,
                headers={
                    "User-Agent": "AutonomousDiscoveryLab/0.1 research",
                    "Accept": "application/json,text/plain,text/html",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise RetrievalError("ENCODED_BODY_UNSUPPORTED")
            content = bytearray()
            while chunk := response.read1(min(65536, self.max_bytes + 1 - len(content))):
                content.extend(chunk)
                if len(content) > self.max_bytes:
                    raise RetrievalError("SOURCE_TOO_LARGE")
                if time.monotonic() >= deadline:
                    raise RetrievalError("RETRIEVAL_TIMEOUT")
            return response.status, headers, bytes(content)
        finally:
            timer.cancel()
            connection.close()

    def fetch(self, url: str) -> Fetched:
        requested = url
        deadline = time.monotonic() + self.timeout
        try:
            for _ in range(4):
                status, headers, body = self._one(url, deadline)
                if status in (301, 302, 303, 307, 308):
                    url = urljoin(url, headers.get("location", ""))
                    # Explicit validation occurs before the next request/connection.
                    continue
                if status != 200:
                    raise RetrievalError(f"SOURCE_HTTP_{status}")
                return Fetched(requested, url, body, headers.get("content-type", ""), now())
        except (OSError, http.client.HTTPException, ValueError):
            raise RetrievalError("SOURCE_TRANSPORT_FAILURE") from None
        raise RetrievalError("REDIRECT_LIMIT")


def crossref_search(
    fetcher: SourceFetcher, query: str, *, count: int = 3
) -> tuple[Fetched, list[dict]]:
    if not 1 <= count <= 5 or not query.strip() or len(query) > 300 or sanitize(query) != query:
        raise RetrievalError("UNSAFE_QUERY_OR_COUNT")
    url = "https://api.crossref.org/works?" + urlencode(
        {"query.bibliographic": query, "rows": count}
    )
    fetched = fetcher.fetch(url)
    try:
        data = json.loads(fetched.body)
        items = data["message"]["items"]
        if not isinstance(items, list) or len(items) > count:
            raise ValueError("invalid metadata")
        return fetched, items
    except (KeyError, TypeError, ValueError):
        raise RetrievalError("INVALID_CROSSREF_METADATA") from None
