#include "BinaryIO.h"

#include <array>
#include <cstring>
#include <stdexcept>

namespace a3ob
{
BinaryReader::BinaryReader(const std::filesystem::path& path)
    : owned_(path, std::ios::binary), stream_(&owned_)
{
}

BinaryReader::BinaryReader(std::istream& stream)
    : stream_(&stream)
{
}

bool BinaryReader::good() const
{
    return stream_ && stream_->good();
}

std::streampos BinaryReader::tell()
{
    return stream_->tellg();
}

void BinaryReader::seek(std::streamoff offset, std::ios_base::seekdir dir)
{
    stream_->seekg(offset, dir);
    if (!*stream_) {
        throw std::runtime_error("Binary seek failed");
    }
}

template <typename T>
T BinaryReader::readPod()
{
    T value{};
    stream_->read(reinterpret_cast<char*>(&value), sizeof(T));
    if (stream_->gcount() != static_cast<std::streamsize>(sizeof(T))) {
        throw std::runtime_error("Unexpected EOF while reading binary value");
    }
    return value;
}

std::uint8_t BinaryReader::readUInt8()
{
    return readPod<std::uint8_t>();
}

bool BinaryReader::readBool()
{
    return readUInt8() != 0;
}

std::uint32_t BinaryReader::readUInt32()
{
    return readPod<std::uint32_t>();
}

float BinaryReader::readFloat()
{
    return readPod<float>();
}

std::string BinaryReader::readChars(std::size_t count)
{
    std::string value(count, '\0');
    stream_->read(value.data(), static_cast<std::streamsize>(count));
    if (stream_->gcount() != static_cast<std::streamsize>(count)) {
        throw std::runtime_error("Unexpected EOF while reading chars");
    }
    return value;
}

std::string BinaryReader::readAsciiz()
{
    std::string value;
    char ch = 0;
    while (stream_->get(ch)) {
        if (ch == '\0') {
            return value;
        }
        value.push_back(ch);
    }
    throw std::runtime_error("Unexpected EOF while reading ASCIIZ string");
}

std::string BinaryReader::readAsciizField(std::size_t fieldLength)
{
    std::string field = readChars(fieldLength);
    const std::size_t pos = field.find('\0');
    if (pos == std::string::npos) {
        throw std::runtime_error("ASCIIZ field length overflow");
    }
    return field.substr(0, pos);
}

std::vector<std::uint32_t> BinaryReader::readUInt32s(std::size_t count)
{
    std::vector<std::uint32_t> values;
    values.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        values.push_back(readUInt32());
    }
    return values;
}

std::vector<float> BinaryReader::readFloats(std::size_t count)
{
    std::vector<float> values;
    values.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        values.push_back(readFloat());
    }
    return values;
}

std::vector<std::uint8_t> BinaryReader::readBytes(std::size_t count)
{
    std::vector<std::uint8_t> values(count);
    stream_->read(reinterpret_cast<char*>(values.data()), static_cast<std::streamsize>(count));
    if (stream_->gcount() != static_cast<std::streamsize>(count)) {
        throw std::runtime_error("Unexpected EOF while reading bytes");
    }
    return values;
}

BinaryWriter::BinaryWriter(const std::filesystem::path& path)
    : owned_(path, std::ios::binary), stream_(&owned_)
{
}

BinaryWriter::BinaryWriter(std::ostream& stream)
    : stream_(&stream)
{
}

bool BinaryWriter::good() const
{
    return stream_ && stream_->good();
}

template <typename T>
void BinaryWriter::writePod(T value)
{
    stream_->write(reinterpret_cast<const char*>(&value), sizeof(T));
    if (!*stream_) {
        throw std::runtime_error("Binary write failed");
    }
}

void BinaryWriter::writeUInt8(std::uint8_t value)
{
    writePod(value);
}

void BinaryWriter::writeBool(bool value)
{
    writeUInt8(value ? 1 : 0);
}

void BinaryWriter::writeUInt32(std::uint32_t value)
{
    writePod(value);
}

void BinaryWriter::writeFloat(float value)
{
    writePod(value);
}

void BinaryWriter::writeChars(const std::string& value)
{
    stream_->write(value.data(), static_cast<std::streamsize>(value.size()));
    if (!*stream_) {
        throw std::runtime_error("Binary char write failed");
    }
}

void BinaryWriter::writeAsciiz(const std::string& value)
{
    writeChars(value);
    writeUInt8(0);
}

void BinaryWriter::writeAsciizField(const std::string& value, std::size_t fieldLength)
{
    if (value.size() + 1 > fieldLength) {
        throw std::runtime_error("ASCIIZ value exceeds fixed field length");
    }

    writeChars(value);
    std::vector<std::uint8_t> padding(fieldLength - value.size(), 0);
    writeBytes(padding);
}

void BinaryWriter::writeBytes(const std::vector<std::uint8_t>& value)
{
    if (value.empty()) {
        return;
    }
    stream_->write(reinterpret_cast<const char*>(value.data()), static_cast<std::streamsize>(value.size()));
    if (!*stream_) {
        throw std::runtime_error("Binary byte write failed");
    }
}
}
