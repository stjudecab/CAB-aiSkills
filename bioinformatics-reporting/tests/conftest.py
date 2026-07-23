#!/usr/bin/env python3
"""Pytest configuration for bioinformatics-reporting."""

from __future__ import annotations

import os

os.environ.setdefault("BIOINFORMATICS_REPORTING_SKIP_ENV_BOOTSTRAP", "1")
