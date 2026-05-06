#include "ModelCfgCommands.h"

#include "formats/ModelCfg.h"

#include <maya/MArgDatabase.h>
#include <maya/MDagPath.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MFnIkJoint.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnStringData.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MGlobal.h>
#include <maya/MItDag.h>
#include <maya/MPlug.h>
#include <maya/MSelectionList.h>
#include <maya/MString.h>

#include <filesystem>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
MStatus setStringAttribute(MObject node, const char* longName, const char* shortName, const MString& value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return status;
    MPlug plug = dep.findPlug(longName, true, &status);
    if (!status) {
        MFnStringData data;
        MObject defaultValue = data.create(value, &status);
        if (!status) return status;
        MFnTypedAttribute attr;
        MObject attrObj = attr.create(longName, shortName, MFnData::kString, defaultValue, &status);
        if (!status) return status;
        attr.setKeyable(true);
        status = dep.addAttribute(attrObj);
        if (!status) return status;
        plug = dep.findPlug(longName, true, &status);
        if (!status) return status;
    }
    return plug.setValue(value);
}

std::string stringPlugValue(const MObject& node, const char* name)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return {};
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) return {};
    MString value;
    plug.getValue(value);
    return value.asChar();
}

MString pathArg(const MSyntax& syntax, const MArgList& args)
{
    MArgDatabase argData(syntax, args);
    MString path;
    if (argData.isFlagSet("-path")) {
        argData.getFlagArgument("-path", 0, path);
    } else if (argData.isFlagSet("-p")) {
        argData.getFlagArgument("-p", 0, path);
    }
    return path;
}

MObject selectedJointOrNull()
{
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MDagPath path;
        MObject component;
        if (selection.getDagPath(i, path, component) && path.node().hasFn(MFn::kJoint)) return path.node();
    }
    return MObject::kNullObj;
}

MObject firstSkeletonRoot()
{
    MStatus status;
    MItDag it(MItDag::kDepthFirst, MFn::kJoint, &status);
    if (!status) return MObject::kNullObj;
    for (; !it.isDone(); it.next()) {
        MObject joint = it.currentItem(&status);
        if (status && !stringPlugValue(joint, "a3obSkeletonName").empty()) return joint;
    }
    return MObject::kNullObj;
}

void collectBones(MObject joint, const std::string& parent, a3ob::cfg::Skeleton& skeleton)
{
    MStatus status;
    MFnDependencyNode dep(joint, &status);
    if (!status) return;
    skeleton.bones.push_back({dep.name().asChar(), parent});

    MFnDagNode dag(joint, &status);
    if (!status) return;
    for (unsigned int i = 0; i < dag.childCount(); ++i) {
        MObject child = dag.child(i, &status);
        if (status && child.hasFn(MFn::kJoint)) collectBones(child, dep.name().asChar(), skeleton);
    }
}
}

void* ImportModelCfgCommand::creator()
{
    return new ImportModelCfgCommand();
}

MSyntax ImportModelCfgCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-p", "-path", MSyntax::kString);
    syntax.addFlag("-s", "-skeletonName", MSyntax::kString);
    return syntax;
}

MStatus ImportModelCfgCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MString path = pathArg(syntax(), args);
    if (path.length() == 0) {
        MGlobal::displayError("a3obImportModelCfg: -path is required");
        return MS::kFailure;
    }

    MString requestedName;
    if (argData.isFlagSet("-skeletonName")) {
        argData.getFlagArgument("-skeletonName", 0, requestedName);
    } else if (argData.isFlagSet("-s")) {
        argData.getFlagArgument("-s", 0, requestedName);
    }

    try {
        const a3ob::cfg::Config config = a3ob::cfg::Config::readFile(std::filesystem::path(path.asChar()));
        const std::vector<a3ob::cfg::Skeleton> skeletons = config.skeletons();
        const a3ob::cfg::Skeleton* skeleton = nullptr;
        for (const a3ob::cfg::Skeleton& candidate : skeletons) {
            if (requestedName.length() == 0 || candidate.name == requestedName.asChar()) {
                skeleton = &candidate;
                break;
            }
        }
        if (!skeleton) {
            MGlobal::displayError("a3obImportModelCfg: skeleton not found");
            return MS::kFailure;
        }

        MStatus status;
        std::map<std::string, MObject> joints;
        for (const a3ob::cfg::SkeletonBone& bone : skeleton->bones) {
            MObject parent = MObject::kNullObj;
            const auto parentIt = joints.find(bone.parent);
            if (parentIt != joints.end()) parent = parentIt->second;
            MFnIkJoint jointFn;
            MObject joint = jointFn.create(parent, &status);
            if (!status) return status;
            jointFn.setName(bone.name.c_str(), false, &status);
            if (!status) return status;
            joints[bone.name] = joint;
            if (bone.parent.empty()) {
                status = setStringAttribute(joint, "a3obSkeletonName", "a3sk", skeleton->name.c_str());
                if (!status) return status;
            }
        }

        MGlobal::displayInfo(MString("a3obImportModelCfg: imported skeleton ") + skeleton->name.c_str() + " bones=" + static_cast<int>(skeleton->bones.size()));
        return MS::kSuccess;
    } catch (const std::exception& error) {
        MGlobal::displayError(MString("a3obImportModelCfg: ") + error.what());
        return MS::kFailure;
    }
}

void* ExportModelCfgCommand::creator()
{
    return new ExportModelCfgCommand();
}

MSyntax ExportModelCfgCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-p", "-path", MSyntax::kString);
    syntax.addFlag("-s", "-skeletonName", MSyntax::kString);
    return syntax;
}

MStatus ExportModelCfgCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MString path = pathArg(syntax(), args);
    if (path.length() == 0) {
        MGlobal::displayError("a3obExportModelCfg: -path is required");
        return MS::kFailure;
    }

    MObject root = selectedJointOrNull();
    if (root.isNull()) root = firstSkeletonRoot();
    if (root.isNull()) {
        MGlobal::displayError("a3obExportModelCfg: select a skeleton root joint");
        return MS::kFailure;
    }

    a3ob::cfg::Skeleton skeleton;
    skeleton.name = stringPlugValue(root, "a3obSkeletonName");
    if (argData.isFlagSet("-skeletonName")) {
        MString name;
        argData.getFlagArgument("-skeletonName", 0, name);
        skeleton.name = name.asChar();
    } else if (argData.isFlagSet("-s")) {
        MString name;
        argData.getFlagArgument("-s", 0, name);
        skeleton.name = name.asChar();
    }
    if (skeleton.name.empty()) skeleton.name = "MayaSkeleton";

    try {
        collectBones(root, "", skeleton);
        a3ob::cfg::Config::skeletonConfig(skeleton).writeFile(std::filesystem::path(path.asChar()));
        MGlobal::displayInfo(MString("a3obExportModelCfg: exported skeleton ") + skeleton.name.c_str() + " bones=" + static_cast<int>(skeleton.bones.size()));
        return MS::kSuccess;
    } catch (const std::exception& error) {
        MGlobal::displayError(MString("a3obExportModelCfg: ") + error.what());
        return MS::kFailure;
    }
}
