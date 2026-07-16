import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class CreateLODCommand(_Base):
    kName = "a3obCreateLOD"

    @staticmethod
    def creator():
        return CreateLODCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-lt", "-lodType", om.MSyntax.kLong)
        s.addFlag("-r", "-resolution", om.MSyntax.kLong)
        s.addFlag("-n", "-name", om.MSyntax.kString)
        return s

    def doIt(self, args):
        import maya.cmds as cmds
        from a3ob.formats.p3d import LodResolution
        argdb = om.MArgDatabase(self.syntax(), args)
        lod_type = argdb.flagArgumentInt("-lt", 0) if argdb.isFlagSet("-lt") else 0
        resolution = argdb.flagArgumentInt("-r", 0) if argdb.isFlagSet("-r") else 0
        name = argdb.flagArgumentString("-n", 0) if argdb.isFlagSet("-n") else ""

        transform = selected_transform_or_null()
        if transform.isNull():
            new_name = cmds.createNode("transform", name=name if name else "a3ob_LOD#", skipSelect=True)
            sel = om.MSelectionList()
            sel.add(new_name)
            transform = sel.getDependNode(0)

        set_lod_attributes(transform, lod_type, resolution)
        result_name = om.MFnDependencyNode(transform).name()
        self.setResult(result_name)
        om.MGlobal.displayInfo("a3obCreateLOD: marked LOD signature=%s" % LodResolution.encode(lod_type, resolution))
