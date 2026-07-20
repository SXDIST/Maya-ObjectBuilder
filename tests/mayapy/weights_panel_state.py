"""The Skinning panel must say what is stored and what to do next (mayapy).

The two attribute slots behind the buttons are invisible, so the panel used to make
the user track in their head whether a save had happened since a re-bind. Every
message below is the answer to a question a rigger actually asked while confused.

Run:  mayapy.exe tests/mayapy/weights_panel_state.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.mayabridge import weightsync  # noqa: E402
from a3ob.ui.panels.skinning import (  # noqa: E402
    _weights_state,
    _weights_state_text,
    _why_nothing_restored,
)


def _rigged_lod():
    cmds.file(new=True, force=True)
    lod = cmds.polyCylinder(name="garment", height=6, subdivisionsY=6, ch=False)[0]
    cmds.addAttr(lod, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(lod + ".a3obIsLOD", True)
    joints = [cmds.joint(name="Pelvis", position=(0, -3, 0)),
              cmds.joint(name="Spine", position=(0, 0, 0))]
    skin = cmds.skinCluster(joints, lod, toSelectedBones=True)[0]
    shape = cmds.listRelatives(lod, shapes=True)[0]
    for vertex in range(cmds.polyEvaluate(lod, vertex=True)):
        cmds.skinPercent(skin, f"{shape}.vtx[{vertex}]",
                         transformValue=[("Spine", 1.0), ("Pelvis", 0.0)])
    cmds.select(lod, replace=True)
    return lod, joints, skin


def _line():
    return _weights_state_text(_weights_state())


def test_messages_are_plain_ascii():
    """These strings reach the Script Editor, which is cp1251 on a Russian Windows.

    A non-ASCII glyph there raises UnicodeEncodeError instead of printing the warning —
    the user would see a traceback where the explanation should be.
    """
    lod, _joints, skin = _rigged_lod()
    weightsync.sync_all_lods()
    cmds.skinCluster(skin, edit=True, unbind=True)
    cmds.select(lod, replace=True)

    for text in (_line(), _why_nothing_restored("baked"), _why_nothing_restored("previous")):
        offenders = sorted({c for c in text if ord(c) > 127})
        _harness.check(not offenders,
                       f"panel text must stay ASCII for cp1251 consoles, found {offenders!r} "
                       f"in: {text}")
    print("OK panel messages are ASCII-safe")


def test_state_line_tracks_the_whole_flow():
    lod, joints, skin = _rigged_lod()

    _harness.check("No stored weights" in _line(),
                   f"a freshly bound, never-saved LOD has nothing stored yet: {_line()}")

    weightsync.sync_all_lods()
    cmds.select(lod, replace=True)
    _harness.check("Stored weights on 1/1" in _line(), f"saving stores them: {_line()}")

    # Unbind: the stored copy must survive, and the panel must say why a restore would
    # do nothing — this is the exact confusion that made the feature look broken.
    cmds.skinCluster(skin, edit=True, unbind=True)
    cmds.delete(lod, constructionHistory=True)
    cmds.select(lod, replace=True)
    line = _line()
    _harness.check("Stored weights on 1/1" in line, f"unbind must not lose the copy: {line}")
    _harness.check("no rig bound" in line, f"unbind must explain the missing rig: {line}")
    _harness.check("bind" in _why_nothing_restored("baked").lower(),
                   "restoring with no rig must tell the user to bind first")

    # Re-bind and save: the good copy moves to the older slot and is now one save from
    # being lost. The warning has to arrive BEFORE that, not after.
    cmds.skinCluster(joints, lod, toSelectedBones=True)
    weightsync.sync_all_lods()
    cmds.select(lod, replace=True)
    line = _line()
    _harness.check("older copy kept" in line, f"the replaced copy is kept: {line}")
    _harness.check("one save from being overwritten" in line,
                   f"the closing window must be announced before it closes: {line}")
    print("OK state line tracks bind -> save -> unbind -> re-bind")


def test_state_is_read_only():
    """The panel refreshes from the scene; it must never dirty it."""
    lod, _joints, _skin = _rigged_lod()
    weightsync.sync_all_lods()
    path = cmds.file(rename=cmds.internalVar(userTmpDir=True) + "weights_panel_state.ma")
    cmds.file(save=True, force=True, type="mayaAscii")
    _harness.check(not cmds.file(query=True, modified=True), "scene is clean after saving")

    cmds.select(lod, replace=True)
    for _ in range(3):
        _weights_state()
        _weights_state_text(_weights_state())
        _why_nothing_restored("baked")

    _harness.check(not cmds.file(query=True, modified=True),
                   "reading the weights state must not mark the scene modified")
    print(f"OK reading the state left {path.rsplit('/', 1)[-1]} clean")


def main():
    test_messages_are_plain_ascii()
    test_state_line_tracks_the_whole_flow()
    test_state_is_read_only()
    print("weights panel state: OK")


if __name__ == "__main__":
    sys.exit(_harness.run(main))
