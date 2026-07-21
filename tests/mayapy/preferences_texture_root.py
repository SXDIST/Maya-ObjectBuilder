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


def _make_textured_material(name, texture_value):
    """A minimal DayZ material fixture: a lambert shader carrying a3obTexture directly on the
    material node — the same schema/enumeration paatex/materials.py's assign_pending_textures
    and apply_alpha_transparency_setting already read (cmds.ls(materials=True) + a3obTexture on
    the shader itself), so scene_texture_source_report walks real production data shape."""
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    cmds.addAttr(shader, longName="a3obTexture", shortName="a3tx", dataType="string")
    cmds.setAttr(shader + ".a3obTexture", texture_value, type="string")
    return shader


def test_a_scene_with_no_textures_says_so_plainly():
    cmds.file(new=True, force=True)
    report = preferences.scene_texture_source_report()
    check(report["sampled"] == 0, "sampled %r, expected 0 for an untextured scene" % report["sampled"])
    check(report["sources"] == {}, "sources %r, expected empty" % report["sources"])
    check(report["message"], "an empty scene must still carry a message, not stay silent")
    check("no" in report["message"].lower(),
          "message %r does not plainly say there are no textures" % report["message"])


def test_a_single_resolving_source_is_named():
    cmds.file(new=True, force=True)
    root = tempfile.mkdtemp()
    relative = "mod\\data\\jacket_co.paa"
    full = os.path.join(root, "mod", "data", "jacket_co.paa")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as handle:
        handle.write(b"\0")
    settings.set_texture_root(root)
    _make_textured_material("singleSourceMat", relative)

    report = preferences.scene_texture_source_report()
    check(report["sampled"] == 1, "sampled %r, expected 1" % report["sampled"])
    check(report["sources"] == {"configured": 1},
          "sources %r, expected {'configured': 1}" % report["sources"])
    check("configured" in report["message"].lower(),
          "message %r does not name the configured root" % report["message"])


def test_a_configured_root_that_exists_is_not_assumed_to_be_in_use():
    """The motivating scenario the brief calls out: a configured root that EXISTS on disk is
    not evidence it is what actually resolved any texture. Root exists but the scene's only
    texture is an absolute path elsewhere, so the report must name 'absolute' and must NOT
    claim 'configured' just because the directory happens to be there."""
    cmds.file(new=True, force=True)
    root = tempfile.mkdtemp()  # exists, real, but has nothing matching in it
    settings.set_texture_root(root)
    elsewhere = tempfile.mkdtemp()
    absolute_path = os.path.join(elsewhere, "boots_co.paa")
    with open(absolute_path, "wb") as handle:
        handle.write(b"\0")
    _make_textured_material("elsewhereMat", absolute_path)

    check(os.path.isdir(root), "the configured root must actually exist for this scenario")
    report = preferences.scene_texture_source_report()
    check(report["sampled"] == 1, "sampled %r, expected 1" % report["sampled"])
    check(report["sources"] == {"absolute": 1},
          "sources %r — a configured root that merely exists must not be reported as the "
          "resolving source when it played no part" % report["sources"])
    check("configured" not in report["message"].lower(),
          "message %r wrongly implies the (existing but unused) configured root resolved "
          "this texture" % report["message"])


def test_multiple_sources_are_all_reported_not_just_one():
    cmds.file(new=True, force=True)
    root = tempfile.mkdtemp()
    relative = "mod\\data\\helmet_co.paa"
    full = os.path.join(root, "mod", "data", "helmet_co.paa")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as handle:
        handle.write(b"\0")
    settings.set_texture_root(root)
    _make_textured_material("configuredMat", relative)

    elsewhere = tempfile.mkdtemp()
    absolute_path = os.path.join(elsewhere, "gloves_co.paa")
    with open(absolute_path, "wb") as handle:
        handle.write(b"\0")
    _make_textured_material("absoluteMat", absolute_path)

    report = preferences.scene_texture_source_report()
    check(report["sampled"] == 2, "sampled %r, expected 2" % report["sampled"])
    check(set(report["sources"]) == {"configured", "absolute"},
          "sources %r, expected both configured and absolute" % report["sources"])
    check("configured" in report["message"].lower() and "absolute" in report["message"].lower(),
          "message %r must name every source found, not collapse to one" % report["message"])


def test_unresolved_textures_are_reported_not_silently_dropped():
    cmds.file(new=True, force=True)
    root = tempfile.mkdtemp()
    settings.set_texture_root(root)
    _make_textured_material("missingMat", "mod\\data\\definitely_absent_co.paa")

    report = preferences.scene_texture_source_report()
    check(report["sampled"] == 1, "sampled %r, expected 1" % report["sampled"])
    check(report["unresolved"] == 1, "unresolved %r, expected 1" % report["unresolved"])
    check(report["sources"] == {}, "sources %r, expected none resolved" % report["sources"])
    check("1" in report["message"], "message %r does not mention the unresolved texture" % report["message"])


def test_scanning_is_bounded():
    """Mirrors resolve.py's _WALK_DIR_LIMIT precedent: a scene with a great many shading
    engines must not be scanned unbounded. Temporarily lowers the module's own bound rather
    than creating hundreds of real materials — the limit is a plain module attribute so this
    is a legitimate way to exercise the bound deterministically and cheaply."""
    cmds.file(new=True, force=True)
    original_limit = preferences._SCENE_MATERIAL_LIMIT
    try:
        preferences._SCENE_MATERIAL_LIMIT = 2
        for index in range(3):
            _make_textured_material("boundedMat%d" % index, "mod\\data\\absent_co.paa")
        report = preferences.scene_texture_source_report()
        check(report["truncated"] is True, "truncated %r, expected True" % report["truncated"])
        check(report["sampled"] <= 2, "sampled %r exceeded the bound of 2" % report["sampled"])
        check("sampled" in report["message"].lower() or "first" in report["message"].lower(),
              "message %r does not note that scanning was truncated" % report["message"])
    finally:
        preferences._SCENE_MATERIAL_LIMIT = original_limit


def test_report_is_a_silent_read():
    """No warnings, no writes — this is a query the window can call on open and on an
    explicit refresh, never on a timer or on every selection event."""
    cmds.file(new=True, force=True)
    root = tempfile.mkdtemp()
    settings.set_texture_root(root)
    _make_textured_material("silentReadMat", "mod\\data\\absent_co.paa")
    path = os.path.join(tempfile.gettempdir(), "preferences_silent_read.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii")
    check(not cmds.file(query=True, modified=True), "scene must be clean right after saving")

    preferences.scene_texture_source_report()
    preferences.scene_texture_source_report()

    check(not cmds.file(query=True, modified=True),
          "scene_texture_source_report must be a silent read and must not dirty the scene")


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
            test_a_scene_with_no_textures_says_so_plainly,
            test_a_single_resolving_source_is_named,
            test_a_configured_root_that_exists_is_not_assumed_to_be_in_use,
            test_multiple_sources_are_all_reported_not_just_one,
            test_unresolved_textures_are_reported_not_silently_dropped,
            test_scanning_is_bounded,
            test_report_is_a_silent_read,
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
