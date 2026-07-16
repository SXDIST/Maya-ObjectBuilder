"""P3D MLOD binary format (read/write).

Direct 1:1 port of the former C++ ``src/formats/P3D.{h,cpp}``. Uses the Blender
add-on's ``io/data_p3d.py`` as a cross-reference. No Maya dependency.

Format invariants preserved exactly (see CLAUDE.md):
* Position is stored on disk as ``(x, z, y)``; normals stored negated ``(-x, -z, -y)``
  and renormalized after read.
* Faces are triangles or quads; triangles pad 16 bytes of zeros after their corners.
* UV ``v`` is inverted on read and write (``1 - v``) in both face data and ``#UVSet#``.
* A TAGG is ``active byte + null-terminated name + uint32 length + data``.
* ``LodResolution`` encodes the LOD type + resolution into the trailing float
  "signature"; the ``signatureMap`` table is copied verbatim.
"""

import math
import re

from .binary import BinaryReader, BinaryWriter

__all__ = [
    "Vec2", "Vec3", "Vertex", "Face",
    "EmptyTaggData", "SharpEdgesTaggData", "PropertyTaggData", "MassTaggData",
    "UVSetTaggData", "SelectionTaggData", "Tagg",
    "LodResolution", "LOD", "MLOD",
]

# -- LOD type constants (order matters, matches the C++ enum values) -----------
LOD_VISUAL = 0
LOD_VIEW_GUNNER = 1
LOD_VIEW_PILOT = 2
LOD_VIEW_CARGO = 3
LOD_SHADOW = 4
LOD_EDIT = 5
LOD_GEOMETRY = 6
LOD_GEOMETRY_BUOY = 7
LOD_GEOMETRY_PHYSX = 8
LOD_MEMORY = 9
LOD_LANDCONTACT = 10
LOD_ROADWAY = 11
LOD_PATHS = 12
LOD_HITPOINTS = 13
LOD_VIEW_GEOMETRY = 14
LOD_FIRE_GEOMETRY = 15
LOD_VIEW_CARGO_GEOMETRY = 16
LOD_VIEW_CARGO_FIRE_GEOMETRY = 17
LOD_VIEW_COMMANDER = 18
LOD_VIEW_COMMANDER_GEOMETRY = 19
LOD_VIEW_COMMANDER_FIRE_GEOMETRY = 20
LOD_VIEW_PILOT_GEOMETRY = 21
LOD_VIEW_PILOT_FIRE_GEOMETRY = 22
LOD_VIEW_GUNNER_GEOMETRY = 23
LOD_VIEW_GUNNER_FIRE_GEOMETRY = 24
LOD_SUBPARTS = 25
LOD_SHADOW_VIEW_CARGO = 26
LOD_SHADOW_VIEW_PILOT = 27
LOD_SHADOW_VIEW_GUNNER = 28
LOD_WRECKAGE = 29
LOD_UNDERGROUND = 30
LOD_GROUNDLAYER = 31
LOD_NAVIGATION = 32
LOD_UNKNOWN = -1

