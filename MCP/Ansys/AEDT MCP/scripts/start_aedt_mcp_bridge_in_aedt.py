# -*- coding: utf-8 -*-
"""AEDT menu-friendly entry point for starting or reloading the MCP bridge."""

from __future__ import print_function

import os


try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

LOADER_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, "reload_bridge_in_aedt.py"))


with open(LOADER_PATH, "r") as handle:
    code = handle.read()

exec(compile(code, LOADER_PATH, "exec"), globals(), globals())
