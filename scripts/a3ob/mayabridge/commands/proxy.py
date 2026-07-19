import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class ProxyCommand(_Base):
    """``a3obProxy`` — non-undoable, like a3obSetFlag/a3obFindComponents.

    It can build a proxy selection objectSet, and MFnSet.create() never enters Maya's undo
    queue, so an _UndoableBase/MDagModifier shape here used to leave an orphan
    ``a3ob_proxy_*`` set behind on Ctrl+Z (the set-building call happened outside the
    modifier). The whole body instead runs inside one undo_chunk() so every cmds call —
    placeholder creation, its attributes, and the selection set — collapses into a single
    user-visible undo step. Do not reintroduce self.modifier here."""

    kName = "a3obProxy"

    @staticmethod
    def creator():
        return ProxyCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-p", "-path", om.MSyntax.kString)
        s.addFlag("-i", "-index", om.MSyntax.kLong)
        s.addFlag("-u", "-update")
        s.addFlag("-fs", "-fromSelection")
        s.addFlag("-ss", "-selectionSet")
        return s

    def doIt(self, args):
        import maya.cmds as cmds
        with undo_chunk():
            argdb = om.MArgDatabase(self.syntax(), args)
            proxy_path = argdb.flagArgumentString("-p", 0) if argdb.isFlagSet("-p") else ""
            if not proxy_path:
                om.MGlobal.displayError("a3obProxy: -path is required")
                return
            proxy_index = argdb.flagArgumentInt("-i", 0) if argdb.isFlagSet("-i") else 1

            lod = selected_lod_or_null()
            if lod.isNull():
                om.MGlobal.displayError("a3obProxy: select a LOD transform, LOD mesh, or mesh components")
                return

            update = argdb.isFlagSet("-u")
            from_selection = argdb.isFlagSet("-fs") or argdb.isFlagSet("-ss")
            selection_name = proxy_selection_name(proxy_path, proxy_index)

            proxy = proxy_placeholder(lod, selection_name) if update else NULL
            if proxy.isNull():
                # skipSelect: cmds.createNode would otherwise clear the active component
                # selection that create_proxy_selection_set() below depends on — the same
                # reason CLAUDE.md documents for the old MDagModifier.createNode path.
                lod_name = om.MFnDagNode(lod).fullPathName()
                created_name = cmds.createNode("transform", name="a3ob_proxy1",
                                                parent=lod_name, skipSelect=True)
                created = om.MSelectionList()
                created.add(created_name)
                proxy = created.getDependNode(0)

            update_proxy_placeholder(proxy, proxy_path, proxy_index)

            if from_selection and not proxy_selection_set_exists(selection_name):
                create_proxy_selection_set(selection_name)

            om.MGlobal.displayInfo("a3obProxy: created " + selection_name)
