#include "ModelCfg.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace a3ob::cfg
{
namespace
{
enum class TokenKind
{
    Identifier,
    String,
    Integer,
    Number,
    Class,
    BraceOpen,
    BraceClose,
    BracketOpen,
    BracketClose,
    Equals,
    PlusEquals,
    Semicolon,
    Comma,
    Colon,
    End,
};

struct Token
{
    TokenKind kind = TokenKind::End;
    std::string text;
};

std::string lower(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return value;
}

std::string readTextFile(const std::filesystem::path& path)
{
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("Could not open model.cfg: " + path.string());
    }
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return buffer.str();
}

std::vector<Token> tokenize(const std::string& text)
{
    std::vector<Token> tokens;
    std::size_t i = 0;
    while (i < text.size()) {
        const char ch = text[i];
        if (std::isspace(static_cast<unsigned char>(ch))) {
            ++i;
            continue;
        }
        if (ch == '/' && i + 1 < text.size() && text[i + 1] == '/') {
            i += 2;
            while (i < text.size() && text[i] != '\n') ++i;
            continue;
        }
        if (ch == '/' && i + 1 < text.size() && text[i + 1] == '*') {
            i += 2;
            while (i + 1 < text.size() && !(text[i] == '*' && text[i + 1] == '/')) ++i;
            i = std::min(i + 2, text.size());
            continue;
        }
        if (ch == '#') {
            throw std::runtime_error("model.cfg preprocessor directives are not supported");
        }
        if (std::isalpha(static_cast<unsigned char>(ch)) || ch == '_') {
            std::size_t start = i++;
            while (i < text.size() && (std::isalnum(static_cast<unsigned char>(text[i])) || text[i] == '_')) ++i;
            std::string value = text.substr(start, i - start);
            tokens.push_back({lower(value) == "class" ? TokenKind::Class : TokenKind::Identifier, value});
            continue;
        }
        if (std::isdigit(static_cast<unsigned char>(ch)) || ((ch == '-' || ch == '+') && i + 1 < text.size() && std::isdigit(static_cast<unsigned char>(text[i + 1])))) {
            std::size_t start = i++;
            bool isFloat = false;
            while (i < text.size() && (std::isdigit(static_cast<unsigned char>(text[i])) || text[i] == '.')) {
                if (text[i] == '.') isFloat = true;
                ++i;
            }
            tokens.push_back({isFloat ? TokenKind::Number : TokenKind::Integer, text.substr(start, i - start)});
            continue;
        }
        if (ch == '"') {
            ++i;
            std::string value;
            while (i < text.size()) {
                if (text[i] == '"') {
                    if (i + 1 < text.size() && text[i + 1] == '"') {
                        value.push_back('"');
                        i += 2;
                        continue;
                    }
                    ++i;
                    break;
                }
                value.push_back(text[i++]);
            }
            tokens.push_back({TokenKind::String, value});
            continue;
        }
        switch (ch) {
        case '{': tokens.push_back({TokenKind::BraceOpen, "{"}); ++i; break;
        case '}': tokens.push_back({TokenKind::BraceClose, "}"}); ++i; break;
        case '[': tokens.push_back({TokenKind::BracketOpen, "["}); ++i; break;
        case ']': tokens.push_back({TokenKind::BracketClose, "]"}); ++i; break;
        case '=': tokens.push_back({TokenKind::Equals, "="}); ++i; break;
        case '+':
            if (i + 1 < text.size() && text[i + 1] == '=') {
                tokens.push_back({TokenKind::PlusEquals, "+="});
                i += 2;
            } else {
                throw std::runtime_error("Unexpected plus token in model.cfg");
            }
            break;
        case ';': tokens.push_back({TokenKind::Semicolon, ";"}); ++i; break;
        case ',': tokens.push_back({TokenKind::Comma, ","}); ++i; break;
        case ':': tokens.push_back({TokenKind::Colon, ":"}); ++i; break;
        default:
            throw std::runtime_error(std::string("Unexpected character in model.cfg: ") + ch);
        }
    }
    tokens.push_back({TokenKind::End, {}});
    return tokens;
}

class Parser
{
public:
    explicit Parser(std::vector<Token> tokens) : tokens_(std::move(tokens)) {}

    Class parseRoot()
    {
        Class root;
        root.name = "__root__";
        while (!check(TokenKind::End)) {
            root.classes.push_back(parseClass());
        }
        return root;
    }

private:
    bool check(TokenKind kind) const { return tokens_[pos_].kind == kind; }

    const Token& consume(TokenKind kind, const char* message)
    {
        if (!check(kind)) {
            throw std::runtime_error(message);
        }
        return tokens_[pos_++];
    }

    Class parseClass()
    {
        consume(TokenKind::Class, "Expected class keyword");
        Class cls;
        cls.name = consume(TokenKind::Identifier, "Expected class name").text;
        if (check(TokenKind::Semicolon)) {
            ++pos_;
            return cls;
        }
        if (check(TokenKind::Colon)) {
            ++pos_;
            cls.parent = consume(TokenKind::Identifier, "Expected parent class name").text;
        }
        consume(TokenKind::BraceOpen, "Expected class body");
        while (!check(TokenKind::BraceClose)) {
            if (check(TokenKind::Class)) {
                cls.classes.push_back(parseClass());
            } else {
                cls.properties.push_back(parseProperty());
            }
        }
        consume(TokenKind::BraceClose, "Expected class closing brace");
        consume(TokenKind::Semicolon, "Expected semicolon after class");
        return cls;
    }

    Property parseProperty()
    {
        Property property;
        property.name = consume(TokenKind::Identifier, "Expected property name").text;
        if (check(TokenKind::BracketOpen)) {
            ++pos_;
            consume(TokenKind::BracketClose, "Expected [] property close");
        }
        if (check(TokenKind::PlusEquals)) {
            property.extends = true;
            ++pos_;
        } else {
            consume(TokenKind::Equals, "Expected property assignment");
        }
        property.value = parseValue();
        consume(TokenKind::Semicolon, "Expected semicolon after property");
        return property;
    }

    Value parseValue()
    {
        if (check(TokenKind::BraceOpen)) {
            ++pos_;
            Array values;
            while (!check(TokenKind::BraceClose)) {
                values.push_back(parseValue());
                if (check(TokenKind::Comma)) ++pos_;
            }
            consume(TokenKind::BraceClose, "Expected array closing brace");
            return Value{values};
        }
        if (check(TokenKind::String)) return Value{tokens_[pos_++].text};
        if (check(TokenKind::Integer)) return Value{std::stoi(tokens_[pos_++].text)};
        if (check(TokenKind::Number)) return Value{std::stod(tokens_[pos_++].text)};
        if (check(TokenKind::Identifier)) return Value{tokens_[pos_++].text};
        throw std::runtime_error("Expected config value");
    }

    std::vector<Token> tokens_;
    std::size_t pos_ = 0;
};

void writeIndent(std::ostream& stream, int indent)
{
    for (int i = 0; i < indent; ++i) stream << '\t';
}

void writeValue(std::ostream& stream, const Value& value, int indent);

void writeArray(std::ostream& stream, const Array& array, int indent)
{
    if (array.empty()) {
        stream << "{}";
        return;
    }
    stream << "{\n";
    for (std::size_t i = 0; i < array.size(); ++i) {
        writeIndent(stream, indent + 1);
        writeValue(stream, array[i], indent + 1);
        if (i + 1 < array.size()) stream << ',';
        stream << "\n";
    }
    writeIndent(stream, indent);
    stream << '}';
}

void writeValue(std::ostream& stream, const Value& value, int indent)
{
    if (value.isString()) {
        stream << '"' << value.asString() << '"';
    } else if (value.isInt()) {
        stream << value.asInt();
    } else if (value.isDouble()) {
        stream << value.asDouble();
    } else {
        writeArray(stream, value.asArray(), indent);
    }
}

void writeClass(std::ostream& stream, const Class& cls, int indent)
{
    writeIndent(stream, indent);
    stream << "class " << cls.name;
    if (!cls.parent.empty()) stream << ": " << cls.parent;
    stream << " {\n";
    for (const Property& property : cls.properties) {
        writeIndent(stream, indent + 1);
        stream << property.name;
        if (property.value.isArray()) stream << "[]";
        stream << (property.extends ? " += " : " = ");
        writeValue(stream, property.value, indent + 1);
        stream << ";\n";
    }
    for (const Class& child : cls.classes) {
        writeClass(stream, child, indent + 1);
    }
    writeIndent(stream, indent);
    stream << "};\n";
}
}

