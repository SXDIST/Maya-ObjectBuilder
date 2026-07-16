"""Reusable Qt widget helpers for the MayaObjectBuilder dock."""

import re

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import UI_MARGIN, UI_SPACING  # noqa: F401


def _qt_icon(name):
    if not QT_AVAILABLE or qt_gui is None or not name:
        return qt_gui.QIcon() if qt_gui is not None else None
    icon = qt_gui.QIcon(name)
    return icon if not icon.isNull() else qt_gui.QIcon()


_SELECTION_KIND_ICONS = {
    "Selection": ":/aselect.png",
    "Proxy": ":/out_reference.png",
    "Vertex Flag": ":/componentTag_vertex.png",
    "Face Flag": ":/polyFace.png",
}


def _qt_button(label, callback, tooltip="", icon=""):
    button = qt_widgets.QPushButton(label)
    if icon:
        qicon = _qt_icon(icon)
        if qicon is not None and not qicon.isNull():
            button.setIcon(qicon)
    if tooltip:
        button.setToolTip(tooltip)
    button.clicked.connect(callback)
    return button


def _icon_button(icon_name, fallback_text, tooltip):
    """Small square button showing a Maya icon, falling back to text if absent."""
    button = qt_widgets.QPushButton()
    icon = _qt_icon(icon_name)
    if icon is not None and not icon.isNull():
        button.setIcon(icon)
    else:
        button.setText(fallback_text)
    if tooltip:
        button.setToolTip(tooltip)
    button.setMaximumWidth(30)
    return button


def _picker_field(container):
    """Return the QLineEdit stored on a path picker built by _path_picker."""
    return getattr(container, "_line_edit", None) if container is not None else None


def _hint(text):
    """A wrapped, muted, slightly smaller secondary caption (no stylesheet)."""
    label = qt_widgets.QLabel(text)
    label.setWordWrap(True)
    if qt_gui is not None:
        pal = label.palette()
        muted = pal.color(qt_gui.QPalette.Disabled, qt_gui.QPalette.WindowText)
        pal.setColor(qt_gui.QPalette.WindowText, muted)
        label.setPalette(pal)
        font = label.font()
        if font.pointSizeF() > 0:
            font.setPointSizeF(font.pointSizeF() * 0.92)
        label.setFont(font)
    return label


def _panel_optionvar_key(title):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return "MayaObjectBuilder_panel_%s_expanded" % slug


class _CollapsibleSection(qt_widgets.QWidget):
    def __init__(self, title, collapsed=False, parent=None):
        super(_CollapsibleSection, self).__init__(parent)
        self._title = title
        self._key = _panel_optionvar_key(title)
        if cmds.optionVar(exists=self._key):
            collapsed = not bool(cmds.optionVar(query=self._key))

        header = qt_widgets.QFrame()
        header.setAutoFillBackground(True)
        if qt_gui is not None:
            pal = header.palette()
            pal.setColor(qt_gui.QPalette.Window, pal.color(qt_gui.QPalette.Mid))
            header.setPalette(pal)
        header_layout = qt_widgets.QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(6)

        self._btn = qt_widgets.QPushButton(("▶ " if collapsed else "▼ ") + title)
        self._btn.setFlat(True)
        self._btn.setCheckable(True)
        self._btn.setChecked(not collapsed)
        self._btn.setCursor(qt_core.Qt.PointingHandCursor)
        font = self._btn.font()
        font.setBold(True)
        self._btn.setFont(font)
        self._btn.setStyleSheet("")  # ensure no inherited stylesheet
        self._btn.setSizePolicy(qt_widgets.QSizePolicy.Expanding, qt_widgets.QSizePolicy.Preferred)
        header_layout.addWidget(self._btn)

        self._body = qt_widgets.QFrame()
        self._body.setFrameShape(qt_widgets.QFrame.NoFrame)
        self._body.setVisible(not collapsed)
        self.body_layout = qt_widgets.QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(12, 6, 4, 6)
        self.body_layout.setSpacing(UI_SPACING)

        outer = qt_widgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(header)
        outer.addWidget(self._body)
        self._btn.toggled.connect(self._on_toggle)

    def _on_toggle(self, checked):
        self._body.setVisible(checked)
        self._btn.setText(("▼ " if checked else "▶ ") + self._title)
        cmds.optionVar(intValue=(self._key, 1 if checked else 0))


__all__ = [
    "_qt_icon",
    "_SELECTION_KIND_ICONS",
    "_qt_button",
    "_icon_button",
    "_picker_field",
    "_hint",
    "_panel_optionvar_key",
    "_CollapsibleSection",
]
