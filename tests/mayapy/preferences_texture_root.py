"""The Preferences window's testable seams: texture-root status and the alpha default (mayapy).

The window itself (preferences.show_preferences) is a real QDialog and is NOT built here — a
QWidget under mayapy segfaults with no traceback unless a QApplication existed before
maya.standalone.initialize() ran, and this suite deliberately does not create one for a plain
seam test. texture_root_status() and resolution_source_label() exist precisely so the window's
logic can be tested without ever instantiating it.

Restores BOTH MayaObjectBuilder_texture_root and MayaObjectBuilder_paa_alpha_transparency in a
finally, including the "did not exist before" case: a Phase 3c test shipped without this and
changed the author's real configuration.

Run:  mayapy.exe tests/mayapy/preferences_texture_root.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.mayabridge.paatex import settings  # noqa: E402
from a3ob.ui import preferences  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_an_unset_root_is_reported_as_unset():
    cmds.optionVar(remove=settings.TEXTURE_ROOT_VAR)
    status = preferences.texture_root_status()
    check(status["root"] == "", "root %r, expected ''" % status["root"])
    check(status["exists"] is False, "exists %r, expected False" % status["exists"])
    check(status["message"], "an unset root must still carry a message, not stay silent")


def test_a_configured_root_that_exists_is_reported_as_present():
    root = tempfile.mkdtemp()
    settings.set_texture_root(root)
    status = preferences.texture_root_status()
    check(status["root"] == root, "root %r, expected %r" % (status["root"], root))
    check(status["exists"] is True, "exists %r, expected True for a real directory" % status["exists"])
    check(root in status["message"], "message %r does not name the configured root" % status["message"])


def test_a_configured_root_that_does_NOT_exist_says_so():
    """The measured scene's exact state. The message must name the problem, not stay silent."""
    root = os.path.join(tempfile.mkdtemp(), "does_not_exist")
    settings.set_texture_root(root)
    status = preferences.texture_root_status()
    check(status["root"] == root, "root %r, expected %r" % (status["root"], root))
    check(status["exists"] is False, "exists %r, expected False for a missing directory" % status["exists"])
    check(root in status["message"],
          "message %r does not name the missing root — it must not stay silent" % status["message"])
    check("not" in status["message"].lower() or "does not exist" in status["message"].lower()
          or "missing" in status["message"].lower(),
          "message %r does not describe the problem" % status["message"])


def test_alpha_transparency_defaults_to_off():
    """A DayZ _ca alpha is often a data channel; on by default makes solid armour see-through."""
    cmds.optionVar(remove=settings.ALPHA_VAR)
    check(settings.alpha_transparency_enabled() is False,
          "alpha transparency must default to OFF")


def test_toggling_alpha_transparency_round_trips():
    settings.set_alpha_transparency(True)
    check(settings.alpha_transparency_enabled() is True, "did not turn on")
    settings.set_alpha_transparency(False)
    check(settings.alpha_transparency_enabled() is False, "did not turn back off")


def test_resolution_source_label_names_the_source():
    root = tempfile.mkdtemp()
    relative = "mod\\data\\jacket_co.paa"
    full = os.path.join(root, "mod", "data", "jacket_co.paa")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as handle:
        handle.write(b"\0")
    settings.set_texture_root(root)
    label = preferences.resolution_source_label(relative)
    check(isinstance(label, str) and label, "resolution_source_label returned %r" % (label,))
    check("configured" in label.lower(),
          "label %r does not name the configured root as the source" % label)


def test_resolution_source_label_says_not_found():
    root = tempfile.mkdtemp()
    settings.set_texture_root(root)
    label = preferences.resolution_source_label("mod\\data\\absent_co.paa")
    check(isinstance(label, str) and label, "resolution_source_label returned %r" % (label,))
    check("not found" in label.lower() or "nothing" in label.lower(),
          "label %r does not say the texture was not found" % label)


def main():
    previous_root = settings.texture_root()
    had_root_var = cmds.optionVar(exists=settings.TEXTURE_ROOT_VAR)
    previous_alpha = settings.alpha_transparency_enabled()
    had_alpha_var = cmds.optionVar(exists=settings.ALPHA_VAR)
    try:
        tests = [
            test_an_unset_root_is_reported_as_unset,
            test_a_configured_root_that_exists_is_reported_as_present,
            test_a_configured_root_that_does_NOT_exist_says_so,
            test_alpha_transparency_defaults_to_off,
            test_toggling_alpha_transparency_round_trips,
            test_resolution_source_label_names_the_source,
            test_resolution_source_label_says_not_found,
        ]
        for test in tests:
            test()
            print("ok:", test.__name__, flush=True)
    finally:
        if had_root_var:
            settings.set_texture_root(previous_root)
        else:
            cmds.optionVar(remove=settings.TEXTURE_ROOT_VAR)
        if had_alpha_var:
            settings.set_alpha_transparency(previous_alpha)
        else:
            cmds.optionVar(remove=settings.ALPHA_VAR)
    print("PREFERENCES TEXTURE ROOT: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