bool Value::isString() const { return std::holds_alternative<std::string>(data); }
bool Value::isInt() const { return std::holds_alternative<int>(data); }
bool Value::isDouble() const { return std::holds_alternative<double>(data); }
bool Value::isArray() const { return std::holds_alternative<Array>(data); }
const std::string& Value::asString() const { return std::get<std::string>(data); }
int Value::asInt() const { return std::get<int>(data); }
double Value::asDouble() const { return std::get<double>(data); }
const Array& Value::asArray() const { return std::get<Array>(data); }

const Class* Class::findClass(const std::string& className) const
{
    const std::string needle = lower(className);
    for (const Class& child : classes) {
        if (lower(child.name) == needle) return &child;
    }
    return nullptr;
}

const Property* Class::findProperty(const std::string& propertyName) const
{
    const std::string needle = lower(propertyName);
    for (const Property& property : properties) {
        if (lower(property.name) == needle) return &property;
    }
    return nullptr;
}

Config Config::readFile(const std::filesystem::path& path)
{
    Parser parser(tokenize(readTextFile(path)));
    Config config;
    config.root = parser.parseRoot();
    return config;
}

void Config::writeFile(const std::filesystem::path& path) const
{
    std::ofstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("Could not write model.cfg: " + path.string());
    }
    for (const Class& cls : root.classes) {
        writeClass(stream, cls, 0);
        stream << '\n';
    }
}

