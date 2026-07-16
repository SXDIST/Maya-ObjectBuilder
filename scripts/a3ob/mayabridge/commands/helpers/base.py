"""commands helper: base."""

"""The ``a3ob*`` Maya commands (OpenMaya 2.0 MPxCommand).

Port of ``src/commands/StubCommands.cpp``. Command names, flags and the resulting
``a3ob*`` attribute schema are preserved exactly — this is the contract the Python UI
and the ``tests/mayapy`` workflows depend on.

First-cut note: these commands are functional but not yet wired for undo. The C++
versions accumulated ``MDGModifier``/``MDagModifier`` operations; here operations are
applied directly. Undo support can be layered on later without changing the surface.
"""

import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers.primitives import *  # noqa: F401,F403


def create_material_nodes(texture, material):
    import maya.cmds as cmds
    normalized_texture = normalize_dayz_path(texture)
    normalized_material = normalize_dayz_path(material)
    shader = cmds.createNode("lambert", name="a3ob_material#")
    shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + "SG")
    cmds.connectAttr(shader + ".outColor", shading_group + ".surfaceShader", force=True)

    sel = om.MSelectionList()
    sel.add(shader)
    sel.add(shading_group)
    shader_obj = sel.getDependNode(0)
    sg_obj = sel.getDependNode(1)
    attr.set_string(shader_obj, A.TEXTURE, normalized_texture)
    attr.set_string(shader_obj, A.MATERIAL, normalized_material)
    attr.set_string(sg_obj, A.SG_TEXTURE, normalized_texture)
    attr.set_string(sg_obj, A.SG_MATERIAL, normalized_material)
    return shading_group


# =============================================================================
# proxy update helpers
# =============================================================================


class _Base(om.MPxCommand):
    def isUndoable(self):
        return False


__all__ = [
    "create_material_nodes",
    "_Base",
]
