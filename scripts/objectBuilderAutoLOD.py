"""Facade: Auto-LOD generation (implementation lives in a3ob.ui.autolod)."""

import sys
from pathlib import Path

_scripts_dir = str(Path(globals().get("__file__") or "objectBuilderAutoLOD.py").resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from a3ob.ui.autolod import generate_auto_lods  # noqa: E402,F401
