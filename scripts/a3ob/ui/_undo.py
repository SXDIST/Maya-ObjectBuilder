"""Undo-queue context managers.

A leaf module on purpose: ``a3ob.ui.actions`` cannot host these because every
module in that package does ``from a3ob.ui.entry import *``, so importing anything
from it inside ``entry`` would run the package __init__ against a half-built
``entry`` namespace.
"""

import contextlib

import maya.cmds as cmds


@contextlib.contextmanager
def _undo_chunk(name):
    """Group Maya operations into a single named undo chunk."""
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def _undo_suspended():
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


__all__ = ["_undo_chunk", "_undo_suspended"]
