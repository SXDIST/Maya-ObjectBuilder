from pathlib import Path
import runpy


INSTALLER_FILE = "install_maya.py"


def _installer_path():
    return Path(__file__).resolve().with_name(INSTALLER_FILE)


def _run_installer():
    installer = _installer_path()
    if not installer.exists():
        raise RuntimeError(f"Missing installer implementation: {installer}")
    namespace = runpy.run_path(str(installer), init_globals={"INSTALLER_PATH": str(installer)})
    runner = namespace.get("_run") or namespace.get("install")
    if runner is None:
        raise RuntimeError(f"Installer implementation does not define _run() or install(): {installer}")
    runner()


def onMayaDroppedPythonFile(*_):
    _run_installer()


if globals().get("__name__") in (None, "__main__"):
    _run_installer()
