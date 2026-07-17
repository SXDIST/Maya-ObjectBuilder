"""PAA (Arma/DayZ texture) reader + decoder — Maya-independent, pure Python.

Ported 1:1 from the Arma3ObjectBuilder reference (``io/data_paa.py`` + ``io/compression.py``:
LZO1X, DXT1, DXT5). Maya cannot read ``.paa`` natively, so on import we decode the largest
mipmap to RGBA and hand it to the Maya layer (which writes a PNG via MImage and assigns it
as a file texture). Rows are produced bottom-to-top (OpenGL convention).

Format reference: https://community.bistudio.com/wiki/PAA_File_Format
"""

import struct
from array import array
from enum import IntEnum
from io import BytesIO, BufferedReader

try:
    import numpy as _np  # optional: vectorised DXT decode (~30x faster); falls back if absent
except ImportError:  # pragma: no cover
    _np = None


class PAA_Error(Exception):
    pass


class LZO_Error(Exception):
    pass


class DXT_Error(Exception):
    pass


def _read_ushort(file):
    return struct.unpack("<H", file.read(2))[0]


def _read_ushorts(file, count):
    return struct.unpack("<%dH" % count, file.read(2 * count))


def _read_ulong(file):
    return struct.unpack("<I", file.read(4))[0]


class PAA_Type(IntEnum):
    UNKNOWN = -1
    DXT1 = 0xff01
    DXT2 = 0xff02
    DXT3 = 0xff03
    DXT4 = 0xff04
    DXT5 = 0xff05
    RGBA4 = 0x4444
    RGBA5 = 0x1555
    RGBA8 = 0x8888
    GRAY = 0x8080


# ---------------------------------------------------------------------------
# LZO1X decompression (Linux-kernel LZO stream format)
# ---------------------------------------------------------------------------

