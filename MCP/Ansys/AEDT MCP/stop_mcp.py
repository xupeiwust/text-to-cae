#!/usr/bin/env python3
from __future__ import annotations

import os

from aedt_socket_protocol import request


HOST = os.environ.get("AEDT_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("AEDT_MCP_PORT", "48252"))
TIMEOUT = float(os.environ.get("AEDT_MCP_TIMEOUT", "10"))
TOKEN = os.environ.get("AEDT_MCP_TOKEN", "")


def main() -> None:
    params = {"token": TOKEN} if TOKEN else {}
    result = request(HOST, PORT, "stop", params, timeout=TIMEOUT)
    print(result.get("message") or result)


if __name__ == "__main__":
    main()
