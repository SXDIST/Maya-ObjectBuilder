"""The ``a3ob*`` Maya commands (OpenMaya 2.0 MPxCommand).

Port of ``src/commands/StubCommands.cpp``. Command names, flags and the resulting
``a3ob*`` attribute schema are preserved exactly — this is the contract the Python UI
and the ``tests/mayapy`` workflows depend on.

First-cut note: these commands are functional but not yet wired for undo. The C++
versions accumulated ``MDGModifier``/``MDagModifier`` operations; here operations are
applied directly. Undo support can be layered on later without changing the surface.
"""

import re

import maya.api.OpenMaya as om

from . import attributes as attr
from .attributes import A

NULL = om.MObject.kNullObj

_PROXY_SELECTION_RE = re.compile(r"^proxy:.*\.\d+$")
_COMPONENT_RE = re.compile(r"^[Cc]omponent\d+$")


# =============================================================================
# string / value helpers
# =============================================================================
def split_semicolon(value):
    return [part for part in value.split(";") if part]


def split_properties(value):
    result = []
    for part in split_semicolon(value):
        sep = part.find("=")
        if sep == -1:
            result.append((part, ""))
        else:
            result.append((part[:sep], part[sep + 1:]))
    return result


def properties_string(properties):
    pieces = []
    for key, value in properties:
        if not key:
            continue
        pieces.append("%s=%s" % (key, value))
    return ";".join(pieces)


def _format_number(value):
    # Mirrors MString += double / int: integers print without a trailing ".0".
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def mass_values_string(values):
    return ";".join(_format_number(v) for v in values)


def repeated_mass_values(count, value):
    return ";".join(_format_number(value) for _ in range(count))


def is_ascii(value):
    return all(ord(ch) <= 127 for ch in value)


def is_proxy_selection_name(value):
    return _PROXY_SELECTION_RE.match(value) is not None


def is_component_selection_name(value):
    return _COMPONENT_RE.match(value) is not None


def proxy_selection_name(path, index):
    return "proxy:%s.%d" % (path, index)


# =============================================================================
# DAG / selection helpers
# =============================================================================
def _iter_selection(sel):
    for i in range(sel.length()):
        try:
            dag_path, component = sel.getComponent(i)
        except Exception:
            continue
        if not dag_path.isValid():
            continue
        yield dag_path, component


def first_mesh_child(transform):
    if transform.isNull():
        return NULL
    dag = om.MFnDagNode(transform)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kMesh):
            return child
    return NULL


def selected_transform_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        node = dag_path.node()
        if node.hasFn(om.MFn.kTransform):
            return node
        if node.hasFn(om.MFn.kMesh):
            return om.MFnDagNode(node).parent(0)
    return NULL


def lod_transform_for_path(dag_path):
    node = dag_path.node()
    while not node.isNull():
        if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
            return node
        dag = om.MFnDagNode(node)
        if dag.parentCount() == 0:
            break
        node = dag.parent(0)
    return NULL


def selected_lod_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        lod = lod_transform_for_path(dag_path)
        if not lod.isNull():
            return lod
    return NULL


def lod_transforms(selection_only):
    lods = []
    if selection_only:
        sel = om.MGlobal.getActiveSelectionList()
        for dag_path, _component in _iter_selection(sel):
            node = dag_path.node()
            if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
                lods.append(node)
        return lods

    it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
    while not it.isDone():
        node = it.currentItem()
        if attr.get_bool(node, A.IS_LOD):
            lods.append(node)
        it.next()
    return lods


def node_name(node):
    if node.isNull():
        return ""
    return om.MFnDependencyNode(node).name()


def same_node(a, b):
    return not a.isNull() and not b.isNull() and a == b


# =============================================================================
# LOD metadata
# =============================================================================
def set_lod_attributes(transform, lod_type, resolution):
    from ..formats.p3d import LodResolution
    signature = LodResolution.encode(lod_type, resolution)
    attr.set_bool(transform, A.IS_LOD, True)
    attr.set_int(transform, A.LOD_TYPE, lod_type)
    attr.set_int(transform, A.RESOLUTION, resolution)
    attr.set_double(transform, A.RESOLUTION_SIGNATURE, signature)
    attr.set_int(transform, A.SOURCE_VERTEX_COUNT, 0)
    attr.set_int(transform, A.SOURCE_FACE_COUNT, 0)


def vertex_count_for_lod(transform):
    mesh = first_mesh_child(transform)
    if not mesh.isNull():
        return om.MFnMesh(mesh).numVertices
    return attr.get_int(transform, A.SOURCE_VERTEX_COUNT, 0)


