"""files action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def import_model_cfg_from_ui():
    # The dedicated Skeleton panel was removed; the model.cfg commands stay reachable
    # from the MayaObjectBuilder menu and prompt for the path via the native dialog.
    import_model_cfg(None)


def export_model_cfg_from_ui():
    export_model_cfg(None)


__all__ = [
    "import_model_cfg_from_ui",
    "export_model_cfg_from_ui",
]
