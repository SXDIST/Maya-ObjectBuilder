import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class SetMassCommand(_UndoableBase):
    kName = "a3obSetMass"

    @staticmethod
    def creator():
        return SetMassCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-v", "-value", om.MSyntax.kDouble)
        s.addFlag("-c", "-clear")
        s.addFlag("-sc", "-selectedComponents")
        return s

    def doIt(self, args):
        transform = selected_transform_or_null()
        if transform.isNull():
            om.MGlobal.displayError("a3obSetMass: select a LOD transform or mesh")
            return

        argdb = om.MArgDatabase(self.syntax(), args)
        if argdb.isFlagSet("-c"):
            attr.set_bool(transform, A.HAS_MASS, False, self.modifier)
            attr.set_string(transform, A.MASS_VALUES, "", self.modifier)
            om.MGlobal.displayInfo("a3obSetMass: cleared mass values")
            return

        value = 1.0
        if argdb.isFlagSet("-v"):
            value = argdb.flagArgumentDouble("-v", 0)
        if argdb.isFlagSet("-sc"):
            if not set_selected_mass_values(transform, value, self.modifier):
                om.MGlobal.displayError("a3obSetMass: select LOD mesh vertex components")
                return
            om.MGlobal.displayInfo("a3obSetMass: set selected vertex mass values")
            return

        count = vertex_count_for_lod(transform)
        if count <= 0:
            om.MGlobal.displayError("a3obSetMass: selected LOD has no vertices")
            return
        attr.set_bool(transform, A.HAS_MASS, True, self.modifier)
        attr.set_string(transform, A.MASS_VALUES, repeated_mass_values(count, value), self.modifier)
        om.MGlobal.displayInfo("a3obSetMass: set mass values count=%d" % count)
