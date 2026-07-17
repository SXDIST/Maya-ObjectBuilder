"""Resolve + decode DayZ ``.paa`` textures and hook them onto Maya materials.

Maya can't read ``.paa``; on P3D import we resolve the texture path against a user-set
texture root, decode the largest mip (``a3ob.formats.paa``), cache it as a PNG via
``MImage``, and wire a ``file`` texture into the material's colour so the model shows
textured. Uses ``createNode`` (not ``shadingNode``, which returns None during File>Import)
and numpy for the byte conversion.
"""

import os
import re
import hashlib

import maya.cmds as cmds

TEXTURE_ROOT_VAR = "MayaObjectBuilder_texture_root"
ALPHA_VAR = "MayaObjectBuilder_paa_alpha_transparency"
_CACHE_DIRNAME = "a3ob_paa_cache_v2"  # bumped: PNGs now carry an alpha-cutout sidecar


def texture_root():
    if cmds.optionVar(exists=TEXTURE_ROOT_VAR):
        return cmds.optionVar(query=TEXTURE_ROOT_VAR) or ""
    return ""


def set_texture_root(path):
    cmds.optionVar(stringValue=(TEXTURE_ROOT_VAR, path or ""))


def alpha_transparency_enabled():
    # Off by default: a DayZ _ca alpha is often a data channel (chainmail, spec) rather than
    # a geometry cut-out, and wiring it makes solid armour see-through. Opt-in for foliage.
    return bool(cmds.optionVar(query=ALPHA_VAR)) if cmds.optionVar(exists=ALPHA_VAR) else False


def set_alpha_transparency(enabled):
    cmds.optionVar(intValue=(ALPHA_VAR, 1 if enabled else 0))


_WALK_DIR_LIMIT = 20000  # guard: never walk an entire huge drive looking for a basename


def _candidate_roots():
    """Roots to try, in order: the configured texture root, then P:\\ (the standard
    Arma/DayZ work drive) so mod textures resolve even if the root points elsewhere."""
    roots = []
    configured = texture_root()
    if configured and os.path.isdir(configured):
        roots.append(configured)
    for drive_root in ("P:/", "P:\\"):
        if os.path.isdir(drive_root) and drive_root not in roots:
            roots.append(drive_root)
            break
    return roots


def resolve_paa_path(texture_path):
    """Resolve a P3D texture path (a mod-relative ``mod\\...\\x_co.paa``) to a real file:
    absolute hit, then ``<root>/relative`` for each candidate root, then a bounded basename
    search under the configured root."""
    if not texture_path:
        return None
    if os.path.isfile(texture_path):
        return texture_path
    relative = texture_path.replace("\\", "/").lstrip("/")
    for root in _candidate_roots():
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            return candidate
    # Last resort: search by file name, but only under the (bounded) configured root —
    # never under P:\\, which could be an enormous tree.
    configured = texture_root()
    if configured and os.path.isdir(configured):
        base = os.path.basename(relative).lower()
        scanned = 0
        for dirpath, _dirs, files in os.walk(configured):
            scanned += 1
            if scanned > _WALK_DIR_LIMIT:
                break
            for name in files:
                if name.lower() == base:
                    return os.path.join(dirpath, name)
    return None


def _cache_dir():
    directory = os.path.join(cmds.internalVar(userTmpDir=True), _CACHE_DIRNAME)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return directory


def _alpha_is_cutout(alpha_np):
    """True only for a genuine cut-out mask: alpha is bimodal (mostly 0 or 1) and has a
    real amount of fully-transparent pixels (foliage/hair). Solid materials whose _ca alpha
    is a mid-range data channel return False, so they are not made see-through."""
    total = alpha_np.size
    if total == 0:
        return False
    near0 = float((alpha_np < 0.05).sum()) / total
    near1 = float((alpha_np > 0.95).sum()) / total
    return (near0 + near1) > 0.9 and near0 > 0.02