# =============================================================================
# proxy / set helpers
# =============================================================================
def proxy_placeholder(lod, selection_name):
    dag = om.MFnDagNode(lod)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if (child.hasFn(om.MFn.kTransform)
                and attr.get_bool_any(child, A.IS_PROXY, A.IS_PROXY_ALT_SHORT)
                and attr.get_string(child, A.PROXY_SELECTION) == selection_name):
            return child
    return NULL


def proxy_selection_set_exists(selection_name):
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        node = it.thisNode()
        if attr.get_bool(node, A.IS_PROXY_SELECTION) and attr.get_string(node, A.SELECTION_NAME) == selection_name:
            return True
        it.next()
    return False


def set_contains_mesh(set_obj, mesh):
    set_fn = om.MFnSet(set_obj)
    members = set_fn.getMembers(True)
    for dag_path, _component in _iter_selection(members):
        if dag_path.node() == mesh:
            return True
    return False


def metadata_set_has_live_members(set_obj):
    members = om.MFnSet(set_obj).getMembers(True)
    return members.length() > 0


def is_object_builder_metadata_set(set_obj):
    return (bool(attr.get_string(set_obj, A.SELECTION_NAME))
            or bool(attr.get_string(set_obj, A.FLAG_COMPONENT))
            or attr.get_bool(set_obj, A.IS_PROXY_SELECTION))


# =============================================================================
# geometry analysis
# =============================================================================
def polygon_has_repeated_vertices(vertices):
    seen = set()
    for v in vertices:
        if v in seen:
            return True
        seen.add(v)
    return False


def polygon_has_near_zero_area(points):
    if len(points) < 3:
        return True
    origin = points[0]
    area = 0.0
    for i in range(1, len(points) - 1):
        a = points[i] - origin
        b = points[i + 1] - origin
        area += (a ^ b).length() * 0.5
    return area < 1.0e-10


EdgeKey = lambda a, b: (a, b) if a < b else (b, a)  # noqa: E731


def closed_face_islands(mesh_fn):
    it = om.MItMeshPolygon(mesh_fn.object())
    num_polygons = mesh_fn.numPolygons
    edge_faces = {}
    face_edges = [[] for _ in range(num_polygons)]
    while not it.isDone():
        vertices = it.getVertices()
        face_index = it.index()
        n = len(vertices)
        for i in range(n):
            key = EdgeKey(vertices[i], vertices[(i + 1) % n])
            edge_faces.setdefault(key, []).append(face_index)
            face_edges[face_index].append(key)
        it.next()

    adjacency = [[] for _ in range(num_polygons)]
    for key, faces in edge_faces.items():
        if len(faces) == 2:
            adjacency[faces[0]].append(faces[1])
            adjacency[faces[1]].append(faces[0])

    visited = [False] * num_polygons
    islands = []
    for start in range(num_polygons):
        if visited[start]:
            continue
        island_faces = set()
        island_vertices = set()
        closed = True
        queue = [start]
        visited[start] = True
        while queue:
            face = queue.pop(0)
            island_faces.add(face)
            for key in face_edges[face]:
                island_vertices.add(key[0])
                island_vertices.add(key[1])
            for nxt in adjacency[face]:
                if not visited[nxt]:
                    visited[nxt] = True
                    queue.append(nxt)
        for face in island_faces:
            for key in face_edges[face]:
                count = sum(1 for ef in edge_faces[key] if ef in island_faces)
                if count != 2:
                    closed = False
        islands.append((island_faces, island_vertices, closed))
    return islands


# =============================================================================
# component selection collection
# =============================================================================
def selected_components():
    """Return (MSelectionList members, lod MObject) for selected mesh components."""
    members = om.MSelectionList()
    sel = om.MGlobal.getActiveSelectionList()
    lod = NULL
    for dag_path, component in _iter_selection(sel):
        if component.isNull():
            continue
        candidate = lod_transform_for_path(dag_path)
        if candidate.isNull():
            continue
        if lod.isNull():
            lod = candidate
        members.add((dag_path, component))
    return members, lod


def mass_values_for_lod(transform, default_value):
    count = max(vertex_count_for_lod(transform), 0)
    values = [default_value] * count
    existing = split_semicolon(attr.get_string(transform, A.MASS_VALUES))
    for i in range(min(len(existing), len(values))):
        values[i] = float(existing[i])
    return values


