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
_CACHE_DIRNAME = "a3ob_paa_cache"


def texture_root():
    if cmds.optionVar(exists=TEXTURE_ROOT_VAR):
        return cmds.optionVar(query=TEXTURE_ROOT_VAR) or ""
    return ""


def set_texture_root(path):
    cmds.optionVar(stringValue=(TEXTURE_ROOT_VAR, path or ""))


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


def paa_to_png(paa_path):
    """Decode a .paa to a cached PNG (keyed by path+mtime) and return the PNG path."""
    key = hashlib.md5(("%s|%s" % (paa_path, os.path.getmtime(paa_path))).encode("utf8")).hexdigest()
    png = os.path.join(_cache_dir(), key + ".png")
    if os.path.isfile(png):
        return png
    import numpy as np
    import maya.api.OpenMaya as om
    from a3ob.formats.paa import decode_largest_mip
    width, height, (red, green, blue, alpha) = decode_largest_mip(paa_path)
    channels = [np.frombuffer(c, dtype=np.float32) for c in (red, green, blue, alpha)]
    rgba = np.stack(channels, axis=1).reshape(height, width, 4)
    rgba = np.flipud(rgba)  # DXT decode is bottom-to-top; PNG/MImage want top-to-bottom
    buffer = np.clip(rgba * 255.0, 0, 255).astype(np.uint8).tobytes()
    image = om.MImage()
    image.setPixels(bytearray(buffer), width, height)
    image.writeToFile(png, "png")
    return png


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
    resolved = resolve_paa_path(texture_path) if texture_path else None
    if not resolved:
        return None
    try:
        return paa_to_png(resolved)
    except Exception as exc:  # decode/format error — non-fatal
        cmds.warning("MayaObjectBuilder: PAA decode failed for %s: %s" % (texture_path, exc))
        return None


def assign_paa_texture(shader, texture_path):
    """Decode ``texture_path`` and wire it onto ``shader``: colour + alpha transparency, and
    (best-effort) the sibling ``_nohq`` normal as a tangent bump. Returns True when the
    colour texture was assigned. Failures are non-fatal — the plain material stays."""
    if not texture_path or not texture_path.lower().endswith(".paa"):
        return False
    png = _decoded_png(texture_path)
    if not png:
        return False
    try:
        color_file = _make_file_texture(png, "sRGB")
        cmds.connectAttr(color_file + ".outColor", shader + ".color", force=True)
        # Alpha -> transparency (foliage / _ca cut-outs). Opaque textures decode alpha=1
        # so transparency stays 0; safe to always wire.
        try:
            cmds.connectAttr(color_file + ".outTransparency", shader + ".transparency", force=True)
        except RuntimeError:
            pass
    except RuntimeError as exc:
        cmds.warning("MayaObjectBuilder: could not assign texture %s: %s" % (texture_path, exc))
        return False

    # Sibling normal map (_nohq) -> tangent bump on normalCamera (best effort; Arma's
    # channel swizzle is not fully reproduced, so this is approximate surface detail).
    if cmds.attributeQuery("normalCamera", node=shader, exists=True):
        normal_png = _decoded_png(_sibling_paa(texture_path, "nohq"))
        if normal_png:
            try:
                normal_file = _make_file_texture(normal_png, "Raw")
                bump = cmds.createNode("bump2d", skipSelect=True)
                cmds.setAttr(bump + ".bumpInterp", 1)  # Tangent Space Normals
                cmds.connectAttr(normal_file + ".outAlpha", bump + ".bumpValue", force=True)
                cmds.connectAttr(bump + ".outNormal", shader + ".normalCamera", force=True)
            except RuntimeError:
                pass
    return True


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
    "TEXTURE_ROOT_VAR", "texture_root", "set_texture_root",
    "resolve_paa_path", "paa_to_png", "assign_paa_texture", "assign_pending_textures",
]
