"""Resolve a material's texture channels from its ``.rvmat`` (or ``_nohq``/``_smdi`` siblings)."""

import re
import math

from a3ob.mayabridge.paatex.resolve import resolve_paa_path


def _sibling_paa(texture_path, new_suffix):
    """Derive a sibling texture path by swapping the trailing _co/_ca suffix (e.g. the
    _nohq normal that shares the colour texture's base name). None if it doesn't apply."""
    if not texture_path:
        return None
    sibling = re.sub(r"_(co|ca)(\.paa)$", "_" + new_suffix + r"\2", texture_path, flags=re.IGNORECASE)
    return sibling if sibling != texture_path else None


def _material_channels(color_texture, material_path):
    """Resolve the material's channels: {color, normal, spec} texture paths + flat
    {specular, specular_power}. Prefers the .rvmat (exact stage textures); falls back to the
    _nohq/_smdi siblings of the colour texture when no rvmat is available."""
    channels = {"color": color_texture, "normal": None, "spec": None,
                "specular": None, "specular_power": None}
    rvmat = None
    if material_path and material_path.lower().endswith(".rvmat"):
        rvmat = resolve_paa_path(material_path)
    if rvmat:
        try:
            from a3ob.formats.rvmat import parse_rvmat_file
            parsed = parse_rvmat_file(rvmat)
            textures = parsed["textures"]
            if textures.get("color"):
                channels["color"] = textures["color"]
            channels["normal"] = textures.get("normal")
            channels["spec"] = textures.get("spec")
            channels["specular"] = parsed["specular"]
            channels["specular_power"] = parsed["specular_power"]
        except Exception:
            pass
    if not channels["normal"]:
        channels["normal"] = _sibling_paa(color_texture, "nohq")
    if not channels["spec"]:
        channels["spec"] = _sibling_paa(color_texture, "smdi")
    return channels


def _roughness_from_power(power):
    if not power or power <= 0:
        return 0.35
    return max(0.02, min(1.0, math.sqrt(2.0 / (power + 2.0))))
