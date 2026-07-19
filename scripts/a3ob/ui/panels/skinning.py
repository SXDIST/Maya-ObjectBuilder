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

    def _set_skinning_summary(self, text):
        if getattr(self, "skinning_summary", None) is not None:
            self.skinning_summary.setText(text)
