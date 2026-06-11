# -*- coding: utf-8 -*-
"""Stop the AEDT MCP bridge inside an already running AEDT script context."""

from __future__ import print_function

import os
import socket
import time


HOST = os.environ.get("AEDT_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("AEDT_MCP_PORT", "48252"))


stopped = False

try:
    stop_bridge
except NameError:
    pass
else:
    try:
        print(stop_bridge())
        stopped = True
    except Exception as exc:
        print("Existing AEDT MCP bridge stop failed: %s" % exc)

if not stopped:
    try:
        sock = socket.create_connection((HOST, PORT), 2)
        try:
            sock.sendall('{"id":"toolbar-stop","method":"stop","params":{"timeout":2}}\n')
            try:
                sock.recv(4096)
            except Exception:
                pass
        finally:
            sock.close()
        stopped = True
        time.sleep(0.5)
        print("AEDT MCP bridge stop requested on %s:%s" % (HOST, PORT))
    except Exception as exc:
        print("AEDT MCP bridge was not reachable on %s:%s: %s" % (HOST, PORT, exc))

globals()["_AEDT_MCP_BRIDGE_STARTED"] = False
