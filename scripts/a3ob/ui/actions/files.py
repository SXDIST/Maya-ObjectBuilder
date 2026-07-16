"""files action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def import_model_cfg_from_ui():
    dock = _active_qt_dock()
    path = dock.model_cfg_import_path() if dock is not None else ""
    import_model_cfg(path or None)


def export_model_cfg_from_ui():
    dock = _active_qt_dock()
    path = dock.model_cfg_export_path() if dock is not None else ""
    export_model_cfg(path or None)


__all__ = [
    "import_model_cfg_from_ui",
    "export_model_cfg_from_ui",
]
