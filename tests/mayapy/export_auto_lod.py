"""Auto LOD at export generates, writes, and leaves the scene as it was (mayapy).

The scene must be identical afterwards: same transforms, same names, same set
membership. That assertion is the whole point — "transient" is a promise about the
scene, not about the file.

Also covers the failure path: a scene with no valid source selected must write no
file and report an error, not a partial export.

Run:  mayapy.exe tests/mayapy/export_auto_lod.py
"""

import os
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def scene_fingerprint():
    transforms = sorted(cmds.ls(type="transform", long=True) or [])
    sets_ = sorted((s, tuple(sorted(cmds.sets(s, query=True) or [])))
                   for s in cmds.ls(type="objectSet") or [])
    return transforms, sets_


def build():
    cmds.file(new=True, force=True)
    transform = cmds.polySphere(name="garment", r=1, sx=12, sy=12, ch=False)[0]
    cmds.select(transform, replace=True)
    return transform


def export(path, options):
    cmds.file(path, force=True, options=options, type="Arma P3D",
              preserveReferences=False, exportSelected=True)


def test_generates_writes_and_leaves_scene_transient():
    build()
    before = scene_fingerprint()

    path = os.path.join(tempfile.mkdtemp(), "auto.p3d")
    export(path, "autoLod=1;autoLodResolution=1;autoLodGeometry=0;selectedOnly=1")

    _harness.check(os.path.isfile(path), "export wrote no file")
    # Read it the way this suite already does — see tests/mayapy/export_uses_live_mesh.py.
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    with BinaryReader(str(path)) as reader:
        mlod = MLOD.read(reader)
    _harness.check(len(mlod.lods) > 1,
                   "expected a generated LOD stack, got %d LOD(s)" % len(mlod.lods))

    after = scene_fingerprint()
    _harness.check(after[0] == before[0],
                   "generation must leave no transform behind:\n  before=%r\n  after=%r"
                   % (before[0], after[0]))
    _harness.check(after[1] == before[1],
                   "generation must leave set membership untouched")
    print("OK - %d LODs written, scene unchanged" % len(mlod.lods))


def test_no_source_writes_no_file_and_reports_error():
    """Zero (or more than one) selected source must be a clean failure, not a partial export."""
    cmds.file(new=True, force=True)
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"), quiet=True)
    # A mesh exists in the scene, but nothing is selected: generate_auto_lods must find no
    # source and the export must fail cleanly rather than silently exporting something else.
    cmds.polySphere(name="unselected_garment", r=1, ch=False)
    cmds.select(clear=True)

    path = os.path.join(tempfile.mkdtemp(), "no_source.p3d")
    _harness.check(not os.path.exists(path), "fixture path must not already exist")

    raised = False
    try:
        export(path, "autoLod=1;selectedOnly=1")
    except RuntimeError:
        raised = True  # the translator raises after do_write reports the error, see writer()

    _harness.check(raised, "export with no Auto LOD source must raise, not silently succeed")
    _harness.check(not os.path.exists(path),
                   "no Auto LOD source must write no file, got one at %r" % path)
    print("OK - no source selected: no file written, export raised")


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    test_generates_writes_and_leaves_scene_transient()
    test_no_source_writes_no_file_and_reports_error()


main()
