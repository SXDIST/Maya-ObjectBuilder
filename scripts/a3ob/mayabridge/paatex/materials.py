"""Wire decoded PAA textures onto Maya materials and texture a freshly-imported model.

``assign_paa_texture`` builds the base-colour / normal / specular network for one shader;
``assign_pending_textures`` is the deferred batch run after a P3D import, with
``_prefetch_pending`` decoding every channel in a thread pool first so the wiring is cache-only.
"""

import maya.cmds as cmds

from a3ob.mayabridge.paatex.settings import alpha_transparency_enabled
from a3ob.mayabridge.paatex.resolve import resolve_paa_path
from a3ob.mayabridge.paatex.decode import _cache_dir, paa_to_png, decode_normal_png, decode_smdi_png
from a3ob.mayabridge.paatex.channels import _material_channels, _roughness_from_power


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
    except Exception:  # noqa: BLE001 - undetectable plugin state must not fail material creation
        pass
    return "blinn"


def _color_attr(shader):
    return "baseColor" if cmds.nodeType(shader) == "aiStandardSurface" else "color"


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
    has_roughness = is_ai and cmds.attributeQuery("specularRoughness", node=shader, exists=True)
    if spec_resolved:
        # DayZ _smdi: G = specular level (grayscale), B = glossiness. Wire the G map as the
        # specular colour and the derived roughness map into specularRoughness — NOT the raw
        # RGB (whose constant R=1 blew the whole surface out with a red-tinted spec).
        spec_png, rough_png = decode_smdi_png(spec_resolved)
        spec_file = _make_file_texture(spec_png, "Raw")
        try:
            cmds.connectAttr(spec_file + ".outColor", "%s.%s" % (shader, spec_attr), force=True)
        except RuntimeError:
            pass
        if has_roughness:
            rough_file = _make_file_texture(rough_png, "Raw")
            try:
                cmds.connectAttr(rough_file + ".outColorR", shader + ".specularRoughness", force=True)
            except RuntimeError:
                pass
        return
    if channels["specular"]:
        r, g, b = channels["specular"][:3]
        try:
            cmds.setAttr("%s.%s" % (shader, spec_attr), r, g, b, type="double3")
        except RuntimeError:
            pass
    if has_roughness:
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
    except Exception as exc:  # noqa: BLE001 - a broken spec channel must not fail an import
        cmds.warning("MayaObjectBuilder: specular wiring failed: %s" % exc)
    return True


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
            except Exception:  # noqa: BLE001 - undecodable texture: treat as not-cutout
                cutout = False
        is_ai = cmds.nodeType(shader) == "aiStandardSurface"
        transp_attr = shader + (".opacityR" if is_ai else ".transparency")
        connected = bool(cmds.listConnections(transp_attr, source=True) or [])
        if enabled and cutout and not connected:
            _wire_transparency(shader, color_file, is_ai)
        elif connected and (not enabled or not cutout):
            _clear_transparency(shader, color_file)


def _prefetch_pending(pending):
    """Decode every channel .paa for the pending shaders into the PNG cache in parallel.

    Path resolution and the cache dir are warmed here on the main thread (cmds.optionVar /
    cmds.internalVar are not thread-safe); the workers only run the numpy/zlib decoders, which
    release the GIL, so the DXT decode + PNG write of many textures overlap. Best-effort — a
    failed decode just falls through to the per-shader warning in assign_paa_texture."""
    _cache_dir()  # resolve+create the cache dir on the main thread before spawning workers
    jobs = {}     # (fn, resolved_path) -> dedupe shared textures across materials
    for _shader, texture, material in pending:
        channels = _material_channels(texture, material or None)
        for path, fn in ((channels["color"], paa_to_png),
                         (channels["normal"], decode_normal_png),
                         (channels["spec"], decode_smdi_png)):
            if not path:
                continue
            resolved = resolve_paa_path(path)
            if resolved:
                jobs[(fn, resolved)] = None
    if len(jobs) <= 1:
        return  # nothing to overlap
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        for future in [pool.submit(fn, path) for (fn, path) in jobs]:
            try:
                future.result()
            except Exception:  # noqa: BLE001 - non-fatal; assign_paa_texture will warn on the missing decode
                pass


def assign_pending_textures():
    """Wire the .paa channels onto every material that has a texture path but no colour file
    yet. Idempotent — run deferred after a P3D import (Maya's File > Import DG context blocks
    creating/connecting the file node inline). Returns the number of materials textured."""
    pending = []
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
        pending.append((shader, texture, material))
    if not pending:
        return 0
    try:
        _prefetch_pending(pending)  # parallel decode into cache; the wiring below is cache-only
    except Exception as exc:  # noqa: BLE001 - fall back to lazy per-shader decode in assign_paa_texture
        cmds.warning("MayaObjectBuilder: PAA prefetch failed, falling back to serial decode: %s" % exc)
    count = 0
    for shader, texture, material in pending:
        if assign_paa_texture(shader, texture, material or None):
            count += 1
    return count
