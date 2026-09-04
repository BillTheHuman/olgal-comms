#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
venv_python = root / ".venv/bin/python"
if venv_python.exists() and Path(sys.prefix) != root / ".venv":
    os.execv(venv_python, [str(venv_python), str(Path(__file__).resolve())])  # noqa: S606
sys.path.insert(0, str(root / "src"))
os.chdir(root)

from olgal_comms.mcp_server import main  # noqa: E402

main()
