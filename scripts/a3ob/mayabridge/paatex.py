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
    sibling = re.sub(r"_(co|ca)(\.paa)$", "_" + new_suffix + r"\2", texture_path, flags=re.IGNORECASE)
    return sibling if sibling != texture_path else None


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


def assign_paa_texture(shader, texture_path):
    """Decode ``texture_path`` and wire it onto ``shader`` as its colour file texture.
    Alpha is connected to transparency ONLY for genuine cut-out masks (foliage/hair) — a
    solid material whose _ca alpha is a data channel is left opaque, so nothing turns
    see-through. Returns True when the colour texture was assigned."""
    if not texture_path or not texture_path.lower().endswith(".paa"):
        return False
    decoded = _decoded_png(texture_path)
    if not decoded:
        return False
    png, is_cutout = decoded
    try:
        color_file = _make_file_texture(png, "sRGB")
        cmds.connectAttr(color_file + ".outColor", shader + ".color", force=True)
        if is_cutout and alpha_transparency_enabled():
            try:
                cmds.connectAttr(color_file + ".outTransparency", shader + ".transparency", force=True)
            except RuntimeError:
                pass
    except RuntimeError as exc:
        cmds.warning("MayaObjectBuilder: could not assign texture %s: %s" % (texture_path, exc))
        return False
    return True


def apply_alpha_transparency_setting():
    """Add or remove the alpha->transparency link on every already-textured Object Builder
    material to match the current setting (so toggling the option updates the scene)."""
    enabled = alpha_transparency_enabled()
    for shader in cmds.ls(materials=True) or []:
        if not cmds.attributeQuery("a3obTexture", node=shader, exists=True):
            continue
        if not cmds.attributeQuery("transparency", node=shader, exists=True):
            continue
        color_files = cmds.listConnections(shader + ".color", source=True, type="file") or []
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
        connected = cmds.listConnections(shader + ".transparency", source=True, type="file") or []
        if enabled and cutout and not connected:
            try:
                cmds.connectAttr(color_file + ".outTransparency", shader + ".transparency", force=True)
            except RuntimeError:
                pass
        elif connected and (not enabled or not cutout):
            try:
                cmds.disconnectAttr(color_file + ".outTransparency", shader + ".transparency")
                cmds.setAttr(shader + ".transparency", 0, 0, 0, type="double3")
            except RuntimeError:
                pass


def assign_pending_textures():
    """Wire the .paa colour texture onto every material that has a texture path but no
    colour file yet. Idempotent — run deferred after a P3D import (Maya's File > Import DG
    context blocks creating/connecting the file node inline, so it must happen afterwards).
    Returns the number of materials textured."""
    count = 0
    for shader in cmds.ls(materials=True) or []:
        if not cmds.attributeQuery("a3obTexture", node=shader, exists=True):
            continue
        if not cmds.attributeQuery("color", node=shader, exists=True):
            continue
        texture = cmds.getAttr(shader + ".a3obTexture") or ""
        if not texture.lower().endswith(".paa"):
            continue
        if cmds.listConnections(shader + ".color", source=True, type="file"):
            continue  # already textured
        if assign_paa_texture(shader, texture):
            count += 1
    return count


__all__ = [
    "TEXTURE_ROOT_VAR", "ALPHA_VAR", "texture_root", "set_texture_root",
    "alpha_transparency_enabled", "set_alpha_transparency", "apply_alpha_transparency_setting",
    "resolve_paa_path", "paa_to_png", "assign_paa_texture", "assign_pending_textures",
]
