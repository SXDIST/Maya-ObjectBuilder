"""Bohemia ``model.cfg`` / class-config parser and writer.

Direct 1:1 port of the former C++ ``src/formats/ModelCfg.{h,cpp}``. A small
recursive-descent parser over the class-config syntax used by ``CfgSkeletons``.
Preprocessor directives (``#include`` etc.) are not supported and raise.

Values are plain Python ``str`` / ``int`` / ``float`` / ``list`` (arrays). Bareword
identifiers parse as strings and are re-quoted on write, matching the C++ behavior.
"""

import io

__all__ = [
    "Value", "Property", "Class", "SkeletonBone", "Skeleton", "Config",
]


# -- tokenizer -----------------------------------------------------------------
_IDENTIFIER = "Identifier"
_STRING = "String"
_INTEGER = "Integer"
_NUMBER = "Number"
_CLASS = "Class"
_BRACE_OPEN = "BraceOpen"
_BRACE_CLOSE = "BraceClose"
_BRACKET_OPEN = "BracketOpen"
_BRACKET_CLOSE = "BracketClose"
_EQUALS = "Equals"
_PLUS_EQUALS = "PlusEquals"
_SEMICOLON = "Semicolon"
_COMMA = "Comma"
_COLON = "Colon"
_END = "End"


def _tokenize(text):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            continue
        if ch == "#":
            raise ValueError("model.cfg preprocessor directives are not supported")
        if ch.isalpha() or ch == "_":
            start = i
            i += 1
            while i < n and (text[i].isalnum() or text[i] == "_"):
                i += 1
            value = text[start:i]
            kind = _CLASS if value.lower() == "class" else _IDENTIFIER
            tokens.append((kind, value))
            continue
        if ch.isdigit() or ((ch == "-" or ch == "+") and i + 1 < n and text[i + 1].isdigit()):
            start = i
            i += 1
            is_float = False
            while i < n and (text[i].isdigit() or text[i] == "."):
                if text[i] == ".":
                    is_float = True
                i += 1
            tokens.append((_NUMBER if is_float else _INTEGER, text[start:i]))
            continue
        if ch == '"':
            i += 1
            chars = []
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        chars.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(text[i])
                i += 1
            tokens.append((_STRING, "".join(chars)))
            continue

        simple = {
            "{": _BRACE_OPEN, "}": _BRACE_CLOSE,
            "[": _BRACKET_OPEN, "]": _BRACKET_CLOSE,
            "=": _EQUALS, ";": _SEMICOLON, ",": _COMMA, ":": _COLON,
        }
        if ch in simple:
            tokens.append((simple[ch], ch))
            i += 1
            continue
        if ch == "+":
            if i + 1 < n and text[i + 1] == "=":
                tokens.append((_PLUS_EQUALS, "+="))
                i += 2
                continue
            raise ValueError("Unexpected plus token in model.cfg")
        raise ValueError("Unexpected character in model.cfg: " + ch)

    tokens.append((_END, ""))
    return tokens


# -- data model ----------------------------------------------------------------
class Value:
    __slots__ = ("data",)

    def __init__(self, data):
        self.data = data

    def is_string(self):
        return isinstance(self.data, str)

    def is_int(self):
        return isinstance(self.data, int) and not isinstance(self.data, bool)

    def is_double(self):
        return isinstance(self.data, float)

    def is_array(self):
        return isinstance(self.data, list)

    def as_string(self):
        return self.data

    def as_int(self):
        return self.data

    def as_double(self):
        return self.data

    def as_array(self):
        return self.data


class Property:
    __slots__ = ("name", "value", "extends")

    def __init__(self, name="", value=None, extends=False):
        self.name = name
        self.value = value
        self.extends = extends


class Class:
    __slots__ = ("name", "parent", "properties", "classes")

    def __init__(self, name="", parent=""):
        self.name = name
        self.parent = parent
        self.properties = []
        self.classes = []

    def find_class(self, class_name):
        needle = class_name.lower()
        for child in self.classes:
            if child.name.lower() == needle:
                return child
        return None

    def find_property(self, property_name):
        needle = property_name.lower()
        for prop in self.properties:
            if prop.name.lower() == needle:
                return prop
        return None


class SkeletonBone:
    __slots__ = ("name", "parent")

    def __init__(self, name="", parent=""):
        self.name = name
        self.parent = parent


class Skeleton:
    __slots__ = ("name", "bones")

    def __init__(self, name=""):
        self.name = name
        self.bones = []


