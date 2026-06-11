from __future__ import annotations

import json
import socket
import uuid
from typing import Any


class ProtocolError(RuntimeError):
    """Raised when the AEDT bridge returns malformed protocol data."""


def send_message(sock: socket.socket, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sock.sendall(data + b"\n")


def send_text_message(sock: socket.socket, payload: dict[str, Any]) -> None:
    """Send JSON as text for IronPython socket bridges that expect str input."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    sock.sendall(data.encode("utf-8"))


def read_message(sock: socket.socket, max_bytes: int = 32 * 1024 * 1024) -> dict[str, Any]:
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ProtocolError("socket closed before a complete message was received")

        newline = chunk.find(b"\n")
        if newline >= 0:
            chunks.append(chunk[:newline])
            break

        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise ProtocolError(f"message exceeded {max_bytes} bytes")

    message = json.loads(b"".join(chunks).decode("utf-8"))
    if not isinstance(message, dict):
        raise ProtocolError("protocol message must be a JSON object")
    return message


def request(
    host: str,
    port: int,
    method: str,
    params: dict[str, Any] | None = None,
    timeout: float = 60.0,
    max_bytes: int = 32 * 1024 * 1024,
) -> dict[str, Any]:
    request_params = dict(params or {})
    request_params.setdefault("timeout", timeout)
    payload = {
        "id": str(uuid.uuid4()),
        "method": method,
        "params": request_params,
    }

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        send_text_message(sock, payload)
        response = read_message(sock, max_bytes=max_bytes)

    if response.get("id") != payload["id"]:
        raise ProtocolError("AEDT bridge returned a mismatched response id")
    if not response.get("ok", False):
        error = response.get("error") or {}
        if isinstance(error, dict):
            raise RuntimeError(error.get("message") or json.dumps(error, ensure_ascii=False))
        raise RuntimeError(str(error))

    result = response.get("result")
    if not isinstance(result, dict):
        raise ProtocolError("AEDT bridge returned an invalid result envelope")
    return result
