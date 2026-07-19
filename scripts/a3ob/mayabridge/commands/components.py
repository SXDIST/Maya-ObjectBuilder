import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


class FindComponentsCommand(_Base):
    kName = "a3obFindComponents"

    @staticmethod
    def creator():
        return FindComponentsCommand()

    @staticmethod
    def syntax():
        return om.MSyntax()

    def doIt(self, args):
        # One Ctrl+Z must undo the whole command, not each cmds call inside it.
        with undo_chunk():
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
        attr.mark_technical_set(set_obj)
