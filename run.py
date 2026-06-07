#!/usr/bin/env python3
"""Simple entry point: python run.py

Pulls latest 50 AI papers per category → filter → review → Excel.
"""

import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
env = os.environ.copy()
env["NO_PROXY"] = "*"

cmd = [sys.executable, "main.py", "--max-results", "50"]
if "--mock" in sys.argv:
    cmd.append("--mock")

proc = subprocess.run(cmd, env=env)
sys.exit(proc.returncode)
