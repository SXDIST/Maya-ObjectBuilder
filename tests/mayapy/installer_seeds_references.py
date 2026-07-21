"""The installer seeds shipped reference assets without ever overwriting (mayapy).

_seed_reference_assets copies assets/references/*.ma from the release package into the
user's Maya folder and points the three reference optionVars at them, so *Add Male
Character* works immediately after installation with no prior save. Never overwrites: a
user who customised their body must not lose it to an upgrade, and a user whose optionVar
points somewhere else entirely must keep pointing there. An absent assets/references/
directory (a git clone, or a build with the assets pruned) is a normal state and must not
fail the install.

install_maya.py may import only the stdlib and maya.cmds, so it is loaded here by path,
reusing installer_preserves_user_data.py's load_installer() shape.

_seed_reference_assets calls _maya_documents_dir(), which reads the user's REAL Maya
folder via cmds.internalVar(userAppDir=True) — a Phase 3c test wrote a junk
dayz_skeleton.ma into exactly that directory by skipping this stub. Every test here
routes through a stubbed _maya_documents_dir pointed at tempfile.mkdtemp(), and the
three reference optionVars are snapshotted and restored in a finally, including the
case where an optionVar did not exist before.

Run:  mayapy.exe tests/mayapy/installer_seeds_references.py
"""

import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

# Duplicated from install/install_maya.py's own duplication of a3ob.mayabridge.references.KINDS —
# the test needs the optionVar names independently of the module under test, so it is
# pinned against the real source of truth instead, in test_reference_assets_match_kinds.
from a3ob.mayabridge.references import KINDS  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_installer():
    """Load install_maya.py by path. It is a drag-into-Maya script, not an importable module."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "install", "install_maya.py")
    spec = importlib.util.spec_from_file_location("install_maya_under_test_seed", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _StubbedDocumentsDir:
    """Redirect installer._maya_documents_dir() to a throwaway tempfile.mkdtemp() folder.

    Without this, _seed_reference_assets writes into the author's real
    ``.../Documents/maya`` — exactly the mistake a Phase 3c test made.
    """

    def __init__(self, installer):
        self._installer = installer
        self._original = installer._maya_documents_dir
        self.directory = Path(tempfile.mkdtemp(prefix="seed-refs-documents-"))

    def __enter__(self):
        self._installer._maya_documents_dir = lambda: self.directory
        return self.directory

    def __exit__(self, exc_type, exc_value, traceback):
        self._installer._maya_documents_dir = self._original


class _SavedOptionVars:
    """Snapshot/restore every reference optionVar, including the never-existed case."""

    def __init__(self, option_vars):
        self._snapshots = {}
        for option_var in option_vars:
            had = cmds.optionVar(exists=option_var)
            self._snapshots[option_var] = (had, cmds.optionVar(query=option_var) if had else None)

    def restore(self):
        for option_var, (had, value) in self._snapshots.items():
            if had:
                cmds.optionVar(stringValue=(option_var, value))
            else:
                cmds.optionVar(remove=option_var)


def make_shipped_assets(source, stems=("dayz_male_body", "dayz_skeleton"), contents="// shipped\n"):
    """A minimal stand-in for assets/references/ as it ships in a release package."""
    directory = Path(source) / "assets" / "references"
    directory.mkdir(parents=True)
    for stem in stems:
        (directory / f"{stem}.ma").write_text(contents, encoding="utf-8")
    return directory


def test_a_fresh_install_copies_the_shipped_assets():
    """Both .ma files land in <documents>/MayaObjectBuilder/references."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    make_shipped_assets(source)

    with _StubbedDocumentsDir(installer) as documents:
        installer._seed_reference_assets(Path(source))

        destination_dir = documents / installer.PLUGIN_NAME / "references"
        check((destination_dir / "dayz_male_body.ma").is_file(),
              "the male body reference was not copied into the destination directory")
        check((destination_dir / "dayz_skeleton.ma").is_file(),
              "the skeleton reference was not copied into the destination directory")


