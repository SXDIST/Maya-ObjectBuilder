"""Pure-Python P3D round-trip test (no Maya).

Mirrors ``tests/cpp/p3d_roundtrip.cpp``: reads each fixture, writes it back out,
re-reads it, and asserts structural stability (LOD / vertex / normal / face / TAGG
counts, TAGG summary, and decoded LOD type + resolution).

Run:  python tests/python/test_p3d_roundtrip.py [fixtures-dir] [output-dir]
"""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from a3ob.formats.p3d import MLOD  # noqa: E402

DEFAULT_FIXTURES = os.path.join(_REPO, "Arma3ObjectBuilder-master", "tests", "inputs", "p3d")


def tagg_summary(lod):
    summary = {}
    for tagg in lod.taggs:
        if tagg.data is None:
            continue
        kind = tagg.data.kind
        if kind == "Property":
            summary["#Property#"] = summary.get("#Property#", 0) + 1
        elif kind == "Mass":
            summary["#Mass#"] = summary.get("#Mass#", 0) + 1
        elif kind == "SharpEdges":
            summary["#SharpEdges#"] = summary.get("#SharpEdges#", 0) + 1
        elif kind == "UVSet":
            summary["#UVSet#"] = summary.get("#UVSet#", 0) + 1
        elif kind == "Selection":
            summary[tagg.name] = summary.get(tagg.name, 0) + 1
    return summary


def check_file(input_path, output_dir):
    first = MLOD.read_file(input_path)
    assert first.lods, "%s has no LODs" % input_path

    stem = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, stem + "_roundtrip.p3d")
    first.write_file(output_path)

    second = MLOD.read_file(output_path)
    assert len(first.lods) == len(second.lods), "%s LOD count changed" % input_path

    for a, b in zip(first.lods, second.lods):
        assert len(a.vertices) == len(b.vertices), "%s vertex count changed" % input_path
        assert len(a.normals) == len(b.normals), "%s normal count changed" % input_path
        assert len(a.faces) == len(b.faces), "%s face count changed" % input_path
        assert len(a.taggs) == len(b.taggs), "%s TAGG count changed" % input_path
        assert tagg_summary(a) == tagg_summary(b), "%s TAGG summary changed" % input_path
        assert a.resolution.lod == b.resolution.lod, "%s LOD type changed" % input_path
        assert a.resolution.resolution == b.resolution.resolution, "%s LOD resolution changed" % input_path

    print("OK %s lods=%d" % (os.path.basename(input_path), len(first.lods)))


def main(argv):
    fixtures = argv[1] if len(argv) > 1 else DEFAULT_FIXTURES
    output_dir = argv[2] if len(argv) > 2 else tempfile.mkdtemp(prefix="p3d-roundtrip-")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isdir(fixtures):
        print("Fixtures directory not found: %s" % fixtures, file=sys.stderr)
        return 2

    count = 0
    for entry in sorted(os.listdir(fixtures)):
        if entry.lower().endswith(".p3d"):
            check_file(os.path.join(fixtures, entry), output_dir)
            count += 1

    assert count > 0, "No .p3d fixtures found"
    print("PASS p3d_roundtrip (%d fixtures)" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
