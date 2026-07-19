import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class ProxyCommand(_UndoableBase):
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
            # Through the modifier so undo removes it again; MDagModifier.createNode also
            # leaves the active component selection alone, which the selection set below
            # depends on (this is what the old skipSelect flag was for).
            proxy = self.modifier.createNode("transform", lod)
            self.modifier.renameNode(proxy, "a3ob_proxy1")
            self.modifier.doIt()

        attr.set_bool(proxy, A.IS_PROXY, True, self.modifier)
        attr.set_string(proxy, A.PROXY_PATH, proxy_path, self.modifier)
        attr.set_int(proxy, A.PROXY_INDEX, proxy_index, self.modifier)
        attr.set_string(proxy, A.PROXY_SELECTION, selection_name, self.modifier)

        if from_selection and not proxy_selection_set_exists(selection_name):
            create_proxy_selection_set(selection_name)

        om.MGlobal.displayInfo("a3obProxy: created " + selection_name)
