"""The dock reacts to scene changes through Maya callbacks, not a poll timer (run with mayapy).

Two things must hold:

* a scene change actually notifies the dock — otherwise panels go stale, which is what the
  500 ms poll was covering up;
* every callback is removed on teardown. A callback that outlives the dock fires into freed
  Python objects and takes Maya down with it, so this is the safety-critical half.

Run:  mayapy.exe tests/mayapy/scene_watch.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.watch import SceneWatcher, LODS, SELECTIONS  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    events = []
    watcher = SceneWatcher(lambda hints: events.append(tuple(hints)))
    watcher.start()

    # 1. Creating a transform must be reported.
    events.clear()
    transform = cmds.polyCube(name="watchLOD", ch=False)[0]
    check(any(LODS in hint for hint in events),
          "creating a transform must notify the LOD panel, got %r" % (events,))

    # 2. Creating an objectSet must be reported.
    events.clear()
    cmds.sets(empty=True, name="watchSet")
    check(any(SELECTIONS in hint for hint in events),
          "creating an objectSet must notify the Selections panel, got %r" % (events,))

    # 3. Editing an a3ob attribute on the watched LOD must be reported...
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    watcher.retarget(transform)
    events.clear()
    cmds.setAttr(transform + ".a3obLodType", 4)
    check(events, "editing an a3ob attribute must notify, got nothing")

    # ...while unrelated attributes must stay silent, or every viewport tumble wakes the UI.
    events.clear()
    cmds.setAttr(transform + ".translateX", 5.0)
    check(not events, "a non-a3ob attribute must not notify, got %r" % (events,))

    # 4. Teardown must remove every callback.
    watcher.stop()
    events.clear()
    cmds.polyCube(name="afterStop", ch=False)
    cmds.sets(empty=True, name="afterStopSet")
    cmds.setAttr(transform + ".a3obLodType", 7)
    check(not events,
          "no callback may survive stop(): got %r (this is the Maya-crash class)" % (events,))

    # stop() twice must be harmless — teardown can run from both hide and plugin unload.
    watcher.stop()

    print("OK scene callbacks fire on change and are fully removed on teardown")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL scene_watch: %s" % error, file=sys.stderr)
        raise
