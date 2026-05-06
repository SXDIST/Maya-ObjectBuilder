#pragma once

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace a3ob
{
class BinaryReader
{
public:
    explicit BinaryReader(const std::filesystem::path& path);
    explicit BinaryReader(std::istream& stream);

    bool good() const;
    std::streampos tell();
    void seek(std::streamoff offset, std::ios_base::seekdir dir);

    std::uint8_t readUInt8();
    bool readBool();
    std::uint32_t readUInt32();
    float readFloat();
    std::string readChars(std::size_t count);
    std::string readAsciiz();
    std::string readAsciizField(std::size_t fieldLength);
    std::vector<std::uint32_t> readUInt32s(std::size_t count);
    std::vector<float> readFloats(std::size_t count);
    std::vector<std::uint8_t> readBytes(std::size_t count);

private:
    std::ifstream owned_;
    std::istream* stream_ = nullptr;

    template <typename T>
    T readPod();
};

class BinaryWriter
{
public:
    explicit BinaryWriter(const std::filesystem::path& path);
    explicit BinaryWriter(std::ostream& stream);

    bool good() const;

    void writeUInt8(std::uint8_t value);
    void writeBool(bool value);
    void writeUInt32(std::uint32_t value);
    void writeFloat(float value);
    void writeChars(const std::string& value);
    void writeAsciiz(const std::string& value);
    void writeAsciizField(const std::string& value, std::size_t fieldLength);
    void writeBytes(const std::vector<std::uint8_t>& value);

private:
    std::ofstream owned_;
    std::ostream* stream_ = nullptr;

    template <typename T>
    void writePod(T value);
};
}
