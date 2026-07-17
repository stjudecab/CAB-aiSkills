"""Pytest path setup for colorblind-sim scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("COLORBLIND_SIM_SKIP_ENV_BOOTSTRAP", "1")

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