# LOD-resolution signature -> LOD type. Keys are ``"%.3e"`` formatted floats.
_SIGNATURE_MAP = {
    "1.000e+03": LOD_VIEW_GUNNER,
    "1.100e+03": LOD_VIEW_PILOT,
    "1.300e+04": LOD_GROUNDLAYER,
    "1.000e+13": LOD_GEOMETRY,
    "2.000e+13": LOD_GEOMETRY_BUOY,
    "3.000e+13": LOD_UNDERGROUND,
    "4.000e+13": LOD_GEOMETRY_PHYSX,
    "5.000e+13": LOD_NAVIGATION,
    "1.000e+15": LOD_MEMORY,
    "2.000e+15": LOD_LANDCONTACT,
    "3.000e+15": LOD_ROADWAY,
    "4.000e+15": LOD_PATHS,
    "5.000e+15": LOD_HITPOINTS,
    "6.000e+15": LOD_VIEW_GEOMETRY,
    "7.000e+15": LOD_FIRE_GEOMETRY,
    "9.000e+15": LOD_VIEW_CARGO_FIRE_GEOMETRY,
    "1.000e+16": LOD_VIEW_COMMANDER,
    "1.100e+16": LOD_VIEW_COMMANDER_GEOMETRY,
    "1.200e+16": LOD_VIEW_COMMANDER_FIRE_GEOMETRY,
    "1.300e+16": LOD_VIEW_PILOT_GEOMETRY,
    "1.400e+16": LOD_VIEW_PILOT_FIRE_GEOMETRY,
    "1.500e+16": LOD_VIEW_GUNNER_GEOMETRY,
    "1.600e+16": LOD_VIEW_GUNNER_FIRE_GEOMETRY,
    "1.700e+16": LOD_SUBPARTS,
    "1.900e+16": LOD_SHADOW_VIEW_PILOT,
    "2.000e+16": LOD_SHADOW_VIEW_GUNNER,
    "2.100e+16": LOD_WRECKAGE,
}

_PROXY_RE = re.compile(r"^proxy:.*\.\d+$")


def _scientific_key(value):
    # Mirrors C++ snprintf("%.3e", value); MSVC and CPython both emit 2-digit exponents.
    return "%.3e" % value


def _starts_and_ends_with_hash(value):
    return len(value) >= 2 and value[0] == "#" and value[-1] == "#"


def _round_half_away(value):
    # Matches C++ std::round (round half away from zero); inputs here are non-negative.
    if value >= 0.0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


# -- geometry primitives -------------------------------------------------------
class Vec2:
    __slots__ = ("u", "v")

    def __init__(self, u=0.0, v=0.0):
        self.u = u
        self.v = v


class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class Vertex:
    __slots__ = ("position", "flag")

    def __init__(self, position=None, flag=0):
        self.position = position if position is not None else Vec3()
        self.flag = flag


class Face:
    __slots__ = ("vertices", "normals", "uvs", "texture", "material", "flag")

    def __init__(self):
        self.vertices = []
        self.normals = []
        self.uvs = []
        self.texture = ""
        self.material = ""
        self.flag = 0


# -- TAGG payloads -------------------------------------------------------------
class EmptyTaggData:
    kind = "Empty"

    def length(self):
        return 0

    def write(self, writer):
        pass


class SharpEdgesTaggData:
    kind = "SharpEdges"

    def __init__(self):
        self.edges = []  # list of (uint32, uint32)

    @staticmethod
    def read(reader, length):
        if length % 8 != 0:
            raise ValueError("Invalid sharp edges length")
        data = SharpEdgesTaggData()
        count_values = length // 4
        for _ in range(0, count_values, 2):
            first = reader.read_uint32()
            second = reader.read_uint32()
            if first != second:
                data.edges.append((first, second))
        return data

    def length(self):
        return len(self.edges) * 8

    def write(self, writer):
        for first, second in self.edges:
            if first == second:
                continue
            writer.write_uint32(first)
            writer.write_uint32(second)


class PropertyTaggData:
    kind = "Property"

    def __init__(self, key="", value=""):
        self.key = key
        self.value = value

    @staticmethod
    def read(reader):
        data = PropertyTaggData()
        data.key = reader.read_asciiz_field(64)
        data.value = reader.read_asciiz_field(64)
        return data

    def length(self):
        return 128

    def write(self, writer):
        writer.write_asciiz_field(self.key, 64)
        writer.write_asciiz_field(self.value, 64)


class MassTaggData:
    kind = "Mass"

    def __init__(self):
        self.masses = []

    @staticmethod
    def read(reader, count_verts):
        data = MassTaggData()
        data.masses = reader.read_floats(count_verts)
        return data

    def length(self):
        return len(self.masses) * 4

    def write(self, writer):
        for value in self.masses:
            writer.write_float(value)