def set_selected_mass_values(lod, value):
    members, selected_lod = selected_components()
    if members.length() == 0:
        return False
    if lod.isNull():
        lod = selected_lod

    masses = mass_values_for_lod(lod, 0.0)
    for i in range(members.length()):
        try:
            dag_path, component = members.getComponent(i)
        except Exception:
            continue
        if component.isNull() or not component.hasFn(om.MFn.kMeshVertComponent):
            continue
        elements = om.MFnSingleIndexedComponent(component).getElements()
        for index in elements:
            if 0 <= index < len(masses):
                masses[index] = value

    attr.set_bool(lod, A.HAS_MASS, True)
    attr.set_string(lod, A.MASS_VALUES, mass_values_string(masses))
    return True


# =============================================================================
# set creation
# =============================================================================
def _create_set_from_members(members, name, restriction=None):
    set_fn = om.MFnSet()
    if restriction is None:
        restriction = om.MFnSet.kNone
    set_obj = set_fn.create(members, restriction)
    set_fn.setName(name)
    return set_obj


def create_metadata_set(set_name, component, value):
    members, _lod = selected_components()
    if members.length() == 0:
        return NULL
    set_obj = _create_set_from_members(members, set_name)
    attr.set_string(set_obj, A.SELECTION_NAME, set_name)
    attr.set_string(set_obj, A.FLAG_COMPONENT, component)
    attr.set_int(set_obj, A.FLAG_VALUE, value)
    attr.mark_technical_set(set_obj)
    return set_obj


def _sanitized_set_name(selection_name):
    name = "a3ob_" + selection_name
    for ch in (":", "/", "\\", "."):
        name = name.replace(ch, "_")
    return name


def create_proxy_selection_set(selection_name):
    members = om.MSelectionList()
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, component in _iter_selection(sel):
        if dag_path.node().hasFn(om.MFn.kMesh) and not component.isNull():
            members.add((dag_path, component))
    if members.length() == 0:
        return
    set_obj = _create_set_from_members(members, _sanitized_set_name(selection_name))
    attr.set_string(set_obj, A.SELECTION_NAME, selection_name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, True)
    attr.mark_technical_set(set_obj)


# =============================================================================
# component (find components) sets
# =============================================================================
class MeshTarget:
    __slots__ = ("mesh_path", "lod")

    def __init__(self, mesh_path, lod):
        self.mesh_path = mesh_path
        self.lod = lod


def _add_mesh_target(mesh_path, lod, targets):
    if mesh_path.isValid() and mesh_path.node().hasFn(om.MFn.kMesh):
        for target in targets:
            if target.mesh_path.node() == mesh_path.node() and (target.lod == lod or same_node(target.lod, lod)):
                return
        targets.append(MeshTarget(mesh_path, lod))


def _add_child_mesh_targets(lod, targets):
    dag = om.MFnDagNode(lod)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kMesh):
            _add_mesh_target(om.MFnDagNode(child).getPath(), lod, targets)
        elif child.hasFn(om.MFn.kTransform):
            mesh = first_mesh_child(child)
            if not mesh.isNull():
                _add_mesh_target(om.MFnDagNode(mesh).getPath(), lod, targets)


def selected_mesh_targets():
    targets = []
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        node = dag_path.node()
        if node.hasFn(om.MFn.kMesh):
            _add_mesh_target(dag_path, lod_transform_for_path(dag_path), targets)
            continue
        if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
            _add_child_mesh_targets(node, targets)
            continue
        if node.hasFn(om.MFn.kTransform):
            mesh = first_mesh_child(node)
            if not mesh.isNull():
                mesh_path = om.MFnDagNode(mesh).getPath()
                _add_mesh_target(mesh_path, lod_transform_for_path(mesh_path), targets)
    return targets


def _component_set_belongs_to_target(set_obj, lod, mesh_path):
    members = om.MFnSet(set_obj).getMembers(True)
    for dag_path, _component in _iter_selection(members):
        if not lod.isNull() and same_node(lod_transform_for_path(dag_path), lod):
            return True
        if lod.isNull() and dag_path.node() == mesh_path.node():
            return True
    return False


def _delete_existing_component_sets(lod, mesh_path):
    to_delete = []
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        set_obj = it.thisNode()
        selection_name = attr.get_string(set_obj, A.SELECTION_NAME)
        if is_component_selection_name(selection_name) and _component_set_belongs_to_target(set_obj, lod, mesh_path):
            to_delete.append(om.MFnDependencyNode(set_obj).name())
        it.next()
    if to_delete:
        import maya.cmds as cmds
        cmds.delete(to_delete)