def paa_to_png(paa_path):
    """Decode a .paa to a cached PNG (keyed by path+mtime). Returns (png_path, is_cutout)
    where is_cutout says whether the alpha is a real transparency mask."""
    key = hashlib.md5(("%s|%s" % (paa_path, os.path.getmtime(paa_path))).encode("utf8")).hexdigest()
    png = os.path.join(_cache_dir(), key + ".png")
    meta = png + ".cutout"
    if os.path.isfile(png):
        cutout = False
        try:
            with open(meta) as handle:
                cutout = handle.read().strip() == "1"
        except OSError:
            pass
        return png, cutout
    import numpy as np
    import maya.api.OpenMaya as om
    from a3ob.formats.paa import decode_largest_mip
    width, height, (red, green, blue, alpha) = decode_largest_mip(paa_path)
    channels = [np.frombuffer(c, dtype=np.float32) for c in (red, green, blue, alpha)]
    cutout = _alpha_is_cutout(channels[3])
    rgba = np.stack(channels, axis=1).reshape(height, width, 4)
    rgba = np.flipud(rgba)  # DXT decode is bottom-to-top; PNG/MImage want top-to-bottom
    buffer = np.clip(rgba * 255.0, 0, 255).astype(np.uint8).tobytes()
    image = om.MImage()
    image.setPixels(bytearray(buffer), width, height)
    image.writeToFile(png, "png")
    try:
        with open(meta, "w") as handle:
            handle.write("1" if cutout else "0")
    except OSError:
        pass
    return png, cutout


_FILE_LINKS = (
    ("outUV", "uvCoord"), ("outUvFilterSize", "uvFilterSize"), ("coverage", "coverage"),
    ("translateFrame", "translateFrame"), ("rotateFrame", "rotateFrame"),
    ("mirrorU", "mirrorU"), ("mirrorV", "mirrorV"), ("stagger", "stagger"),
    ("wrapU", "wrapU"), ("wrapV", "wrapV"), ("repeatUV", "repeatUV"), ("offset", "offset"),
    ("rotateUV", "rotateUV"), ("noiseUV", "noiseUV"), ("vertexUvOne", "vertexUvOne"),
    ("vertexUvTwo", "vertexUvTwo"), ("vertexUvThree", "vertexUvThree"),
    ("vertexCameraOne", "vertexCameraOne"),
)


def _make_file_texture(png, color_space):
    """Create a file+place2dTexture pair pointed at ``png``. createNode (not shadingNode) so
    it also works during File > Import."""
    file_node = cmds.createNode("file", skipSelect=True)
    place = cmds.createNode("place2dTexture", skipSelect=True)
    for src, dst in _FILE_LINKS:
        try:
            cmds.connectAttr("%s.%s" % (place, src), "%s.%s" % (file_node, dst), force=True)
        except RuntimeError:
            pass
    cmds.setAttr(file_node + ".fileTextureName", png, type="string")
    try:
        cmds.setAttr(file_node + ".colorSpace", color_space, type="string")
    except RuntimeError:
        pass
    return file_node


def _sibling_paa(texture_path, new_suffix):
    """Derive a sibling texture path by swapping the trailing _co/_ca suffix (e.g. the
    _nohq normal that shares the colour texture's base name). None if it doesn't apply."""
    if not texture_path:
        return None
    sibling = re.sub(r"_(co|ca)(\.paa)$", "_" + new_suffix + r"\2", texture_path, flags=re.IGNORECASE)
    return sibling if sibling != texture_path else None


def decode_normal_png(nohq_path):
    """Decode an Arma _nohq (DXT5nm: normal.X in alpha, normal.Y in green, Z reconstructed)
    into a proper tangent-space normal PNG. Cached (path+mtime)."""
    key = hashlib.md5(("N|%s|%s" % (nohq_path, os.path.getmtime(nohq_path))).encode("utf8")).hexdigest()
    png = os.path.join(_cache_dir(), key + "_n.png")
    if os.path.isfile(png):
        return png
    import numpy as np
    import maya.api.OpenMaya as om
    from a3ob.formats.paa import decode_largest_mip
    width, height, (_red, green, _blue, alpha) = decode_largest_mip(nohq_path)
    nx = np.frombuffer(alpha, dtype=np.float32) * 2.0 - 1.0
    ny = np.frombuffer(green, dtype=np.float32) * 2.0 - 1.0
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0.0, 1.0))
    ones = np.ones_like(nx)
    rgba = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5, ones], axis=1).reshape(height, width, 4)
    rgba = np.flipud(rgba)
    buffer = np.clip(rgba * 255.0, 0, 255).astype(np.uint8).tobytes()
    image = om.MImage()
    image.setPixels(bytearray(buffer), width, height)
    image.writeToFile(png, "png")
    return png


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
    import math
    return max(0.02, min(1.0, math.sqrt(2.0 / (power + 2.0))))


