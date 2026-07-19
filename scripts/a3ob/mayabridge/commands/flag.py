import maya.api.OpenMaya as om

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class SetFlagCommand(_Base):
    kName = "a3obSetFlag"

    @staticmethod
    def creator():
        return SetFlagCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-c", "-component", om.MSyntax.kString)
        s.addFlag("-v", "-value", om.MSyntax.kLong)
        s.addFlag("-n", "-name", om.MSyntax.kString)
        return s

    def doIt(self, args):
        # One Ctrl+Z must undo the whole command, not each cmds call inside it.
        with undo_chunk():
            argdb = om.MArgDatabase(self.syntax(), args)
            component = argdb.flagArgumentString("-c", 0) if argdb.isFlagSet("-c") else "face"
            value = argdb.flagArgumentInt("-v", 0) if argdb.isFlagSet("-v") else 0
            name = argdb.flagArgumentString("-n", 0) if argdb.isFlagSet("-n") else "a3ob_flag#"
            if component not in ("vertex", "face"):
                om.MGlobal.displayError("a3obSetFlag: -component must be vertex or face")
                return
            if value == 0:
                om.MGlobal.displayError("a3obSetFlag: -value must be non-zero")
                return
            if create_metadata_set(name, component, value).isNull():
                om.MGlobal.displayError("a3obSetFlag: select mesh vertex or face components")
                return
            om.MGlobal.displayInfo("a3obSetFlag: created flag set")
