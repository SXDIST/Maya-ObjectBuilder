"""The Skinning panel's transfer summary reads differently for fitted vs. detached shells (mayapy).

Task 3 removed the panel's "Detached over" field. With no field left to correct a
misclassification, ``run_transfer_skin``'s summary line is the ONLY remaining signal that a
shell was classified as detached (rigidified) rather than fitted — so "0 rigid" and "N rigid"
must read as distinct classification outcomes, not the same template with a number swapped in.
``tests/mayapy/transfer_reports_rigid_shells.py`` stops at the ``_transfer_skin`` wrapper and
never calls ``run_transfer_skin`` itself, so a change that collapsed both branches into a single
"{0} mesh(es); {1} rigid" format string would pass every test in the suite except this one.

For the fixture: ``skintransfer.shell_distances`` measures each shell vertex's distance to the
CLOSEST point on the reference surface and takes the median. A garment as tall as it is wide,
straddling the body's surface, always measures roughly half its own height regardless of
offset — see transfer_reports_rigid_shells.py's ``build_body_and_garment`` docstring for the
full account of why that first attempt never reported zero. The garment here is the same thin
box (height 0.05) that fixture settled on, which is thin enough to actually hug the surface at
offset 0.0.

Constructing a real QWidget under mayapy needs a genuine QApplication in place *before*
maya.standalone.initialize() runs, or building one segfaults the process with no Python
traceback at all — see _harness.bootstrap()/_built_active_dock() docstrings.

Run:  mayapy.exe tests/mayapy/transfer_summary_wording.py
"""

import sys

from PySide6 import QtWidgets

_qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import _harness
from _harness import _built_active_dock, _release_active_dock

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

_harness.load_plugin()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_body_and_garment(garment_offset=0.0):
    """A skinned body plus one thin garment shell ``garment_offset`` from its surface.

    Mirrors transfer_reports_rigid_shells.py's fixture exactly: at offset 0.0 the shell's
    corners sit ~0.025 units from the body surface (fitted, well under
    DEFAULT_FAR_DISTANCE=0.06); at offset 0.5 they sit ~0.475-0.525 units away (detached)."""
    cmds.file(new=True, force=True)
    body = cmds.polyCube(name="body", width=2, height=2, depth=2, ch=False)[0]
    root = cmds.joint(name="Pelvis", position=(0, 0, 0))
    cmds.joint(name="Spine", position=(0, 1, 0))
    cmds.select(body, root, replace=True)
    cmds.skinCluster(root, body, toSelectedBones=True)

    garment = cmds.polyCube(name="garment", width=1, height=0.05, depth=1, ch=False)[0]
    cmds.move(0, 1.0 + garment_offset, 0, garment, absolute=True)
    return body, garment


def summary_for(garment_offset):
    """Build a real dock, run the transfer through the panel method (not the bare wrapper),
    and return the summary line it wrote."""
    _body, garment = build_body_and_garment(garment_offset)
    dock = _built_active_dock()
    try:
        cmds.select(garment, replace=True)
        dock.run_transfer_skin()
        return dock.skinning_summary.text()
    finally:
        _release_active_dock(dock)


def test_fitted_and_detached_summaries_read_differently():
    fitted = summary_for(0.0)
    detached = summary_for(0.5)

    check(fitted != detached,
          "the fitted and detached summaries must read differently, both are %r" % (fitted,))
    check("none detached" in fitted.lower(),
          "the fitted summary should name the classification outcome (no shell rigidified), "
          "got %r" % fitted)
    check("rigid" in detached.lower() and "none detached" not in detached.lower(),
          "the detached summary should report a rigidified-shell count, got %r" % detached)


def main():
    for test in (test_fitted_and_detached_summaries_read_differently,):
        test()
        print("ok:", test.__name__, flush=True)
    print("TRANSFER SUMMARY WORDING: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
