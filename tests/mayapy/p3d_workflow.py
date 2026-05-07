import os
import runpy
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


def mesh_extents(meshes):
    points = []
    for mesh in meshes:
        raw = cmds.xform(mesh + ".vtx[*]", query=True, translation=True, worldSpace=True) or []
        points.extend((float(raw[index]), float(raw[index + 1]), float(raw[index + 2])) for index in range(0, len(raw), 3))
    if not points:
        raise RuntimeError("No mesh vertices found for axis orientation check")
    xs, ys, zs = zip(*points)
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


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
    cmds.delete(set_node)
    if ui["_live_set_members"](set_node):
        raise RuntimeError("Deleted selection set still returned live members")
    if any(item["node"] == set_node for item in ui["_selection_sets"]()):
        raise RuntimeError("Deleted selection set remained in live Selection Manager data")
    cmds.a3obValidate()
    print("OK stale Selection Manager data is pruned after deletion")


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
    expected = {"a3obValidate", "a3obSetMass", "a3obSetMaterial", "a3obSetFlag", "a3obCreateLOD", "a3obProxy", "a3obNamedProperty", "a3obUpdateProxy"}
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

    assert_stale_selection_ui_refresh()
    create_generated_fixture(OUTDIR / "generated_dayz_metadata.p3d")
    assert_selected_export_modes(OUTDIR)

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
