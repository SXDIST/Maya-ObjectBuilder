"""The Auto LOD option keys parse with the documented defaults.

The option box hands the translator a "key=value;key=value" string. These keys are new;
their defaults decide what a user who never opens the option box gets, and the answer
has to be "exactly what happened before".
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEL = ROOT / "scripts" / "mayaObjectBuilderP3DOptions.mel"

AUTOLOD_KEYS = [
    "autoLod", "autoLodOutput", "autoLodReduction", "autoLodFirst",
    "autoLodResolution", "autoLodGeometry", "autoLodMemory", "autoLodFire",
    "autoLodView", "autoLodGeometryType", "autoLodFireQuality",
]


def test_every_autolod_key_is_emitted():
    text = MEL.read_text(encoding="utf-8", errors="ignore")
    missing = [key for key in AUTOLOD_KEYS if '"%s"' % key not in text]
    assert not missing, "option string never emits: %r" % (missing,)


def test_autolod_is_off_by_default():
    text = MEL.read_text(encoding="utf-8", errors="ignore")
    line = [ln for ln in text.splitlines() if '"autoLod"' in ln and "Default" in ln]
    assert line, "autoLod has no default-bearing emit line"
    assert '"0"' in line[0], (
        "autoLod must default to 0 — a default export must not silently generate LODs: %r"
        % (line[0],))
