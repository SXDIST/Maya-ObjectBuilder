import os
import runpy
import struct
from pathlib import Path

import maya.cmds as cmds
import maya.standalone


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "build" / "Debug" / "MayaObjectBuilder.mll"
INPUTS = [
    ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_2_crate.p3d",
    ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_1_character.p3d",
]
OUTDIR = ROOT / "build" / "mayapy-workflow"
DAYZ_OUTDIR = ROOT / "build" / "dayz-p3d-workflow"
UI_SCRIPT = ROOT / "scripts" / "objectBuilderMenu.py"


def optional_dayz_inputs():
    candidates = []
    if os.environ.get("DAYZ_P3D_FIXTURES"):
        candidates.append(Path(os.environ["DAYZ_P3D_FIXTURES"]))
    candidates.extend([ROOT / "tests" / "inputs" / "dayz_p3d", ROOT / "local" / "dayz_p3d"])
    inputs = []
    for candidate in candidates:
        if candidate.exists():
            inputs.extend(sorted(candidate.glob("*.p3d")))
    return inputs


def lod_counts():
    counts = []
    for node in cmds.ls(type="transform") or []:
        if cmds.attributeQuery("a3obIsLOD", node=node, exists=True):
            counts.append((
                cmds.getAttr(node + ".a3obResolutionSignature"),
                cmds.getAttr(node + ".a3obSourceVertexCount"),
                cmds.getAttr(node + ".a3obSourceFaceCount"),
            ))
    return sorted(counts)


def proxy_selection_sets():
    names = []
    for node in cmds.ls(type="objectSet") or []:
        if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True) and cmds.getAttr(node + ".a3obIsProxySelection"):
            names.append(cmds.getAttr(node + ".a3obSelectionName"))
    return sorted(names)


def selection_names():
    names = []
    for node in cmds.ls(type="objectSet") or []:
        if cmds.attributeQuery("a3obSelectionName", node=node, exists=True):
            names.append(cmds.getAttr(node + ".a3obSelectionName"))
    return sorted(names)


def component_selection_sets():
    sets = []
    for node in cmds.ls(type="objectSet") or []:
        if cmds.attributeQuery("a3obSelectionName", node=node, exists=True):
            name = cmds.getAttr(node + ".a3obSelectionName")
            if name.startswith("Component"):
                sets.append((name, node))
    return sorted(sets)


def selection_component_counts():
    counts = []
    for node in cmds.ls(type="objectSet") or []:
        if not cmds.attributeQuery("a3obSelectionName", node=node, exists=True):
            continue
        name = cmds.getAttr(node + ".a3obSelectionName")
        vertex_count = 0
        face_count = 0
        for member in cmds.sets(node, query=True) or []:
            expanded = cmds.ls(member, flatten=True) or []
            vertex_count += sum(".vtx[" in item for item in expanded)
            face_count += sum(".f[" in item for item in expanded)
        counts.append((name, vertex_count, face_count))
    return sorted(counts)


def object_builder_set_nodes():
    return [node for node in cmds.ls(type="objectSet") or [] if cmds.attributeQuery("a3obSelectionName", node=node, exists=True)]


def assert_object_builder_sets_hidden(context):
    for node in object_builder_set_nodes():
        if not cmds.attributeQuery("a3obTechnicalSet", node=node, exists=True) or not cmds.getAttr(node + ".a3obTechnicalSet"):
            raise RuntimeError(f"Object Builder set missing technical marker after {context}: {node}")
        if cmds.attributeQuery("hiddenInOutliner", node=node, exists=True) and not cmds.getAttr(node + ".hiddenInOutliner"):
            raise RuntimeError(f"Object Builder set is visible in Outliner after {context}: {node}")


def material_pairs():
    pairs = []
    for node in (cmds.ls(type="shadingEngine") or []) + (cmds.ls(materials=True) or []):
        if cmds.attributeQuery("a3obTexture", node=node, exists=True) or cmds.attributeQuery("a3obMaterial", node=node, exists=True):
            texture = cmds.getAttr(node + ".a3obTexture") if cmds.attributeQuery("a3obTexture", node=node, exists=True) else ""
            material = cmds.getAttr(node + ".a3obMaterial") if cmds.attributeQuery("a3obMaterial", node=node, exists=True) else ""
            pairs.append((texture, material))
    return sorted(set(pairs))