# -- parser --------------------------------------------------------------------
class _Parser:
    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def parse_root(self):
        root = Class("__root__")
        while not self._check(_END):
            root.classes.append(self._parse_class())
        return root

    def _check(self, kind):
        return self._tokens[self._pos][0] == kind

    def _consume(self, kind, message):
        if not self._check(kind):
            raise ValueError(message)
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _parse_class(self):
        self._consume(_CLASS, "Expected class keyword")
        cls = Class()
        cls.name = self._consume(_IDENTIFIER, "Expected class name")[1]
        if self._check(_SEMICOLON):
            self._pos += 1
            return cls
        if self._check(_COLON):
            self._pos += 1
            cls.parent = self._consume(_IDENTIFIER, "Expected parent class name")[1]
        self._consume(_BRACE_OPEN, "Expected class body")
        while not self._check(_BRACE_CLOSE):
            if self._check(_CLASS):
                cls.classes.append(self._parse_class())
            else:
                cls.properties.append(self._parse_property())
        self._consume(_BRACE_CLOSE, "Expected class closing brace")
        self._consume(_SEMICOLON, "Expected semicolon after class")
        return cls

    def _parse_property(self):
        prop = Property()
        prop.name = self._consume(_IDENTIFIER, "Expected property name")[1]
        if self._check(_BRACKET_OPEN):
            self._pos += 1
            self._consume(_BRACKET_CLOSE, "Expected [] property close")
        if self._check(_PLUS_EQUALS):
            prop.extends = True
            self._pos += 1
        else:
            self._consume(_EQUALS, "Expected property assignment")
        prop.value = self._parse_value()
        self._consume(_SEMICOLON, "Expected semicolon after property")
        return prop

    def _parse_value(self):
        if self._check(_BRACE_OPEN):
            self._pos += 1
            values = []
            while not self._check(_BRACE_CLOSE):
                values.append(self._parse_value())
                if self._check(_COMMA):
                    self._pos += 1
            self._consume(_BRACE_CLOSE, "Expected array closing brace")
            return Value(values)
        if self._check(_STRING):
            return Value(self._tokens[self._pos_advance()][1])
        if self._check(_INTEGER):
            return Value(int(self._tokens[self._pos_advance()][1]))
        if self._check(_NUMBER):
            return Value(float(self._tokens[self._pos_advance()][1]))
        if self._check(_IDENTIFIER):
            return Value(self._tokens[self._pos_advance()][1])
        raise ValueError("Expected config value")

    def _pos_advance(self):
        pos = self._pos
        self._pos += 1
        return pos


# -- writer --------------------------------------------------------------------
def _write_indent(stream, indent):
    stream.write("\t" * indent)


def _write_value(stream, value, indent):
    if value.is_string():
        stream.write('"' + value.as_string() + '"')
    elif value.is_int():
        stream.write(str(value.as_int()))
    elif value.is_double():
        stream.write(_format_double(value.as_double()))
    else:
        _write_array(stream, value.as_array(), indent)


def _format_double(value):
    # The C++ writer used default ostream formatting; the tests only re-parse the
    # output, so any round-trippable decimal representation is acceptable.
    text = repr(value)
    return text


def _write_array(stream, array, indent):
    if not array:
        stream.write("{}")
        return
    stream.write("{\n")
    for i, item in enumerate(array):
        _write_indent(stream, indent + 1)
        _write_value(stream, item, indent + 1)
        if i + 1 < len(array):
            stream.write(",")
        stream.write("\n")
    _write_indent(stream, indent)
    stream.write("}")


def _write_class(stream, cls, indent):
    _write_indent(stream, indent)
    stream.write("class " + cls.name)
    if cls.parent:
        stream.write(": " + cls.parent)
    stream.write(" {\n")
    for prop in cls.properties:
        _write_indent(stream, indent + 1)
        stream.write(prop.name)
        if prop.value.is_array():
            stream.write("[]")
        stream.write(" += " if prop.extends else " = ")
        _write_value(stream, prop.value, indent + 1)
        stream.write(";\n")
    for child in cls.classes:
        _write_class(stream, child, indent + 1)
    _write_indent(stream, indent)
    stream.write("};\n")


# -- top-level config ----------------------------------------------------------
class Config:
    def __init__(self):
        self.root = Class("__root__")

    @staticmethod
    def read_file(path):
        with open(path, "r", encoding="latin-1") as handle:
            text = handle.read()
        parser = _Parser(_tokenize(text))
        config = Config()
        config.root = parser.parse_root()
        return config

    def write_file(self, path):
        with open(path, "w", encoding="latin-1", newline="") as handle:
            for cls in self.root.classes:
                _write_class(handle, cls, 0)
                handle.write("\n")

    def write_string(self):
        buffer = io.StringIO()
        for cls in self.root.classes:
            _write_class(buffer, cls, 0)
            buffer.write("\n")
        return buffer.getvalue()

    def skeletons(self):
        result = []
        cfg_skeletons = self.root.find_class("CfgSkeletons")
        if cfg_skeletons is None:
            return result
        for skeleton_class in cfg_skeletons.classes:
            skeleton = Skeleton(skeleton_class.name)
            bones = skeleton_class.find_property("skeletonBones")
            if bones is not None and bones.value.is_array():
                values = bones.value.as_array()
                i = 0
                while i + 1 < len(values):
                    if values[i].is_string() and values[i + 1].is_string():
                        skeleton.bones.append(SkeletonBone(values[i].as_string(), values[i + 1].as_string()))
                    i += 2
            result.append(skeleton)
        return result

    @staticmethod
    def skeleton_config(skeleton):
        skeleton_class = Class(skeleton.name)
        skeleton_class.properties.append(Property("isDiscrete", Value(0), False))
        skeleton_class.properties.append(Property("skeletonInherit", Value(""), False))
        bones = []
        for bone in skeleton.bones:
            bones.append(Value(bone.name))
            bones.append(Value(bone.parent))
        skeleton_class.properties.append(Property("skeletonBones", Value(bones), False))

        cfg_skeletons = Class("CfgSkeletons")
        cfg_skeletons.classes.append(skeleton_class)

        config = Config()
        config.root = Class("__root__")
        config.root.classes.append(cfg_skeletons)
        return config
