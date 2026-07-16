"""Shared action helpers."""

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


__all__ = ["_undo_chunk"]
