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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
PLUGIN = os.path.join(REPO, "plug-ins", "MayaObjectBuilder.py")

_initialized = False


def bootstrap():
    """Put ``scripts/`` on the path and start Maya standalone. Idempotent."""
    global _initialized
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
