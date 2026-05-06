from pathlib import Path

import maya.cmds as cmds
import maya.standalone


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "build" / "Debug" / "MayaObjectBuilder.mll"
INPUT = ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "model.cfg"
OUTPUT = ROOT / "build" / "model-cfg-workflow.cfg"


def main():
    maya.standalone.initialize(name="python")
    cmds.loadPlugin(str(PLUGIN), quiet=True)
    commands = set(cmds.pluginInfo("MayaObjectBuilder", query=True, command=True) or [])
    expected = {"a3obImportModelCfg", "a3obExportModelCfg"}
    missing = expected - commands
    if missing:
        raise RuntimeError(f"Missing commands: {sorted(missing)}")

    cmds.file(new=True, force=True)
    cmds.a3obImportModelCfg(path=str(INPUT))
    joints = cmds.ls(type="joint") or []
    if len(joints) != 18:
        raise RuntimeError(f"Expected 18 joints, got {len(joints)}")
    roots = [joint for joint in joints if cmds.attributeQuery("a3obSkeletonName", node=joint, exists=True)]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one skeleton root, got {roots}")
    cmds.select(roots[0])
    cmds.a3obExportModelCfg(path=str(OUTPUT))
    if not OUTPUT.exists():
        raise RuntimeError("model.cfg export was not created")
    print(f"OK model.cfg joints={len(joints)} root={roots[0]}")

    maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
