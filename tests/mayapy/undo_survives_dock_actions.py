"""After dock actions that suppress undo, the caller's undo state must be unchanged.

Regression for four undoInfo blocks in entry.py that were exactly backwards:

    cmds.undoInfo(stateWithoutFlush=True)   # was: ENABLES undo (no-op when already on)
    try:
        cmds.a3obValidate(...)
    finally:
        cmds.undoInfo(stateWithoutFlush=False)  # was: DISABLES it — permanently

Clicking "Validate" in the dock, or the Validation panel's automatic refresh on every
selection change, silently killed Ctrl+Z for the rest of the session.

The fix: capture the prior state, disable undo for the body, restore in finally.

Run:  mayapy.exe tests/mayapy/undo_survives_dock_actions.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402 - after bootstrap()

# entry.py imports _qt which guards against missing PySide6; safe under mayapy.
from a3ob.ui import entry  # noqa: E402


def _attr_or(node, attr, default):
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return default
    return cmds.getAttr(node + "." + attr)


def test_run_validation_leaves_undo_state_unchanged():
    """_run_validation must not alter the caller's undo state.

    This is the path the dock's Validation panel hits on every selection change, and
    also the Quick Action "Validate" button (dock.py ~line 255)."""
    cmds.file(new=True, force=True)
    # entry.load_plugin() resolves the path correctly from entry.py's own __file__,
    # and is idempotent when the plugin is already loaded.
    entry.load_plugin()
    # mayapy starts with undo disabled; enable it explicitly — that is the state a user
    # session is always in, and is what the test is asserting survives.
    cmds.undoInfo(state=True, infinity=True)

    # Put a real undoable action on the queue so we can verify Ctrl+Z still reaches it.
    lod = _harness.make_lod("validateUndoLOD")
    cmds.select(lod, replace=True)
    cmds.a3obSetMass(value=3.0)
    mass_after_set = _attr_or(lod, "a3obMassValues", "")
    _harness.check(mass_after_set, "a3obSetMass must write a3obMassValues before the test is meaningful")

    # The Validation panel calls this on every selection change.
    entry._run_validation(False)

    # --- the assertion that fails against the unfixed code ---
    state_after = cmds.undoInfo(query=True, state=True)
    _harness.check(
        state_after,
        "_run_validation left undo state=%r; the finally block turned undo off "
        "(expected True — the state before the call)" % state_after,
    )

    # Undo must still be functional: the mass assignment must be reversible.
    cmds.undo()
    mass_after_undo = _attr_or(lod, "a3obMassValues", "")
    _harness.check(
        mass_after_undo != mass_after_set,
        "cmds.undo() did not revert the mass (undo queue was killed); "
        "before=%r after_undo=%r" % (mass_after_set, mass_after_undo),
    )

    print("OK _run_validation leaves undo state unchanged and undo queue intact")


def test_validate_scene_no_flush_leaves_undo_state_unchanged():
    """_validate_scene_no_flush has the same bug pattern; test it separately."""
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)

    lod = _harness.make_lod("sceneValidateUndoLOD")
    cmds.select(lod, replace=True)
    cmds.a3obSetMass(value=4.0)

    entry._validate_scene_no_flush()

    state_after = cmds.undoInfo(query=True, state=True)
    _harness.check(
        state_after,
        "_validate_scene_no_flush left undo state=%r (expected True)" % state_after,
    )
    print("OK _validate_scene_no_flush leaves undo state unchanged")


def test_undo_disabled_caller_stays_disabled():
    """If the caller had undo OFF, the functions must leave it OFF — not silently enable it.

    Hardcoding True in the restore would break batch-mode callers that run with undo
    intentionally disabled."""
    cmds.file(new=True, force=True)
    # Put undo in the off state to simulate a batch / non-interactive caller.
    cmds.undoInfo(stateWithoutFlush=False)
    _harness.check(not cmds.undoInfo(query=True, state=True), "fixture: undo must be off")

    entry._run_validation(False)

    state_after = cmds.undoInfo(query=True, state=True)
    _harness.check(
        not state_after,
        "_run_validation must not re-enable undo when the caller had it off; "
        "got state=%r" % state_after,
    )
    print("OK _run_validation respects a caller that had undo disabled")


def main():
    test_run_validation_leaves_undo_state_unchanged()
    test_validate_scene_no_flush_leaves_undo_state_unchanged()
    test_undo_disabled_caller_stays_disabled()
    print("undo_survives_dock_actions: OK")
    return 0


if __name__ == "__main__":
    _harness.run(main)
