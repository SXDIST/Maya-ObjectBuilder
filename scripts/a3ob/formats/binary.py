"""Little-endian binary reader/writer.

Direct 1:1 port of the former C++ ``src/formats/BinaryIO.{h,cpp}``. Works over any
binary file object (``open(path, "rb"/"wb")``) or an in-memory ``io.BytesIO``.

Strings are decoded/encoded as latin-1 so every byte 0..255 round-trips losslessly —
the P3D format stores raw ``char`` names and fixed ASCIIZ fields, not Unicode text.
Every short read/write raises ``EOFError``/``IOError`` to mirror the C++ ``std::runtime_error``.
"""

import io
import os
import struct

__all__ = ["BinaryReader", "BinaryWriter"]

_U8 = struct.Struct("<B")
_U32 = struct.Struct("<I")
_F32 = struct.Struct("<f")


class BinaryReader:
    """Reads little-endian POD values from a binary stream."""

    def __init__(self, source):
        # ``source`` is a filesystem path (str/os.PathLike) or an already-open binary stream.
        if isinstance(source, (str, bytes, os.PathLike)):
            self._stream = open(source, "rb")
            self._owned = True
        else:
            self._stream = source
            self._owned = False

    # -- lifecycle ---------------------------------------------------------
    def close(self):
        if self._owned:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # -- positioning -------------------------------------------------------
    def good(self):
        return self._stream is not None and not self._stream.closed

    def tell(self):
        return self._stream.tell()

    def seek(self, offset, whence=io.SEEK_SET):
        self._stream.seek(offset, whence)

    # -- scalar reads ------------------------------------------------------
    def _read_exact(self, count):
        data = self._stream.read(count)
        if len(data) != count:
            raise EOFError("Unexpected EOF while reading binary value")
        return data

    def read_uint8(self):
        return _U8.unpack(self._read_exact(1))[0]

    def read_bool(self):
        return self.read_uint8() != 0

    def read_uint32(self):
        return _U32.unpack(self._read_exact(4))[0]

    def read_float(self):
        return _F32.unpack(self._read_exact(4))[0]

    def read_chars(self, count):
        return self._read_exact(count).decode("latin-1")

    def read_asciiz(self):
        chars = bytearray()
        while True:
            byte = self._stream.read(1)
            if not byte:
                raise EOFError("Unexpected EOF while reading ASCIIZ string")
            if byte == b"\x00":
                return chars.decode("latin-1")
            chars += byte

    def read_asciiz_field(self, field_length):
        field = self._read_exact(field_length)
        pos = field.find(b"\x00")
        if pos == -1:
            raise ValueError("ASCIIZ field length overflow")
        return field[:pos].decode("latin-1")

    # -- array reads -------------------------------------------------------
    def read_uint32s(self, count):
        if count == 0:
            return []
        data = self._read_exact(4 * count)
        return list(struct.unpack("<%dI" % count, data))

    def read_floats(self, count):
        if count == 0:
            return []
        data = self._read_exact(4 * count)
        return list(struct.unpack("<%df" % count, data))

    def read_bytes(self, count):
        if count == 0:
            return b""
        return self._read_exact(count)


class BinaryWriter:
    """Writes little-endian POD values to a binary stream."""

    def __init__(self, target):
        if isinstance(target, (str, bytes, os.PathLike)):
            self._stream = open(target, "wb")
            self._owned = True
        else:
            self._stream = target
            self._owned = False

    def close(self):
        if self._owned:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def good(self):
        return self._stream is not None and not self._stream.closed

    def write_uint8(self, value):
        self._stream.write(_U8.pack(value & 0xFF))

    def write_bool(self, value):
        self.write_uint8(1 if value else 0)

    def write_uint32(self, value):
        self._stream.write(_U32.pack(value & 0xFFFFFFFF))

    def write_float(self, value):
        self._stream.write(_F32.pack(value))

    def write_chars(self, value):
        self._stream.write(value.encode("latin-1"))

    def write_asciiz(self, value):
        self.write_chars(value)
        self.write_uint8(0)

    def write_asciiz_field(self, value, field_length):
        if len(value) + 1 > field_length:
            raise ValueError("ASCIIZ value exceeds fixed field length")
        self.write_chars(value)
        self._stream.write(b"\x00" * (field_length - len(value)))

    def write_bytes(self, value):
        if not value:
            return
        self._stream.write(bytes(value))
