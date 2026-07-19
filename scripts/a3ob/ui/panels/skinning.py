"""Skinning panel of the MayaObjectBuilder dock: reference assets, weight transfer, pose test."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class SkinningPanelMixin:
    def _build_skinning_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        layout.addWidget(_hint("Reference assets are saved once from your scene and dropped "
                               "into any other with one click."))
        reference_row = qt_widgets.QHBoxLayout()
        reference_row.addWidget(_qt_button(
            "Add Male Body", lambda: _add_reference_asset("male_body"),
            "Import the saved male body proxy (with its materials and skeleton).", ":/kinJoint.png"))
        reference_row.addWidget(_qt_button(
            "Add Skeleton", lambda: _add_reference_asset("skeleton"),
            "Import the saved DayZ skeleton on its own.", ":/kinJoint.png"))
        layout.addLayout(reference_row)

        save_row = qt_widgets.QHBoxLayout()
        save_row.addWidget(_qt_button(
            "Save Selection as Body", lambda: _save_reference_asset("male_body"),
            "Store the selected body as the reusable male reference.", ":/save.png"))
        save_row.addWidget(_qt_button(
            "Save Selection as Skeleton", lambda: _save_reference_asset("skeleton"),
            "Store the selected joint hierarchy as the reusable skeleton.", ":/save.png"))
        layout.addLayout(save_row)

        layout.addWidget(_hint("Select the garment, then transfer. Weights come from the body, "
                               "so the garment deforms with it; detached shells (pouches, "
                               "backpacks) are made rigid."))
        transfer_row = qt_widgets.QHBoxLayout()
        transfer_row.addWidget(qt_widgets.QLabel("Detached over"))
        self.skin_distance_field = qt_widgets.QLineEdit("0.06")
        self.skin_distance_field.setToolTip(
            "Distance from the body, in scene units, above which a shell counts as a separate "
            "rigid object. Measured on a DayZ character: fitted garments sit at 0.01-0.03, a "
            "backpack at 0.10.")
        self.skin_distance_field.setMaximumWidth(60)
        transfer_row.addWidget(self.skin_distance_field)
        transfer_row.addWidget(_qt_button(
            "Transfer Skin from Body", self.run_transfer_skin,
            "Bind the selected garment and copy DayZ weights from the reference body.",
            ":/smoothSkin.png"))
        layout.addLayout(transfer_row)

        layout.addWidget(_hint("Bad weights are invisible in bind pose. Test Pose bends the rig, "
                               "reports vertices that move unlike their neighbours, and puts "
                               "the skeleton back."))
        layout.addWidget(_qt_button(
            "Test Pose", self.run_test_pose,
            "Bend knees/elbows/shoulders, select deformation spikes, restore the pose.",
            ":/aselect.png"))

        layout.addWidget(_hint("Deleting the skeleton deletes the weights with it. Bake them "
                               "onto the LODs first and they survive — export falls back to "
                               "them when no skinCluster is left."))
        layout.addWidget(_qt_button(
            "Bake Weights onto LODs", self.run_bake_skin,
            "Copy the live skinCluster weights onto the LOD transforms before deleting a rig.",
            ":/save.png"))

        layout.addWidget(_hint("Bones driving the selected mesh. Filter narrows the list; "
                               "the buttons act on what you highlight in it. Removing a "
                               "bone moves its weight to the vertex's remaining bones — "
                               "weight is never deleted, only moved."))

        filter_row = qt_widgets.QHBoxLayout()
        filter_row.addWidget(qt_widgets.QLabel("Filter"))
        self.influence_filter = qt_widgets.QLineEdit(
            cmds.optionVar(query="MayaObjectBuilder_influence_filter")
            if cmds.optionVar(exists="MayaObjectBuilder_influence_filter") else "")
        self.influence_filter.setPlaceholderText("Face_*   (blank shows everything)")
        self.influence_filter.setToolTip(
            "Shell-style mask matched against the bone name, e.g. Face_* or Eye*. "
            "Leave blank to list every influence.")
        self.influence_filter.textChanged.connect(self.refresh_influences)
        filter_row.addWidget(self.influence_filter)
        layout.addLayout(filter_row)

        self.influence_list = qt_widgets.QListWidget()
        self.influence_list.setSelectionMode(
            qt_widgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.influence_list.setMaximumHeight(160)
        self.influence_list.setToolTip("Bones driving the selected mesh.")
        layout.addWidget(self.influence_list)

        influence_row = qt_widgets.QHBoxLayout()
        influence_row.addWidget(_qt_button(
            "Select Vertices", self.run_select_influence_vertices,
            "Select the vertices the highlighted bone actually drives.", ":/aselect.png"))
        influence_row.addWidget(_qt_button(
            "Remove", self.run_remove_influences,
            "Remove the highlighted bones; their weight moves to each vertex's remaining bones.",
            ":/delete.png"))
        layout.addLayout(influence_row)

        self.skinning_summary = _hint("")
        layout.addWidget(self.skinning_summary)
        return widget

    def run_transfer_skin(self):
        try:
            distance = float(self.skin_distance_field.text())
        except (ValueError, AttributeError):
            distance = 0.06
        done = _transfer_skin(distance)
        self._set_skinning_summary(
            "Transferred onto {0} mesh(es).".format(done) if done
            else "Nothing transferred — see the script editor for why.")

    def run_test_pose(self):
        spikes = _test_pose()
        self._set_skinning_summary(
            "No deformation spikes ✓" if spikes == 0
            else "{0} vertex(es) deform unlike their neighbours — selected.".format(spikes))

    def run_bake_skin(self):
        baked = _bake_skin_weights()
        self._set_skinning_summary(
            "Baked weights onto {0} LOD(s) — they now survive deleting the rig.".format(baked)
            if baked else "Nothing baked: no skinned LOD found.")

    def refresh_influences(self):
        """Repopulate the influence list from the selected mesh, keeping the highlight."""
        if getattr(self, "influence_list", None) is None:
            return
        from a3ob.mayabridge.influences import leaf_name, match_names

        # Restore by the FULL name (UserRole), never by displayed text: leaf names collide
        # across namespaces (ns1:Head / ns2:Head both show "Head"), which is exactly the case
        # where restoring by leaf would re-select an influence the user never highlighted.
        previously = {item.data(qt_core.Qt.ItemDataRole.UserRole) for item in self.influence_list.selectedItems()}
        names = _list_influences()
        pattern = self.influence_filter.text().strip() if self.influence_filter else ""
        shown = match_names(names, pattern) if pattern else names

        self.influence_list.clear()
        for name in shown:
            # The list shows the short, readable leaf name, but -removeInfluences matches
            # EXACTLY while -selectVertices only falls back to leaf matching (and refuses an
            # ambiguous bare leaf across namespaces/DAG paths). So the full name the command
            # needs travels as the item's data role; only the label is the trimmed leaf.
            item = qt_widgets.QListWidgetItem(leaf_name(name))
            item.setData(qt_core.Qt.ItemDataRole.UserRole, name)
            self.influence_list.addItem(item)
        for index in range(self.influence_list.count()):
            item = self.influence_list.item(index)
            if item.data(qt_core.Qt.ItemDataRole.UserRole) in previously:
                item.setSelected(True)

        cmds.optionVar(stringValue=("MayaObjectBuilder_influence_filter", pattern))

    def _highlighted_influences(self):
        return [item.data(qt_core.Qt.ItemDataRole.UserRole) for item in self.influence_list.selectedItems()]

    def run_select_influence_vertices(self):
        picked = self._highlighted_influences()
        if not picked:
            self._set_skinning_summary("Highlight a bone in the list first.")
            return
        count = _select_influence_vertices(picked[0])
        self._set_skinning_summary(
            "{0} drives {1} vertex(es) — selected.".format(picked[0], count) if count
            else "{0} drives no vertices worth exporting.".format(picked[0]))

    def run_remove_influences(self):
        picked = self._highlighted_influences()
        if not picked:
            self._set_skinning_summary("Highlight the bones to remove first.")
            return
        removed = _remove_influences(picked)
        self.refresh_influences()
        self._set_skinning_summary(
            "Removed {0} influence(s); weight moved to each vertex's remaining bones.".format(removed)
            if removed else "Nothing removed — see the script editor for why.")

    def _set_skinning_summary(self, text):
        if getattr(self, "skinning_summary", None) is not None:
            self.skinning_summary.setText(text)
