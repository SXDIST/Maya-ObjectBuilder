import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class ProxyCommand(_Base):
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
            lod_name = om.MFnDependencyNode(lod).name()
            # skipSelect so the active component selection survives for the selection set below.
            new_name = cmds.createNode("transform", name="a3ob_proxy#", parent=lod_name, skipSelect=True)
            sel = om.MSelectionList()
            sel.add(new_name)
            proxy = sel.getDependNode(0)

        attr.set_bool(proxy, A.IS_PROXY, True)
        attr.set_string(proxy, A.PROXY_PATH, proxy_path)
        attr.set_int(proxy, A.PROXY_INDEX, proxy_index)
        attr.set_string(proxy, A.PROXY_SELECTION, selection_name)

        if from_selection and not proxy_selection_set_exists(selection_name):
            create_proxy_selection_set(selection_name)

        om.MGlobal.displayInfo("a3obProxy: created " + selection_name)
