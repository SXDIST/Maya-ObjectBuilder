import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class UpdateProxyCommand(_UndoableBase):
    kName = "a3obUpdateProxy"

    @staticmethod
    def creator():
        return UpdateProxyCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-p", "-path", om.MSyntax.kString)
        s.addFlag("-i", "-index", om.MSyntax.kLong)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        path = argdb.flagArgumentString("-p", 0) if argdb.isFlagSet("-p") else ""
        if not path:
            om.MGlobal.displayError("a3obUpdateProxy: -path is required")
            return
        index = argdb.flagArgumentInt("-i", 0) if argdb.isFlagSet("-i") else 1

        node = selected_dependency_node_or_null()
        if node.isNull():
            om.MGlobal.displayError("a3obUpdateProxy: select a proxy placeholder or proxy selection set")
            return
        if attr.get_bool_any(node, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
            update_proxy_placeholder(node, path, index, self.modifier)
            return
        if attr.get_bool(node, A.IS_PROXY_SELECTION) or node.hasFn(om.MFn.kSet):
            update_proxy_selection_set(node, path, index)
            return
        om.MGlobal.displayError("a3obUpdateProxy: selected node is not a proxy placeholder or proxy selection set")
