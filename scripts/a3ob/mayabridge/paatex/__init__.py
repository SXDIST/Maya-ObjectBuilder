"""Resolve + decode DayZ ``.paa`` textures and hook them onto Maya materials.

Maya can't read ``.paa``; on P3D import we resolve the texture path against a user-set texture
root, decode the largest mip (``a3ob.formats.paa``) to a cached PNG, and wire a ``file`` texture
into the material so the model shows textured (``createNode``, not ``shadingNode`` which returns
None during File > Import). Split by concern:

- ``settings``  — the ``MayaObjectBuilder_*`` optionVars (texture root, alpha-transparency toggle)
- ``resolve``   — turn a mod-relative P3D texture path into a real file on disk
- ``decode``    — decode PAA/normal/SMDI to cached PNGs (thread-safe numpy+zlib, no MImage)
- ``channels``  — resolve a material's colour/normal/spec channels from its ``.rvmat`` or siblings
- ``materials`` — wire the decoded textures onto aiStandardSurface/blinn + the deferred batch

This module is a facade re-exporting the public API so ``a3ob.mayabridge.paatex.<name>`` keeps
working (notably the ``translator.do_read`` ``evalDeferred`` string).
"""

from a3ob.mayabridge.paatex.settings import (
    TEXTURE_ROOT_VAR,
    ALPHA_VAR,
    texture_root,
    set_texture_root,
    alpha_transparency_enabled,
    set_alpha_transparency,
)
from a3ob.mayabridge.paatex.resolve import resolve_paa_path
from a3ob.mayabridge.paatex.decode import paa_to_png, decode_normal_png, decode_smdi_png
from a3ob.mayabridge.paatex.materials import (
    preferred_shader_type,
    assign_paa_texture,
    assign_pending_textures,
    apply_alpha_transparency_setting,
)

__all__ = [
    "TEXTURE_ROOT_VAR", "ALPHA_VAR", "texture_root", "set_texture_root",
    "alpha_transparency_enabled", "set_alpha_transparency", "apply_alpha_transparency_setting",
    "resolve_paa_path", "paa_to_png", "decode_normal_png", "decode_smdi_png",
    "preferred_shader_type", "assign_paa_texture", "assign_pending_textures",
]
