"""Byte-contract gate for P3D export.

``capture`` imports each fixture, saves the scene as ``.ma``, exports it back to
``.p3d`` and records the SHA256 plus every ``a3ob*`` attribute in the scene.
``verify`` re-opens those saved ``.ma`` scenes and exports them again, comparing
the hashes against the recorded ones.

Verify deliberately opens the SAVED SCENE rather than re-importing the fixture:
exporting a fresh import would mix import nondeterminism into a test that exists
to prove the exporter writes identical bytes.

    mayapy tests/golden.py capture
    mayapy tests/golden.py verify
"""

import hashlib
import json
import sys
from pathlib import Path

import maya.standalone

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402 - Maya must be initialized before cmds imports


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [
    ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_2_crate.p3d",
    ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_1_character.p3d",
]
GOLDEN = ROOT / "build" / "golden"
MANIFEST = GOLDEN / "manifest.json"


def _load_plugin():
    plugin = str(ROOT / "plug-ins" / "MayaObjectBuilder.py")
    if not cmds.pluginInfo(plugin, query=True, loaded=True):
        cmds.loadPlugin(plugin)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _attribute_dump():
    """Every a3ob* attribute on every node, sorted — the schema half of the gate."""
    rows = []
    for node in cmds.ls() or []:
        for attribute in cmds.listAttr(node) or []:
            if not attribute.startswith("a3ob"):
                continue
            try:
                value = cmds.getAttr(f"{node}.{attribute}")
            except (RuntimeError, ValueError):
                continue
            rows.append(f"{node}.{attribute}={value!r}")
    return sorted(rows)


def _export_to(path):
    cmds.file(rename=str(path))
    cmds.file(exportAll=True, force=True, type="Arma P3D")


def capture():
    GOLDEN.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for fixture in FIXTURES:
        if not fixture.exists():
            print(f"SKIP {fixture.name} — fixture absent")
            continue
        scene = GOLDEN / (fixture.stem + ".ma")
        exported = GOLDEN / fixture.name

        cmds.file(new=True, force=True)
        _load_plugin()
        cmds.file(str(fixture), i=True, type="Arma P3D", ignoreVersion=True, ra=True,
                  mergeNamespacesOnClash=False, namespace="golden")
        cmds.file(rename=str(scene))
        cmds.file(save=True, force=True, type="mayaAscii")
        # Reopen before exporting so capture and verify walk the identical path.
        # Measured: exporting a freshly imported scene and exporting that same scene
        # saved-and-reopened give the SAME BYTE COUNT but different bytes (6145116 both
        # ways) — a .ma round-trip reorders the DG, and TAGG order follows DG order.
        # Export is deterministic per scene state; it is not deterministic across
        # provenance, so the baseline has to be taken from the state verify will use.
        cmds.file(str(scene), open=True, force=True)

        _export_to(exported)
        manifest[fixture.name] = {
            "scene": scene.name,
            "sha256": _sha256(exported),
            "bytes": exported.stat().st_size,
            "attributes": _attribute_dump(),
        }
        print(f"CAPTURED {fixture.name} {manifest[fixture.name]['sha256'][:16]} "
              f"({manifest[fixture.name]['bytes']} bytes, "
              f"{len(manifest[fixture.name]['attributes'])} a3ob attrs)")

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written: {MANIFEST}")
    return 0


def verify():
    if not MANIFEST.exists():
        print(f"FAIL no manifest at {MANIFEST} — run 'capture' first")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = 0
    for name, expected in sorted(manifest.items()):
        scene = GOLDEN / expected["scene"]
        if not scene.exists():
            print(f"FAIL {name} — saved scene {scene.name} is missing")
            failures += 1
            continue

        cmds.file(new=True, force=True)
        _load_plugin()
        cmds.file(str(scene), open=True, force=True)

        exported = GOLDEN / ("verify_" + name)
        _export_to(exported)
        actual = _sha256(exported)

        if actual != expected["sha256"]:
            size = exported.stat().st_size
            print(f"FAIL {name} — BYTES CHANGED\n"
                  f"     expected {expected['sha256']} ({expected['bytes']} bytes)\n"
                  f"     actual   {actual} ({size} bytes)")
            failures += 1
            continue

        attributes = _attribute_dump()
        if attributes != expected["attributes"]:
            missing = set(expected["attributes"]) - set(attributes)
            added = set(attributes) - set(expected["attributes"])
            print(f"FAIL {name} — a3ob schema drifted "
                  f"(-{len(missing)} +{len(added)})")
            for row in sorted(missing)[:5]:
                print(f"     missing {row}")
            for row in sorted(added)[:5]:
                print(f"     added   {row}")
            failures += 1
            continue

        print(f"OK {name} {actual[:16]} ({expected['bytes']} bytes)")

    print("\nGOLDEN VERIFY: " + ("PASS" if not failures else f"{failures} FAILED"))
    return 1 if failures else 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if mode not in ("capture", "verify"):
        print(f"usage: mayapy {Path(__file__).name} [capture|verify]")
        return 2
    return capture() if mode == "capture" else verify()


if __name__ == "__main__":
    sys.exit(main())
