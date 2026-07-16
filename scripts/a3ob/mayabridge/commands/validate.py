import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


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