class UVSetTaggData:
    kind = "UVSet"

    def __init__(self):
        self.id = 0
        self.uvs = []  # list of Vec2

    @staticmethod
    def read(reader, length):
        if length < 4 or (length - 4) % 8 != 0:
            raise ValueError("Invalid UV set length")
        data = UVSetTaggData()
        data.id = reader.read_uint32()
        count_values = (length - 4) // 4
        for _ in range(0, count_values, 2):
            u = reader.read_float()
            v = reader.read_float()
            data.uvs.append(Vec2(u, 1.0 - v))
        return data

    def length(self):
        return len(self.uvs) * 8 + 4

    def write(self, writer):
        writer.write_uint32(self.id)
        for uv in self.uvs:
            writer.write_float(uv.u)
            writer.write_float(1.0 - uv.v)


class SelectionTaggData:
    kind = "Selection"

    def __init__(self):
        self.count_verts = 0
        self.count_faces = 0
        self.vertex_weights = []  # list of (index, weight)
        self.face_weights = []

    @staticmethod
    def decode_weight(weight):
        if weight == 0 or weight == 1:
            return float(weight)
        return (255 - weight) / 254.0

    @staticmethod
    def encode_weight(weight):
        if weight == 0.0 or weight == 1.0:
            return int(weight)
        return _round_half_away(255.0 - 254.0 * weight) & 0xFF

    @staticmethod
    def read(reader, count_verts, count_faces):
        data = SelectionTaggData()
        data.count_verts = count_verts
        data.count_faces = count_faces

        vertex_bytes = reader.read_bytes(count_verts)
        for i in range(count_verts):
            if vertex_bytes[i] > 0:
                data.vertex_weights.append((i, SelectionTaggData.decode_weight(vertex_bytes[i])))

        face_bytes = reader.read_bytes(count_faces)
        for i in range(count_faces):
            if face_bytes[i] > 0:
                data.face_weights.append((i, SelectionTaggData.decode_weight(face_bytes[i])))

        return data

    def length(self):
        return self.count_verts + self.count_faces

    def write(self, writer):
        vertex_bytes = bytearray(self.count_verts)
        for idx, weight in self.vertex_weights:
            if idx < len(vertex_bytes):
                vertex_bytes[idx] = self.encode_weight(weight)

        face_bytes = bytearray(self.count_faces)
        for idx, weight in self.face_weights:
            if idx < len(face_bytes):
                face_bytes[idx] = self.encode_weight(weight)

        writer.write_bytes(bytes(vertex_bytes))
        writer.write_bytes(bytes(face_bytes))


class Tagg:
    __slots__ = ("active", "name", "data")

    def __init__(self):
        self.active = True
        self.name = ""
        self.data = EmptyTaggData()

    def is_proxy(self):
        return _PROXY_RE.match(self.name) is not None

    def is_selection(self):
        return not _starts_and_ends_with_hash(self.name)

    @staticmethod
    def read(reader, count_verts, count_faces):
        tagg = Tagg()
        tagg.active = reader.read_bool()
        tagg.name = reader.read_asciiz()
        length = reader.read_uint32()

        if tagg.name == "#EndOfFile#":
            if length != 0:
                raise ValueError("Invalid P3D EOF TAGG")
            tagg.active = False
            return tagg

        if tagg.name == "#SharpEdges#":
            tagg.data = SharpEdgesTaggData.read(reader, length)
        elif tagg.name == "#Property#":
            if length != 128:
                raise ValueError("Invalid property TAGG length")
            tagg.data = PropertyTaggData.read(reader)
        elif tagg.name == "#Mass#":
            tagg.data = MassTaggData.read(reader, count_verts)
        elif tagg.name == "#UVSet#":
            tagg.data = UVSetTaggData.read(reader, length)
        elif tagg.is_selection():
            tagg.data = SelectionTaggData.read(reader, count_verts, count_faces)
        else:
            reader.seek(length, 1)  # SEEK_CUR
            tagg.active = False
            tagg.data = EmptyTaggData()

        return tagg

    def write(self, writer):
        if not self.active:
            return
        writer.write_bool(self.active)
        writer.write_asciiz(self.name)
        writer.write_uint32(self.data.length() if self.data else 0)
        if self.data:
            self.data.write(writer)


