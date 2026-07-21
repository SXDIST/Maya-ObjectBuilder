"""Installing must not delete the user's own files from the install root (mayapy).

_copy_runtime_package opened with `shutil.rmtree(target)`, and target is
<userAppDir>/MayaObjectBuilder — the SAME directory that holds references.default_directory()
and, on the author's machine, a `backups/` folder with an 899 KB weights backup written by no
code in this repo. Re-running the installer deleted all of it.

install_maya.py may import only the stdlib and maya.cmds, so it is loaded here by path rather
than imported as a package.

Run:  mayapy.exe tests/mayapy/installer_preserves_user_data.py
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import _harness

_harness.bootstrap()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_installer():
    """Load install_maya.py by path. It is a drag-into-Maya script, not an importable module."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "install", "install_maya.py")
    spec = importlib.util.spec_from_file_location("install_maya_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_package(source):
    """A minimal stand-in for an extracted release: the two runtime dirs with one file each."""
    for relative in ("plug-ins", "scripts"):
        os.makedirs(os.path.join(source, relative))
        with open(os.path.join(source, relative, "marker.txt"), "w") as handle:
            handle.write(relative)


def test_user_files_beside_the_runtime_dirs_survive():
    installer = load_installer()
    source = tempfile.mkdtemp()
    target = tempfile.mkdtemp()
    make_package(source)

    # The user's own data, in the same folder the installer targets.
    os.makedirs(os.path.join(target, "references"))
    with open(os.path.join(target, "references", "dayz_male_body.ma"), "w") as handle:
        handle.write("the user's customised body")
    os.makedirs(os.path.join(target, "backups"))
    with open(os.path.join(target, "backups", "weights.json"), "w") as handle:
        handle.write("{}")

    installer._copy_runtime_package(Path(source), Path(target))

    body = os.path.join(target, "references", "dayz_male_body.ma")
    check(os.path.isfile(body), "the user's saved reference was deleted by the installer")
    with open(body) as handle:
        check(handle.read() == "the user's customised body", "the saved reference was overwritten")
    check(os.path.isfile(os.path.join(target, "backups", "weights.json")),
          "the user's backups folder was deleted by the installer")


def test_the_runtime_dirs_are_still_replaced_wholesale():
    """The point of the rmtree was to drop files a previous version shipped and this one does
    not. That must survive the fix, or an upgrade leaves orphans behind."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    target = tempfile.mkdtemp()
    make_package(source)

    os.makedirs(os.path.join(target, "scripts"))
    with open(os.path.join(target, "scripts", "removed_last_version.py"), "w") as handle:
        handle.write("stale")

    installer._copy_runtime_package(Path(source), Path(target))

    check(not os.path.exists(os.path.join(target, "scripts", "removed_last_version.py")),
          "a stale file from a previous version survived the install")
    check(os.path.isfile(os.path.join(target, "scripts", "marker.txt")),
          "the new scripts/ was not copied")


def main():
    for test in (test_user_files_beside_the_runtime_dirs_survive,
                 test_the_runtime_dirs_are_still_replaced_wholesale):
        test()
        print("ok:", test.__name__, flush=True)
    print("INSTALLER PRESERVES USER DATA: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
