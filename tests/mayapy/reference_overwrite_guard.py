"""Saving over an existing reference asset asks first (mayapy).

references.save_reference exports with force=True and no confirmation, so a wrong selection
plus one click silently replaces a reference the user may have spent real work on. Phase 3c
moves the save actions off the panel and into a menu submenu; the guard is what makes that
move a safety improvement rather than just a relocation.

The confirmation lives in the UI wrapper, not in references.py: mayabridge must never import
from a3ob.ui, and a dialog in the scene layer would be exactly that.

Run:  mayapy.exe tests/mayapy/reference_overwrite_guard.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

_harness.load_plugin()

from a3ob.mayabridge import references  # noqa: E402
from a3ob.ui import entry  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def scene_with_a_joint():
    cmds.file(new=True, force=True)
    joint = cmds.joint(name="Pelvis", position=(0, 0, 0))
    cmds.select(joint, replace=True)
    return joint


def existing_reference(tmpdir, contents="// placeholder\n"):
    path = os.path.join(tmpdir, "dayz_skeleton.ma")
    with open(path, "w") as handle:
        handle.write(contents)
    references.set_reference_path("skeleton", path)
    return path


class _Answer:
    """Stand in for cmds.confirmDialog, recording what it was asked."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def test_declining_leaves_the_file_untouched():
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    path = existing_reference(tmpdir, "// original\n")

    answer = _Answer("Cancel")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        saved = entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(answer.calls, "no confirmation was shown before overwriting")
    check(saved is False, "declining should report that nothing was saved, got %r" % saved)
    with open(path) as handle:
        check(handle.read() == "// original\n", "the reference was overwritten after declining")


def test_the_prompt_names_the_file_it_would_replace():
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    path = existing_reference(tmpdir)

    answer = _Answer("Cancel")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    message = " ".join(str(call["message"]) for call in answer.calls if "message" in call)
    check(os.path.basename(path) in message,
          "the prompt's message does not name the file it would replace: %r" % message)


def test_accepting_writes_the_file():
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    path = existing_reference(tmpdir, "// original\n")

    answer = _Answer("Replace")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        saved = entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(saved is True, "accepting should report a save, got %r" % saved)
    with open(path) as handle:
        check(handle.read() != "// original\n", "the reference was not written after accepting")


def test_no_prompt_when_there_is_nothing_to_replace():
    """A first save must not ask — there is no work to lose."""
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    references.set_reference_path("skeleton", os.path.join(tmpdir, "not_there_yet.ma"))

    answer = _Answer("Cancel")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(not answer.calls,
          "a confirmation was shown even though no existing file would be replaced")


def test_nothing_selected_still_refuses_without_writing():
    """The existing clear error must survive the new guard."""
    tmpdir = tempfile.mkdtemp()
    cmds.file(new=True, force=True)
    cmds.select(clear=True)
    path = existing_reference(tmpdir, "// original\n")

    answer = _Answer("Replace")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        saved = entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(saved is False,
          "an empty selection must report that nothing was saved, got %r" % saved)
    with open(path) as handle:
        check(handle.read() == "// original\n",
              "an empty selection overwrote the reference")


def main():
    for test in (test_declining_leaves_the_file_untouched,
                 test_the_prompt_names_the_file_it_would_replace,
                 test_accepting_writes_the_file,
                 test_no_prompt_when_there_is_nothing_to_replace,
                 test_nothing_selected_still_refuses_without_writing):
        test()
        print("ok:", test.__name__, flush=True)
    print("REFERENCE OVERWRITE GUARD: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
