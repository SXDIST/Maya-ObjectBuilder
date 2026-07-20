"""Undo-queue context managers.

A leaf module on purpose: the export path needs these while running in
``a3ob.mayabridge``, which must never import from ``a3ob.ui`` (every module in
``a3ob.ui.actions`` does ``from a3ob.ui.entry import *``, so a mayabridge -> ui
import would risk that cycle). ``a3ob.ui._undo`` re-exports these under the
names its existing callers already use.
"""

import contextlib

import maya.cmds as cmds


@contextlib.contextmanager
def undo_chunk(name):
    """Group Maya operations into a single named undo chunk."""
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def undo_suspended():
    """Run a query without it landing in the undo queue, then restore the prior state.

    Restores what the caller had rather than forcing undo back on: a batch or
    non-interactive caller may have disabled it deliberately. Getting this backwards
    is what left Maya's undo queue dead for a whole session after one Validate click.
    """
    prior = cmds.undoInfo(query=True, state=True)
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        cmds.undoInfo(stateWithoutFlush=prior)


__all__ = ["undo_chunk", "undo_suspended"]
