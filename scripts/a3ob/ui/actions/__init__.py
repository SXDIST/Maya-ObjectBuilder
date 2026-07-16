"""Action wrappers package (split by domain)."""

from a3ob.ui.actions import _common as _c
from a3ob.ui.actions import lod as _lod
from a3ob.ui.actions import metadata as _metadata
from a3ob.ui.actions import files as _files
from a3ob.ui.actions import selections as _selections
from a3ob.ui.actions import memory as _memory
from a3ob.ui.actions import named as _named
from a3ob.ui.actions import materials as _materials

from a3ob.ui.actions._common import *  # noqa: F401,F403
from a3ob.ui.actions.lod import *  # noqa: F401,F403
from a3ob.ui.actions.metadata import *  # noqa: F401,F403
from a3ob.ui.actions.files import *  # noqa: F401,F403
from a3ob.ui.actions.selections import *  # noqa: F401,F403
from a3ob.ui.actions.memory import *  # noqa: F401,F403
from a3ob.ui.actions.named import *  # noqa: F401,F403
from a3ob.ui.actions.materials import *  # noqa: F401,F403

# Aggregate __all__ so `from a3ob.ui.actions import *` re-exports the underscore wrappers.
__all__ = (_c.__all__ + _lod.__all__ + _metadata.__all__ + _files.__all__
           + _selections.__all__ + _memory.__all__ + _named.__all__ + _materials.__all__)
