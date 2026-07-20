"""Finding the LOD transform a DAG path belongs to (OpenMaya 2.0).

The same upward walk was written out twice on the Maya-API side — once in
``commands.helpers.scene`` returning an MObject, once in ``export.parse`` returning an
MDagPath — and the two packages have no dependency edge between them, so neither could
simply call the other. It lives here instead, below both.

The two copies were verified equivalent before being collapsed: both stop at the FIRST
ancestor carrying ``a3obIsLOD`` (a LOD nested under another LOD belongs to itself), both
require the carrier to be a transform, and both stop before testing the world node. The one
real difference was that ``commands.helpers.scene`` walked MObjects via ``parent(0)`` — the
first parent, which is instance-blind — while the export copy popped the MDagPath, following
the instance actually selected. The MDagPath walk is the correct one and is what survived.
"""

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A


def lod_dag_path_for(dag_path):
    """The nearest LOD transform at or above ``dag_path``, as an MDagPath, else None."""
    node = dag_path.node()
    if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
        return om.MDagPath(dag_path)
    walker = om.MDagPath(dag_path)
    if walker.hasFn(om.MFn.kMesh):
        walker.pop()
    while walker.length() > 0:
        if walker.node().hasFn(om.MFn.kTransform) and attr.get_bool(walker.node(), A.IS_LOD):
            return om.MDagPath(walker)
        walker.pop()
    return None


__all__ = ["lod_dag_path_for"]
