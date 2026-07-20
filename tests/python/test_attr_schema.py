"""Lock the on-scene ``a3ob*`` attribute schema.

The long+short names in ``attributes.py`` are a data contract: they are what is
written into users' ``.ma`` scenes and what import/export/commands/UI read back.
Renaming one does not fail any test — it silently stops resolving old scenes. So
this test pins every pair against a golden list; changing the schema has to be a
deliberate edit here too.

Read via ``ast`` rather than ``import``: ``attributes.py`` imports
``maya.api.OpenMaya`` at module level, and this suite has to run under a plain
system Python with no Maya at all.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTRIBUTES = ROOT / "scripts" / "a3ob" / "mayabridge" / "attributes.py"

# 2026-07-20: BAKED_WEIGHTS and BAKED_WEIGHTS_PREVIOUS were removed deliberately, taking
# this list from 35 pairs to 33. The skinCluster is now the only place weights live —
# docs/specs/2026-07-20-weights-live-skincluster-design.md. Verified first that no mesh
# held a bake without a live cluster, so no scene lost data.
# (constant, long name, short name) — exactly as class A declares them.
GOLDEN = [
    ("IS_LOD", "a3obIsLOD", "a3lod"),
    ("LOD_TYPE", "a3obLodType", "a3lt"),
    ("RESOLUTION", "a3obResolution", "a3res"),
    ("RESOLUTION_SIGNATURE", "a3obResolutionSignature", "a3sig"),
    ("SOURCE_VERTEX_COUNT", "a3obSourceVertexCount", "a3svc"),
    ("SOURCE_FACE_COUNT", "a3obSourceFaceCount", "a3sfc"),
    ("HAS_MASS", "a3obHasMass", "a3mass"),
    ("MASS_VALUES", "a3obMassValues", "a3mv"),
    ("PROPERTIES", "a3obProperties", "a3prop"),
    ("TEXTURES", "a3obTextures", "a3tex"),
    ("MATERIALS", "a3obMaterials", "a3mat"),
    ("SELECTIONS", "a3obSelections", "a3sel"),
    ("PROXIES", "a3obProxies", "a3prx"),
    ("HAS_SHARP_EDGES", "a3obHasSharpEdges", "a3sharp"),
    ("SHARP_EDGES", "a3obSharpEdges", "a3se"),
    ("UVSET_TAGG_COUNT", "a3obUVSetTaggCount", "a3uvtc"),
    ("UVSET_TAGGS", "a3obUVSetTaggs", "a3uvt"),
    ("SOURCE_VERTICES", "a3obSourceVertices", "a3sv"),
    ("VERTEX_SOURCE_INDICES", "a3obVertexSourceIndices", "a3vsi"),
    ("IS_PROXY", "a3obIsProxy", "a3px"),
    ("PROXY_PATH", "a3obProxyPath", "a3pp"),
    ("PROXY_INDEX", "a3obProxyIndex", "a3pi"),
    ("PROXY_SELECTION", "a3obProxySelection", "a3ps"),
    ("SELECTION_NAME", "a3obSelectionName", "a3sn"),
    ("FLAG_COMPONENT", "a3obFlagComponent", "a3fc"),
    ("FLAG_VALUE", "a3obFlagValue", "a3fv"),
    ("IS_PROXY_SELECTION", "a3obIsProxySelection", "a3ips"),
    ("TECHNICAL_SET", "a3obTechnicalSet", "a3ts"),
    ("TEXTURE", "a3obTexture", "a3tx"),
    ("MATERIAL", "a3obMaterial", "a3mt"),
    ("SG_TEXTURE", "a3obTexture", "a3sgtx"),
    ("SG_MATERIAL", "a3obMaterial", "a3sgmt"),
    ("SKELETON_NAME", "a3obSkeletonName", "a3sk"),
]


def declared_schema():
    tree = ast.parse(ATTRIBUTES.read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.ClassDef) and n.name == "A")
    schema = []
    for statement in node.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not isinstance(statement.value, ast.Tuple):
            continue
        names = [element.value for element in statement.value.elts]
        schema.append((statement.targets[0].id, names[0], names[1]))
    return schema


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_schema_is_unchanged():
    actual = declared_schema()
    check(actual == GOLDEN,
          "the a3ob* attribute schema changed.\n"
          "  removed: %s\n  added:   %s\n"
          "If this was deliberate, update GOLDEN here in the same commit — and note "
          "that renaming an attribute orphans the data in every existing .ma scene."
          % (sorted(set(GOLDEN) - set(actual)), sorted(set(actual) - set(GOLDEN))))
    print("OK a3ob schema: %d attributes unchanged" % len(actual))


def test_short_names_stay_within_mayas_limit():
    # Maya truncates over-long short names, which silently collides two attributes.
    too_long = [(c, s) for c, _, s in declared_schema() if len(s) > 8]
    check(not too_long, "short names over 8 chars risk truncation: %s" % too_long)
    print("OK a3ob schema: every short name fits")


def test_short_names_are_unique():
    schema = declared_schema()
    shorts = [s for _, _, s in schema]
    duplicates = sorted({s for s in shorts if shorts.count(s) > 1})
    check(not duplicates, "duplicate short names would alias attributes: %s" % duplicates)
    # Long names may legitimately repeat: TEXTURE/SG_TEXTURE and MATERIAL/SG_MATERIAL
    # deliberately share a long name across the shader and its shading group, and are
    # told apart by the short name alone. That is exactly why the shorts must be unique.
    print("OK a3ob schema: %d short names, all distinct" % len(shorts))


def main():
    test_schema_is_unchanged()
    test_short_names_stay_within_mayas_limit()
    test_short_names_are_unique()
    return 0


if __name__ == "__main__":
    sys.exit(main())
