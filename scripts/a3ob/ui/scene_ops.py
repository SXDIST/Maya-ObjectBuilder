"""Facade re-exporting the a3ob.ui.scene package (kept for import stability)."""

from a3ob.ui.scene import attrs as _attrs
from a3ob.ui.scene import lods as _lods
from a3ob.ui.scene import selections as _selections
from a3ob.ui.scene import materials as _materials
from a3ob.ui.scene import memory as _memory

from a3ob.ui.scene.attrs import *  # noqa: F401,F403
from a3ob.ui.scene.lods import *  # noqa: F401,F403
from a3ob.ui.scene.selections import *  # noqa: F401,F403
from a3ob.ui.scene.materials import *  # noqa: F401,F403
from a3ob.ui.scene.memory import *  # noqa: F401,F403

# Aggregate __all__ so `from a3ob.ui.scene_ops import *` re-exports the underscore helpers.
__all__ = (_attrs.__all__ + _lods.__all__ + _selections.__all__
           + _materials.__all__ + _memory.__all__)
