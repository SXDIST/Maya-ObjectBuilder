"""P3D MLOD -> Maya DAG/mesh conversion (OpenMaya 2.0).

Port of ``src/maya/MayaMeshImport.cpp``. Builds a root transform named after the file,
groups LODs by category, and for each LOD creates a mesh (shape directly under the LOD
transform), applies UVs/custom normals, materials, selection/flag sets, proxy
placeholders, Memory-LOD locators and the ``a3ob*`` round-trip metadata.

Coordinate convention: P3D (Z-up) -> Maya (Y-up) point ``(x, y, z) -> (x, z, -y)``.
"""

import os
import re

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.import_.convert import *  # noqa: F401,F403
from a3ob.mayabridge.import_.builders import *  # noqa: F401,F403

class MayaMeshImport:
    def __init__(self):
        self._materials = {}  # (texture, material) -> shading group name

    def import_mlod(self, mlod, source_name):
        created = []
        stem = os.path.splitext(os.path.basename(source_name))[0]
        root_name = _create_transform(None, sanitized_name(stem))

        groups = {}
        for lod in mlod.lods:
            group_name = lod_group_name(lod.resolution.lod)
            group = groups.get(group_name)
            if group is None:
                group = _create_transform(root_name, group_name)
                groups[group_name] = group
            self._import_lod(lod, group, created)
        return created

    def _get_or_create_material(self, texture, material):
        key = (texture, material)
        existing = self._materials.get(key)
        if existing is not None:
            return existing
        # createNode (not shadingNode) so material creation also works during a
        # File > Import operation, where shadingNode's UI/hypershade work returns None.
        shader = cmds.createNode("lambert", name=material_node_name(texture, material))
        # Register in the default shader list — shadingNode does this automatically, but
        # createNode does not, and without it cmds.ls(materials=True)/Hypershade don't see the
        # node as a material, so the Materials panel showed it as "No material".
        if cmds.objExists("defaultShaderList1"):
            cmds.connectAttr(shader + ".message", "defaultShaderList1.shaders", nextAvailable=True, force=True)
        shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + "SG")
        cmds.connectAttr(shader + ".outColor", shading_group + ".surfaceShader", force=True)
        shader_obj = _name_to_object(shader)
        sg_obj = _name_to_object(shading_group)
        attr.set_string(shader_obj, A.TEXTURE, texture)
        attr.set_string(shader_obj, A.MATERIAL, material)
        attr.set_string(sg_obj, A.SG_TEXTURE, texture)
        attr.set_string(sg_obj, A.SG_MATERIAL, material)
        self._materials[key] = shading_group
        return shading_group

    def _assign_materials(self, mesh, lod):
        mesh_path = om.MFnDagNode(mesh).getPath()
        face_groups = {}
        for face_index, face in enumerate(lod.faces):
            key = (face.texture.replace("/", "\\"), face.material.replace("/", "\\"))
            face_groups.setdefault(key, []).append(face_index)

        for key in sorted(face_groups):
            shading_group = self._get_or_create_material(key[0], key[1])
            component_fn = om.MFnSingleIndexedComponent()
            faces = component_fn.create(om.MFn.kMeshPolygonComponent)
            component_fn.addElements(om.MIntArray(face_groups[key]))
            members = om.MSelectionList()
            members.add((mesh_path, faces))
            om.MFnSet(_name_to_object(shading_group)).addMembers(members)

    def _import_lod(self, lod, parent_name, created):
        transform_name = _create_transform(parent_name, lod_name(lod.resolution))

        vertex_source_indices = []
        if lod.faces:
            vertex_remap = {}
            for face in lod.faces:
                for vi in face.vertices:
                    if vi not in vertex_remap:
                        vertex_remap[vi] = len(vertex_remap)

            vertex_source_indices = [0] * len(vertex_remap)
            for source_index, imported_index in vertex_remap.items():
                vertex_source_indices[imported_index] = source_index

            points = om.MPointArray()
            points.setLength(len(vertex_remap))
            for source_index, imported_index in vertex_remap.items():
                if source_index >= len(lod.vertices):
                    raise ValueError("P3D face references a vertex outside the LOD vertex table")
                points[imported_index] = core_to_maya_point(lod.vertices[source_index].position)

            face_counts = om.MIntArray()
            face_connects = om.MIntArray()
            for face in lod.faces:
                face_counts.append(len(face.vertices))
                for vi in face.vertices:
                    face_connects.append(vertex_remap[vi])

            transform_obj = _name_to_object(transform_name)
            mesh_fn = om.MFnMesh()
            mesh = mesh_fn.create(points, face_counts, face_connects, parent=transform_obj)
            cmds.rename(om.MFnDagNode(mesh).fullPathName(), _leaf(transform_name) + "Shape")

            apply_uvs(mesh_fn, lod)
            apply_normals(mesh_fn, lod, vertex_remap)
            self._assign_materials(mesh, lod)
            create_selection_sets(mesh, lod, vertex_remap)
            create_flag_sets(mesh, lod, vertex_remap)

        create_proxy_placeholders(transform_name, _leaf(transform_name), lod)

        # Memory LODs carry their named points as single-vertex selections. Reconstruct
        # them as locators whether or not the LOD also contains helper faces — otherwise
        # points on a Memory LOD that happens to have geometry are silently dropped.
        if lod.resolution.lod == 9:
            create_locators_for_memory_lod(transform_name, lod)

        set_lod_metadata(_name_to_object(transform_name), lod,
                         vertex_source_indices if vertex_source_indices else None)
        created.append(transform_name)


__all__ = [
    "MayaMeshImport",
]
