"""The Auto LOD option keys parse with the documented defaults.

The option box hands the translator a "key=value;key=value" string. These keys are new;
their defaults decide what a user who never opens the option box gets, and the answer
has to be "exactly what happened before".
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEL = ROOT / "scripts" / "mayaObjectBuilderP3DOptions.mel"

EXPORT_AUTOLOD_KEYS = [
    "autoLod", "autoLodOutput", "autoLodReduction", "autoLodFirst",
    "autoLodResolution", "autoLodGeometry", "autoLodMemory", "autoLodFire",
    "autoLodView", "autoLodGeometryType", "autoLodFireQuality",
]

IMPORT_OPTION_KEYS = [
    "importTextures",
]

# All export and import option keys that must be wired in both Set/Get procedures
OPTION_KEYS = EXPORT_AUTOLOD_KEYS + IMPORT_OPTION_KEYS

SET_PROC = "mayaObjectBuilderP3DSetOptions"
GET_PROC = "mayaObjectBuilderP3DGetOptions"


def _strip_comments(text):
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


def _extract_proc_body(text, proc_name):
    """Pull just one MEL proc's `{ ... }` body out of the file (brace-matched),
    so a key mentioned in a comment or in another proc cannot satisfy the check.
    """
    header = re.search(
        r"global\s+proc\s+(?:\w+\s+)?%s\s*\([^)]*\)\s*\{" % re.escape(proc_name),
        text,
    )
    assert header, "proc %s not found in %s" % (proc_name, MEL)
    start = header.end() - 1  # index of the opening '{'
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("unbalanced braces while scanning proc %s" % proc_name)


def test_every_autolod_key_is_wired_both_ways():
    """Each export autoLod* key and import option key must round-trip: SetOptions applies it
    to a control on open, and GetOptions reads it back out on close. A key wired only one way
    silently loses the user's choice the next time the dialog reopens.
    """
    text = MEL.read_text(encoding="utf-8", errors="ignore")
    set_body = _strip_comments(_extract_proc_body(text, SET_PROC))
    get_body = _strip_comments(_extract_proc_body(text, GET_PROC))

    missing_set = [key for key in OPTION_KEYS if '"%s"' % key not in set_body]
    missing_get = [key for key in OPTION_KEYS if '"%s"' % key not in get_body]

    assert not missing_set, "%s never applies: %r" % (SET_PROC, missing_set)
    assert not missing_get, "%s never emits: %r" % (GET_PROC, missing_get)


def test_autolod_is_off_by_default():
    text = MEL.read_text(encoding="utf-8", errors="ignore")
    line = [ln for ln in text.splitlines() if '"autoLod"' in ln and "Default" in ln]
    assert line, "autoLod has no default-bearing emit line"
    assert '"0"' in line[0], (
        "autoLod must default to 0 — a default export must not silently generate LODs: %r"
        % (line[0],))