def uv_values(mesh):
    raw = cmds.polyEditUV(mesh + ".map[*]", query=True) or []
    pairs = []
    for index in range(0, len(raw), 2):
        pairs.append((round(float(raw[index]), 4), round(float(raw[index + 1]), 4)))
    return sorted(pairs)


def mesh_points(meshes):
    points = []
    for mesh in meshes:
        raw = cmds.xform(mesh + ".vtx[*]", query=True, translation=True, worldSpace=True) or []
        points.extend((float(raw[index]), float(raw[index + 1]), float(raw[index + 2])) for index in range(0, len(raw), 3))
    return points


def mesh_extents(meshes):
    points = mesh_points(meshes)
    if not points:
        raise RuntimeError("No mesh vertices found for axis orientation check")
    xs, ys, zs = zip(*points)
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def mesh_center(meshes):
    points = mesh_points(meshes)
    if not points:
        raise RuntimeError("No mesh vertices found for center check")
    xs, ys, zs = zip(*points)
    return ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2)


class P3DReader:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.offset = 0

    def read_bytes(self, count):
        value = self.data[self.offset:self.offset + count]
        self.offset += count
        return value

    def read_u32(self):
        value = struct.unpack_from("<I", self.data, self.offset)[0]
        self.offset += 4
        return value

    def read_float(self):
        value = struct.unpack_from("<f", self.data, self.offset)[0]
        self.offset += 4
        return value

    def read_stringz(self):
        end = self.data.index(b"\0", self.offset)
        value = self.data[self.offset:end].decode("ascii", errors="ignore")
        self.offset = end + 1
        return value


def skip_tagg(reader):
    reader.read_bytes(1)
    name = reader.read_stringz()
    length = reader.read_u32()
    if name == "#EndOfFile#":
        if length != 0:
            raise RuntimeError("Invalid P3D EOF TAGG length")
        return False
    reader.read_bytes(length)
    return True


def raw_p3d_lod_points(path, lod_index=0):
    reader = P3DReader(path)
    if reader.read_bytes(4) != b"MLOD":
        raise RuntimeError(f"Invalid P3D signature in {path}")
    if reader.read_u32() != 257:
        raise RuntimeError(f"Unsupported P3D version in {path}")
    count_lods = reader.read_u32()
    for current_lod in range(count_lods):
        if reader.read_bytes(4) != b"P3DM":
            raise RuntimeError(f"Invalid P3D LOD signature in {path}")
        reader.read_u32()
        reader.read_u32()
        count_verts = reader.read_u32()
        count_normals = reader.read_u32()
        count_faces = reader.read_u32()
        reader.read_u32()
        points = []
        for _ in range(count_verts):
            x = reader.read_float()
            z = reader.read_float()
            y = reader.read_float()
            reader.read_u32()
            points.append((x, y, z))
        reader.read_bytes(count_normals * 12)
        for _ in range(count_faces):
            count_face_verts = reader.read_u32()
            reader.read_bytes(count_face_verts * 16)
            if count_face_verts < 4:
                reader.read_bytes(16)
            reader.read_u32()
            reader.read_stringz()
            reader.read_stringz()
        if reader.read_bytes(4) != b"TAGG":
            raise RuntimeError(f"Invalid P3D TAGG section signature in {path}")
        while skip_tagg(reader):
            pass
        reader.read_float()
        if current_lod == lod_index:
            return points
    raise RuntimeError(f"P3D file {path} has no LOD index {lod_index}")


def point_extents(points):
    if not points:
        raise RuntimeError("No points found for extent check")
    xs, ys, zs = zip(*points)
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def point_center(points):
    if not points:
        raise RuntimeError("No points found for center check")
    xs, ys, zs = zip(*points)
    return ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2)


def assert_y_up_character_orientation(namespace):
    meshes = cmds.ls(f"{namespace}:*", type="mesh", long=True) or []
    if not meshes:
        raise RuntimeError(f"No imported meshes found in namespace {namespace}")
    x_extent, y_extent, z_extent = mesh_extents(meshes)
    if y_extent <= z_extent:
        raise RuntimeError(f"Expected imported character to be Maya Y-up, got extents x={x_extent:.4f} y={y_extent:.4f} z={z_extent:.4f}")