def test_the_optionvars_point_at_what_was_copied():
    """Add Male Character works immediately after installation — that is the whole point."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    shipped_stems = ("dayz_male_body", "dayz_skeleton")
    make_shipped_assets(source, stems=shipped_stems)

    with _StubbedDocumentsDir(installer) as documents:
        installer._seed_reference_assets(Path(source))

        destination_dir = documents / installer.PLUGIN_NAME / "references"

        # Skip based on what the FIXTURE shipped, not on whether the destination file
        # exists. Gating on "did the copy land" makes "was this kind shipped" and "did
        # _seed_reference_assets actually run" indistinguishable — if the function were
        # reverted to a no-op, every asset.is_file() would be False, every iteration would
        # `continue`, and this test would report success without calling check() once.
        checked_kinds = []
        for option_var, stem in installer.REFERENCE_ASSETS:
            if stem not in shipped_stems:
                continue
            asset = destination_dir / f"{stem}.ma"
            check(cmds.optionVar(exists=option_var),
                  "optionVar %r was never set" % option_var)
            configured = cmds.optionVar(query=option_var)
            check(configured == asset.as_posix(),
                  "optionVar %r points at %r, not the copied asset %r"
                  % (option_var, configured, asset.as_posix()))
            checked_kinds.append(stem)

        # Positive control: an assertion-free loop (every iteration `continue`-ing) must
        # not read as success. Without this, the checks above could ALL be skipped and the
        # test would still print "ok".
        check(checked_kinds == list(shipped_stems),
              "expected to check the %d shipped kinds %r, actually checked %r — the loop "
              "skipped every kind, which is exactly the vacuous-pass this test must catch"
              % (len(shipped_stems), list(shipped_stems), checked_kinds))


def test_a_reference_the_user_already_saved_is_never_overwritten():
    """The file's CONTENT must be unchanged, not merely present. Someone who customised their
    body must not lose it to an upgrade."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    make_shipped_assets(source, contents="// shipped default\n")

    with _StubbedDocumentsDir(installer) as documents:
        destination_dir = documents / installer.PLUGIN_NAME / "references"
        destination_dir.mkdir(parents=True)
        customised = destination_dir / "dayz_male_body.ma"
        customised.write_text("// the user's customised body\n", encoding="utf-8")

        installer._seed_reference_assets(Path(source))

        check(customised.read_text(encoding="utf-8") == "// the user's customised body\n",
              "the user's customised reference was overwritten by the shipped default")


