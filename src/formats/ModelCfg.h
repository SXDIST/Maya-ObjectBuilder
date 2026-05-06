#pragma once

#include <filesystem>
#include <string>
#include <variant>
#include <vector>

namespace a3ob::cfg
{
struct Value;
using Array = std::vector<Value>;

struct Value
{
    std::variant<std::string, int, double, Array> data;

    bool isString() const;
    bool isInt() const;
    bool isDouble() const;
    bool isArray() const;
    const std::string& asString() const;
    int asInt() const;
    double asDouble() const;
    const Array& asArray() const;
};

struct Property
{
    std::string name;
    Value value;
    bool extends = false;
};

struct Class
{
    std::string name;
    std::string parent;
    std::vector<Property> properties;
    std::vector<Class> classes;

    const Class* findClass(const std::string& className) const;
    const Property* findProperty(const std::string& propertyName) const;
};

struct SkeletonBone
{
    std::string name;
    std::string parent;
};

struct Skeleton
{
    std::string name;
    std::vector<SkeletonBone> bones;
};

struct Config
{
    Class root;

    static Config readFile(const std::filesystem::path& path);
    void writeFile(const std::filesystem::path& path) const;
    std::vector<Skeleton> skeletons() const;
    static Config skeletonConfig(const Skeleton& skeleton);
};
}
