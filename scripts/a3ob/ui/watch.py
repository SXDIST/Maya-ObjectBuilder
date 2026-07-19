"""Scene change notifications for the dock — Maya callbacks instead of polling.

The dock used to run a 500 ms timer that rebuilt a snapshot of the scene and compared it
with the previous one. That burns CPU forever even when nothing happens, and still reacts up
to half a second late. Maya's own mechanism is a callback: OpenMaya tells us the moment a
node is added, removed or edited, so the dock does exactly zero work while the scene is idle.

Two rules this module exists to enforce:

* every registered callback id is remembered and removed again in ``stop()`` — a callback
  that outlives the plugin fires into freed Python objects and takes Maya down with it;
* callbacks report *what kind* of thing changed and never touch the UI directly, because
  they run inside Maya's evaluation. The dock coalesces them through its debounce timer.
"""

import maya.api.OpenMaya as om

# Panel hints handed to the change listener.
LODS = "LODs"
SELECTIONS = "Selections"
MATERIALS = "Materials"
NAMED = "Named Properties"

ALL_PANELS = (LODS, SELECTIONS, MATERIALS, NAMED)


class SceneWatcher:
    """Registers Maya callbacks and forwards them as panel hints.

    ``on_change(hints)`` is called with a tuple of panel names that may need refreshing. It
    must be cheap and must not raise — it runs inside Maya's callback."""

    def __init__(self, on_change):
        self._on_change = on_change
        self._global_ids = []   # node added/removed — live for the whole session
        self._node_ids = []     # attribute/topology watches on the current LOD

    # -- lifecycle ------------------------------------------------------------

    def start(self):
        if self._global_ids:
            return
        self._global_ids.append(
            om.MDGMessage.addNodeAddedCallback(self._node_added_removed, "objectSet"))
        self._global_ids.append(
            om.MDGMessage.addNodeRemovedCallback(self._node_added_removed, "objectSet"))
        self._global_ids.append(
            om.MDGMessage.addNodeAddedCallback(self._transform_changed, "transform"))
        self._global_ids.append(
            om.MDGMessage.addNodeRemovedCallback(self._transform_changed, "transform"))

    def stop(self):
        self.retarget(None)
        self._remove(self._global_ids)

    @staticmethod
    def _remove(ids):
        while ids:
            try:
                om.MMessage.removeCallback(ids.pop())
            except Exception:  # noqa: BLE001 - already gone, or Maya is tearing down
                pass

    # -- per-LOD watches ------------------------------------------------------

    def retarget(self, lod_name):
        """Watch the attributes and geometry of the LOD the dock is currently showing.

        Attribute edits only matter for the node on screen, so one watch is re-pointed rather
        than registering a callback per node in the scene."""
        self._remove(self._node_ids)
        if not lod_name:
            return
        try:
            selection = om.MSelectionList()
            selection.add(lod_name)
            node = selection.getDependNode(0)
        except Exception:  # noqa: BLE001 - node vanished between selection and here
            return

        try:
            self._node_ids.append(
                om.MNodeMessage.addAttributeChangedCallback(node, self._attribute_changed))
        except Exception:  # noqa: BLE001
            pass

        # Topology edits change the LOD list's triangle counts; nothing else reports them.
        try:
            dag = om.MFnDagNode(node)
            for i in range(dag.childCount()):
                child = dag.child(i)
                if child.hasFn(om.MFn.kMesh):
                    self._node_ids.append(
                        om.MPolyMessage.addPolyTopologyChangedCallback(child, self._topology_changed))
        except Exception:  # noqa: BLE001
            pass

    # -- callbacks ------------------------------------------------------------

    def _notify(self, *hints):
        try:
            self._on_change(hints)
        except Exception:  # noqa: BLE001 - never let UI trouble escape into Maya's callback
            pass

    def _node_added_removed(self, node, _data=None):
        self._notify(SELECTIONS, LODS)

    def _transform_changed(self, node, _data=None):
        self._notify(LODS)

    def _attribute_changed(self, msg, plug, _other_plug=None, _data=None):
        if not (msg & (om.MNodeMessage.kAttributeSet | om.MNodeMessage.kAttributeAdded
                       | om.MNodeMessage.kAttributeRemoved)):
            return
        name = plug.partialName(useLongNames=True)
        if not name.startswith("a3ob"):
            return
        self._notify(LODS, NAMED, MATERIALS, SELECTIONS)

    def _topology_changed(self, _node, _data=None):
        self._notify(LODS)


__all__ = [
    "SceneWatcher",
    "LODS",
    "SELECTIONS",
    "MATERIALS",
    "NAMED",
    "ALL_PANELS",
]