def test_an_optionvar_the_user_already_set_is_left_alone():
    """A user pointing at a reference OUTSIDE the default directory must keep pointing there."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    make_shipped_assets(source)

    elsewhere = Path(tempfile.mkdtemp(prefix="seed-refs-elsewhere-")) / "my_own_body.ma"
    elsewhere.write_text("// a reference the user keeps somewhere else entirely\n", encoding="utf-8")
    option_var = dict((stem, var) for var, stem in installer.REFERENCE_ASSETS)["dayz_male_body"]
    cmds.optionVar(stringValue=(option_var, elsewhere.as_posix()))

    with _StubbedDocumentsDir(installer) as documents:
        installer._seed_reference_assets(Path(source))

        configured = cmds.optionVar(query=option_var)
        check(configured == elsewhere.as_posix(),
              "the user's own optionVar was repointed at the shipped default: now %r" % configured)


def test_an_optionvar_set_to_empty_or_a_stale_path_is_reseeded():
    """An empty-string optionVar and one pointing at a file that no longer exists both mean
    "not really configured" — the same two states references.reference_path() folds into ""
    (unsaved) elsewhere in the plugin. _seed_reference_assets must reseed in both cases, or a
    user whose optionVar happens to be "" (never explicitly saved) or whose reference file was
    moved/deleted would never get Add Male Character working again after an upgrade."""
    installer = load_installer()
    option_var = dict((stem, var) for var, stem in installer.REFERENCE_ASSETS)["dayz_male_body"]

    cases = (
        ("", "an empty string"),
        (str(Path(tempfile.mkdtemp(prefix="seed-refs-stale-")) / "deleted.ma"),
         "a path that no longer exists"),
    )
    for existing_value, label in cases:
        source = tempfile.mkdtemp()
        make_shipped_assets(source, stems=("dayz_male_body", "dayz_skeleton"))
        cmds.optionVar(stringValue=(option_var, existing_value))

        with _StubbedDocumentsDir(installer) as documents:
            installer._seed_reference_assets(Path(source))

            destination_dir = documents / installer.PLUGIN_NAME / "references"
            asset = destination_dir / "dayz_male_body.ma"
            configured = cmds.optionVar(query=option_var)
            check(configured == asset.as_posix(),
                  "optionVar left at %r (%s) instead of being reseeded to the copied asset %r"
                  % (configured, label, asset.as_posix()))


def test_a_missing_assets_directory_is_not_an_error():
    """A git clone without the assets must still install cleanly, writing nothing."""
    installer = load_installer()
    source = tempfile.mkdtemp()  # no assets/references/ at all

    with _StubbedDocumentsDir(installer) as documents:
        written = installer._seed_reference_assets(Path(source))

        check(written == [], "expected nothing to be written, got %r" % (written,))
        destination_dir = documents / installer.PLUGIN_NAME / "references"
        check(not destination_dir.exists(),
              "a destination directory was created even though assets/references/ is absent")


def test_a_kind_with_no_shipped_file_is_skipped():
    """female_body has no asset today and that is a normal state, not a failure."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    make_shipped_assets(source, stems=("dayz_male_body", "dayz_skeleton"))
    # dayz_female_body.ma deliberately absent, matching the repo's current assets/references/.

    female_option_var = dict((stem, var) for var, stem in installer.REFERENCE_ASSETS)["dayz_female_body"]

    with _StubbedDocumentsDir(installer) as documents:
        written = installer._seed_reference_assets(Path(source))

        destination_dir = documents / installer.PLUGIN_NAME / "references"
        check(not (destination_dir / "dayz_female_body.ma").exists(),
              "a female_body file appeared even though none was shipped")
        check(not any(path.name == "dayz_female_body.ma" for path in written),
              "the missing female_body kind was reported as written")
        check(not cmds.optionVar(exists=female_option_var),
              "the female_body optionVar was set even though no asset was shipped for it")


def test_reference_assets_match_kinds():
    """install_maya.py's REFERENCE_ASSETS is a deliberate duplicate of references.KINDS —
    guard both properties so the two cannot silently drift apart, the way
    REQUIRED_PACKAGE_FILES and package_release.ps1's $RequiredFiles did across a refactor."""
    installer = load_installer()

    expected = {(option_var, stem) for kind, (option_var, _name, stem) in KINDS.items()}
    actual = set(installer.REFERENCE_ASSETS)
    check(actual == expected,
          "install_maya.py's REFERENCE_ASSETS %r no longer matches "
          "a3ob.mayabridge.references.KINDS %r" % (actual, expected))


def _clear_option_vars(option_vars):
    """Reset every reference optionVar to "does not exist", matching a fresh install.

    Each test below asserts on optionVar state as it would be seen right after
    _seed_reference_assets runs. Without this, one test's real optionVar writes (they are
    real Maya optionVars, process-wide) leak into the next test in the same mayapy
    process and make its assertions depend on run order instead of on the code.
    """
    for option_var in option_vars:
        if cmds.optionVar(exists=option_var):
            cmds.optionVar(remove=option_var)


def main():
    installer = load_installer()
    option_vars = [option_var for option_var, _stem in installer.REFERENCE_ASSETS]
    saved = _SavedOptionVars(option_vars)

    try:
        for test in (test_a_fresh_install_copies_the_shipped_assets,
                     test_the_optionvars_point_at_what_was_copied,
                     test_a_reference_the_user_already_saved_is_never_overwritten,
                     test_an_optionvar_the_user_already_set_is_left_alone,
                     test_an_optionvar_set_to_empty_or_a_stale_path_is_reseeded,
                     test_a_missing_assets_directory_is_not_an_error,
                     test_a_kind_with_no_shipped_file_is_skipped,
                     test_reference_assets_match_kinds):
            _clear_option_vars(option_vars)
            test()
            print("ok:", test.__name__, flush=True)
    finally:
        saved.restore()

    print("INSTALLER SEEDS REFERENCES: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
