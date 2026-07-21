"""The release manifest has two hardcoded twins that must both match the repo.

``install/install_maya.py``'s ``REQUIRED_PACKAGE_FILES`` and
``tools/package_release.ps1``'s ``$RequiredFiles`` each list the same set of files a
release must contain, and ``install_maya.py``'s ``_validate_package()`` refuses to
install a package missing any of them. Commit 6d824ea moved
``scripts/a3ob/ui/autolod/`` to ``scripts/a3ob/mayabridge/autolod/`` and only the
PowerShell list was updated (092dc0b) — the Python list kept naming the old path,
so ``_validate_package()`` would refuse EVERY install built from that state
(``RuntimeError("Release package is incomplete. Missing: ...")``).

Nothing checked that either list still matched the repo, or that the two lists
matched each other. This guards both properties so a future move of any of these
files fails a test immediately instead of surviving a refactor, a packaging run,
and a review, the way this one did.

install_maya.py may import only the stdlib and maya.cmds, so it is loaded here by
path, mirroring installer_preserves_user_data.py's load_installer().

Run:  mayapy.exe tests/mayapy/release_manifest_matches_repo.py
"""

import importlib.util
import os
import re
import sys

import _harness

_harness.bootstrap()

REPO_ROOT = _harness.REPO
PS1_PATH = os.path.join(REPO_ROOT, "tools", "package_release.ps1")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_installer():
    """Load install_maya.py by path. It is a drag-into-Maya script, not an importable module."""
    path = os.path.join(REPO_ROOT, "install", "install_maya.py")
    spec = importlib.util.spec_from_file_location("install_maya_under_test_manifest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def python_required_files():
    """REQUIRED_PACKAGE_FILES as repo-relative, forward-slash strings."""
    installer = load_installer()
    return [p.as_posix() for p in installer.REQUIRED_PACKAGE_FILES]


def extract_powershell_required_files(text):
    """Pull the quoted paths out of ``$RequiredFiles = @( ... )`` in package_release.ps1.

    This is regex-scraping of PowerShell, not a real parser — deliberately: the
    array is a flat list of quoted string literals with no nesting, no variable
    interpolation, and no expressions, so a parser would buy nothing a regex
    doesn't already give. What matters is that this CANNOT silently match
    nothing: test_parser_rejects_a_deliberately_wrong_path below proves the
    extraction + existence check actually goes red when a listed file does not
    exist, and test_powershell_list_is_non_empty below guards against the block
    itself failing to match (e.g. after someone reformats the .ps1) and this
    whole file passing vacuously with an empty list.
    """
    block_match = re.search(r"\$RequiredFiles\s*=\s*@\((.*?)\)", text, re.DOTALL)
    check(block_match is not None,
          "could not find a $RequiredFiles = @( ... ) block in package_release.ps1 — "
          "the packager's manifest format changed and this scraper needs updating")
    block = block_match.group(1)
    return re.findall(r'"([^"]+)"', block)


def check_files_exist(root, relative_posix_paths, source_label):
    missing = [rel for rel in relative_posix_paths
               if not os.path.exists(os.path.join(root, *rel.split("/")))]
    check(not missing,
          "%s lists file(s) that do not exist in the repo: %s" % (source_label, missing))


def test_python_required_files_exist_in_repo():
    check_files_exist(REPO_ROOT, python_required_files(), "install_maya.py REQUIRED_PACKAGE_FILES")


def test_powershell_required_files_exist_in_repo():
    with open(PS1_PATH, "r") as handle:
        text = handle.read()
    ps1_files = extract_powershell_required_files(text)
    check_files_exist(REPO_ROOT, ps1_files, "package_release.ps1 $RequiredFiles")


def test_powershell_list_is_non_empty():
    """A guard against the regex itself going silently blind (see docstring above)."""
    with open(PS1_PATH, "r") as handle:
        text = handle.read()
    ps1_files = extract_powershell_required_files(text)
    check(len(ps1_files) >= 10,
          "extracted only %d entries from $RequiredFiles — the scraper likely stopped "
          "matching the real array and this test would pass vacuously" % len(ps1_files))


def test_python_and_powershell_lists_agree():
    """The property that actually broke: the two twin lists must name the same files."""
    py_files = set(python_required_files())
    with open(PS1_PATH, "r") as handle:
        text = handle.read()
    ps1_files = set(extract_powershell_required_files(text))

    only_in_python = sorted(py_files - ps1_files)
    only_in_powershell = sorted(ps1_files - py_files)
    check(not only_in_python and not only_in_powershell,
          "install_maya.py REQUIRED_PACKAGE_FILES and package_release.ps1 $RequiredFiles "
          "disagree — only in install_maya.py: %s; only in package_release.ps1: %s"
          % (only_in_python, only_in_powershell))


def test_parser_rejects_a_deliberately_wrong_path():
    """Prove the guard can actually fail: point it at a manifest naming a bogus file."""
    fabricated = '$RequiredFiles = @(\n    "scripts/this_file_does_not_exist_xyz.py"\n)\n'
    bogus_files = extract_powershell_required_files(fabricated)
    check(bogus_files == ["scripts/this_file_does_not_exist_xyz.py"],
          "sanity check on the extractor itself failed: got %r" % (bogus_files,))
    raised = False
    try:
        check_files_exist(REPO_ROOT, bogus_files, "fabricated manifest")
    except AssertionError:
        raised = True
    check(raised, "check_files_exist() did NOT raise for a path that does not exist on "
                  "disk — the guard would pass vacuously on a real stale entry")


def main():
    for test in (test_python_required_files_exist_in_repo,
                 test_powershell_required_files_exist_in_repo,
                 test_powershell_list_is_non_empty,
                 test_python_and_powershell_lists_agree,
                 test_parser_rejects_a_deliberately_wrong_path):
        test()
        print("ok:", test.__name__, flush=True)
    print("RELEASE MANIFEST MATCHES REPO: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