# =============================================================================
# material nodes
# =============================================================================
def normalize_dayz_path(value):
    path = value.strip()
    path = path.replace("/", "\\")
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        path = path[2:]
        while path and path[0] == "\\":
            path = path[1:]
    normalized = []
    previous_slash = False
    for ch in path:
        if ch == "\\":
            if not previous_slash:
                normalized.append(ch)
            previous_slash = True
        else:
            normalized.append(ch)
            previous_slash = False
    return "".join(normalized)


def create_material_nodes(texture, material):
    import maya.cmds as cmds
    normalized_texture = normalize_dayz_path(texture)
    normalized_material = normalize_dayz_path(material)
    shader = cmds.createNode("lambert", name="a3ob_material#")
    shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + "SG")
    cmds.connectAttr(shader + ".outColor", shading_group + ".surfaceShader", force=True)

    sel = om.MSelectionList()
    sel.add(shader)
    sel.add(shading_group)
    shader_obj = sel.getDependNode(0)
    sg_obj = sel.getDependNode(1)
    attr.set_string(shader_obj, A.TEXTURE, normalized_texture)
    attr.set_string(shader_obj, A.MATERIAL, normalized_material)
    attr.set_string(sg_obj, A.SG_TEXTURE, normalized_texture)
    attr.set_string(sg_obj, A.SG_MATERIAL, normalized_material)
    return shading_group


# =============================================================================
# proxy update helpers
# =============================================================================
def selected_dependency_node_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for i in range(sel.length()):
        node = sel.getDependNode(i)
        if not node.isNull():
            return node
    return NULL


def update_proxy_selection_set(set_obj, path, index):
    import maya.cmds as cmds
    selection_name = proxy_selection_name(path, index)
    attr.set_string(set_obj, A.SELECTION_NAME, selection_name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, True)
    attr.mark_technical_set(set_obj)
    cmds.rename(om.MFnDependencyNode(set_obj).name(), _sanitized_set_name(selection_name))


def update_proxy_placeholder(proxy, path, index):
    selection_name = proxy_selection_name(path, index)
    attr.set_bool(proxy, A.IS_PROXY, True)
    attr.set_string(proxy, A.PROXY_PATH, path)
    attr.set_int(proxy, A.PROXY_INDEX, index)
    attr.set_string(proxy, A.PROXY_SELECTION, selection_name)


def named_property_result(lod):
    return ["%s=%s" % (key, value) for key, value in split_properties(attr.get_string(lod, A.PROPERTIES))]


# =============================================================================
# Commands
# =============================================================================
class _Base(om.MPxCommand):
    def isUndoable(self):
        return False