std::vector<Skeleton> Config::skeletons() const
{
    std::vector<Skeleton> result;
    const Class* cfgSkeletons = root.findClass("CfgSkeletons");
    if (!cfgSkeletons) return result;
    for (const Class& skeletonClass : cfgSkeletons->classes) {
        Skeleton skeleton;
        skeleton.name = skeletonClass.name;
        const Property* bones = skeletonClass.findProperty("skeletonBones");
        if (bones && bones->value.isArray()) {
            const Array& values = bones->value.asArray();
            for (std::size_t i = 0; i + 1 < values.size(); i += 2) {
                if (values[i].isString() && values[i + 1].isString()) {
                    skeleton.bones.push_back({values[i].asString(), values[i + 1].asString()});
                }
            }
        }
        result.push_back(std::move(skeleton));
    }
    return result;
}

Config Config::skeletonConfig(const Skeleton& skeleton)
{
    Class skeletonClass;
    skeletonClass.name = skeleton.name;
    skeletonClass.properties.push_back({"isDiscrete", Value{0}, false});
    skeletonClass.properties.push_back({"skeletonInherit", Value{std::string()}, false});
    Array bones;
    for (const SkeletonBone& bone : skeleton.bones) {
        bones.push_back(Value{bone.name});
        bones.push_back(Value{bone.parent});
    }
    skeletonClass.properties.push_back({"skeletonBones", Value{bones}, false});

    Class cfgSkeletons;
    cfgSkeletons.name = "CfgSkeletons";
    cfgSkeletons.classes.push_back(std::move(skeletonClass));

    Config config;
    config.root.name = "__root__";
    config.root.classes.push_back(std::move(cfgSkeletons));
    return config;
}
}
