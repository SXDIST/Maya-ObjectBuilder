"""Guarded PySide6 / shiboken / OpenMayaUI import layer for the UI package."""

import importlib

try:
    omui = importlib.import_module("maya.OpenMayaUI")
    shiboken = importlib.import_module("shiboken6")
    wrapInstance = shiboken.wrapInstance
    qt_is_valid = shiboken.isValid
    qt_widgets = importlib.import_module("PySide6.QtWidgets")
    qt_core = importlib.import_module("PySide6.QtCore")
    qt_gui = importlib.import_module("PySide6.QtGui")
    QT_AVAILABLE = True
except ImportError:
    omui = None
    wrapInstance = None
    qt_is_valid = None
    qt_widgets = None
    qt_core = None
    qt_gui = None
    QT_AVAILABLE = False


__all__ = [
    "omui",
    "shiboken",
    "wrapInstance",
    "qt_is_valid",
    "qt_widgets",
    "qt_core",
    "qt_gui",
    "QT_AVAILABLE",
]