class ValidateCommand(_Base):
    kName = "a3obValidate"

    @staticmethod
    def creator():
        return ValidateCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-so", "-selectionOnly")
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        selection_only = argdb.isFlagSet("-so")
        lods = lod_transforms(selection_only)
        warnings = [0]
        errors = [0]

        if not lods:
            om.MGlobal.displayError("a3obValidate: no LOD transforms found")
            return

        signatures = {}
        for lod in lods:
            name = om.MFnDependencyNode(lod).name()
            signature = attr.get_double(lod, A.RESOLUTION_SIGNATURE, 0.0)
            signatures[signature] = signatures.get(signature, 0) + 1
            if signatures[signature] > 1:
                om.MGlobal.displayWarning("a3obValidate: duplicate LOD resolution signature on " + name)
                warnings[0] += 1

            mesh = first_mesh_child(lod)
            source_vertex_count = attr.get_int(lod, A.SOURCE_VERTEX_COUNT, 0)
            source_face_count = attr.get_int(lod, A.SOURCE_FACE_COUNT, 0)
            if mesh.isNull() and source_vertex_count == 0 and source_face_count > 0:
                om.MGlobal.displayWarning("a3obValidate: LOD has source faces but no mesh/source vertices: " + name)
                warnings[0] += 1

            masses = split_semicolon(attr.get_string(lod, A.MASS_VALUES))
            if masses and len(masses) != vertex_count_for_lod(lod):
                om.MGlobal.displayWarning("a3obValidate: mass count does not match vertex count on " + name)
                warnings[0] += 1
            for mass in masses:
                try:
                    if float(mass) < 0.0:
                        om.MGlobal.displayError("a3obValidate: negative mass value on " + name)
                        errors[0] += 1
                        break
                except ValueError:
                    om.MGlobal.displayError("a3obValidate: invalid mass value on " + name)
                    errors[0] += 1
                    break

            proxy_selections = self._proxy_placeholder_selections(lod, name, warnings, errors)

            if not mesh.isNull():
                self._validate_mesh(lod, mesh, name, source_face_count, proxy_selections, warnings, errors)

        om.MGlobal.displayInfo("a3obValidate: checked LODs=%d, warnings=%d, errors=%d" % (len(lods), warnings[0], errors[0]))
        if errors[0] != 0:
            raise RuntimeError("a3obValidate failed with %d errors" % errors[0])

    def _proxy_placeholder_selections(self, lod, lod_name, warnings, errors):
        proxy_selections = set()
        dag = om.MFnDagNode(lod)
        for i in range(dag.childCount()):
            child = dag.child(i)
            if not (child.hasFn(om.MFn.kTransform) and attr.get_bool_any(child, A.IS_PROXY, A.IS_PROXY_ALT_SHORT)):
                continue
            path = attr.get_string(child, A.PROXY_PATH)
            index = attr.get_int(child, A.PROXY_INDEX, -1)
            selection = attr.get_string(child, A.PROXY_SELECTION)
            if not path or index < 0 or not is_proxy_selection_name(selection):
                om.MGlobal.displayError("a3obValidate: invalid proxy placeholder under " + lod_name)
                errors[0] += 1
                continue
            if selection in proxy_selections:
                om.MGlobal.displayWarning("a3obValidate: duplicate proxy placeholder under " + lod_name)
                warnings[0] += 1
            proxy_selections.add(selection)
            if not proxy_selection_set_exists(selection):
                om.MGlobal.displayWarning("a3obValidate: proxy placeholder has no matching selection set under " + lod_name)
                warnings[0] += 1
        return proxy_selections

    def _validate_mesh(self, lod, mesh, name, source_face_count, proxy_selections, warnings, errors):
        mesh_fn = om.MFnMesh(mesh)
        mesh_path = om.MFnDagNode(mesh).getPath()
        poly_it = om.MItMeshPolygon(mesh_path)
        while not poly_it.isDone():
            vertex_count = poly_it.polygonVertexCount()
            if vertex_count < 3:
                om.MGlobal.displayError("a3obValidate: face with fewer than 3 vertices on " + name)
                errors[0] += 1
                break
            if vertex_count > 4:
                om.MGlobal.displayWarning("a3obValidate: N-gon face (%d verts) on %s — will be auto-triangulated on export" % (vertex_count, name))
                warnings[0] += 1
            vertex_ids = poly_it.getVertices()
            if polygon_has_repeated_vertices(vertex_ids):
                om.MGlobal.displayError("a3obValidate: face uses repeated vertices on " + name)
                errors[0] += 1
                break
            if source_face_count == 0:
                points = poly_it.getPoints(om.MSpace.kObject)
                if polygon_has_near_zero_area(points):
                    om.MGlobal.displayWarning("a3obValidate: near-zero-area face on " + name)
                    warnings[0] += 1
            poly_it.next()

        shaders, _indices = mesh_fn.getConnectedShaders(0)
        for shader in shaders:
            texture = attr.get_string(shader, A.TEXTURE)
            material = attr.get_string(shader, A.MATERIAL)
            if not is_ascii(texture) or not is_ascii(material):
                om.MGlobal.displayWarning("a3obValidate: non-ASCII texture/material path on " + name)
                warnings[0] += 1

        self._validate_object_sets(mesh, name, proxy_selections, warnings, errors)

    def _validate_object_sets(self, mesh, lod_name, proxy_placeholders, warnings, errors):
        it = om.MItDependencyNodes(om.MFn.kSet)
        selection_names = set()
        while not it.isDone():
            set_obj = it.thisNode()
            it_advance = True
            if is_object_builder_metadata_set(set_obj):
                set_name = om.MFnDependencyNode(set_obj).name()
                if not metadata_set_has_live_members(set_obj):
                    om.MGlobal.displayWarning("a3obValidate: Object Builder set has no live members and will be ignored: " + set_name)
                    warnings[0] += 1
                elif set_contains_mesh(set_obj, mesh):
                    selection_name = attr.get_string(set_obj, A.SELECTION_NAME)
                    if selection_name:
                        if selection_name in selection_names:
                            om.MGlobal.displayWarning("a3obValidate: duplicate selection name on " + lod_name)
                            warnings[0] += 1
                        selection_names.add(selection_name)
                        if attr.get_bool(set_obj, A.IS_PROXY_SELECTION):
                            if not is_proxy_selection_name(selection_name):
                                om.MGlobal.displayError("a3obValidate: invalid proxy selection name on " + lod_name)
                                errors[0] += 1
                            elif selection_name not in proxy_placeholders:
                                om.MGlobal.displayWarning("a3obValidate: proxy selection has no matching placeholder on " + lod_name)
                                warnings[0] += 1
                    flag_component = attr.get_string(set_obj, A.FLAG_COMPONENT)
                    if flag_component and flag_component not in ("vertex", "face"):
                        om.MGlobal.displayError("a3obValidate: invalid flag component type on " + lod_name)
                        errors[0] += 1
                    if flag_component and attr.get_int(set_obj, A.FLAG_VALUE, 0) == 0:
                        om.MGlobal.displayError("a3obValidate: invalid zero flag value on " + lod_name)
                        errors[0] += 1
            if it_advance:
                it.next()


