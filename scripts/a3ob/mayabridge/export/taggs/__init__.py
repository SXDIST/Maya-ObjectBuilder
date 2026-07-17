"""P3D TAGG builders for export: data (property/mass/selection/flag/sharp/UVSet),
memory (locators), skin (skinCluster -> weighted bone selections), lodexport (per-LOD)."""

from a3ob.mayabridge.export.taggs import data as _data
from a3ob.mayabridge.export.taggs import memory as _memory
from a3ob.mayabridge.export.taggs import skin as _skin
from a3ob.mayabridge.export.taggs import lodexport as _lodexport

from a3ob.mayabridge.export.taggs.data import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs.memory import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs.skin import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs.lodexport import *  # noqa: F401,F403

__all__ = (_data.__all__ + _memory.__all__ + _skin.__all__ + _lodexport.__all__)
