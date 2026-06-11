# -*- coding: utf-8 -*-
"""Reload the AEDT MCP bridge inside an already running AEDT script context."""

from __future__ import print_function

import os
import socket
import time


try:
    ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    ROOT = os.getcwd()

BRIDGE_PATH = os.path.join(ROOT, "aedt_mcp_bridge.py")
HOST = os.environ.get("AEDT_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("AEDT_MCP_PORT", "48252"))


try:
    stop_bridge
except NameError:
    pass
else:
    try:
        print(stop_bridge())
    except Exception as exc:
        print("Existing AEDT MCP bridge stop failed: %s" % exc)

try:
    sock = socket.create_connection((HOST, PORT), 2)
    try:
        sock.sendall('{"id":"reload-stop","method":"stop","params":{"timeout":2}}\n')
    finally:
        sock.close()
    time.sleep(0.5)
except Exception as exc:
    print("Socket stop skipped: %s" % exc)

globals()["_AEDT_MCP_BRIDGE_STARTED"] = False

with open(BRIDGE_PATH, "r") as handle:
    code = handle.read()

exec(compile(code, BRIDGE_PATH, "exec"), globals(), globals())
