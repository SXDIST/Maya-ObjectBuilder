"""Skinning panel of the MayaObjectBuilder dock: reference assets, weight transfer, pose test."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


def _weights_state():
    """What the LODs in scope actually hold. Read-only — panels must never write.

    The storage model (two hidden attribute slots, refreshed on save) is invisible, so the
    buttons used to demand the user track it in their head. This is what makes it visible.
    Kept to cheap attribute and history queries: it runs on every SelectionChanged.
    """
    lods = [node for node in cmds.ls(selection=True, long=True, type="transform") or []
            if cmds.attributeQuery("a3obIsLOD", node=node, exists=True)]
    scope = "selected"
    if not lods:
        lods = cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []
        scope = "scene"

    state = {"lods": len(lods), "scope": scope, "stored": 0, "previous": 0, "rigged": 0}
    for lod in lods:
        for key, attribute in (("stored", "a3obBakedWeights"),
                               ("previous", "a3obBakedWeightsPrevious")):
            if (cmds.attributeQuery(attribute, node=lod, exists=True)
                    and cmds.getAttr(lod + "." + attribute)):
                state[key] += 1
        shapes = cmds.listRelatives(lod, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []
        if shapes and cmds.ls(cmds.listHistory(shapes[0], pruneDagObjects=True) or [],
                              type="skinCluster"):
            state["rigged"] += 1
    return state


def _weights_state_text(state):
    """One line a rigger can act on, without knowing the storage model exists."""
    if not state["lods"]:
        return "No Object Builder LOD in the scene."

    where = "selected LOD" if state["scope"] == "selected" else "scene"
    if not state["stored"]:
        return ("No stored weights ({0}). Deleting the rig would lose them — "
                "bake, or just save the scene.".format(where))

    parts = ["Stored weights on {0}/{1} LOD(s)".format(state["stored"], state["lods"])]
    if state["previous"]:
        parts.append("older copy kept")
    if not state["rigged"]:
        parts.append("no rig bound - bind before restoring")
    elif state["previous"]:
        # store_bake pushes the older copy out the next time the live rig differs from the
        # stored one, which is one save away after a re-bind. Say so BEFORE it happens.
        parts.append("WARNING: the older copy is one save from being overwritten")
    return "  |  ".join(parts)


def _why_nothing_restored(which):
    """Name the actual reason a restore did nothing, instead of pointing at the log."""
    state = _weights_state()
    if not state["lods"]:
        return "Nothing restored: no Object Builder LOD selected."
    if which == "previous" and not state["previous"]:
        return "Nothing restored: there is no older copy stored."
    if which != "previous" and not state["stored"]:
        return "Nothing restored: no weights stored on the selected LOD(s)."
    if not state["rigged"]:
        return ("Nothing restored: the weights are safe, but there is no skinCluster to put "
                "them on. Bind the mesh to the skeleton first, then restore.")
    return "Nothing restored - see the script editor for why."


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

        layout.addWidget(_hint("The mesh keeps its own copy of the weights, refreshed every "
                               "time you save, so deleting the rig does not lose them. After "
                               "re-binding, Restore puts them back on the new skeleton."))
        # The state line is the point: the two attribute slots behind these buttons are
        # invisible, so without it the user has to track in their head whether a save has
        # happened since a re-bind in order to pick a button.
        self.weights_state_label = _hint("")
        layout.addWidget(self.weights_state_label)

        bake_row = qt_widgets.QHBoxLayout()
        bake_row.addWidget(_qt_button(
            "Restore Weights", self.run_restore_skin,
            "Write the stored weights back onto the current skinCluster, matching bones by "
            "name. Not undoable — what it replaces is kept as the older copy.",
            ":/undo_s.png"))
        # Hidden until it is the answer to a question the user has actually asked: it appears
        # after a restore ("not the copy you wanted?") or when the state shows an older copy
        # exists and the rig was re-bound. Two Restore buttons side by side was the thing
        # nobody could choose between.
        self.restore_previous_button = _qt_button(
            "Use the Older Copy", lambda: self.run_restore_skin(previous=True),
            "Restore the copy the last overwrite replaced — the way back when a save "
            "refreshed the stored weights from a rig you had just re-bound. Runs as a swap.",
            ":/undo.png")
        self.restore_previous_button.setVisible(False)
        bake_row.addWidget(self.restore_previous_button)
        bake_row.addWidget(_qt_button(
            "Bake Now", self.run_bake_skin,
            "Force a copy right now. Usually unnecessary — saving the scene does it — but "
            "useful just before deleting a rig if you have not saved since.",
            ":/save.png"))
        layout.addLayout(bake_row)

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
            "Stored the weights of {0} LOD(s) — they now survive deleting the rig.".format(baked)
            if baked else "Nothing stored: no skinned LOD found.")
        self.refresh_weights_state()

    def run_restore_skin(self, previous=False):
        restored = _restore_skin_weights(previous)
        which = "previous" if previous else "baked"
        if restored:
            self._set_skinning_summary(
                "Restored onto {0} LOD(s). Not what you expected? The copy it replaced is "
                "one click away.".format(restored) if not previous
                else "Restored the older copy onto {0} LOD(s). Running it again swaps "
                     "back.".format(restored))
            # Offer the way back only once there is something to go back to, and only after
            # the user has seen a result they might disagree with.
            self._show_restore_previous(True)
            self.refresh_weights_state()
            return
        # "see the script editor" sent people hunting for a bug that was not there. By far the
        # most common reason is restoring straight after an Unbind: restore WRITES weights into
        # a live skinCluster, so with no rig bound there is nothing to write onto. The stored
        # copy is untouched — say that, rather than leaving it looking like the bake was lost.
        self._set_skinning_summary(_why_nothing_restored(which))
        self.refresh_weights_state()

    def _show_restore_previous(self, visible):
        button = getattr(self, "restore_previous_button", None)
        if button is not None:
            button.setVisible(bool(visible))

    def refresh_weights_state(self):
        """Update the stored-weights line. Silent and read-only: runs on SelectionChanged."""
        label = getattr(self, "weights_state_label", None)
        if label is None:
            return
        state = _weights_state()
        label.setText(_weights_state_text(state))
        # Surface the older copy when it is likely to be the one wanted: a rig is bound and a
        # previous copy exists, which is exactly the post-re-bind situation.
        if state["previous"] and state["rigged"]:
            self._show_restore_previous(True)

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
