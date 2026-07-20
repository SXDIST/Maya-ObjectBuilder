"""Maya-scene business logic package."""

from . import attrs as _attrs
from . import lods as _lods
from . import selections as _selections
from . import materials as _materials
from . import memory as _memory

from a3ob.ui.scene.attrs import *  # noqa: F401,F403
from a3ob.ui.scene.lods import *  # noqa: F401,F403
from a3ob.ui.scene.selections import *  # noqa: F401,F403
from a3ob.ui.scene.materials import *  # noqa: F401,F403
from a3ob.ui.scene.memory import *  # noqa: F401,F403

# Aggregate __all__ so `from a3ob.ui.scene import *` re-exports the underscore helpers.
__all__ = (_attrs.__all__ + _lods.__all__ + _selections.__all__
           + _materials.__all__ + _memory.__all__)
