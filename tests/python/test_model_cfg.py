"""Pure-Python model.cfg test (no Maya).

Parses the fixture skeleton (expects one skeleton with 18 bones), builds an 11-bone
skeleton config, writes it, re-reads it, and asserts the exported skeleton
round-trips to 11 bones.

Run:  python tests/python/test_model_cfg.py [input-model.cfg] [output-model.cfg]
"""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from a3ob.formats.model_cfg import Config, Skeleton, SkeletonBone  # noqa: E402

DEFAULT_INPUT = os.path.join(_REPO, "Arma3ObjectBuilder-master", "tests", "inputs", "model.cfg")


def main(argv):
    input_path = argv[1] if len(argv) > 1 else DEFAULT_INPUT
    output_path = argv[2] if len(argv) > 2 else os.path.join(tempfile.mkdtemp(prefix="model-cfg-"), "model.cfg")

    if not os.path.isfile(input_path):
        print("Input model.cfg not found: %s" % input_path, file=sys.stderr)
        return 2

    config = Config.read_file(input_path)
    skeletons = config.skeletons()
    assert len(skeletons) == 1, "Expected one skeleton, got %d" % len(skeletons)
    assert len(skeletons[0].bones) == 18, "Expected 18 skeleton bones, got %d" % len(skeletons[0].bones)

    skeleton = Skeleton("Skeleton")
    skeleton.bones.append(SkeletonBone("bone_0", ""))
    for i in range(10):
        skeleton.bones.append(SkeletonBone("bone_%d" % (i + 1), "bone_0"))

    output = Config.skeleton_config(skeleton)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output.write_file(output_path)

    reread = Config.read_file(output_path)
    exported = reread.skeletons()
    assert len(exported) == 1, "Expected one exported skeleton, got %d" % len(exported)
    assert len(exported[0].bones) == 11, "Expected 11 exported bones, got %d" % len(exported[0].bones)

    print("OK model.cfg skeletons=%d bones=%d" % (len(skeletons), len(skeletons[0].bones)))
    print("PASS model_cfg")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