def lzo1x_decompress(file, expected):
    state = 0
    start = file.tell()
    output = bytearray()
    struct_le16 = struct.Struct("<H")

    def check_free_space(length):
        free_space = expected - len(output)
        if free_space < length:
            raise LZO_Error("Output overrun (free: %d, match length: %d)" % (free_space, length))

    def copy_match(distance, length):
        check_free_space(length)
        begin = len(output) - distance
        output.extend(output[begin:] * (length // distance))
        output.extend(output[begin:(begin + (length % distance))])

    def get_length(x, mask):
        length = x & mask
        if not length:
            while True:
                x = file.read(1)[0]
                if x:
                    break
                length += 255
            length += mask + x
        return length

    x = file.read(1)[0]
    if x > 17:
        length = x - 17
        check_free_space(length)
        output.extend(file.read(length))
        state = min(4, length)
        x = file.read(1)[0]

    while True:
        if x <= 15:
            if not state:
                length = 3 + get_length(x, 15)
                check_free_space(length)
                output.extend(file.read(length))
                state = 4
            elif state < 4:
                length = 2
                state = x & 3
                distance = (file.read(1)[0] << 2) + (x >> 2) + 1
                copy_match(distance, length)
                check_free_space(state)
                output.extend(file.read(state))
            elif state == 4:
                length = 3
                state = x & 3
                distance = (file.read(1)[0] << 2) + (x >> 2) + 2049
                copy_match(distance, length)
                check_free_space(state)
                output.extend(file.read(state))
        elif x > 127:
            state = x & 3
            length = 5 + ((x >> 5) & 3)
            distance = (file.read(1)[0] << 3) + ((x >> 2) & 7) + 1
            copy_match(distance, length)
            check_free_space(state)
            output.extend(file.read(state))
        elif x > 63:
            state = x & 3
            length = 3 + ((x >> 5) & 1)
            distance = (file.read(1)[0] << 3) + ((x >> 2) & 7) + 1
            copy_match(distance, length)
            check_free_space(state)
            output.extend(file.read(state))
        elif x > 31:
            length = 2 + get_length(x, 31)
            extra = struct_le16.unpack(file.read(2))[0]
            distance = (extra >> 2) + 1
            state = extra & 3
            copy_match(distance, length)
            check_free_space(state)
            output.extend(file.read(state))
        else:
            length = 2 + get_length(x, 7)
            extra = struct_le16.unpack(file.read(2))[0]
            distance = 16384 + ((x & 8) << 11) + (extra >> 2)
            state = extra & 3
            if distance == 16384:
                if length != 3:
                    raise LZO_Error("Invalid EOS (expected length 3, got %s)" % length)
                break
            copy_match(distance, length)
            check_free_space(state)
            output.extend(file.read(state))

        x = file.read(1)[0]

    if expected - len(output):
        raise LZO_Error("Short output (expected %d, got %d)" % (expected, len(output)))

    return file.tell() - start, output


# ---------------------------------------------------------------------------
# S3TC / DXT decompression (returns per-channel float arrays, bottom-to-top rows)
# ---------------------------------------------------------------------------

def _dxt5_python(file, width, height):
    if width % 4 != 0 or height % 4 != 0:
        raise DXT_Error("Unexpected resolution: %d x %d" % (width, height))

    red = array('f', bytearray(width * height * 4))
    green = array('f', bytearray(width * height * 4))
    blue = array('f', bytearray(width * height * 4))
    alpha = array('f', bytearray(width * height * 4))
    struct_block_color = struct.Struct('<HHI')
    struct_block_alpha = struct.Struct('BB')
    struct_block_atable = struct.Struct('<Q')

    acoef67, acoef17, acoef57, acoef27, acoef47, acoef37 = 6/7, 1/7, 5/7, 2/7, 4/7, 3/7
    acoef45, acoef15, acoef35, acoef25 = 4/5, 1/5, 3/5, 2/5
    coef23, coef13 = 2/3, 1/3

    block_count_w = width // 4
    block_count_h = height // 4

    for brow in range(block_count_h):
        for bcol in range(block_count_w):
            a0, a1 = struct_block_alpha.unpack(file.read(2))
            atable = struct_block_atable.unpack(file.read(6) + b"\x00\x00")[0]
            v0, v1, table = struct_block_color.unpack(file.read(8))

            r0 = (v0 >> 11) / 31; g0 = ((v0 >> 5) & 0x3f) / 63; b0 = (v0 & 0x1f) / 31
            r1 = (v1 >> 11) / 31; g1 = ((v1 >> 5) & 0x3f) / 63; b1 = (v1 & 0x1f) / 31

            if v0 > v1:
                r2 = coef23 * r0 + coef13 * r1; g2 = coef23 * g0 + coef13 * g1; b2 = coef23 * b0 + coef13 * b1
                r3 = coef13 * r0 + coef23 * r1; g3 = coef13 * g0 + coef23 * g1; b3 = coef13 * b0 + coef23 * b1
            else:
                r2 = 0.5 * (r0 + r1); g2 = 0.5 * (g0 + g1); b2 = 0.5 * (b0 + b1)
                r3 = g3 = b3 = 0

            if a0 > a1:
                a0 /= 255; a1 /= 255
                a2 = acoef67 * a0 + acoef17 * a1; a3 = acoef57 * a0 + acoef27 * a1
                a4 = acoef47 * a0 + acoef37 * a1; a5 = acoef37 * a0 + acoef47 * a1
                a6 = acoef27 * a0 + acoef57 * a1; a7 = acoef17 * a0 + acoef67 * a1
            else:
                a0 /= 255; a1 /= 255
                a2 = acoef45 * a0 + acoef15 * a1; a3 = acoef35 * a0 + acoef25 * a1
                a4 = acoef25 * a0 + acoef35 * a1; a5 = acoef15 * a0 + acoef45 * a1
                a6 = 0; a7 = 1

            codes = tuple((table >> (2 * i)) & 0x3 for i in range(16))
            acodes = tuple((atable >> (3 * i)) & 0x7 for i in range(16))
            lut = ((r0, g0, b0), (r1, g1, b1), (r2, g2, b2), (r3, g3, b3))
            alut = (a0, a1, a2, a3, a4, a5, a6, a7)

            bstartrow = height - brow * 4
            bstartcol = bcol * 4
            for row in range(4):
                current_row_col = (bstartrow - row - 1) * width + bstartcol
                for col in range(4):
                    pix = row * 4 + col
                    r, g, b = lut[codes[pix]]
                    a = alut[acodes[pix]]
                    idx = current_row_col + col
                    red[idx] = r; green[idx] = g; blue[idx] = b; alpha[idx] = a

    return red, green, blue, alpha


def _dxt1_python(file, width, height):
    if width % 4 != 0 or height % 4 != 0:
        raise DXT_Error("Unexpected resolution: %d x %d" % (width, height))

    red = array('f', bytearray(width * height * 4))
    green = array('f', bytearray(width * height * 4))
    blue = array('f', bytearray(width * height * 4))
    alpha = array('f', bytearray(width * height * 4))
    struct_block = struct.Struct('<HHI')
    coef0, coef1 = 2/3, 1/3

    block_count_w = width // 4
    block_count_h = height // 4
    a0 = a1 = a2 = 1

    for brow in range(block_count_h):
        for bcol in range(block_count_w):
            v0, v1, table = struct_block.unpack(file.read(8))

            r0 = (v0 >> 11) / 31; g0 = ((v0 >> 5) & 0x3f) / 63; b0 = (v0 & 0x1f) / 31
            r1 = (v1 >> 11) / 31; g1 = ((v1 >> 5) & 0x3f) / 63; b1 = (v1 & 0x1f) / 31

            if v0 > v1:
                r2 = coef0 * r0 + coef1 * r1; g2 = coef0 * g0 + coef1 * g1; b2 = coef0 * b0 + coef1 * b1
                r3 = coef1 * r0 + coef0 * r1; g3 = coef1 * g0 + coef0 * g1; b3 = coef1 * b0 + coef0 * b1
                a3 = 1
            else:
                r2 = 0.5 * (r0 + r1); g2 = 0.5 * (g0 + g1); b2 = 0.5 * (b0 + b1)
                r3 = g3 = b3 = a3 = 0

            codes = tuple((table >> (2 * i)) & 0x3 for i in range(16))
            lut = ((r0, g0, b0, a0), (r1, g1, b1, a1), (r2, g2, b2, a2), (r3, g3, b3, a3))

            bstartrow = height - brow * 4
            bstartcol = bcol * 4
            for row in range(4):
                current_row_col = (bstartrow - row - 1) * width + bstartcol
                for col in range(4):
                    r, g, b, a = lut[codes[row * 4 + col]]
                    idx = current_row_col + col
                    red[idx] = r; green[idx] = g; blue[idx] = b; alpha[idx] = a

    return red, green, blue, alpha


# ---------------------------------------------------------------------------
# Vectorised DXT decode (numpy) — byte-identical output to the pure-Python paths,
# ~30x faster. Used when numpy is importable; else the _*_python fallbacks run.
# ---------------------------------------------------------------------------

def _place_bottom_up(chan, bh, bw, height, width):
    """[nblocks,16] block-major (pix = row*4+col) -> flat float32 in the same
    bottom-to-top row order the Python decoders emit (block row 0 at the array bottom)."""
    nat = chan.reshape(bh, bw, 4, 4).transpose(0, 2, 1, 3).reshape(height, width)
    return _np.ascontiguousarray(nat[::-1], dtype=_np.float32).ravel()


def _dxt1_numpy(file, width, height):
    if width % 4 != 0 or height % 4 != 0:
        raise DXT_Error("Unexpected resolution: %d x %d" % (width, height))
    bw, bh = width // 4, height // 4
    n = bw * bh
    raw = _np.frombuffer(file.read(n * 8), dtype=_np.uint8).reshape(n, 8).astype(_np.uint32)
    v0 = raw[:, 0] | (raw[:, 1] << 8)
    v1 = raw[:, 2] | (raw[:, 3] << 8)
    table = raw[:, 4] | (raw[:, 5] << 8) | (raw[:, 6] << 16) | (raw[:, 7] << 24)

    r0 = (v0 >> 11) / 31.0; g0 = ((v0 >> 5) & 0x3f) / 63.0; b0 = (v0 & 0x1f) / 31.0
    r1 = (v1 >> 11) / 31.0; g1 = ((v1 >> 5) & 0x3f) / 63.0; b1 = (v1 & 0x1f) / 31.0
    gt = v0 > v1
    r2 = _np.where(gt, (2 / 3) * r0 + (1 / 3) * r1, 0.5 * (r0 + r1))
    g2 = _np.where(gt, (2 / 3) * g0 + (1 / 3) * g1, 0.5 * (g0 + g1))
    b2 = _np.where(gt, (2 / 3) * b0 + (1 / 3) * b1, 0.5 * (b0 + b1))
    r3 = _np.where(gt, (1 / 3) * r0 + (2 / 3) * r1, 0.0)
    g3 = _np.where(gt, (1 / 3) * g0 + (2 / 3) * g1, 0.0)
    b3 = _np.where(gt, (1 / 3) * b0 + (2 / 3) * b1, 0.0)
    a3 = _np.where(gt, 1.0, 0.0)
    ones = _np.ones(n)

    codes = (table[:, None] >> (_np.arange(16, dtype=_np.uint32) * 2)) & 0x3
    rows = _np.arange(n)[:, None]
    out = []
    for pal in (_np.stack([r0, r1, r2, r3], axis=1), _np.stack([g0, g1, g2, g3], axis=1),
                _np.stack([b0, b1, b2, b3], axis=1), _np.stack([ones, ones, ones, a3], axis=1)):
        out.append(_place_bottom_up(pal[rows, codes], bh, bw, height, width))
    return tuple(out)


def _dxt5_numpy(file, width, height):
    if width % 4 != 0 or height % 4 != 0:
        raise DXT_Error("Unexpected resolution: %d x %d" % (width, height))
    bw, bh = width // 4, height // 4
    n = bw * bh
    raw = _np.frombuffer(file.read(n * 16), dtype=_np.uint8).reshape(n, 16).astype(_np.uint64)
    a0 = raw[:, 0] / 255.0
    a1 = raw[:, 1] / 255.0
    atable = (raw[:, 2] | (raw[:, 3] << 8) | (raw[:, 4] << 16)
              | (raw[:, 5] << 24) | (raw[:, 6] << 32) | (raw[:, 7] << 40))
    v0 = raw[:, 8] | (raw[:, 9] << 8)
    v1 = raw[:, 10] | (raw[:, 11] << 8)
    table = raw[:, 12] | (raw[:, 13] << 8) | (raw[:, 14] << 16) | (raw[:, 15] << 24)

    r0 = (v0 >> 11) / 31.0; g0 = ((v0 >> 5) & 0x3f) / 63.0; b0 = (v0 & 0x1f) / 31.0
    r1 = (v1 >> 11) / 31.0; g1 = ((v1 >> 5) & 0x3f) / 63.0; b1 = (v1 & 0x1f) / 31.0
    gt = v0 > v1
    r2 = _np.where(gt, (2 / 3) * r0 + (1 / 3) * r1, 0.5 * (r0 + r1))
    g2 = _np.where(gt, (2 / 3) * g0 + (1 / 3) * g1, 0.5 * (g0 + g1))
    b2 = _np.where(gt, (2 / 3) * b0 + (1 / 3) * b1, 0.5 * (b0 + b1))
    r3 = _np.where(gt, (1 / 3) * r0 + (2 / 3) * r1, 0.0)
    g3 = _np.where(gt, (1 / 3) * g0 + (2 / 3) * g1, 0.0)
    b3 = _np.where(gt, (1 / 3) * b0 + (2 / 3) * b1, 0.0)

    ga = raw[:, 0] > raw[:, 1]
    a2 = _np.where(ga, (6 / 7) * a0 + (1 / 7) * a1, (4 / 5) * a0 + (1 / 5) * a1)
    a3a = _np.where(ga, (5 / 7) * a0 + (2 / 7) * a1, (3 / 5) * a0 + (2 / 5) * a1)
    a4 = _np.where(ga, (4 / 7) * a0 + (3 / 7) * a1, (2 / 5) * a0 + (3 / 5) * a1)
    a5 = _np.where(ga, (3 / 7) * a0 + (4 / 7) * a1, (1 / 5) * a0 + (4 / 5) * a1)
    a6 = _np.where(ga, (2 / 7) * a0 + (5 / 7) * a1, 0.0)
    a7 = _np.where(ga, (1 / 7) * a0 + (6 / 7) * a1, 1.0)

    codes = (table[:, None] >> (_np.arange(16, dtype=_np.uint64) * 2)) & 0x3
    acodes = (atable[:, None] >> (_np.arange(16, dtype=_np.uint64) * 3)) & 0x7
    rows = _np.arange(n)[:, None]

    cpal = (_np.stack([r0, r1, r2, r3], axis=1), _np.stack([g0, g1, g2, g3], axis=1),
            _np.stack([b0, b1, b2, b3], axis=1))
    apal = _np.stack([a0, a1, a2, a3a, a4, a5, a6, a7], axis=1)
    out = [_place_bottom_up(pal[rows, codes], bh, bw, height, width) for pal in cpal]
    out.append(_place_bottom_up(apal[rows, acodes], bh, bw, height, width))
    return tuple(out)


if _np is not None:
    dxt1_decompress = _dxt1_numpy
    dxt5_decompress = _dxt5_numpy
else:  # pragma: no cover
    dxt1_decompress = _dxt1_python
    dxt5_decompress = _dxt5_python


# ---------------------------------------------------------------------------
# PAA structures
# ---------------------------------------------------------------------------

class PAA_TAGG:
    def __init__(self):
        self.name = ""
        self.data = None

    @classmethod
    def read(cls, file):
        output = cls()
        output.name = file.read(4).decode("utf8")[::-1]
        length = _read_ulong(file)
        output.data = file.read(length)
        return output


class PAA_MIPMAP:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.data = None       # (red, green, blue, alpha) float arrays after decompress()
        self.data_raw = None
        self.lzo_compressed = False

    @classmethod
    def read(cls, file):
        output = cls()
        output.width, output.height = _read_ushorts(file, 2)
        if output.width == output.height == 0:
            return output
        if output.width & 0x8000:
            output.lzo_compressed = True
            output.width ^= 0x8000
        length = struct.unpack('<I', file.read(3) + b"\x00")[0]
        output.data_raw = bytearray(file.read(length))
        return output

    def decompress(self, paa_type):
        if paa_type == PAA_Type.DXT1:
            decompressor = dxt1_decompress
            lzo_expected = self.width * self.height // 2
        elif paa_type == PAA_Type.DXT5:
            decompressor = dxt5_decompress
            lzo_expected = self.width * self.height
        else:
            raise PAA_Error("Unsupported format for decompression: %s" % paa_type)

        data = self.data_raw
        if self.lzo_compressed:
            _, data = lzo1x_decompress(BufferedReader(BytesIO(self.data_raw)), lzo_expected)

        self.data = decompressor(BufferedReader(BytesIO(data)), self.width, self.height)
        return self.data


class PAA_File:
    def __init__(self):
        self.source = ""
        self.type = PAA_Type.UNKNOWN
        self.taggs = []
        self.mips = []

    @classmethod
    def read(cls, file):
        output = cls()
        data_type = _read_ushort(file)
        try:
            output.type = PAA_Type(data_type)
            if output.type == PAA_Type.UNKNOWN:
                raise ValueError()
        except ValueError:
            raise PAA_Error("Unknown format type: %d" % data_type)

        while True:
            if file.read(4) != b"GGAT":
                file.seek(-4, 1)
                break
            output.taggs.append(PAA_TAGG.read(file))

        if _read_ushort(file) != 0:
            raise PAA_Error("Indexed palettes are not supported")

        while True:
            mip = PAA_MIPMAP.read(file)
            if mip.width == mip.height == 0:
                break
            output.mips.append(mip)

        return output

    @classmethod
    def read_file(cls, filepath):
        with open(filepath, "rb") as file:
            output = cls.read(file)
        output.source = filepath
        return output

    def get_tagg(self, name):
        for tagg in self.taggs:
            if tagg.name == name:
                return tagg
        return None


def decode_largest_mip(filepath):
    """Read a .paa and decode its largest mipmap. Returns (width, height, (r,g,b,a) float
    arrays, bottom-to-top rows) or raises PAA_Error."""
    paa = PAA_File.read_file(filepath)
    if not paa.mips:
        raise PAA_Error("No mipmaps in %s" % filepath)
    mip = paa.mips[0]  # PAA stores mipmaps largest-first
    mip.decompress(paa.type)
    return mip.width, mip.height, mip.data