def assert_generated_metadata():
    if "proxy:proxy/generated_dayz.p3d.7" not in proxy_selection_sets():
        raise RuntimeError("Generated proxy selection did not roundtrip")
    if "generated_vertex_flag" not in selection_names() or "generated_face_flag" not in selection_names():
        raise RuntimeError("Generated flag sets did not roundtrip")
    if ("dz\\weapons\\generated_ca.paa", "dz\\weapons\\generated.rvmat") not in material_pairs():
        raise RuntimeError("Generated material metadata did not roundtrip")
    assert_object_builder_sets_hidden("generated metadata import")
    lods = [node for node in cmds.ls(type="transform") or [] if cmds.attributeQuery("a3obIsLOD", node=node, exists=True)]
    if len(lods) != 1:
        raise RuntimeError(f"Expected one generated LOD, got {lods}")
    lod = lods[0]
    masses = cmds.getAttr(lod + ".a3obMassValues").split(";")
    if len(masses) != cmds.getAttr(lod + ".a3obSourceVertexCount"):
        raise RuntimeError("Generated mass count did not roundtrip")


def assert_stale_selection_ui_refresh():
    cmds.file(new=True, force=True)
    lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name="stale_ui_lod")
    mesh = cmds.polyPlane(name="stale_ui_mesh", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.parent(mesh, lod)
    cmds.select(mesh + ".f[0]")
    set_node = cmds.sets(cmds.ls(selection=True, flatten=True), name="a3ob_SEL_stale")
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", "stale", type="string")

    ui = runpy.run_path(str(UI_SCRIPT))
    if not any(item["node"] == set_node for item in ui["_selection_sets"]()):
        raise RuntimeError("Stale test selection set was not found before deletion")
    assert_object_builder_sets_hidden("Selection Manager normalization")
    cmds.delete(mesh)
    if ui["_live_set_members"](set_node):
        raise RuntimeError("Selection set with deleted members still returned live members")
    if any(item["node"] == set_node for item in ui["_selection_sets"]()):
        raise RuntimeError("Empty selection set remained in live Selection Manager data")
    if cmds.objExists(set_node):
        cmds.delete(set_node)
    if any(item["node"] == set_node for item in ui["_selection_sets"]()):
        raise RuntimeError("Deleted selection set remained in live Selection Manager data")
    cmds.a3obValidate()
    print("OK stale and empty Selection Manager data is pruned")


def assert_ui_redesign_helpers_load():
    ui = runpy.run_path(str(UI_SCRIPT))
    for name in ("MayaObjectBuilderDock", "_build_qt_dock", "_delete_qt_dock", "_quick_action_bar", "_action_row", "_path_row", "_labeled_row", "import_model_cfg_from_ui", "export_model_cfg_from_ui"):
        if name not in ui:
            raise RuntimeError(f"Missing redesigned UI helper: {name}")
    dock_class = ui["MayaObjectBuilderDock"]
    for name in ("refresh_named_properties", "refresh_material_metadata", "refresh_selection_manager", "selected_selection_set_node", "set_selection_details"):
        if not hasattr(dock_class, name):
            raise RuntimeError(f"Missing Qt dock method: {name}")

    window = "MayaObjectBuilderDockBuildSmokeWindow"
    if cmds.window(window, exists=True):
        cmds.deleteUI(window)
    window = cmds.window(window, title="MayaObjectBuilder UI Smoke")
    try:
        cmds.columnLayout(adjustableColumn=True)
        ui["_build_dock_contents"]()
        cmds.showWindow(window)
    finally:
        if cmds.window(window, exists=True):
            cmds.deleteUI(window)
        ui["_delete_qt_dock"]()
    if ui["_active_qt_dock"]() is not None:
        raise RuntimeError("Qt dock wrapper remained active after UI smoke cleanup")
    ui["_refresh_context_ui"]()
    print("OK redesigned UI builds without layout errors")


def assert_selection_manager_clear_all():
    cmds.file(new=True, force=True)
    cube = cmds.polyCube(name="clear_all_cube", width=1, height=1, depth=1)[0]
    cmds.select(cube + ".vtx[0]")
    first = cmds.sets(cmds.ls(selection=True, flatten=True), name="a3ob_SEL_clear_first")
    cmds.addAttr(first, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(first + ".a3obSelectionName", "clear_first", type="string")
    cmds.select(cube + ".vtx[1]")
    second = cmds.sets(cmds.ls(selection=True, flatten=True), name="a3ob_SEL_clear_second")
    cmds.addAttr(second, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(second + ".a3obSelectionName", "clear_second", type="string")
    maya_set = cmds.sets(cube, name="plain_maya_set")

    ui = runpy.run_path(str(UI_SCRIPT))
    if len(ui["_selection_sets"]()) != 2:
        raise RuntimeError("Clear-all setup did not create two Object Builder sets")
    ui["_clear_all_object_builder_sets"]()
    if ui["_selection_sets"]():
        raise RuntimeError("Clear All OB Sets did not remove Object Builder sets")
    if not cmds.objExists(maya_set):
        raise RuntimeError("Clear All OB Sets removed a plain Maya set")
    print("OK Selection Manager can clear all Object Builder sets")


def create_generated_fixture(path):
    cmds.file(new=True, force=True)
    lod = cmds.a3obCreateLOD(lodType=1, resolution=25, name="generated_dayz_lod")
    mesh_transform = cmds.polyPlane(name="generated_dayz_mesh", subdivisionsX=1, subdivisionsY=1)[0]
    mesh_shape = cmds.listRelatives(mesh_transform, shapes=True, fullPath=True)[0]
    cmds.parent(mesh_shape, lod, shape=True, relative=True)
    cmds.delete(mesh_transform)
    mesh = cmds.ls(cmds.listRelatives(lod, shapes=True, fullPath=True)[0], long=True)[0]
    cmds.polyEditUV(mesh + ".map[0]", u=0.125, v=0.875, relative=False)
    cmds.polyEditUV(mesh + ".map[1]", u=0.625, v=0.625, relative=False)
    cmds.polyEditUV(mesh + ".map[2]", u=0.875, v=0.375, relative=False)
    cmds.polyEditUV(mesh + ".map[3]", u=0.375, v=0.125, relative=False)

    cmds.select(mesh + ".f[0]")
    cmds.a3obSetMaterial(texture="dz\\weapons\\generated_ca.paa", material="dz\\weapons\\generated.rvmat")

    cmds.select(lod)
    cmds.a3obSetMass(value=2.5)
    cmds.select(mesh + ".vtx[0]")
    cmds.a3obSetMass(value=7.5, selectedComponents=True)
    cmds.select(mesh + ".f[0]")
    cmds.a3obProxy(path="proxy/generated_dayz.p3d", index=7, fromSelection=True)
    cmds.select(mesh + ".vtx[0:1]")
    cmds.a3obSetFlag(component="vertex", value=123, name="generated_vertex_flag")
    cmds.select(mesh + ".f[0]")
    cmds.a3obSetFlag(component="face", value=456, name="generated_face_flag")

    before_uvs = uv_values(mesh)
    cmds.select(lod)
    cmds.a3obValidate()
    cmds.file(rename=str(path))
    cmds.file(exportAll=True, force=True, type="Arma P3D")
    cmds.file(new=True, force=True)
    cmds.file(str(path), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="generated")
    assert_generated_metadata()
    imported_meshes = cmds.ls("generated:*", type="mesh") or []
    if imported_meshes and uv_values(imported_meshes[0]) != before_uvs:
        raise RuntimeError("Generated UV values changed after roundtrip")
    print("OK generated DayZ-style P3D metadata workflow")


def assert_import_hierarchy(path):
    root = "p3d:" + path.stem.replace(".", "_")
    if not cmds.objExists(root):
        raise RuntimeError(f"Missing import root {root}")
    groups = set(cmds.listRelatives(root, children=True, type="transform") or [])
    if "p3d:Visuals" not in groups:
        raise RuntimeError(f"Missing Visuals group for {path.name}")
    lod_names = set()
    for group in groups:
        lod_names.update(cmds.listRelatives(group, children=True, type="transform") or [])
    if not any("Resolution" in name for name in lod_names):
        raise RuntimeError(f"Missing human-readable visual LOD names for {path.name}")
    if any(cmds.getAttr(node + ".a3obLodType") in (6, 14, 15) for node in cmds.ls(type="transform") or [] if cmds.attributeQuery("a3obIsLOD", node=node, exists=True)) and "p3d:Geometries" not in groups:
        raise RuntimeError(f"Missing Geometries group for {path.name}")


def assert_selected_export(selection, outdir, name):
    out = outdir / f"selected_{name}.p3d"
    cmds.select(selection, replace=True)
    cmds.file(rename=str(out))
    cmds.file(exportSelected=True, force=True, type="Arma P3D")
    cmds.file(new=True, force=True)
    cmds.file(str(out), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace=f"sel_{name}")
    exported = lod_counts()
    if len(exported) != 1:
        raise RuntimeError(f"Selected export {name} wrote {len(exported)} LODs: {exported}")


def assert_find_components():
    cmds.file(new=True, force=True)
    lod = cmds.a3obCreateLOD(lodType=6, resolution=0, name="components_lod")
    cube = cmds.polyCube(name="closed_component_cube", width=1, height=1, depth=1)[0]
    plane = cmds.polyPlane(name="open_component_plane", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.setAttr(plane + ".translateX", 3)
    cmds.parent(cube, lod)
    cmds.parent(plane, lod)

    cmds.select(cube + ".vtx[0]")
    stale_set = cmds.sets(cmds.ls(selection=True, flatten=True), name="a3ob_SEL_Component03")
    cmds.addAttr(stale_set, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(stale_set + ".a3obSelectionName", "Component03", type="string")

    cmds.select(plane + ".vtx[0]")
    unrelated_set = cmds.sets(cmds.ls(selection=True, flatten=True), name="a3ob_SEL_unrelated")
    cmds.addAttr(unrelated_set, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(unrelated_set + ".a3obSelectionName", "unrelated", type="string")

    cmds.select(lod, replace=True)
    cmds.a3obFindComponents()
    first_components = component_selection_sets()
    if [name for name, _ in first_components] != ["Component01"]:
        raise RuntimeError(f"Find Components created unexpected sets: {first_components}")
    cmds.a3obFindComponents()
    components = component_selection_sets()
    if [name for name, _ in components] != ["Component01"]:
        raise RuntimeError(f"Find Components rerun appended unexpected sets: {components}")
    if not cmds.objExists(unrelated_set):
        raise RuntimeError("Find Components deleted an unrelated Object Builder selection set")
    members = cmds.sets(components[0][1], query=True) or []
    expanded = cmds.ls(members, flatten=True) or []
    if sum(".vtx[" in item for item in expanded) != 8:
        raise RuntimeError(f"Find Components expected 8 cube vertices, got {expanded}")
    print("OK Find Components replaces Component## sets and skips open shells")


def assert_find_components_plain_mesh():
    cmds.file(new=True, force=True)
    cube = cmds.polyCube(name="plain_component_cube", width=1, height=1, depth=1)[0]
    cmds.select(cube, replace=True)
    cmds.a3obFindComponents()
    components = component_selection_sets()
    if [name for name, _ in components] != ["Component01"]:
        raise RuntimeError(f"Find Components did not support plain mesh selection: {components}")
    print("OK Find Components supports plain mesh selection")


def assert_export_scale_units(outdir):
    previous_unit = cmds.currentUnit(query=True, linear=True)
    try:
        cmds.currentUnit(linear="cm")
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="scale_units_cube", width=100, height=100, depth=100)[0]
        cmds.select(cube, replace=True)
        lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name="scale_units_lod")
        cmds.select(lod, replace=True)
        out = outdir / "scale_units_centimeter_scene.p3d"
        cmds.file(rename=str(out))
        cmds.file(exportSelected=True, force=True, type="Arma P3D", options="selectedOnly=1;applyTransforms=1")
        raw_extents = point_extents(raw_p3d_lod_points(out))
        if any(abs(value - 100.0) > 0.01 for value in raw_extents):
            raise RuntimeError(f"Raw centimeter-scene P3D export scale changed: extents={raw_extents}")
        cmds.file(new=True, force=True)
        cmds.currentUnit(linear="cm")
        cmds.file(str(out), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="scale")
        meshes = cmds.ls("scale:*", type="mesh") or []
        extents = mesh_extents(meshes)
        if any(abs(value - 100.0) > 0.01 for value in extents):
            raise RuntimeError(f"Centimeter-scene P3D reimport scale changed: extents={extents}")
        print("OK raw centimeter-scene P3D export preserves scale")
    finally:
        cmds.currentUnit(linear=previous_unit)


def assert_export_transform_bake(outdir):
    previous_unit = cmds.currentUnit(query=True, linear=True)
    try:
        cmds.currentUnit(linear="cm")
        cmds.file(new=True, force=True)
        lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name="transform_bake_lod")
        cube = cmds.polyCube(name="transform_bake_cube", width=100, height=100, depth=100)[0]
        cube_shape = cmds.listRelatives(cube, shapes=True, fullPath=True)[0]
        cmds.parent(cube_shape, lod, shape=True, relative=True)
        cmds.delete(cube)
        cmds.setAttr(lod + ".scaleX", 2)
        cmds.setAttr(lod + ".scaleY", 3)
        cmds.setAttr(lod + ".scaleZ", 4)
        cmds.setAttr(lod + ".translateX", 5)
        lod_shape = cmds.listRelatives(lod, shapes=True, fullPath=True)[0]
        expected_extents = mesh_extents([lod_shape])
        expected_center = mesh_center([lod_shape])
        cmds.select(lod, replace=True)
        out = outdir / "transform_bake_meter_scene.p3d"
        cmds.file(rename=str(out))
        cmds.file(exportSelected=True, force=True, type="Arma P3D", options="selectedOnly=1;applyTransforms=1")
        raw_points = raw_p3d_lod_points(out)
        raw_extents = point_extents(raw_points)
        raw_center = point_center(raw_points)
        expected_raw_extents = (expected_extents[0], expected_extents[2], expected_extents[1])
        expected_raw_center = (expected_center[0], -expected_center[2], expected_center[1])
        if any(abs(raw_extents[index] - expected_raw_extents[index]) > 0.01 for index in range(3)):
            raise RuntimeError(f"Raw P3D export did not bake transform scale: {raw_extents} != {expected_raw_extents}")
        if any(abs(raw_center[index] - expected_raw_center[index]) > 0.01 for index in range(3)):
            raise RuntimeError(f"Raw P3D export did not bake transform translation: {raw_center} != {expected_raw_center}")
        cmds.file(new=True, force=True)
        cmds.currentUnit(linear="cm")
        cmds.file(str(out), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="bake")
        meshes = cmds.ls("bake:*", type="mesh") or []
        extents = mesh_extents(meshes)
        center = mesh_center(meshes)
        expected_reimport_extents = expected_extents
        expected_reimport_center = expected_center
        if any(abs(extents[index] - expected_reimport_extents[index]) > 0.01 for index in range(3)):
            raise RuntimeError(f"P3D export did not bake transform scale: {extents} != {expected_reimport_extents}")
        if any(abs(center[index] - expected_reimport_center[index]) > 0.01 for index in range(3)):
            raise RuntimeError(f"P3D export did not bake transform translation: {center} != {expected_reimport_center}")
        print("OK raw P3D export bakes transforms at meter scale")
    finally:
        cmds.currentUnit(linear=previous_unit)


def assert_selected_export_modes(outdir):
    cases = [
        ("{lod}", "lod_transform"),
        ("{mesh}", "mesh_transform"),
        ("{mesh}.f[0]", "face_component"),
        ("{mesh}.vtx[0]", "vertex_component"),
    ]
    for selection, name in cases:
        cmds.file(new=True, force=True)
        first_lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name=f"{name}_first_lod")
        first_mesh = cmds.polyPlane(name=f"{name}_first_mesh", subdivisionsX=1, subdivisionsY=1)[0]
        cmds.parent(first_mesh, first_lod)
        second_lod = cmds.a3obCreateLOD(lodType=1, resolution=1, name=f"{name}_second_lod")
        second_mesh = cmds.polyPlane(name=f"{name}_second_mesh", subdivisionsX=1, subdivisionsY=1)[0]
        cmds.parent(second_mesh, second_lod)
        selection = selection.format(lod=first_lod, mesh=first_mesh)
        assert_selected_export(selection, outdir, name)


def assert_selection_set_export_modes(outdir):
    cases = [
        ("{mesh}", "mesh_set", 4),
        ("{mesh}.f[0]", "face_set", 4),
        ("{mesh}.vtx[0]", "vertex_set", 1),
    ]
    for selection, name, expected_vertices in cases:
        cmds.file(new=True, force=True)
        lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name=f"{name}_lod")
        mesh = cmds.polyPlane(name=f"{name}_mesh", subdivisionsX=1, subdivisionsY=1)[0]
        cmds.parent(mesh, lod)
        cmds.select(selection.format(mesh=mesh), replace=True)
        ui = runpy.run_path(str(UI_SCRIPT))
        components = ui["_canonical_selection_components"]()
        if len(components) != expected_vertices:
            raise RuntimeError(f"Canonical selection {name} expected {expected_vertices} vertices, got {components}")
        set_node = cmds.sets(components, name=f"a3ob_SEL_{name}")
        cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
        cmds.setAttr(set_node + ".a3obSelectionName", name, type="string")
        out = outdir / f"selection_set_{name}.p3d"
        cmds.file(rename=str(out))
        cmds.file(exportAll=True, force=True, type="Arma P3D")
        cmds.file(new=True, force=True)
        cmds.file(str(out), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace=f"set_{name}")
        counts = [item for item in selection_component_counts() if item[0] == name]
        if not counts or counts[0][1] != expected_vertices:
            raise RuntimeError(f"Selection set {name} did not roundtrip expected vertex count: {counts}")
        assert_object_builder_sets_hidden(f"selection set {name} import")
        for node in object_builder_set_nodes():
            if "_lod_SEL_" in node or "_mesh_SEL_" in node:
                raise RuntimeError(f"Imported selection set kept noisy LOD/mesh prefix: {node}")
    print("OK Object Builder selection sets export from mesh, face, and vertex selections")


def roundtrip_file(path, outdir):
    cmds.file(new=True, force=True)
    cmds.file(str(path), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="p3d")
    assert_import_hierarchy(path)
    if path.name == "sample_1_character.p3d":
        assert_y_up_character_orientation("p3d")
    before = lod_counts()
    before_selections = selection_component_counts()
    cmds.a3obValidate()
    out = outdir / path.name
    cmds.file(rename=str(out))
    cmds.file(exportAll=True, force=True, type="Arma P3D")
    cmds.file(new=True, force=True)
    cmds.file(str(out), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="rt")
    if path.name == "sample_1_character.p3d":
        assert_y_up_character_orientation("rt")
    after = lod_counts()
    after_selections = selection_component_counts()
    if before != after:
        raise RuntimeError(f"LOD counts changed for {path.name}: {before} != {after}")
    if before_selections != after_selections:
        raise RuntimeError(f"Selection counts changed for {path.name}: {before_selections} != {after_selections}")
    print(f"OK {path.name} lods={len(after)}")


def main():
    maya.standalone.initialize(name="python")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    DAYZ_OUTDIR.mkdir(parents=True, exist_ok=True)
    cmds.loadPlugin(str(PLUGIN), quiet=True)
    commands = set(cmds.pluginInfo("MayaObjectBuilder", query=True, command=True) or [])
    expected = {"a3obValidate", "a3obSetMass", "a3obSetMaterial", "a3obSetFlag", "a3obFindComponents", "a3obCreateLOD", "a3obProxy", "a3obNamedProperty", "a3obUpdateProxy"}
    missing = expected - commands
    if missing:
        raise RuntimeError(f"Missing commands: {sorted(missing)}")

    cmds.file(new=True, force=True)
    lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name="workflow_lod")
    mesh = cmds.polyPlane(name="workflow_mesh", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.parent(mesh, lod)
    cmds.select(mesh + ".f[0]")
    cmds.a3obProxy(path="proxy/workflow.p3d", index=1, fromSelection=True)
    if "proxy:proxy/workflow.p3d.1" not in proxy_selection_sets():
        raise RuntimeError("Proxy selection set was not created")
    cmds.select(lod)
    cmds.a3obValidate()

    assert_ui_redesign_helpers_load()
    assert_stale_selection_ui_refresh()
    assert_selection_manager_clear_all()
    assert_find_components()
    assert_find_components_plain_mesh()
    create_generated_fixture(OUTDIR / "generated_dayz_metadata.p3d")
    assert_export_scale_units(OUTDIR)
    assert_export_transform_bake(OUTDIR)
    assert_selected_export_modes(OUTDIR)
    assert_selection_set_export_modes(OUTDIR)

    for path in INPUTS:
        roundtrip_file(path, OUTDIR)

    dayz_inputs = optional_dayz_inputs()
    if dayz_inputs:
        for path in dayz_inputs:
            roundtrip_file(path, DAYZ_OUTDIR)
    else:
        print("SKIP optional DayZ P3D fixtures: set DAYZ_P3D_FIXTURES or add tests/inputs/dayz_p3d/*.p3d")

    maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
