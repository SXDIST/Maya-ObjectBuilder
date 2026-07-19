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


class undo_chunk:
    """Collapse several ``cmds.*`` calls into ONE user-visible undo step.

    Commands that build scene nodes through ``cmds`` get undo for free, but each call is its
    own record — undoing "create a flag set" would otherwise take several Ctrl+Z presses and
    could leave the set half-dismantled in between. This is Maya's own grouping mechanism.

    Not needed by _UndoableBase subclasses: an MDagModifier is already a single record."""

    def __enter__(self):
        import maya.cmds as cmds
        cmds.undoInfo(openChunk=True)
        return self

    def __exit__(self, *_exc):
        import maya.cmds as cmds
        cmds.undoInfo(closeChunk=True)
        return False


class _Base(om.MPxCommand):
    def __init__(self):
        om.MPxCommand.__init__(self)

    def isUndoable(self):
        return False


class _UndoableBase(_Base):
    """Base for commands whose scene changes go through an MDGModifier.

    Maya only offers Ctrl+Z on a command that declares itself undoable AND routes its edits
    through a modifier — plug setters bypass the undo queue entirely. Subclasses build their
    changes with ``self.modifier`` (passing it to ``attributes.set_*``) and get undo/redo for
    free.

    IMPORTANT: once a command is undoable, EVERY scene change it makes must go through this
    modifier. Mixing in ``cmds.createNode`` leaves the node behind on undo — Maya treats the
    command as a single record and only replays what the modifier knows about. An MDagModifier
    is used (not MDGModifier) so DAG nodes can be created here too; it inherits the DG
    operations, and its createNode does not disturb the active selection, which is why the
    ``skipSelect`` workaround is unnecessary on this path."""

    def __init__(self):
        _Base.__init__(self)
        self.modifier = om.MDagModifier()

    def isUndoable(self):
        return True

    def redoIt(self):
        self.modifier.doIt()

    def undoIt(self):
        self.modifier.undoIt()


__all__ = [
    "create_material_nodes",
    "undo_chunk",
    "_Base",
    "_UndoableBase",
]