def _decoded_png(texture_path):
    """(png_path, is_cutout) for a texture path, or None when unresolved/undecodable."""
    resolved = resolve_paa_path(texture_path) if texture_path else None
    if not resolved:
        return None
    try:
        return paa_to_png(resolved)
    except Exception as exc:  # decode/format error — non-fatal
        cmds.warning("MayaObjectBuilder: PAA decode failed for %s: %s" % (texture_path, exc))
        return None


def preferred_shader_type():
    """aiStandardSurface when Arnold is loaded (full PBR: base/spec/normal), else blinn
    (specular + normalCamera), else lambert. Chosen at material-creation time on import."""
    try:
        if cmds.pluginInfo("mtoa", query=True, loaded=True):
            return "aiStandardSurface"
    except Exception:
        pass
    return "blinn"


def _wire_transparency(shader, color_file, is_ai):
    if is_ai:
        for comp in ("R", "G", "B"):
            try:
                cmds.connectAttr(color_file + ".outAlpha", "%s.opacity%s" % (shader, comp), force=True)
            except RuntimeError:
                pass
    else:
        try:
            cmds.connectAttr(color_file + ".outTransparency", shader + ".transparency", force=True)
        except RuntimeError:
            pass


def _wire_normal(shader, nohq_path, is_ai):
    normal_file = _make_file_texture(decode_normal_png(nohq_path), "Raw")
    if is_ai:
        normal_map = cmds.createNode("aiNormalMap", skipSelect=True)
        cmds.connectAttr(normal_file + ".outColor", normal_map + ".input", force=True)
        cmds.connectAttr(normal_map + ".outValue", shader + ".normalCamera", force=True)
    # Non-Arnold: skip the normal (bump2d can't take an RGB tangent normal reliably).


def _wire_specular(shader, channels, is_ai):
    spec_resolved = resolve_paa_path(channels["spec"]) if channels["spec"] else None
    spec_attr = "specularColor"
    if not cmds.attributeQuery(spec_attr, node=shader, exists=True):
        return
    if spec_resolved:
        spec_png, _cut = paa_to_png(spec_resolved)
        spec_file = _make_file_texture(spec_png, "Raw")
        try:
            cmds.connectAttr(spec_file + ".outColor", "%s.%s" % (shader, spec_attr), force=True)
        except RuntimeError:
            pass
    elif channels["specular"]:
        r, g, b = channels["specular"][:3]
        try:
            cmds.setAttr("%s.%s" % (shader, spec_attr), r, g, b, type="double3")
        except RuntimeError:
            pass
    if is_ai and cmds.attributeQuery("specularRoughness", node=shader, exists=True):
        try:
            cmds.setAttr(shader + ".specularRoughness", _roughness_from_power(channels["specular_power"]))
        except RuntimeError:
            pass


def assign_paa_texture(shader, texture_path, material_path=None):
    """Full material pipeline: decode the colour texture and (via the .rvmat, or _nohq/_smdi
    siblings) wire base colour, a reconstructed tangent normal, and specular onto ``shader``
    (aiStandardSurface / blinn / lambert). Alpha becomes transparency only for genuine
    cut-out masks and only when the opt-in is on. Returns True when colour was assigned."""
    if not texture_path or not texture_path.lower().endswith(".paa"):
        return False
    channels = _material_channels(texture_path, material_path)
    decoded = _decoded_png(channels["color"])
    if not decoded:
        return False
    png, is_cutout = decoded
    is_ai = cmds.nodeType(shader) == "aiStandardSurface"
    color_attr = "baseColor" if is_ai else "color"
    if not cmds.attributeQuery(color_attr, node=shader, exists=True):
        return False
    try:
        color_file = _make_file_texture(png, "sRGB")
        cmds.connectAttr(color_file + ".outColor", "%s.%s" % (shader, color_attr), force=True)
        if is_cutout and alpha_transparency_enabled():
            _wire_transparency(shader, color_file, is_ai)
    except RuntimeError as exc:
        cmds.warning("MayaObjectBuilder: could not assign colour %s: %s" % (texture_path, exc))
        return False

    normal_resolved = resolve_paa_path(channels["normal"]) if channels["normal"] else None
    if normal_resolved and cmds.attributeQuery("normalCamera", node=shader, exists=True):
        try:
            _wire_normal(shader, normal_resolved, is_ai)
        except Exception as exc:
            cmds.warning("MayaObjectBuilder: normal wiring failed: %s" % exc)
    try:
        _wire_specular(shader, channels, is_ai)
    except Exception:
        pass
    return True


