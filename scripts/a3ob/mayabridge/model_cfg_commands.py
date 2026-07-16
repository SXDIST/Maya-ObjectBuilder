"""``a3obImportModelCfg`` / ``a3obExportModelCfg`` skeleton commands (OpenMaya 2.0).

Port of ``src/commands/ModelCfgCommands.cpp``. Import builds a Maya joint hierarchy
from a ``CfgSkeletons`` skeleton; export walks a joint hierarchy back into a skeleton
config. The skeleton-root joint carries the ``a3obSkeletonName`` attribute.
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

from . import attributes as attr
from .attributes import A
from ..formats.model_cfg import Config, Skeleton, SkeletonBone

NULL = om.MObject.kNullObj


def _selected_joint_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for i in range(sel.length()):
        try:
            dag_path = sel.getDagPath(i)
        except Exception:
            continue
        if dag_path.node().hasFn(om.MFn.kJoint):
            return dag_path.node()
    return NULL


def _first_skeleton_root():
    it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
    while not it.isDone():
        joint = it.currentItem()
        if attr.get_string(joint, A.SKELETON_NAME):
            return joint
        it.next()
    return NULL


def _collect_bones(joint, parent, skeleton):
    dep = om.MFnDependencyNode(joint)
    name = dep.name()
    skeleton.bones.append(SkeletonBone(name, parent))
    dag = om.MFnDagNode(joint)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kJoint):
            _collect_bones(child, name, skeleton)


class _Base(om.MPxCommand):
    def isUndoable(self):
        return False


class ImportModelCfgCommand(_Base):
    kName = "a3obImportModelCfg"

    @staticmethod
    def creator():
        return ImportModelCfgCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-p", "-path", om.MSyntax.kString)
        s.addFlag("-s", "-skeletonName", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        path = argdb.flagArgumentString("-p", 0) if argdb.isFlagSet("-p") else ""
        if not path:
            om.MGlobal.displayError("a3obImportModelCfg: -path is required")
            return
        requested_name = argdb.flagArgumentString("-s", 0) if argdb.isFlagSet("-s") else ""

        try:
            config = Config.read_file(path)
            skeletons = config.skeletons()
            skeleton = None
            for candidate in skeletons:
                if not requested_name or candidate.name == requested_name:
                    skeleton = candidate
                    break
            if skeleton is None:
                om.MGlobal.displayError("a3obImportModelCfg: skeleton not found")
                return

            joints = {}
            for bone in skeleton.bones:
                parent = joints.get(bone.parent, NULL)
                joint_fn = oma.MFnIkJoint()
                joint = joint_fn.create(parent) if not parent.isNull() else joint_fn.create()
                joint_fn.setName(bone.name)
                joints[bone.name] = joint
                if not bone.parent:
                    attr.set_string(joint, A.SKELETON_NAME, skeleton.name)

            om.MGlobal.displayInfo("a3obImportModelCfg: imported skeleton %s bones=%d" % (skeleton.name, len(skeleton.bones)))
        except Exception as error:  # noqa: BLE001 - mirror C++ catch-all
            om.MGlobal.displayError("a3obImportModelCfg: %s" % error)


class ExportModelCfgCommand(_Base):
    kName = "a3obExportModelCfg"

    @staticmethod
    def creator():
        return ExportModelCfgCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-p", "-path", om.MSyntax.kString)
        s.addFlag("-s", "-skeletonName", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        path = argdb.flagArgumentString("-p", 0) if argdb.isFlagSet("-p") else ""
        if not path:
            om.MGlobal.displayError("a3obExportModelCfg: -path is required")
            return

        root = _selected_joint_or_null()
        if root.isNull():
            root = _first_skeleton_root()
        if root.isNull():
            om.MGlobal.displayError("a3obExportModelCfg: select a skeleton root joint")
            return

        skeleton = Skeleton(attr.get_string(root, A.SKELETON_NAME))
        if argdb.isFlagSet("-s"):
            skeleton.name = argdb.flagArgumentString("-s", 0)
        if not skeleton.name:
            skeleton.name = "MayaSkeleton"

        try:
            _collect_bones(root, "", skeleton)
            Config.skeleton_config(skeleton).write_file(path)
            om.MGlobal.displayInfo("a3obExportModelCfg: exported skeleton %s bones=%d" % (skeleton.name, len(skeleton.bones)))
        except Exception as error:  # noqa: BLE001 - mirror C++ catch-all
            om.MGlobal.displayError("a3obExportModelCfg: %s" % error)


COMMANDS = [ImportModelCfgCommand, ExportModelCfgCommand]
