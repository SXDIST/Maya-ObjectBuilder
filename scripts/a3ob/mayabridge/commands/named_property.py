import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class NamedPropertyCommand(_Base):
    kName = "a3obNamedProperty"

    @staticmethod
    def creator():
        return NamedPropertyCommand()

    @staticmethod
    def syntax():
        # Two deviations forced by OpenMaya 2.0's MSyntax vs the former C++ MSyntax:
        #  * addFlag accepts only ONE argument type, so the old two-argument
        #    "-set key value" form is passed as a single "key=value" string.
        #  * the long flag name "set" is reserved and rejected by om2, so the long
        #    alias is "-setproperty"; the short "-s" form is unchanged.
        s = om.MSyntax()
        s.addFlag("-l", "-list")
        s.addFlag("-s", "-setproperty", om.MSyntax.kString)
        s.addFlag("-r", "-remove", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        lod = selected_lod_or_null()
        if lod.isNull():
            om.MGlobal.displayError("a3obNamedProperty: select a LOD transform, LOD mesh, or mesh components")
            return

        if argdb.isFlagSet("-l"):
            self.setResult(named_property_result(lod))
            return

        properties = split_properties(attr.get_string(lod, A.PROPERTIES))
        if argdb.isFlagSet("-s"):
            payload = argdb.flagArgumentString("-s", 0)
            sep = payload.find("=")
            key = payload if sep == -1 else payload[:sep]
            value = "" if sep == -1 else payload[sep + 1:]
            if not key:
                om.MGlobal.displayError("a3obNamedProperty: property key cannot be empty")
                return
            properties = [item for item in properties if item[0] != key]
            properties.append((key, value))
            attr.set_string(lod, A.PROPERTIES, properties_string(properties))
            self.setResult(named_property_result(lod))
            return

        if argdb.isFlagSet("-r"):
            key = argdb.flagArgumentString("-r", 0)
            properties = [item for item in properties if item[0] != key]
            attr.set_string(lod, A.PROPERTIES, properties_string(properties))
            self.setResult(named_property_result(lod))
            return

        self.setResult(named_property_result(lod))
