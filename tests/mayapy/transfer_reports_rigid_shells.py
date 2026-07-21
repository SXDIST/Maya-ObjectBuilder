"""a3obTransferSkin reports rigidified shells, not just the mesh count (mayapy).

Phase 3c removes the panel's "Detached over" field: DEFAULT_FAR_DISTANCE = 0.06 was measured
on a real DayZ character (boots 0.009, trousers 0.019, jacket 0.024, helmet 0.025, backpack
0.102), so the field only ever overrode an already-correct value. But the margin between
fitted cloth and a backpack is 1.7x, and a bulky vest could fall inside it. With no field to
correct a misclassification, the misclassification has to be visible instead — so the count
the command already computes has to reach the caller.

Run:  mayapy.exe tests/mayapy/transfer_reports_rigid_shells.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

_harness.load_plugin()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_body_and_garment(garment_offset=0.0):
    """A skinned body plus one garment shell sitting `garment_offset` away from its surface.

    The body is a 2x2x2 cube (corners at +-1). The garment is a thin box (height 0.05)
    straddling the body's top face at y=1: at garment_offset=0.0 every one
    of its 8 corners sits 0.025 units from the body surface (well under
    DEFAULT_FAR_DISTANCE=0.06) — fitted. Pushed up by garment_offset=0.5 those same corners
    end up ~0.475-0.525 units away — clearly detached.

    A first version of this fixture used a garment as tall as it was wide (height=1,
    centered at y=1.0+offset) on the theory that offset alone tells fitted from detached.
    It does not: with a 0.5-unit half-height straddling the surface, half the shell's
    corners are ALWAYS ~0.5 units from the surface regardless of offset (the shell's own
    thickness dominates), so even the "fitted" case measured ~0.5 and was rigidified. The
    classifier (`skintransfer.shell_distances`) measures median distance from each shell's
    vertices to the reference mesh's closest surface point, not a gap between origins — so
    the fixture has to make the shell itself thin enough to actually hug the surface."""
    cmds.file(new=True, force=True)
    body = cmds.polyCube(name="body", width=2, height=2, depth=2, ch=False)[0]
    root = cmds.joint(name="Pelvis", position=(0, 0, 0))
    cmds.joint(name="Spine", position=(0, 1, 0))
    cmds.select(body, root, replace=True)
    cmds.skinCluster(root, body, toSelectedBones=True)

    garment = cmds.polyCube(name="garment", width=1, height=0.05, depth=1, ch=False)[0]
    cmds.move(0, 1.0 + garment_offset, 0, garment, absolute=True)
    return body, garment


def transfer(body, garment):
    """Select the garment ONLY, then transfer.

    ``find_reference`` docstring: "the best candidate not selected" — it walks every
    skinCluster in the SCENE and explicitly skips anything that is part of the passed-in
    target list (``skintransfer.py`` line ~87: ``dag_path.fullPathName() in target_keys:
    continue``). Selecting the body alongside the garment puts the body in ``targets`` too,
    so it is excluded from consideration as a reference and ``ensure_reference`` raises
    "no skinned reference in the scene" (witnessed: selecting both fails every time). The
    body must stay unselected in the scene for it to be picked automatically; only the
    garment goes into the selection. Deliberately does NOT touch the male_body optionVar:
    that is the user's real saved reference, and skin_transfer.py saves and restores it
    precisely because writing it leaks out of the test."""
    cmds.select(garment, replace=True)
    return cmds.a3obTransferSkin()


def test_the_result_is_a_pair():
    body, garment = build_body_and_garment()
    result = transfer(body, garment)
    check(isinstance(result, (list, tuple)) and len(result) == 2,
          "expected a two-element result, got %r" % (result,))


def test_element_zero_is_still_the_mesh_count():
    """Scripted callers reading result[0] must be unaffected by this change."""
    body, garment = build_body_and_garment()
    result = transfer(body, garment)
    check(int(result[0]) == 1, "element 0 is %r, expected the mesh count 1" % (result[0],))


def test_a_detached_shell_is_counted():
    body, garment = build_body_and_garment(garment_offset=0.5)
    result = transfer(body, garment)
    check(int(result[1]) >= 1,
          "a shell 0.5 from the body was not counted as rigidified: %r" % (result,))


def test_a_fitted_shell_reports_zero():
    """Zero must be reachable and distinct from the detached case — otherwise the number the
    panel shows carries no information."""
    body, garment = build_body_and_garment(garment_offset=0.0)
    result = transfer(body, garment)
    check(int(result[1]) == 0,
          "a fitted shell was reported as rigidified: %r" % (result,))


def test_the_ui_wrapper_returns_both_numbers():
    from a3ob.ui.entry import _transfer_skin
    _body, garment = build_body_and_garment(garment_offset=0.5)
    cmds.select(garment, replace=True)
    meshes, rigid = _transfer_skin()
    check(meshes == 1, "wrapper reported %r meshes" % meshes)
    check(rigid >= 1, "wrapper reported %r rigid shells" % rigid)


def test_the_wrapper_omits_the_distance_flag_when_none():
    """Task 3 deletes the panel's distance field. The wrapper must then NOT pass -distance at
    all, so the command applies its own measured DEFAULT_FAR_DISTANCE — rather than the UI
    hard-coding 0.06 and silently drifting from it."""
    from a3ob.ui import entry
    seen = {}
    original = cmds.a3obTransferSkin

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return [0, 0]

    cmds.a3obTransferSkin = spy
    try:
        entry._transfer_skin()
        check("distance" not in seen,
              "the wrapper passed distance=%r when it should have omitted the flag"
              % seen.get("distance"))
        seen.clear()
        entry._transfer_skin(0.2)
        check(seen.get("distance") == 0.2,
              "an explicit distance was not forwarded: %r" % seen)
    finally:
        cmds.a3obTransferSkin = original


def main():
    for test in (test_the_result_is_a_pair,
                 test_element_zero_is_still_the_mesh_count,
                 test_a_detached_shell_is_counted,
                 test_a_fitted_shell_reports_zero,
                 test_the_ui_wrapper_returns_both_numbers,
                 test_the_wrapper_omits_the_distance_flag_when_none):
        test()
        print("ok:", test.__name__, flush=True)
    print("TRANSFER RIGID SHELLS: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