class SetMassCommand(_Base):
    kName = "a3obSetMass"

    @staticmethod
    def creator():
        return SetMassCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-v", "-value", om.MSyntax.kDouble)
        s.addFlag("-c", "-clear")
        s.addFlag("-sc", "-selectedComponents")
        return s

    def doIt(self, args):
        transform = selected_transform_or_null()
        if transform.isNull():
            om.MGlobal.displayError("a3obSetMass: select a LOD transform or mesh")
            return

        argdb = om.MArgDatabase(self.syntax(), args)
        if argdb.isFlagSet("-c"):
            attr.set_bool(transform, A.HAS_MASS, False)
            attr.set_string(transform, A.MASS_VALUES, "")
            om.MGlobal.displayInfo("a3obSetMass: cleared mass values")
            return

        value = 1.0
        if argdb.isFlagSet("-v"):
            value = argdb.flagArgumentDouble("-v", 0)
        if argdb.isFlagSet("-sc"):
            if not set_selected_mass_values(transform, value):
                om.MGlobal.displayError("a3obSetMass: select LOD mesh vertex components")
                return
            om.MGlobal.displayInfo("a3obSetMass: set selected vertex mass values")
            return

        count = vertex_count_for_lod(transform)
        if count <= 0:
            om.MGlobal.displayError("a3obSetMass: selected LOD has no vertices")
            return
        attr.set_bool(transform, A.HAS_MASS, True)
        attr.set_string(transform, A.MASS_VALUES, repeated_mass_values(count, value))
        om.MGlobal.displayInfo("a3obSetMass: set mass values count=%d" % count)


class SetMaterialCommand(_Base):
    kName = "a3obSetMaterial"

    @staticmethod
    def creator():
        return SetMaterialCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-t", "-texture", om.MSyntax.kString)
        s.addFlag("-m", "-material", om.MSyntax.kString)
        return s

    def doIt(self, args):
        import maya.cmds as cmds
        argdb = om.MArgDatabase(self.syntax(), args)
        texture = argdb.flagArgumentString("-t", 0) if argdb.isFlagSet("-t") else ""
        material = argdb.flagArgumentString("-m", 0) if argdb.isFlagSet("-m") else ""

        selected_faces = cmds.ls(selection=True)
        members, _lod = selected_components()
        if members.length() == 0:
            om.MGlobal.displayError("a3obSetMaterial: select mesh faces")
            return

        shading_group = create_material_nodes(texture, material)
        if selected_faces:
            cmds.sets(selected_faces, edit=True, forceElement=shading_group)
        om.MGlobal.displayInfo("a3obSetMaterial: assigned material metadata")


