"""The resolver reports WHICH source found a texture, not just that one was found (mayapy).

The measured scene had MayaObjectBuilder_texture_root pointing at a directory that does not
exist, and textures displayed anyway because the chain falls through to P:/. The field stated
one source while another did the work, and nothing said so. The Preferences window has to be
able to say so, which means the resolver has to report it.

Restores the texture-root optionVar in a finally: it is the user's real configuration, and a
test that leaves it pointing at a deleted temp directory has changed their environment.

Run:  mayapy.exe tests/mayapy/texture_resolution_source.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.mayabridge.paatex import settings  # noqa: E402
from a3ob.mayabridge.paatex.resolve import (  # noqa: E402
    resolve_paa_path, resolve_paa_path_with_source)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_texture(directory, relative):
    path = os.path.join(directory, relative.replace("\\", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"\0")
    return path


def test_absolute_path_reports_absolute():
    root = tempfile.mkdtemp()
    path = make_texture(root, "direct_co.paa")
    resolved, source = resolve_paa_path_with_source(path)
    check(resolved == path, "resolved %r" % resolved)
    check(source == "absolute", "source is %r, expected 'absolute'" % source)


def test_a_hit_under_the_configured_root_reports_configured():
    root = tempfile.mkdtemp()
    make_texture(root, "mod\\data\\jacket_co.paa")
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("mod\\data\\jacket_co.paa")
    check(resolved is not None, "nothing resolved under the configured root")
    check(source == "configured", "source is %r, expected 'configured'" % source)


def test_a_basename_hit_reports_search():
    """The file exists under the root but NOT at the relative path — the bounded walk finds
    it. That is a materially different answer from a clean relative hit and must say so.

    The relative path below (``mod\\data\\qbz_fixture_co.paa``) is deliberately synthetic —
    not a plausible real DayZ asset name — and ``mod\\data\\`` does not exist under this
    machine's real P:/ drive either. Both the direct configured/drive candidate check AND the
    bounded search walk only ever look under the configured root, so this cannot collide with
    a real file living on P:/; but a plausible name (e.g. ``helmet_co.paa``) could plausibly
    exist for real on some machine's P:/, which would make the direct-candidate P:/ check hit
    before the search fallback ever runs, and report "drive" instead of "search" for a reason
    that has nothing to do with this test's logic.
    """
    root = tempfile.mkdtemp()
    make_texture(root, "somewhere\\else\\qbz_fixture_co.paa")
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("mod\\data\\qbz_fixture_co.paa")
    check(resolved is not None, "the basename search found nothing")
    check(source == "search", "source is %r, expected 'search'" % source)


def test_nothing_found_reports_an_empty_source():
    root = tempfile.mkdtemp()
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("mod\\data\\absent_co.paa")
    check(resolved is None, "resolved %r for a texture that does not exist" % resolved)
    check(source == "", "source is %r, expected ''" % source)


def test_a_configured_root_that_does_not_exist_is_not_reported_as_configured():
    """The exact situation from the measured scene. Whatever resolves it, it is not the
    configured root, and the caller must be able to tell."""
    settings.set_texture_root(os.path.join(tempfile.mkdtemp(), "gone"))
    _resolved, source = resolve_paa_path_with_source("mod\\data\\absent_co.paa")
    check(source != "configured",
          "a nonexistent configured root was reported as the resolving source")


def test_a_real_p_drive_hit_reports_drive():
    """This machine has a real P:/ — the brief requires this case be exercised rather than
    left untested when a drive is actually present. Keyed on a real file (P:/Core/black_co.paa)
    rather than writing into P:/, with the configured root pointed at an empty temp directory
    so the SAME relative path is absent there and only P:/ can be the source of the hit."""
    check(os.path.isdir("P:/"), "P:/ is expected to exist on this machine")
    check(os.path.isfile("P:/Core/black_co.paa"),
          "P:/Core/black_co.paa is expected to exist on this machine as a fixed reference point")
    root = tempfile.mkdtemp()  # empty: the relative path must NOT resolve here
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("Core/black_co.paa")
    check(resolved is not None, "the real P:/ file did not resolve")
    check(source == "drive", "source is %r, expected 'drive'" % source)


def test_the_old_entry_point_is_unchanged():
    """resolve_paa_path is on the import path. Its signature and answer must not move.

    Compared via os.path.normpath rather than raw string equality: the resolver builds its
    candidate with ``os.path.join(root, relative)`` where ``relative`` already has forward
    slashes, so on Windows the raw answer is a mixed-separator path (e.g.
    ``root\\mod/data/boots_co.paa``) — a real, pre-existing quirk of the untouched join logic,
    not something this task changed. It still names the same file; normpath is what makes that
    comparison honest instead of failing on formatting."""
    root = tempfile.mkdtemp()
    made = make_texture(root, "mod\\data\\boots_co.paa")
    settings.set_texture_root(root)
    expected = os.path.join(root, "mod", "data", "boots_co.paa")
    actual = resolve_paa_path("mod\\data\\boots_co.paa")
    check(os.path.normpath(actual) == os.path.normpath(expected)
          or os.path.normpath(actual) == os.path.normpath(made),
          "resolve_paa_path changed its answer: %r" % (actual,))
    check(resolve_paa_path("mod\\data\\absent_co.paa") is None,
          "resolve_paa_path should still return None when nothing resolves")


def main():
    previous = settings.texture_root()
    had_var = cmds.optionVar(exists=settings.TEXTURE_ROOT_VAR)
    try:
        tests = [test_absolute_path_reports_absolute,
                  test_a_hit_under_the_configured_root_reports_configured,
                  test_a_basename_hit_reports_search,
                  test_nothing_found_reports_an_empty_source,
                  test_a_configured_root_that_does_not_exist_is_not_reported_as_configured]
        if os.path.isdir("P:/"):
            tests.append(test_a_real_p_drive_hit_reports_drive)
        tests.append(test_the_old_entry_point_is_unchanged)
        for test in tests:
            test()
            print("ok:", test.__name__, flush=True)
    finally:
        if had_var:
            settings.set_texture_root(previous)
        else:
            cmds.optionVar(remove=settings.TEXTURE_ROOT_VAR)
    print("TEXTURE RESOLUTION SOURCE: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
