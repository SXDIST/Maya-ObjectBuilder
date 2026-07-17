"""Decode ``.paa`` textures to cached PNGs.

Pure numpy + zlib (no Maya API beyond resolving the cache directory once), so the decoders
are thread-safe and can run in a worker pool. Each decode is keyed by source path + mtime and
cached under ``a3ob_paa_cache_v3`` in Maya's user tmp dir. Decoded rows are bottom-to-top (as
``a3ob.formats.paa`` emits, OpenGL convention); ``_write_png`` flips them to top-to-bottom.
"""

import os
import struct
import hashlib

import maya.cmds as cmds

_CACHE_DIRNAME = "a3ob_paa_cache_v3"  # bumped: fixed vertical flip (PNGs were upside-down)
_CACHE_DIR = None  # resolved once on the main thread (cmds.internalVar is not thread-safe)


def _cache_dir():
    global _CACHE_DIR
    if _CACHE_DIR is None:
        directory = os.path.join(cmds.internalVar(userTmpDir=True), _CACHE_DIRNAME)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        _CACHE_DIR = directory
    return _CACHE_DIR


def _write_png(path, rgba):
    """Write an RGBA uint8 image to ``path`` as a PNG. Pure numpy+zlib (no Maya API), so it
    is thread-safe and ~10x faster than MImage. Input rows are bottom-to-top (as the DXT
    decoders emit); a standard PNG is top-to-bottom, so the rows are flipped on write — this
    reproduces exactly what MImage.setPixels/writeToFile did (verified vs the game's _co.png)."""
    import numpy as np
    import zlib
    rows = np.ascontiguousarray(rgba[::-1])  # bottom-to-top -> top-to-bottom
    height, width = rows.shape[:2]
    raw = np.empty((height, 1 + width * 4), dtype=np.uint8)
    raw[:, 0] = 0  # PNG "None" filter per scanline
    raw[:, 1:] = rows.reshape(height, width * 4)
    compressed = zlib.compress(raw.tobytes(), 1)  # level 1: fast; cache size is not a concern

    def _chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit, colour type 6 = RGBA
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b""))


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
    from a3ob.formats.paa import decode_largest_mip
    width, height, (red, green, blue, alpha) = decode_largest_mip(paa_path)
    channels = [np.frombuffer(c, dtype=np.float32) for c in (red, green, blue, alpha)]
    cutout = _alpha_is_cutout(channels[3])
    rgba = np.stack(channels, axis=1).reshape(height, width, 4)
    _write_png(png, np.clip(rgba * 255.0, 0, 255).astype(np.uint8))
    try:
        with open(meta, "w") as handle:
            handle.write("1" if cutout else "0")
    except OSError:
        pass
    return png, cutout


def decode_smdi_png(smdi_path):
    """Decode a DayZ ``_smdi`` specular map into (spec_png, rough_png).

    Arma/DayZ SMDI channel layout (verified against own_femida_top_smdi): R is a
    constant 1.0 (unused), **G is the per-texel specular level** (dark = matte, bright =
    shiny), **B is the glossiness/power** (near-constant per material). Feeding the raw RGB
    into ``specularColor`` was wrong — R=1 forced a full-strength red-tinted spec across the
    whole surface (the over-bright blow-out). Instead: spec_png is grayscale G (specular
    only where the map says so), rough_png is grayscale ``1 - B`` (glossy where B is high).
    Both cached (path+mtime)."""
    key = hashlib.md5(("S|%s|%s" % (smdi_path, os.path.getmtime(smdi_path))).encode("utf8")).hexdigest()
    spec_png = os.path.join(_cache_dir(), key + "_s.png")
    rough_png = os.path.join(_cache_dir(), key + "_r.png")
    if os.path.isfile(spec_png) and os.path.isfile(rough_png):
        return spec_png, rough_png
    import numpy as np
    from a3ob.formats.paa import decode_largest_mip
    width, height, (_red, green, blue, _alpha) = decode_largest_mip(smdi_path)
    g = np.frombuffer(green, dtype=np.float32)
    b = np.frombuffer(blue, dtype=np.float32)
    rough = np.clip(1.0 - b, 0.03, 0.98)
    ones = np.ones_like(g)
    for arr, path in ((g, spec_png), (rough, rough_png)):
        rgba = np.stack([arr, arr, arr, ones], axis=1).reshape(height, width, 4)
        _write_png(path, np.clip(rgba * 255.0, 0, 255).astype(np.uint8))
    return spec_png, rough_png


def decode_normal_png(nohq_path):
    """Decode an Arma _nohq (DXT5nm: normal.X in alpha, normal.Y in green, Z reconstructed)
    into a proper tangent-space normal PNG. Cached (path+mtime)."""
    key = hashlib.md5(("N|%s|%s" % (nohq_path, os.path.getmtime(nohq_path))).encode("utf8")).hexdigest()
    png = os.path.join(_cache_dir(), key + "_n.png")
    if os.path.isfile(png):
        return png
    import numpy as np
    from a3ob.formats.paa import decode_largest_mip
    width, height, (_red, green, _blue, alpha) = decode_largest_mip(nohq_path)
    nx = np.frombuffer(alpha, dtype=np.float32) * 2.0 - 1.0
    ny = np.frombuffer(green, dtype=np.float32) * 2.0 - 1.0
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0.0, 1.0))
    ones = np.ones_like(nx)
    rgba = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5, ones], axis=1).reshape(height, width, 4)
    _write_png(png, np.clip(rgba * 255.0, 0, 255).astype(np.uint8))
    return png
