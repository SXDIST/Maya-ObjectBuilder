#pragma once

#include "BinaryIO.h"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace a3ob::p3d
{
struct Vec2
{
    float u = 0.0f;
    float v = 0.0f;
};

struct Vec3
{
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

struct Vertex
{
    Vec3 position;
    std::uint32_t flag = 0;
};

struct Face
{
    std::vector<std::uint32_t> vertices;
    std::vector<std::uint32_t> normals;
    std::vector<Vec2> uvs;
    std::string texture;
    std::string material;
    std::uint32_t flag = 0;
};

enum class TaggKind
{
    Empty,
    SharpEdges,
    Property,
    Mass,
    UVSet,
    Selection,
};

struct TaggData
{
    virtual ~TaggData() = default;
    virtual TaggKind kind() const = 0;
    virtual std::uint32_t length() const = 0;
    virtual void write(BinaryWriter& writer) const = 0;
};

struct EmptyTaggData final : TaggData
{
    TaggKind kind() const override { return TaggKind::Empty; }
    std::uint32_t length() const override { return 0; }
    void write(BinaryWriter&) const override {}
};

struct SharpEdgesTaggData final : TaggData
{
    std::vector<std::pair<std::uint32_t, std::uint32_t>> edges;

    static std::unique_ptr<SharpEdgesTaggData> read(BinaryReader& reader, std::uint32_t length);
    TaggKind kind() const override { return TaggKind::SharpEdges; }
    std::uint32_t length() const override;
    void write(BinaryWriter& writer) const override;
};

struct PropertyTaggData final : TaggData
{
    std::string key;
    std::string value;

    static std::unique_ptr<PropertyTaggData> read(BinaryReader& reader);
    TaggKind kind() const override { return TaggKind::Property; }
    std::uint32_t length() const override { return 128; }
    void write(BinaryWriter& writer) const override;
};

struct MassTaggData final : TaggData
{
    std::vector<float> masses;

    static std::unique_ptr<MassTaggData> read(BinaryReader& reader, std::uint32_t countVerts);
    TaggKind kind() const override { return TaggKind::Mass; }
    std::uint32_t length() const override;
    void write(BinaryWriter& writer) const override;
};

struct UVSetTaggData final : TaggData
{
    std::uint32_t id = 0;
    std::vector<Vec2> uvs;

    static std::unique_ptr<UVSetTaggData> read(BinaryReader& reader, std::uint32_t length);
    TaggKind kind() const override { return TaggKind::UVSet; }
    std::uint32_t length() const override;
    void write(BinaryWriter& writer) const override;
};

struct SelectionTaggData final : TaggData
{
    std::uint32_t countVerts = 0;
    std::uint32_t countFaces = 0;
    std::vector<std::pair<std::uint32_t, float>> vertexWeights;
    std::vector<std::pair<std::uint32_t, float>> faceWeights;

    static float decodeWeight(std::uint8_t weight);
    static std::uint8_t encodeWeight(float weight);
    static std::unique_ptr<SelectionTaggData> read(BinaryReader& reader, std::uint32_t countVerts, std::uint32_t countFaces);
    TaggKind kind() const override { return TaggKind::Selection; }
    std::uint32_t length() const override;
    void write(BinaryWriter& writer) const override;
};

struct Tagg
{
    bool active = true;
    std::string name;
    std::unique_ptr<TaggData> data = std::make_unique<EmptyTaggData>();

    Tagg();
    Tagg(Tagg&&) noexcept = default;
    Tagg& operator=(Tagg&&) noexcept = default;

    bool isProxy() const;
    bool isSelection() const;
    void write(BinaryWriter& writer) const;
    static Tagg read(BinaryReader& reader, std::uint32_t countVerts, std::uint32_t countFaces);
};

struct LodResolution
{
    int lod = 0;
    int resolution = 0;
    float source = 0.0f;

    static float encode(int lod, int resolution);
    static LodResolution fromFloat(float value);
    float asFloat() const;
};

struct LOD
{
    std::uint32_t versionMajor = 0x1c;
    std::uint32_t versionMinor = 0x100;
    std::uint32_t flags = 0;
    LodResolution resolution;
    std::vector<Vertex> vertices;
    std::vector<Vec3> normals;
    std::vector<Face> faces;
    std::vector<Tagg> taggs;

    static LOD read(BinaryReader& reader);
    void write(BinaryWriter& writer) const;
    void renormalizeNormals();
};

struct MLOD
{
    std::uint32_t version = 257;
    std::vector<LOD> lods;

    static MLOD read(BinaryReader& reader, bool firstLodOnly = false);
    static MLOD readFile(const std::filesystem::path& path, bool firstLodOnly = false);
    void write(BinaryWriter& writer) const;
    void writeFile(const std::filesystem::path& path) const;
};
}
