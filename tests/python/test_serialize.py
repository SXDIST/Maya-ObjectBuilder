"""Guard the shared ``a3ob*`` attribute serialization primitives (no Maya).

``split_semicolon`` used to exist three times — in the command helpers, in the export
parser (where a comment calls it the inverse of the import-side serialization), and inline
inside ``vertex_source_index_map``. All three now come from ``a3ob.formats.serialize``.
Because the export copy sits on the P3D byte path, this pins the exact behaviour the merge
had to preserve, in particular the dropping of empty fields.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from a3ob.formats.serialize import split_semicolon  # noqa: E402


def _reference(value):
    """The implementation as it stood in all three call sites before the merge."""
    return [part for part in value.split(";") if part]


CASES = [
    "",
    ";",
    ";;;",
    "a",
    "a;",
    "a;b",
    "a;b;",
    ";a;b",
    "a;;b",
    "0;1;2;3;",
    "1.5;-2.0;3;",
    " ; a ; b ; ",
    "key=value;other=thing;",
    "a,b,c;d,e,f;",
]


def test_matches_the_pre_merge_behaviour():
    for case in CASES:
        got = split_semicolon(case)
        want = _reference(case)
        assert got == want, f"{case!r}: {got!r} != {want!r}"


def test_empty_fields_are_dropped_not_yielded():
    # The serializers append a trailing separator, so every stored attribute ends in ";".
    # A naive split would hand back a phantom final field and shift every consumer that
    # indexes the result (mass values, the vertex remap).
    assert split_semicolon("0;1;2;") == ["0", "1", "2"]
    assert split_semicolon(";;") == []
    assert split_semicolon("") == []


def test_whitespace_is_preserved():
    # Callers that want trimming do it themselves (vertex_source_index_map); the split must
    # not silently trim, or a value with meaningful spaces would change on round-trip.
    assert split_semicolon(" a ; b ") == [" a ", " b "]


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("serialize primitives OK")


if __name__ == "__main__":
    main()
