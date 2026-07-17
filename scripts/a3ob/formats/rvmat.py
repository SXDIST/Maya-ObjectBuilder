"""Minimal .rvmat reader — Maya-independent.

An .rvmat is an Arma/DayZ material config: top-level ``specular[]`` / ``specularPower`` and
``class StageN { texture="..."; }`` blocks. Stage textures are either real ``.paa`` files
(colour ``_co``/``_ca``, normal ``_nohq``, spec ``_smdi``, …) or procedural placeholders
like ``#(argb,8,8,3)color(0.5,0.5,1,1,SMDI)`` (flat channel, no file). We extract the real
file textures, classified by suffix, plus the flat specular so materials can be wired
exactly instead of guessing sibling names.
"""

import os
import re

_TEXTURE_RE = re.compile(r'texture\s*=\s*"([^"]+)"', re.IGNORECASE)
_SPECULAR_RE = re.compile(r'specular\s*\[\s*\]\s*=\s*\{([^}]*)\}', re.IGNORECASE)
_SPECULAR_POWER_RE = re.compile(r'specularPower\s*=\s*([0-9.eE+-]+)', re.IGNORECASE)

# Longest/most specific suffixes first so _mca wins over _ca, _nohq stays distinct, etc.
_SUFFIX_ROLE = (
    ("_nohq", "normal"), ("_smdi", "spec"), ("_as", "ambient"),
    ("_mca", "macro"), ("_mc", "macro"), ("_dt", "detail"),
    ("_co", "color"), ("_ca", "color"),
)


def _classify(path):
    stem = os.path.splitext(os.path.basename(path.replace("\\", "/")))[0].lower()
    for suffix, role in _SUFFIX_ROLE:
        if stem.endswith(suffix):
            return role
    return "color"  # unsuffixed texture is treated as the colour


def parse_rvmat(text):
    """Return {"textures": {role: path}, "specular": [r,g,b] or None, "specular_power":
    float or None} from rvmat text. Only real .paa file stages are included."""
    textures = {}
    for match in _TEXTURE_RE.finditer(text):
        path = match.group(1)
        if not path.lower().endswith(".paa"):
            continue  # procedural placeholder, not a file
        textures.setdefault(_classify(path), path)

    specular = None
    spec_match = _SPECULAR_RE.search(text)
    if spec_match:
        try:
            values = [float(x) for x in spec_match.group(1).split(",") if x.strip()]
            if len(values) >= 3:
                specular = values[:3]
        except ValueError:
            specular = None

    specular_power = None
    power_match = _SPECULAR_POWER_RE.search(text)
    if power_match:
        try:
            specular_power = float(power_match.group(1))
        except ValueError:
            specular_power = None

    return {"textures": textures, "specular": specular, "specular_power": specular_power}


def parse_rvmat_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return parse_rvmat(handle.read())