class LodResolution:
    __slots__ = ("lod", "resolution", "source")

    def __init__(self, lod=0, resolution=0, source=0.0):
        self.lod = lod
        self.resolution = resolution
        self.source = source

    @staticmethod
    def encode(lod, resolution):
        if lod == LOD_VISUAL or lod == LOD_UNKNOWN:
            return float(resolution)

        for signature, mapped_lod in _SIGNATURE_MAP.items():
            if mapped_lod == lod:
                return float(signature)

        if lod == LOD_VIEW_CARGO:
            return 1.2e3 + float(resolution)
        if lod == LOD_SHADOW:
            return 1.0e4 + float(resolution)
        if lod == LOD_EDIT:
            return 2.0e4 + float(resolution)
        if lod == LOD_VIEW_CARGO_GEOMETRY:
            return 8.0e15 + float(resolution) * 1.0e13
        if lod == LOD_SHADOW_VIEW_CARGO:
            return 1.8e16 + float(resolution) * 1.0e13

        return float(resolution)

    @staticmethod
    def from_float(value):
        output = LodResolution()
        output.source = value

        if value < 1.0e3:
            output.lod = LOD_VISUAL
            output.resolution = _round_half_away(value)
            return output
        if 1.2e3 <= value < 1.3e3:
            output.lod = LOD_VIEW_CARGO
            output.resolution = _round_half_away(value - 1.2e3)
            return output
        if 1.0e4 <= value < 1.2e4:
            output.lod = LOD_SHADOW
            output.resolution = _round_half_away(value - 1.0e4)
            return output
        if 2.0e4 <= value < 3.0e4:
            output.lod = LOD_EDIT
            output.resolution = _round_half_away(value - 2.0e4)
            return output

        key = _scientific_key(value)
        if key in _SIGNATURE_MAP:
            output.lod = _SIGNATURE_MAP[key]
            output.resolution = 0
            return output

        exp_pos = key.find("e")
        exponent = 0 if exp_pos == -1 else int(key[exp_pos + 1:])
        if exponent == 15:
            output.lod = LOD_VIEW_CARGO_GEOMETRY
            output.resolution = int(key[2:4])
            return output
        if exponent == 16:
            output.lod = LOD_SHADOW_VIEW_CARGO
            output.resolution = int(key[3:5])
            return output

        output.lod = LOD_UNKNOWN
        output.resolution = _round_half_away(value)
        return output

    def as_float(self):
        return LodResolution.encode(self.lod, self.resolution)


