"""Shared bootstrap and assertions for the mayapy workflow tests.

Under ``mayapy tests/mayapy/foo.py`` Python puts ``tests/mayapy/`` itself on
``sys.path[0]``, so ``import _harness`` works with no path setup at all — which is
why every test can open with just::

    import _harness

    _harness.bootstrap()

    import maya.cmds as cmds

``bootstrap()`` is what puts ``scripts/`` on the path and initializes Maya, so it
has to run before any ``maya.cmds`` import.
"""

import os
import sys

# tests/mayapy/_harness.py -> tests/mayapy -> tests -> repo root
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(REPO, "scripts")
PLUGIN = os.path.join(REPO, "plug-ins", "MayaObjectBuilder.py")

_initialized = False


def bootstrap():
    """Put ``scripts/`` on the path and start Maya standalone. Idempotent."""
    global _initialized
    # Fail loudly on a bad repo root. This repo is usually also registered as a Maya
    # module (dev_install), so `import a3ob` resolves through MAYA_MODULE_PATH even
    # when SCRIPTS is wrong — which silently tests whatever Maya found instead of the
    # working copy. An off-by-one dirname here did exactly that and went unnoticed.
    for required in (SCRIPTS, PLUGIN):
        if not os.path.exists(required):
            raise RuntimeError(
                "harness resolved the repo root to %r, but %r does not exist"
                % (REPO, required))
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    if not _initialized:
        import maya.standalone

        maya.standalone.initialize()
        _initialized = True


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_plugin():
    import maya.cmds as cmds

    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)
    return PLUGIN


def make_lod(name, kind="cube", lod_type=None, resolution=None, subdivisions=20):
    """A transform marked as a LOD by hand.

    Deliberately does NOT go through ``a3obCreateLOD``: these tests need a LOD that
    exists regardless of whether the command works, so that a broken command fails
    the assertion rather than the fixture.
    """
    import maya.cmds as cmds

    if kind == "sphere":
        transform = cmds.polySphere(name=name, subdivisionsX=subdivisions,
                                    subdivisionsY=subdivisions, ch=False)[0]
    else:
        transform = cmds.polyCube(name=name, ch=False)[0]

    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    if lod_type is not None:
        cmds.setAttr(transform + ".a3obLodType", lod_type)
    if resolution is not None:
        cmds.setAttr(transform + ".a3obResolution", resolution)
    return transform


def _built_active_dock():
    """Build a real dock and register it as the entry module's active dock.

    ``_active_qt_dock()`` is defined in ``a3ob.ui.entry`` and reads the module-level
    ``_qt_dock_widget`` global. Every action module star-imports the FUNCTION, but a
    function's globals stay bound to the module it was defined in — so setting
    ``entry._qt_dock_widget`` here is visible to ``_active_qt_dock()`` no matter which
    module calls it. ``_build_qt_dock(control)`` cannot be used outside interactive
    Maya: it requires a real workspaceControl to parent into, which does not exist
    under mayapy's batch mode.

    Pair every call with :func:`release_active_dock` — a dock left with its Maya
    callbacks attached is the exit-time crash class ``entry._delete_qt_dock``
    documents.

    Qt is imported here rather than at module scope on purpose: ``_harness`` is
    imported by every mayapy test, including ones that must never build a widget.
    """
    from PySide6 import QtWidgets

    # A real QWidget needs a full QApplication that existed BEFORE
    # maya.standalone.initialize() ran — Maya's bring-up otherwise leaves a bare
    # QGuiApplication behind and constructing a QWidget against it segfaults the
    # process with no Python traceback at all. bootstrap() deliberately does not
    # create one (that would drag Qt into every non-widget test), so the calling
    # test file must, in its header, before `import _harness`. Turn the segfault
    # into a message.
    app = QtWidgets.QApplication.instance()
    if not isinstance(app, QtWidgets.QApplication):
        raise RuntimeError(
            "no QtWidgets.QApplication exists (found %r) — a widget test must create "
            "one in its header BEFORE _harness.bootstrap(), or building the dock "
            "segfaults with no traceback" % (app,))

    from a3ob.ui import entry
    from a3ob.ui.dock import MayaObjectBuilderDock

    dock = MayaObjectBuilderDock()
    dock.show()  # _active_qt_dock() rejects a hidden widget
    entry._qt_dock_widget = dock
    return dock


def _release_active_dock(dock):
    """Tear a test dock down the way ``entry._delete_qt_dock`` does.

    ``teardown()`` first, and not optional: it stops the debounce timer and the
    scene-change watcher. A Maya callback that outlives its widget fires into freed
    Python objects — and in this suite a segfault produces no traceback at all, so a
    test that skipped this would keep passing while accumulating the crash state.
    """
    from a3ob.ui import entry

    if dock is not None:
        dock.teardown()
        dock.setParent(None)
        dock.close()
        dock.deleteLater()
    entry._qt_dock_widget = None


def name_of(result):
    """Unwrap an MPxCommand result.

    Under mayapy standalone an API 2.0 ``setResult`` comes back from ``cmds`` as a
    1-element list, unlike the former C++ plugin's scalar string.
    """
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


def run(main):
    """Run a test's ``main`` and turn it into a process exit code.

    Unifies the two conventions the suite grew: some tests called ``main()`` and
    then ``sys.exit(0)``, others ``sys.exit(main())``. A failure prints
    ``FAIL <test>: <error>`` to stderr so the runner can attribute it.
    """
    test = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    try:
        return main() or 0
    except Exception as error:  # noqa: BLE001 - the runner reports, the traceback follows
        print("FAIL %s: %s" % (test, error), file=sys.stderr)
        raise
