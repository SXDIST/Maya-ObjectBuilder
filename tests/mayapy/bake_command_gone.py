"""a3obBakeSkin no longer exists; a3obSkinWeights still does (run with mayapy).

Deregistering a command is a deliberate break of the registered-name contract. This
pins the intent so a later reader sees a decision rather than an accident.

Run:  mayapy.exe tests/mayapy/bake_command_gone.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    _harness.check(not hasattr(cmds, "a3obBakeSkin"),
                   "a3obBakeSkin should be deregistered")
    _harness.check(hasattr(cmds, "a3obSkinWeights"),
                   "a3obSkinWeights must survive — it is the outlier selector")
    _harness.check(hasattr(cmds, "a3obTransferSkin"),
                   "a3obTransferSkin must survive")
    print("OK - bake command gone, the skin tools that matter remain")


main()
