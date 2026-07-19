import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class _IssueLog:
    """Collects validation issues (severity, node, message) while still printing them to
    the script editor, so the command can both log and return them for inline display."""

    def __init__(self):
        self.items = []

    def _record(self, severity, node, message):
        self.items.append((severity, node or "", message))

    def warn(self, node, message):
        self._record("warning", node, message)
        om.MGlobal.displayWarning("a3obValidate: %s%s" % (message, (" on " + node) if node else ""))

    def error(self, node, message):
        self._record("error", node, message)
        om.MGlobal.displayError("a3obValidate: %s%s" % (message, (" on " + node) if node else ""))

    @property
    def warnings(self):
        return sum(1 for severity, _, _ in self.items if severity == "warning")

    @property
    def errors(self):
        return sum(1 for severity, _, _ in self.items if severity == "error")

    def as_result(self):
        # "severity|node|message" rows — parsed by the Validation panel.
        return ["%s|%s|%s" % (severity, node, message) for severity, node, message in self.items]


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
        log = _IssueLog()

        if not lods:
            log.error("", "no LOD transforms found")
            self.setResult(log.as_result())
            return

        signatures = {}
        for lod in lods:
            name = om.MFnDependencyNode(lod).name()
            signature = attr.get_double(lod, A.RESOLUTION_SIGNATURE, 0.0)
            signatures[signature] = signatures.get(signature, 0) + 1
            if signatures[signature] > 1:
                log.warn(name, "duplicate LOD resolution signature")

            mesh = first_mesh_child(lod)
            source_vertex_count = attr.get_int(lod, A.SOURCE_VERTEX_COUNT, 0)
            source_face_count = attr.get_int(lod, A.SOURCE_FACE_COUNT, 0)
            if mesh.isNull() and source_vertex_count == 0 and source_face_count > 0:
                log.warn(name, "LOD has source faces but no mesh/source vertices")

            masses = split_semicolon(attr.get_string(lod, A.MASS_VALUES))
            if masses and len(masses) != vertex_count_for_lod(lod):
                log.warn(name, "mass count does not match vertex count")
            for mass in masses:
                try:
                    if float(mass) < 0.0:
                        log.error(name, "negative mass value")
                        break
                except ValueError:
                    log.error(name, "invalid mass value")
                    break

            proxy_selections = self._proxy_placeholder_selections(lod, name, log)

            if not mesh.isNull():
                self._validate_mesh(lod, mesh, name, source_face_count, proxy_selections, log)

        self._validate_bind_pose(log)

        om.MGlobal.displayInfo("a3obValidate: checked LODs=%d, warnings=%d, errors=%d" % (len(lods), log.warnings, log.errors))
        self.setResult(log.as_result())

    def _validate_bind_pose(self, log):
        """Warn when the rig is posed: export writes the deformed mesh, so the pose would be
        baked into the .p3d as though it were the model's shape."""
        from a3ob.mayabridge.posetest import skeleton_is_posed
        try:
            posed = skeleton_is_posed()
        except Exception as error:  # noqa: BLE001 - never let this break validation
            log.warn("", "could not check bind pose: %s" % error)
            return
        if posed:
            log.warn(posed[0].split("|")[-1],
                     "skeleton is not in bind pose (%d joint(s), e.g. %s) — exporting now "
                     "would bake the pose into the model"
                     % (len(posed), ", ".join(j.split("|")[-1] for j in posed[:3])))

    def _proxy_placeholder_selections(self, lod, lod_name, log):
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
                log.error(lod_name, "invalid proxy placeholder")
                continue
            if selection in proxy_selections:
                log.warn(lod_name, "duplicate proxy placeholder")
            proxy_selections.add(selection)
            if not proxy_selection_set_exists(selection):
                log.warn(lod_name, "proxy placeholder has no matching selection set")
        return proxy_selections

    def _validate_mesh(self, lod, mesh, name, source_face_count, proxy_selections, log):
        mesh_fn = om.MFnMesh(mesh)
        mesh_path = om.MFnDagNode(mesh).getPath()
        poly_it = om.MItMeshPolygon(mesh_path)
        while not poly_it.isDone():
            vertex_count = poly_it.polygonVertexCount()
            if vertex_count < 3:
                log.error(name, "face with fewer than 3 vertices")
                break
            if vertex_count > 4:
                log.warn(name, "N-gon face (%d verts) — will be auto-triangulated on export" % vertex_count)
            vertex_ids = poly_it.getVertices()
            if polygon_has_repeated_vertices(vertex_ids):
                log.error(name, "face uses repeated vertices")
                break
            if source_face_count == 0:
                points = poly_it.getPoints(om.MSpace.kObject)
                if polygon_has_near_zero_area(points):
                    log.warn(name, "near-zero-area face")
            poly_it.next()

        shaders, _indices = mesh_fn.getConnectedShaders(0)
        for shader in shaders:
            texture = attr.get_string(shader, A.TEXTURE)
            material = attr.get_string(shader, A.MATERIAL)
            if not is_ascii(texture) or not is_ascii(material):
                log.warn(name, "non-ASCII texture/material path")

        self._validate_skin_weights(mesh_path, name, log)
        self._validate_object_sets(mesh, name, proxy_selections, log)

    def _validate_skin_weights(self, mesh_path, name, log):
        """Flag vertices whose skin weights disagree with their neighbours — weight-transfer
        artefacts that stay invisible in bind pose but export as stray bone selections."""
        from a3ob.mayabridge.commands.skin import outliers_for_mesh
        try:
            outliers = outliers_for_mesh(mesh_path)
        except Exception as error:  # noqa: BLE001 - never let a skin read break validation
            log.warn(name, "could not read skin weights: %s" % error)
            return
        if outliers:
            log.warn(name, "%d skin weight outlier vertex(es) — a3obSkinWeights selects them; "
                           "fix with Skin > Smooth Skin Weights" % len(outliers))

    def _validate_object_sets(self, mesh, lod_name, proxy_placeholders, log):
        it = om.MItDependencyNodes(om.MFn.kSet)
        selection_names = set()
        while not it.isDone():
            set_obj = it.thisNode()
            if is_object_builder_metadata_set(set_obj):
                set_name = om.MFnDependencyNode(set_obj).name()
                if not metadata_set_has_live_members(set_obj):
                    log.warn(set_name, "Object Builder set has no live members and will be ignored")
                elif set_contains_mesh(set_obj, mesh):
                    selection_name = attr.get_string(set_obj, A.SELECTION_NAME)
                    if selection_name:
                        if selection_name in selection_names:
                            log.warn(lod_name, "duplicate selection name")
                        selection_names.add(selection_name)
                        if attr.get_bool(set_obj, A.IS_PROXY_SELECTION):
                            if not is_proxy_selection_name(selection_name):
                                log.error(lod_name, "invalid proxy selection name")
                            elif selection_name not in proxy_placeholders:
                                log.warn(lod_name, "proxy selection has no matching placeholder")
                    flag_component = attr.get_string(set_obj, A.FLAG_COMPONENT)
                    if flag_component and flag_component not in ("vertex", "face"):
                        log.error(lod_name, "invalid flag component type")
                    if flag_component and attr.get_int(set_obj, A.FLAG_VALUE, 0) == 0:
                        log.error(lod_name, "invalid zero flag value")
            it.next()
