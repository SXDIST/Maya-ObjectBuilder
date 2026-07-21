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


class _DefaultReferenceDirectory:
    """Stub ``references.default_directory`` to a throwaway temp dir for the duration.

    _save_reference_asset passes store="1" (the ReferenceAssetCommand sentinel for "no
    explicit path yet") whenever a kind has no reference configured, and
    references.save_reference then resolves that sentinel through default_directory() —
    which is the user's REAL ``.../Documents/maya/MayaObjectBuilder/references`` folder.
    test_no_prompt_when_there_is_nothing_to_replace deliberately exercises exactly that
    "nothing configured yet" branch, so without this stub it writes the test's own
    fixture into the user's actual Maya data directory. references is a plain module, so
    patching the attribute here redirects every call the whole suite makes, and __exit__
    restores the real function so production behavior is unaffected once the test ends.
    """

    def __init__(self):
        self._original = references.default_directory
        self.directory = tempfile.mkdtemp(prefix="ref-default-dir-")

    def __enter__(self):
        references.default_directory = lambda: self.directory
        return self.directory

    def __exit__(self, exc_type, exc_value, traceback):
        references.default_directory = self._original


class _SavedOptionVar:
    """Snapshot/restore one optionVar around a test run.

    Every test in this file points the "skeleton" reference at a temp path via
    references.set_reference_path (directly, or through existing_reference()) and none
    of them restore it — left alone, a test run repoints
    MayaObjectBuilder_ref_skeleton at a path in the OS temp dir that no longer exists
    once the process exits, corrupting the user's real configuration. Mirrors the
    save/restore idiom tests/mayapy/skin_transfer.py already uses for
    MayaObjectBuilder_ref_male_body.
    """

    def __init__(self, option_var):
        self._option_var = option_var
        self._had = cmds.optionVar(exists=option_var)
        self._previous = cmds.optionVar(query=option_var) if self._had else ""

    def restore(self):
        if self._had:
            cmds.optionVar(stringValue=(self._option_var, self._previous))
        else:
            cmds.optionVar(remove=self._option_var)


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
    # Snapshot the REAL default directory before touching anything, not just whether it
    # exists: a user who has actually saved a reference already has files here, and the
    # guard must prove this run left them alone rather than merely that the folder is
    # still present.
    real_default_directory = references.default_directory()
    real_existed_before = os.path.isdir(real_default_directory)
    real_entries_before = set(os.listdir(real_default_directory)) if real_existed_before else set()

    option_var = references.KINDS["skeleton"][0]
    saved_option_var = _SavedOptionVar(option_var)

    try:
        with _DefaultReferenceDirectory() as stub_directory:
            for test in (test_declining_leaves_the_file_untouched,
                         test_the_prompt_names_the_file_it_would_replace,
                         test_accepting_writes_the_file,
                         test_no_prompt_when_there_is_nothing_to_replace,
                         test_nothing_selected_still_refuses_without_writing):
                test()
                print("ok:", test.__name__, flush=True)

            # test_no_prompt_when_there_is_nothing_to_replace routes through the
            # store="1" -> default_directory() branch, so proving THAT write landed in
            # the stub (not merely that the stub dir is untouched) is what shows the
            # sentinel path was actually exercised rather than skipped.
            check(os.path.isfile(os.path.join(stub_directory, "dayz_skeleton.ma")),
                  "the no-existing-reference branch never wrote into the stubbed "
                  "default directory — the sentinel path was not exercised")

        # The real point of the guard: nothing from this run may have reached the
        # user's actual Maya data directory, whether it was empty, missing, or already
        # holding the user's own real reference files.
        real_exists_after = os.path.isdir(real_default_directory)
        if real_existed_before:
            real_entries_after = set(os.listdir(real_default_directory))
            check(real_entries_after == real_entries_before,
                  "the user's real default directory %r changed during the test run: "
                  "had %r, now has %r"
                  % (real_default_directory, real_entries_before, real_entries_after))
        else:
            check(not real_exists_after,
                  "a reference was written into the user's real default directory: %r"
                  % real_default_directory)
    finally:
        saved_option_var.restore()

    print("REFERENCE OVERWRITE GUARD: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