class LOD:
    def __init__(self):
        self.version_major = 0x1c
        self.version_minor = 0x100
        self.flags = 0
        self.resolution = LodResolution()
        self.vertices = []
        self.normals = []
        self.faces = []
        self.taggs = []

    @staticmethod
    def read(reader):
        if reader.read_chars(4) != "P3DM":
            raise ValueError("Unsupported P3D LOD signature")

        lod = LOD()
        lod.version_major = reader.read_uint32()
        lod.version_minor = reader.read_uint32()
        if lod.version_major != 0x1c or lod.version_minor != 0x100:
            raise ValueError("Unsupported P3D LOD version")

        count_verts = reader.read_uint32()
        count_normals = reader.read_uint32()
        count_faces = reader.read_uint32()
        lod.flags = reader.read_uint32()

        for _ in range(count_verts):
            x = reader.read_float()
            z = reader.read_float()
            y = reader.read_float()
            flag = reader.read_uint32()
            lod.vertices.append(Vertex(Vec3(x, y, z), flag))

        for _ in range(count_normals):
            x = reader.read_float()
            z = reader.read_float()
            y = reader.read_float()
            lod.normals.append(Vec3(-x, -y, -z))
        lod.renormalize_normals()

        for _ in range(count_faces):
            face = Face()
            count_sides = reader.read_uint32()
            for _side in range(count_sides):
                face.vertices.append(reader.read_uint32())
                face.normals.append(reader.read_uint32())
                u = reader.read_float()
                v = reader.read_float()
                face.uvs.append(Vec2(u, 1.0 - v))
            if count_sides < 4:
                reader.seek(16, 1)  # SEEK_CUR
            face.flag = reader.read_uint32()
            face.texture = reader.read_asciiz()
            face.material = reader.read_asciiz()
            lod.faces.append(face)

        if reader.read_chars(4) != "TAGG":
            raise ValueError("Invalid P3D TAGG section signature")

        while True:
            tagg = Tagg.read(reader, count_verts, count_faces)
            if tagg.name == "#EndOfFile#":
                break
            if tagg.active:
                lod.taggs.append(tagg)

        lod.resolution = LodResolution.from_float(reader.read_float())
        return lod

    def write(self, writer):
        writer.write_chars("P3DM")
        writer.write_uint32(self.version_major)
        writer.write_uint32(self.version_minor)
        writer.write_uint32(len(self.vertices))
        writer.write_uint32(len(self.normals))
        writer.write_uint32(len(self.faces))
        writer.write_uint32(self.flags)

        for vertex in self.vertices:
            writer.write_float(vertex.position.x)
            writer.write_float(vertex.position.z)
            writer.write_float(vertex.position.y)
            writer.write_uint32(vertex.flag)

        for normal in self.normals:
            writer.write_float(-normal.x)
            writer.write_float(-normal.z)
            writer.write_float(-normal.y)

        for face in self.faces:
            writer.write_uint32(len(face.vertices))
            for i in range(len(face.vertices)):
                writer.write_uint32(face.vertices[i])
                writer.write_uint32(face.normals[i])
                writer.write_float(face.uvs[i].u)
                writer.write_float(1.0 - face.uvs[i].v)
            if len(face.vertices) < 4:
                writer.write_bytes(b"\x00" * 16)
            writer.write_uint32(face.flag)
            writer.write_asciiz(face.texture)
            writer.write_asciiz(face.material)

        writer.write_chars("TAGG")
        for tagg in self.taggs:
            tagg.write(writer)

        eof = Tagg()
        eof.name = "#EndOfFile#"
        eof.write(writer)
        writer.write_float(self.resolution.as_float())

    def renormalize_normals(self):
        for normal in self.normals:
            length = math.sqrt(normal.x * normal.x + normal.y * normal.y + normal.z * normal.z)
            if length == 0.0:
                continue
            normal.x /= length
            normal.y /= length
            normal.z /= length


class MLOD:
    def __init__(self):
        self.version = 257
        self.lods = []

    @staticmethod
    def read(reader, first_lod_only=False):
        if reader.read_chars(4) != "MLOD":
            raise ValueError("Invalid P3D MLOD signature")

        mlod = MLOD()
        mlod.version = reader.read_uint32()
        if mlod.version != 257:
            raise ValueError("Unsupported P3D MLOD version")

        count_lods = reader.read_uint32()
        if first_lod_only and count_lods > 1:
            count_lods = 1

        for _ in range(count_lods):
            mlod.lods.append(LOD.read(reader))

        return mlod

    @staticmethod
    def read_file(path, first_lod_only=False):
        with BinaryReader(path) as reader:
            return MLOD.read(reader, first_lod_only)

    def write(self, writer):
        if not self.lods:
            raise ValueError("Cannot write MLOD with no LODs")
        writer.write_chars("MLOD")
        writer.write_uint32(self.version)
        writer.write_uint32(len(self.lods))
        for lod in self.lods:
            lod.write(writer)

    def write_file(self, path):
        with BinaryWriter(path) as writer:
            self.write(writer)

    def begin_write(self, writer, lod_count):
        if lod_count == 0:
            raise ValueError("Cannot write MLOD with no LODs")
        writer.write_chars("MLOD")
        writer.write_uint32(self.version)
        writer.write_uint32(lod_count)

    def write_lod(self, writer, lod):
        lod.write(writer)