class SetFlagCommand(_Base):
    kName = "a3obSetFlag"

    @staticmethod
    def creator():
        return SetFlagCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-c", "-component", om.MSyntax.kString)
        s.addFlag("-v", "-value", om.MSyntax.kLong)
        s.addFlag("-n", "-name", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        component = argdb.flagArgumentString("-c", 0) if argdb.isFlagSet("-c") else "face"
        value = argdb.flagArgumentInt("-v", 0) if argdb.isFlagSet("-v") else 0
        name = argdb.flagArgumentString("-n", 0) if argdb.isFlagSet("-n") else "a3ob_flag#"
        if component not in ("vertex", "face"):
            om.MGlobal.displayError("a3obSetFlag: -component must be vertex or face")
            return
        if value == 0:
            om.MGlobal.displayError("a3obSetFlag: -value must be non-zero")
            return
        if create_metadata_set(name, component, value).isNull():
            om.MGlobal.displayError("a3obSetFlag: select mesh vertex or face components")
            return
        om.MGlobal.displayInfo("a3obSetFlag: created flag set")


class FindComponentsCommand(_Base):
    kName = "a3obFindComponents"

    @staticmethod
    def creator():
        return FindComponentsCommand()

    @staticmethod
    def syntax():
        return om.MSyntax()

    def doIt(self, args):
        targets = selected_mesh_targets()
        if not targets:
            om.MGlobal.displayError("a3obFindComponents: select an Object Builder LOD, mesh, or mesh component")
            return

        cleaned_targets = set()
        created_total = 0
        skipped = 0
        for target in targets:
            target_name = node_name(target.lod)
            if not target_name:
                target_name = target.mesh_path.fullPathName()
            if target_name not in cleaned_targets:
                _delete_existing_component_sets(target.lod, target.mesh_path)
                cleaned_targets.add(target_name)

            mesh_fn = om.MFnMesh(target.mesh_path)
            created_for_target = 0
            for island_faces, island_vertices, closed in closed_face_islands(mesh_fn):
                if not closed or not island_vertices:
                    skipped += 1
                    continue
                self._create_component_set(target.mesh_path, created_for_target + 1, island_vertices)
                created_for_target += 1
                created_total += 1

        if created_total == 0:
            om.MGlobal.displayError("a3obFindComponents: no closed components found, skipped=%d" % skipped)
            return
        if skipped > 0:
            om.MGlobal.displayWarning("a3obFindComponents: created components=%d, skipped open/non-manifold islands=%d" % (created_total, skipped))
        else:
            om.MGlobal.displayInfo("a3obFindComponents: created components=%d" % created_total)

    def _create_component_set(self, mesh_path, component_index, vertices):
        component_fn = om.MFnSingleIndexedComponent()
        component = component_fn.create(om.MFn.kMeshVertComponent)
        component_fn.addElements(sorted(vertices))
        members = om.MSelectionList()
        members.add((mesh_path, component))
        component_name = "Component%02d" % component_index if component_index < 10 else "Component%d" % component_index
        set_obj = _create_set_from_members(members, "a3ob_" + component_name)
        attr.set_string(set_obj, A.SELECTION_NAME, component_name)


class CreateLODCommand(_Base):
    kName = "a3obCreateLOD"

    @staticmethod
    def creator():
        return CreateLODCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-lt", "-lodType", om.MSyntax.kLong)
        s.addFlag("-r", "-resolution", om.MSyntax.kLong)
        s.addFlag("-n", "-name", om.MSyntax.kString)
        return s

    def doIt(self, args):
        import maya.cmds as cmds
        from ..formats.p3d import LodResolution
        argdb = om.MArgDatabase(self.syntax(), args)
        lod_type = argdb.flagArgumentInt("-lt", 0) if argdb.isFlagSet("-lt") else 0
        resolution = argdb.flagArgumentInt("-r", 0) if argdb.isFlagSet("-r") else 0
        name = argdb.flagArgumentString("-n", 0) if argdb.isFlagSet("-n") else ""

        transform = selected_transform_or_null()
        if transform.isNull():
            new_name = cmds.createNode("transform", name=name if name else "a3ob_LOD#", skipSelect=True)
            sel = om.MSelectionList()
            sel.add(new_name)
            transform = sel.getDependNode(0)

        set_lod_attributes(transform, lod_type, resolution)
        result_name = om.MFnDependencyNode(transform).name()
        self.setResult(result_name)
        om.MGlobal.displayInfo("a3obCreateLOD: marked LOD signature=%s" % LodResolution.encode(lod_type, resolution))


class ProxyCommand(_Base):
    kName = "a3obProxy"

    @staticmethod
    def creator():
        return ProxyCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-p", "-path", om.MSyntax.kString)
        s.addFlag("-i", "-index", om.MSyntax.kLong)
        s.addFlag("-u", "-update")
        s.addFlag("-fs", "-fromSelection")
        s.addFlag("-ss", "-selectionSet")
        return s

    def doIt(self, args):
        import maya.cmds as cmds
        argdb = om.MArgDatabase(self.syntax(), args)
        proxy_path = argdb.flagArgumentString("-p", 0) if argdb.isFlagSet("-p") else ""
        if not proxy_path:
            om.MGlobal.displayError("a3obProxy: -path is required")
            return
        proxy_index = argdb.flagArgumentInt("-i", 0) if argdb.isFlagSet("-i") else 1

        lod = selected_lod_or_null()
        if lod.isNull():
            om.MGlobal.displayError("a3obProxy: select a LOD transform, LOD mesh, or mesh components")
            return

        update = argdb.isFlagSet("-u")
        from_selection = argdb.isFlagSet("-fs") or argdb.isFlagSet("-ss")
        selection_name = proxy_selection_name(proxy_path, proxy_index)

        proxy = proxy_placeholder(lod, selection_name) if update else NULL
        if proxy.isNull():
            lod_name = om.MFnDependencyNode(lod).name()
            # skipSelect so the active component selection survives for the selection set below.
            new_name = cmds.createNode("transform", name="a3ob_proxy#", parent=lod_name, skipSelect=True)
            sel = om.MSelectionList()
            sel.add(new_name)
            proxy = sel.getDependNode(0)

        attr.set_bool(proxy, A.IS_PROXY, True)
        attr.set_string(proxy, A.PROXY_PATH, proxy_path)
        attr.set_int(proxy, A.PROXY_INDEX, proxy_index)
        attr.set_string(proxy, A.PROXY_SELECTION, selection_name)

        if from_selection and not proxy_selection_set_exists(selection_name):
            create_proxy_selection_set(selection_name)

        om.MGlobal.displayInfo("a3obProxy: created " + selection_name)


class NamedPropertyCommand(_Base):
    kName = "a3obNamedProperty"

    @staticmethod
    def creator():
        return NamedPropertyCommand()

    @staticmethod
    def syntax():
        # Two deviations forced by OpenMaya 2.0's MSyntax vs the former C++ MSyntax:
        #  * addFlag accepts only ONE argument type, so the old two-argument
        #    "-set key value" form is passed as a single "key=value" string.
        #  * the long flag name "set" is reserved and rejected by om2, so the long
        #    alias is "-setproperty"; the short "-s" form is unchanged.
        s = om.MSyntax()
        s.addFlag("-l", "-list")
        s.addFlag("-s", "-setproperty", om.MSyntax.kString)
        s.addFlag("-r", "-remove", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        lod = selected_lod_or_null()
        if lod.isNull():
            om.MGlobal.displayError("a3obNamedProperty: select a LOD transform, LOD mesh, or mesh components")
            return

        if argdb.isFlagSet("-l"):
            self.setResult(named_property_result(lod))
            return

        properties = split_properties(attr.get_string(lod, A.PROPERTIES))
        if argdb.isFlagSet("-s"):
            payload = argdb.flagArgumentString("-s", 0)
            sep = payload.find("=")
            key = payload if sep == -1 else payload[:sep]
            value = "" if sep == -1 else payload[sep + 1:]
            if not key:
                om.MGlobal.displayError("a3obNamedProperty: property key cannot be empty")
                return
            properties = [item for item in properties if item[0] != key]
            properties.append((key, value))
            attr.set_string(lod, A.PROPERTIES, properties_string(properties))
            self.setResult(named_property_result(lod))
            return

        if argdb.isFlagSet("-r"):
            key = argdb.flagArgumentString("-r", 0)
            properties = [item for item in properties if item[0] != key]
            attr.set_string(lod, A.PROPERTIES, properties_string(properties))
            self.setResult(named_property_result(lod))
            return

        self.setResult(named_property_result(lod))


class UpdateProxyCommand(_Base):
    kName = "a3obUpdateProxy"

    @staticmethod
    def creator():
        return UpdateProxyCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-p", "-path", om.MSyntax.kString)
        s.addFlag("-i", "-index", om.MSyntax.kLong)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        path = argdb.flagArgumentString("-p", 0) if argdb.isFlagSet("-p") else ""
        if not path:
            om.MGlobal.displayError("a3obUpdateProxy: -path is required")
            return
        index = argdb.flagArgumentInt("-i", 0) if argdb.isFlagSet("-i") else 1

        node = selected_dependency_node_or_null()
        if node.isNull():
            om.MGlobal.displayError("a3obUpdateProxy: select a proxy placeholder or proxy selection set")
            return
        if attr.get_bool_any(node, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
            update_proxy_placeholder(node, path, index)
            return
        if attr.get_bool(node, A.IS_PROXY_SELECTION) or node.hasFn(om.MFn.kSet):
            update_proxy_selection_set(node, path, index)
            return
        om.MGlobal.displayError("a3obUpdateProxy: selected node is not a proxy placeholder or proxy selection set")


COMMANDS = [
    ValidateCommand, SetMassCommand, SetMaterialCommand, SetFlagCommand,
    FindComponentsCommand, CreateLODCommand, ProxyCommand, NamedPropertyCommand,
    UpdateProxyCommand,
]
