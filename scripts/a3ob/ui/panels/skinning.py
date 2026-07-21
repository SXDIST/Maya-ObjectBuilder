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

        layout.addWidget(_qt_button(
            "Add Male Character", lambda: _add_reference_asset("male_body"),
            "Import the saved male character — mesh, materials and skeleton. "
            "Reference assets live in the MayaObjectBuilder menu under Reference Assets.",
            ":/kinJoint.png"))
        layout.addWidget(_qt_button(
            "Transfer Skin from Body", self.run_transfer_skin,
            "Select the garment, then transfer: weights come from the reference body so the "
            "garment deforms with it, and detached shells (pouches, backpacks) are made rigid. "
            "Scripted callers can override the detachment threshold with "
            "a3obTransferSkin -distance.",
            ":/smoothSkin.png"))
        layout.addWidget(_qt_button(
            "Test Pose", self.run_test_pose,
            "Bad weights are invisible in bind pose. This bends knees/elbows/shoulders, selects "
            "vertices that deform unlike their neighbours, and restores the pose.",
            ":/aselect.png"))

        layout.addWidget(_qt_button(
            "Select Skin Outliers", self.run_skin_weights,
            "Select vertices whose weights disagree with their neighbours — transfer "
            "artefacts, invisible in bind pose. Fix them with Skin > Smooth Skin Weights.",
            ":/aselect.png"))

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
        self.influence_list.setToolTip(
            "Bones driving the selected mesh. Clicking one while Paint Skin Weights is "
            "active makes it the bone you are painting.")
        self.influence_list.itemSelectionChanged.connect(self.on_influence_highlighted)
        layout.addWidget(self.influence_list)

        influence_row = qt_widgets.QHBoxLayout()
        influence_row.addWidget(_qt_button(
            "Select Vertices", self.run_select_influence_vertices,
            "Select the vertices the highlighted bone actually drives.", ":/aselect.png"))
        influence_row.addWidget(_qt_button(
            "Remove", self.run_remove_influences,
            "Remove the highlighted bones. Their weight moves to each vertex's remaining bones "
            "— weight is never deleted, only redistributed.",
            ":/delete.png"))
        layout.addLayout(influence_row)

        self.skinning_summary = _hint("")
        layout.addWidget(self.skinning_summary)
        return widget

    def run_transfer_skin(self):
        meshes, rigid = _transfer_skin()
        if not meshes:
            self._set_skinning_summary("Nothing transferred — see the script editor for why.")
            return
        # Report zero distinctly from a count: with the distance field gone, this line is the
        # only signal that a shell was classified as detached, and "0 rigid" has to be
        # readable as "nothing was treated as detached" rather than as an absent number.
        self._set_skinning_summary(
            "Transferred onto {0} mesh(es); {1} shell(s) made rigid.".format(meshes, rigid)
            if rigid else
            "Transferred onto {0} mesh(es); none detached.".format(meshes))

    def run_test_pose(self):
        spikes = _test_pose()
        self._set_skinning_summary(
            "No deformation spikes ✓" if spikes == 0
            else "{0} vertex(es) deform unlike their neighbours — selected.".format(spikes))

    def run_skin_weights(self):
        count = _run_skin_weights()
        self._set_skinning_summary(
            "No skin weight outliers found ✓" if count == 0
            else "Selected {0} outlier vertex(es) — fix with Skin > Smooth Skin "
                 "Weights.".format(count))

    def refresh_influences(self):
        """Repopulate the influence list from the selected mesh, keeping the highlight."""
        if getattr(self, "influence_list", None) is None:
            return
        from a3ob.mayabridge.influences import leaf_name, match_names

        # Rebuilding clears and re-selects rows, which fires itemSelectionChanged for every
        # one of them. Without this guard a refresh would re-point the paint tool at whatever
        # row happened to be restored last.
        self._influence_refreshing = True
        try:
            self._rebuild_influence_list(leaf_name, match_names)
        finally:
            self._influence_refreshing = False

    def _rebuild_influence_list(self, leaf_name, match_names):

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

    def on_influence_highlighted(self):
        """Point Paint Skin Weights at the clicked bone.

        Clicking a row here should do what clicking a row in the tool's own influence list
        does — otherwise you pick a bone in one panel and keep painting another. Only for a
        single highlighted row: painting has exactly one active influence, so a multi-select
        (which is what Remove is for) has no meaningful answer. A no-op when the paint tool
        is not the current context."""
        if getattr(self, "_influence_refreshing", False):
            return
        picked = self._highlighted_influences()
        if len(picked) != 1:
            return
        _paint_influence(picked[0])

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
