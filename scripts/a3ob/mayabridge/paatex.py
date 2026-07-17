"""Resolve + decode DayZ ``.paa`` textures and hook them onto Maya materials.

Maya can't read ``.paa``; on P3D import we resolve the texture path against a user-set
texture root, decode the largest mip (``a3ob.formats.paa``), cache it as a PNG via
``MImage``, and wire a ``file`` texture into the material's colour so the model shows
textured. Uses ``createNode`` (not ``shadingNode``, which returns None during File>Import)
and numpy for the byte conversion.
"""

import os
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


def resolve_paa_path(texture_path):
    """Resolve a P3D texture path (usually a mod-relative ``dz\\...\\x_co.paa``) to a real
    file: absolute hit, then ``root/relative``, then a basename search under the root."""
    if not texture_path:
        return None
    if os.path.isfile(texture_path):
        return texture_path
    root = texture_root()
    if not root or not os.path.isdir(root):
        return None
    relative = texture_path.replace("\\", "/").lstrip("/")
    candidate = os.path.join(root, relative)
    if os.path.isfile(candidate):
        return candidate
    base = os.path.basename(relative).lower()
    for dirpath, _dirs, files in os.walk(root):
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


def assign_paa_texture(shader, texture_path):
    """Resolve+decode ``texture_path`` and connect it as ``shader``'s colour file texture.
    Returns True when a texture was assigned, False otherwise (path unresolved / not .paa /
    decode failed) — callers keep the plain lambert in that case."""
    if not texture_path or not texture_path.lower().endswith(".paa"):
        return False
    resolved = resolve_paa_path(texture_path)
    if not resolved:
        return False
    try:
        png = paa_to_png(resolved)
    except Exception as exc:  # decode/format error — keep going with a plain material
        cmds.warning("MayaObjectBuilder: PAA decode failed for %s: %s" % (texture_path, exc))
        return False
    try:
        # createNode (not shadingNode) so this also works during File > Import.
        file_node = cmds.createNode("file", skipSelect=True)
        place = cmds.createNode("place2dTexture", skipSelect=True)
        for src, dst in _FILE_LINKS:
            try:
                cmds.connectAttr("%s.%s" % (place, src), "%s.%s" % (file_node, dst), force=True)
            except RuntimeError:
                pass
        cmds.setAttr(file_node + ".fileTextureName", png, type="string")
        try:
            cmds.setAttr(file_node + ".colorSpace", "sRGB", type="string")
        except RuntimeError:
            pass
        cmds.connectAttr(file_node + ".outColor", shader + ".color", force=True)
    except RuntimeError as exc:
        cmds.warning("MayaObjectBuilder: could not assign texture %s: %s" % (texture_path, exc))
        return False
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