def _color_attr(shader):
    return "baseColor" if cmds.nodeType(shader) == "aiStandardSurface" else "color"


def _clear_transparency(shader, color_file):
    if cmds.nodeType(shader) == "aiStandardSurface":
        for comp in ("R", "G", "B"):
            try:
                cmds.disconnectAttr(color_file + ".outAlpha", "%s.opacity%s" % (shader, comp))
            except RuntimeError:
                pass
        try:
            cmds.setAttr(shader + ".opacity", 1, 1, 1, type="double3")
        except RuntimeError:
            pass
    else:
        try:
            cmds.disconnectAttr(color_file + ".outTransparency", shader + ".transparency")
            cmds.setAttr(shader + ".transparency", 0, 0, 0, type="double3")
        except RuntimeError:
            pass


def apply_alpha_transparency_setting():
    """Add or remove the alpha->transparency link on every already-textured Object Builder
    material to match the current setting (so toggling the option updates the scene)."""
    enabled = alpha_transparency_enabled()
    for shader in cmds.ls(materials=True) or []:
        if not cmds.attributeQuery("a3obTexture", node=shader, exists=True):
            continue
        color_attr = _color_attr(shader)
        color_files = cmds.listConnections("%s.%s" % (shader, color_attr), source=True, type="file") or []
        if not color_files:
            continue
        color_file = color_files[0]
        resolved = resolve_paa_path(cmds.getAttr(shader + ".a3obTexture") or "")
        cutout = False
        if resolved:
            try:
                _png, cutout = paa_to_png(resolved)
            except Exception:
                cutout = False
        is_ai = cmds.nodeType(shader) == "aiStandardSurface"
        transp_attr = shader + (".opacityR" if is_ai else ".transparency")
        connected = bool(cmds.listConnections(transp_attr, source=True) or [])
        if enabled and cutout and not connected:
            _wire_transparency(shader, color_file, is_ai)
        elif connected and (not enabled or not cutout):
            _clear_transparency(shader, color_file)


def assign_pending_textures():
    """Wire the .paa channels onto every material that has a texture path but no colour file
    yet. Idempotent — run deferred after a P3D import (Maya's File > Import DG context blocks
    creating/connecting the file node inline). Returns the number of materials textured."""
    count = 0
    for shader in cmds.ls(materials=True) or []:
        if not cmds.attributeQuery("a3obTexture", node=shader, exists=True):
            continue
        color_attr = _color_attr(shader)
        if not cmds.attributeQuery(color_attr, node=shader, exists=True):
            continue
        texture = cmds.getAttr(shader + ".a3obTexture") or ""
        if not texture.lower().endswith(".paa"):
            continue
        if cmds.listConnections("%s.%s" % (shader, color_attr), source=True, type="file"):
            continue  # already textured
        material = ""
        if cmds.attributeQuery("a3obMaterial", node=shader, exists=True):
            material = cmds.getAttr(shader + ".a3obMaterial") or ""
        if assign_paa_texture(shader, texture, material or None):
            count += 1
    return count


__all__ = [
    "TEXTURE_ROOT_VAR", "ALPHA_VAR", "texture_root", "set_texture_root",
    "alpha_transparency_enabled", "set_alpha_transparency", "apply_alpha_transparency_setting",
    "resolve_paa_path", "paa_to_png", "decode_normal_png", "preferred_shader_type",
    "assign_paa_texture", "assign_pending_textures",
]
