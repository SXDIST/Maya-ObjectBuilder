#include "P3D.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <map>
#include <regex>
#include <stdexcept>

namespace a3ob::p3d
{
namespace
{
constexpr int LOD_VISUAL = 0;
constexpr int LOD_VIEW_GUNNER = 1;
constexpr int LOD_VIEW_PILOT = 2;
constexpr int LOD_VIEW_CARGO = 3;
constexpr int LOD_SHADOW = 4;
constexpr int LOD_EDIT = 5;
constexpr int LOD_GEOMETRY = 6;
constexpr int LOD_GEOMETRY_BUOY = 7;
constexpr int LOD_GEOMETRY_PHYSX = 8;
constexpr int LOD_MEMORY = 9;
constexpr int LOD_LANDCONTACT = 10;
constexpr int LOD_ROADWAY = 11;
constexpr int LOD_PATHS = 12;
constexpr int LOD_HITPOINTS = 13;
constexpr int LOD_VIEW_GEOMETRY = 14;
constexpr int LOD_FIRE_GEOMETRY = 15;
constexpr int LOD_VIEW_CARGO_GEOMETRY = 16;
constexpr int LOD_VIEW_CARGO_FIRE_GEOMETRY = 17;
constexpr int LOD_VIEW_COMMANDER = 18;
constexpr int LOD_VIEW_COMMANDER_GEOMETRY = 19;
constexpr int LOD_VIEW_COMMANDER_FIRE_GEOMETRY = 20;
constexpr int LOD_VIEW_PILOT_GEOMETRY = 21;
constexpr int LOD_VIEW_PILOT_FIRE_GEOMETRY = 22;
constexpr int LOD_VIEW_GUNNER_GEOMETRY = 23;
constexpr int LOD_VIEW_GUNNER_FIRE_GEOMETRY = 24;
constexpr int LOD_SUBPARTS = 25;
constexpr int LOD_SHADOW_VIEW_CARGO = 26;
constexpr int LOD_SHADOW_VIEW_PILOT = 27;
constexpr int LOD_SHADOW_VIEW_GUNNER = 28;
constexpr int LOD_WRECKAGE = 29;
constexpr int LOD_UNDERGROUND = 30;
constexpr int LOD_GROUNDLAYER = 31;
constexpr int LOD_NAVIGATION = 32;
constexpr int LOD_UNKNOWN = -1;

const std::map<std::string, int>& signatureMap()
{
    static const std::map<std::string, int> values = {
        {"1.000e+03", LOD_VIEW_GUNNER},
        {"1.100e+03", LOD_VIEW_PILOT},
        {"1.300e+04", LOD_GROUNDLAYER},
        {"1.000e+13", LOD_GEOMETRY},
        {"2.000e+13", LOD_GEOMETRY_BUOY},
        {"3.000e+13", LOD_UNDERGROUND},
        {"4.000e+13", LOD_GEOMETRY_PHYSX},
        {"5.000e+13", LOD_NAVIGATION},
        {"1.000e+15", LOD_MEMORY},
        {"2.000e+15", LOD_LANDCONTACT},
        {"3.000e+15", LOD_ROADWAY},
        {"4.000e+15", LOD_PATHS},
        {"5.000e+15", LOD_HITPOINTS},
        {"6.000e+15", LOD_VIEW_GEOMETRY},
        {"7.000e+15", LOD_FIRE_GEOMETRY},
        {"9.000e+15", LOD_VIEW_CARGO_FIRE_GEOMETRY},
        {"1.000e+16", LOD_VIEW_COMMANDER},
        {"1.100e+16", LOD_VIEW_COMMANDER_GEOMETRY},
        {"1.200e+16", LOD_VIEW_COMMANDER_FIRE_GEOMETRY},
        {"1.300e+16", LOD_VIEW_PILOT_GEOMETRY},
        {"1.400e+16", LOD_VIEW_PILOT_FIRE_GEOMETRY},
        {"1.500e+16", LOD_VIEW_GUNNER_GEOMETRY},
        {"1.600e+16", LOD_VIEW_GUNNER_FIRE_GEOMETRY},
        {"1.700e+16", LOD_SUBPARTS},
        {"1.900e+16", LOD_SHADOW_VIEW_PILOT},
        {"2.000e+16", LOD_SHADOW_VIEW_GUNNER},
        {"2.100e+16", LOD_WRECKAGE},
    };
    return values;
}

std::string scientificKey(float value)
{
    char buffer[32] = {};
    std::snprintf(buffer, sizeof(buffer), "%.3e", value);
    return buffer;
}

bool startsAndEndsWithHash(const std::string& value)
{
    return value.size() >= 2 && value.front() == '#' && value.back() == '#';
}
}

std::unique_ptr<SharpEdgesTaggData> SharpEdgesTaggData::read(BinaryReader& reader, std::uint32_t length)
{
    if (length % 8 != 0) {
        throw std::runtime_error("Invalid sharp edges length");
    }

    auto data = std::make_unique<SharpEdgesTaggData>();
    const std::uint32_t countValues = length / 4;
    for (std::uint32_t i = 0; i < countValues; i += 2) {
        const std::uint32_t first = reader.readUInt32();
        const std::uint32_t second = reader.readUInt32();
        if (first != second) {
            data->edges.emplace_back(first, second);
        }
    }
    return data;
}

std::uint32_t SharpEdgesTaggData::length() const
{
    return static_cast<std::uint32_t>(edges.size() * 8);
}

void SharpEdgesTaggData::write(BinaryWriter& writer) const
{
    for (const auto& edge : edges) {
        if (edge.first == edge.second) {
            continue;
        }
        writer.writeUInt32(edge.first);
        writer.writeUInt32(edge.second);
    }
}

std::unique_ptr<PropertyTaggData> PropertyTaggData::read(BinaryReader& reader)
{
    auto data = std::make_unique<PropertyTaggData>();
    data->key = reader.readAsciizField(64);
    data->value = reader.readAsciizField(64);
    return data;
}

void PropertyTaggData::write(BinaryWriter& writer) const
{
    writer.writeAsciizField(key, 64);
    writer.writeAsciizField(value, 64);
}

std::unique_ptr<MassTaggData> MassTaggData::read(BinaryReader& reader, std::uint32_t countVerts)
{
    auto data = std::make_unique<MassTaggData>();
    data->masses = reader.readFloats(countVerts);
    return data;
}

std::uint32_t MassTaggData::length() const
{
    return static_cast<std::uint32_t>(masses.size() * 4);
}

void MassTaggData::write(BinaryWriter& writer) const
{
    for (const float value : masses) {
        writer.writeFloat(value);
    }
}

std::unique_ptr<UVSetTaggData> UVSetTaggData::read(BinaryReader& reader, std::uint32_t length)
{
    if (length < 4 || (length - 4) % 8 != 0) {
        throw std::runtime_error("Invalid UV set length");
    }

    auto data = std::make_unique<UVSetTaggData>();
    data->id = reader.readUInt32();
    const std::uint32_t countValues = (length - 4) / 4;
    for (std::uint32_t i = 0; i < countValues; i += 2) {
        const float u = reader.readFloat();
        const float v = reader.readFloat();
        data->uvs.push_back({u, 1.0f - v});
    }
    return data;
}

std::uint32_t UVSetTaggData::length() const
{
    return static_cast<std::uint32_t>(uvs.size() * 8 + 4);
}

void UVSetTaggData::write(BinaryWriter& writer) const
{
    writer.writeUInt32(id);
    for (const Vec2& uv : uvs) {
        writer.writeFloat(uv.u);
        writer.writeFloat(1.0f - uv.v);
    }
}

float SelectionTaggData::decodeWeight(std::uint8_t weight)
{
    if (weight == 0 || weight == 1) {
        return static_cast<float>(weight);
    }
    return static_cast<float>(255 - weight) / 254.0f;
}

std::uint8_t SelectionTaggData::encodeWeight(float weight)
{
    if (weight == 0.0f || weight == 1.0f) {
        return static_cast<std::uint8_t>(weight);
    }
    return static_cast<std::uint8_t>(std::round(255.0f - 254.0f * weight));
}

std::unique_ptr<SelectionTaggData> SelectionTaggData::read(BinaryReader& reader, std::uint32_t countVerts, std::uint32_t countFaces)
{
    auto data = std::make_unique<SelectionTaggData>();
    data->countVerts = countVerts;
    data->countFaces = countFaces;

    const std::vector<std::uint8_t> vertexBytes = reader.readBytes(countVerts);
    for (std::uint32_t i = 0; i < countVerts; ++i) {
        if (vertexBytes[i] > 0) {
            data->vertexWeights.emplace_back(i, decodeWeight(vertexBytes[i]));
        }
    }

    const std::vector<std::uint8_t> faceBytes = reader.readBytes(countFaces);
    for (std::uint32_t i = 0; i < countFaces; ++i) {
        if (faceBytes[i] > 0) {
            data->faceWeights.emplace_back(i, decodeWeight(faceBytes[i]));
        }
    }

    return data;
}

std::uint32_t SelectionTaggData::length() const
{
    return countVerts + countFaces;
}

void SelectionTaggData::write(BinaryWriter& writer) const
{
    std::vector<std::uint8_t> vertexBytes(countVerts, 0);
    for (const auto& [idx, weight] : vertexWeights) {
        if (idx < vertexBytes.size()) {
            vertexBytes[idx] = encodeWeight(weight);
        }
    }

    std::vector<std::uint8_t> faceBytes(countFaces, 0);
    for (const auto& [idx, weight] : faceWeights) {
        if (idx < faceBytes.size()) {
            faceBytes[idx] = encodeWeight(weight);
        }
    }

    writer.writeBytes(vertexBytes);
    writer.writeBytes(faceBytes);
}

Tagg::Tagg() = default;

bool Tagg::isProxy() const
{
    static const std::regex proxyRegex(R"(^proxy:.*\.\d+$)");
    return std::regex_match(name, proxyRegex);
}

bool Tagg::isSelection() const
{
    return !startsAndEndsWithHash(name);
}

Tagg Tagg::read(BinaryReader& reader, std::uint32_t countVerts, std::uint32_t countFaces)
{
    Tagg tagg;
    tagg.active = reader.readBool();
    tagg.name = reader.readAsciiz();
    const std::uint32_t length = reader.readUInt32();

    if (tagg.name == "#EndOfFile#") {
        if (length != 0) {
            throw std::runtime_error("Invalid P3D EOF TAGG");
        }
        tagg.active = false;
        return tagg;
    }

    if (tagg.name == "#SharpEdges#") {
        tagg.data = SharpEdgesTaggData::read(reader, length);
    } else if (tagg.name == "#Property#") {
        if (length != 128) {
            throw std::runtime_error("Invalid property TAGG length");
        }
        tagg.data = PropertyTaggData::read(reader);
    } else if (tagg.name == "#Mass#") {
        tagg.data = MassTaggData::read(reader, countVerts);
    } else if (tagg.name == "#UVSet#") {
        tagg.data = UVSetTaggData::read(reader, length);
    } else if (tagg.isSelection()) {
        tagg.data = SelectionTaggData::read(reader, countVerts, countFaces);
    } else {
        reader.seek(length, std::ios::cur);
        tagg.active = false;
        tagg.data = std::make_unique<EmptyTaggData>();
    }

    return tagg;
}

void Tagg::write(BinaryWriter& writer) const
{
    if (!active) {
        return;
    }
    writer.writeBool(active);
    writer.writeAsciiz(name);
    writer.writeUInt32(data ? data->length() : 0);
    if (data) {
        data->write(writer);
    }
}

float LodResolution::encode(int lod, int resolution)
{
    if (lod == LOD_VISUAL || lod == LOD_UNKNOWN) {
        return static_cast<float>(resolution);
    }

    for (const auto& [signature, mappedLod] : signatureMap()) {
        if (mappedLod == lod) {
            return std::stof(signature);
        }
    }

    if (lod == LOD_VIEW_CARGO) return 1.2e3f + static_cast<float>(resolution);
    if (lod == LOD_SHADOW) return 1.0e4f + static_cast<float>(resolution);
    if (lod == LOD_EDIT) return 2.0e4f + static_cast<float>(resolution);
    if (lod == LOD_VIEW_CARGO_GEOMETRY) return 8.0e15f + static_cast<float>(resolution) * 1.0e13f;
    if (lod == LOD_SHADOW_VIEW_CARGO) return 1.8e16f + static_cast<float>(resolution) * 1.0e13f;

    return static_cast<float>(resolution);
}

LodResolution LodResolution::fromFloat(float value)
{
    LodResolution output;
    output.source = value;

    if (value < 1.0e3f) {
        output.lod = LOD_VISUAL;
        output.resolution = static_cast<int>(std::round(value));
        return output;
    }
    if (value >= 1.2e3f && value < 1.3e3f) {
        output.lod = LOD_VIEW_CARGO;
        output.resolution = static_cast<int>(std::round(value - 1.2e3f));
        return output;
    }
    if (value >= 1.0e4f && value < 1.2e4f) {
        output.lod = LOD_SHADOW;
        output.resolution = static_cast<int>(std::round(value - 1.0e4f));
        return output;
    }
    if (value >= 2.0e4f && value < 3.0e4f) {
        output.lod = LOD_EDIT;
        output.resolution = static_cast<int>(std::round(value - 2.0e4f));
        return output;
    }

    const std::string key = scientificKey(value);
    const auto mapped = signatureMap().find(key);
    if (mapped != signatureMap().end()) {
        output.lod = mapped->second;
        output.resolution = 0;
        return output;
    }

    const std::size_t expPos = key.find('e');
    const int exponent = expPos == std::string::npos ? 0 : std::stoi(key.substr(expPos + 1));
    if (exponent == 15) {
        output.lod = LOD_VIEW_CARGO_GEOMETRY;
        output.resolution = std::stoi(key.substr(2, 2));
        return output;
    }
    if (exponent == 16) {
        output.lod = LOD_SHADOW_VIEW_CARGO;
        output.resolution = std::stoi(key.substr(3, 2));
        return output;
    }

    output.lod = LOD_UNKNOWN;
    output.resolution = static_cast<int>(std::round(value));
    return output;
}

float LodResolution::asFloat() const
{
    return encode(lod, resolution);
}

LOD LOD::read(BinaryReader& reader)
{
    if (reader.readChars(4) != "P3DM") {
        throw std::runtime_error("Unsupported P3D LOD signature");
    }

    LOD lod;
    lod.versionMajor = reader.readUInt32();
    lod.versionMinor = reader.readUInt32();
    if (lod.versionMajor != 0x1c || lod.versionMinor != 0x100) {
        throw std::runtime_error("Unsupported P3D LOD version");
    }

    const std::uint32_t countVerts = reader.readUInt32();
    const std::uint32_t countNormals = reader.readUInt32();
    const std::uint32_t countFaces = reader.readUInt32();
    lod.flags = reader.readUInt32();

    lod.vertices.reserve(countVerts);
    for (std::uint32_t i = 0; i < countVerts; ++i) {
        const float x = reader.readFloat();
        const float z = reader.readFloat();
        const float y = reader.readFloat();
        const std::uint32_t flag = reader.readUInt32();
        lod.vertices.push_back({{x, y, z}, flag});
    }

    lod.normals.reserve(countNormals);
    for (std::uint32_t i = 0; i < countNormals; ++i) {
        const float x = reader.readFloat();
        const float z = reader.readFloat();
        const float y = reader.readFloat();
        lod.normals.push_back({-x, -y, -z});
    }
    lod.renormalizeNormals();

    lod.faces.reserve(countFaces);
    for (std::uint32_t i = 0; i < countFaces; ++i) {
        Face face;
        const std::uint32_t countSides = reader.readUInt32();
        face.vertices.reserve(countSides);
        face.normals.reserve(countSides);
        face.uvs.reserve(countSides);
        for (std::uint32_t side = 0; side < countSides; ++side) {
            face.vertices.push_back(reader.readUInt32());
            face.normals.push_back(reader.readUInt32());
            const float u = reader.readFloat();
            const float v = reader.readFloat();
            face.uvs.push_back({u, 1.0f - v});
        }
        if (countSides < 4) {
            reader.seek(16, std::ios::cur);
        }
        face.flag = reader.readUInt32();
        face.texture = reader.readAsciiz();
        face.material = reader.readAsciiz();
        lod.faces.push_back(std::move(face));
    }

    if (reader.readChars(4) != "TAGG") {
        throw std::runtime_error("Invalid P3D TAGG section signature");
    }

    while (true) {
        Tagg tagg = Tagg::read(reader, countVerts, countFaces);
        if (tagg.name == "#EndOfFile#") {
            break;
        }
        if (tagg.active) {
            lod.taggs.push_back(std::move(tagg));
        }
    }

    lod.resolution = LodResolution::fromFloat(reader.readFloat());
    return lod;
}

void LOD::write(BinaryWriter& writer) const
{
    writer.writeChars("P3DM");
    writer.writeUInt32(versionMajor);
    writer.writeUInt32(versionMinor);
    writer.writeUInt32(static_cast<std::uint32_t>(vertices.size()));
    writer.writeUInt32(static_cast<std::uint32_t>(normals.size()));
    writer.writeUInt32(static_cast<std::uint32_t>(faces.size()));
    writer.writeUInt32(flags);

    for (const Vertex& vertex : vertices) {
        writer.writeFloat(vertex.position.x);
        writer.writeFloat(vertex.position.z);
        writer.writeFloat(vertex.position.y);
        writer.writeUInt32(vertex.flag);
    }

    for (const Vec3& normal : normals) {
        writer.writeFloat(-normal.x);
        writer.writeFloat(-normal.z);
        writer.writeFloat(-normal.y);
    }

    for (const Face& face : faces) {
        writer.writeUInt32(static_cast<std::uint32_t>(face.vertices.size()));
        for (std::size_t i = 0; i < face.vertices.size(); ++i) {
            writer.writeUInt32(face.vertices[i]);
            writer.writeUInt32(face.normals[i]);
            writer.writeFloat(face.uvs[i].u);
            writer.writeFloat(face.uvs[i].v);
        }
        if (face.vertices.size() < 4) {
            writer.writeBytes(std::vector<std::uint8_t>(16, 0));
        }
        writer.writeUInt32(face.flag);
        writer.writeAsciiz(face.texture);
        writer.writeAsciiz(face.material);
    }

    writer.writeChars("TAGG");
    for (const Tagg& tagg : taggs) {
        tagg.write(writer);
    }

    Tagg eof;
    eof.name = "#EndOfFile#";
    eof.write(writer);
    writer.writeFloat(resolution.asFloat());
}

void LOD::renormalizeNormals()
{
    for (Vec3& normal : normals) {
        const float length = std::sqrt(normal.x * normal.x + normal.y * normal.y + normal.z * normal.z);
        if (length == 0.0f) {
            continue;
        }
        normal.x /= length;
        normal.y /= length;
        normal.z /= length;
    }
}

MLOD MLOD::read(BinaryReader& reader, bool firstLodOnly)
{
    if (reader.readChars(4) != "MLOD") {
        throw std::runtime_error("Invalid P3D MLOD signature");
    }

    MLOD mlod;
    mlod.version = reader.readUInt32();
    if (mlod.version != 257) {
        throw std::runtime_error("Unsupported P3D MLOD version");
    }

    std::uint32_t countLods = reader.readUInt32();
    if (firstLodOnly && countLods > 1) {
        countLods = 1;
    }

    mlod.lods.reserve(countLods);
    for (std::uint32_t i = 0; i < countLods; ++i) {
        mlod.lods.push_back(LOD::read(reader));
    }

    return mlod;
}

MLOD MLOD::readFile(const std::filesystem::path& path, bool firstLodOnly)
{
    BinaryReader reader(path);
    return read(reader, firstLodOnly);
}

void MLOD::write(BinaryWriter& writer) const
{
    if (lods.empty()) {
        throw std::runtime_error("Cannot write MLOD with no LODs");
    }

    writer.writeChars("MLOD");
    writer.writeUInt32(version);
    writer.writeUInt32(static_cast<std::uint32_t>(lods.size()));
    for (const LOD& lod : lods) {
        lod.write(writer);
    }
}

void MLOD::writeFile(const std::filesystem::path& path) const
{
    BinaryWriter writer(path);
    write(writer);
}
}
