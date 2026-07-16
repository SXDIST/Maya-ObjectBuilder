"""Facade: the MayaObjectBuilder dock UI (implementation in a3ob.ui.*)."""

import sys
from pathlib import Path

_scripts_dir = str(Path(globals().get("__file__") or "objectBuilderMenu.py").resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from a3ob.ui.constants import *   # noqa: E402,F401,F403
from a3ob.ui.scene_ops import *   # noqa: E402,F401,F403
from a3ob.ui.widgets import *     # noqa: E402,F401,F403
from a3ob.ui.actions import *     # noqa: E402,F401,F403
from a3ob.ui.entry import *       # noqa: E402,F401,F403
from a3ob.ui.dock import MayaObjectBuilderDock  # noqa: E402,F401
