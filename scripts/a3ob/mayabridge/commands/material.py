import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class SetMaterialCommand(_Base):
    kName = "a3obSetMaterial"

    @staticmethod
    def creator():
        return SetMaterialCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-t", "-texture", om.MSyntax.kString)
        s.addFlag("-m", "-material", om.MSyntax.kString)
        return s

    def doIt(self, args):
        # One Ctrl+Z must undo the whole command, not each cmds call inside it.
        with undo_chunk():
            import maya.cmds as cmds
            argdb = om.MArgDatabase(self.syntax(), args)
            texture = argdb.flagArgumentString("-t", 0) if argdb.isFlagSet("-t") else ""
            material = argdb.flagArgumentString("-m", 0) if argdb.isFlagSet("-m") else ""

            members, _lod = selected_components()
            if members.length() == 0:
                om.MGlobal.displayError("a3obSetMaterial: select mesh faces")
                return

            # Assign what selected_components() resolved, NOT the raw selection: cmds.ls includes
            # the transform when it is selected alongside the faces, and forceElement on a
            # transform assigns the shader at object level over the whole mesh.
            selected_faces = members.getSelectionStrings()

            shading_group = create_material_nodes(texture, material)
            if selected_faces:
                cmds.sets(selected_faces, edit=True, forceElement=shading_group)
            om.MGlobal.displayInfo("a3obSetMaterial: assigned material metadata")
