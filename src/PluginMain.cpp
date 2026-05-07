#include "commands/ModelCfgCommands.h"
#include "commands/StubCommands.h"
#include "translators/P3DTranslator.h"

#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>
#include <maya/MStatus.h>

#include <filesystem>
#include <string>

namespace
{
constexpr const char* kP3DOptionScript = "mayaObjectBuilderP3DOptions";
constexpr const char* kP3DDefaultOptions =
    "firstLodOnly=0;"
    "validateMeshes=0;"
    "enclose=1;"
    "groupBy=type;"
    "absolutePaths=1;"
    "additionalData=1;"
    "customNormals=1;"
    "flags=1;"
    "namedProperties=1;"
    "vertexMass=1;"
    "selections=1;"
    "uvSets=1;"
    "materials=1;"
    "sections=preserve;"
    "translateSelections=0;"
    "cleanupSelections=0;"
    "proxyAction=separate;"
    "relativePaths=1;"
    "selectedOnly=0;"
    "visibleOnly=1;"
    "exportValidateMeshes=0;"
    "applyModifiers=1;"
    "applyTransforms=1;"
    "sortSections=1;"
    "generateComponents=1;"
    "collisions=fail;"
    "validateLods=0;"
    "warningsAreErrors=1;"
    "renumberComponents=0;"
    "forceLowercase=1;"
    "exportTranslateSelections=0";

std::string normalizeMelPath(std::filesystem::path path)
{
    std::string value = path.lexically_normal().generic_string();
    std::size_t position = 0;
    while ((position = value.find('"', position)) != std::string::npos) {
        value.replace(position, 1, "\\\"");
        position += 2;
    }
    return value;
}

void sourceOptionScript(const MFnPlugin& plugin)
{
    std::filesystem::path base(plugin.loadPath().asChar());
    if (base.has_filename() && base.extension() == ".mll") {
        base = base.parent_path();
    }

    for (std::filesystem::path current = base; !current.empty(); current = current.parent_path()) {
        const std::filesystem::path candidate = current / "scripts" / "mayaObjectBuilderP3DOptions.mel";
        if (std::filesystem::exists(candidate)) {
            MGlobal::executeCommand(MString("source \"") + normalizeMelPath(candidate).c_str() + "\"", false, false);
            return;
        }
        if (current == current.parent_path()) {
            break;
        }
    }
}

MStatus registerCommand(MFnPlugin& plugin, const char* name, MCreatorFunction creator)
{
    const MStatus status = plugin.registerCommand(name, creator);
    if (!status) {
        status.perror(MString("registerCommand ") + name);
    }
    return status;
}

MStatus deregisterCommand(MFnPlugin& plugin, const char* name)
{
    const MStatus status = plugin.deregisterCommand(name);
    if (!status) {
        status.perror(MString("deregisterCommand ") + name);
    }
    return status;
}
}

MStatus initializePlugin(MObject obj)
{
    MFnPlugin plugin(obj, "MayaObjectBuilder", "0.1.0", "2027");
    sourceOptionScript(plugin);

    MStatus status = plugin.registerFileTranslator(
        P3DTranslator::kTranslatorName,
        "",
        P3DTranslator::creator,
        const_cast<char*>(kP3DOptionScript),
        const_cast<char*>(kP3DDefaultOptions),
        false);
    if (!status) {
        status.perror("registerFileTranslator Arma P3D");
        return status;
    }

    if (!(status = plugin.registerCommand(ValidateCommand::kName, ValidateCommand::creator, ValidateCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(SetMassCommand::kName, SetMassCommand::creator, SetMassCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(SetMaterialCommand::kName, SetMaterialCommand::creator, SetMaterialCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(SetFlagCommand::kName, SetFlagCommand::creator, SetFlagCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(CreateLODCommand::kName, CreateLODCommand::creator, CreateLODCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(ProxyCommand::kName, ProxyCommand::creator, ProxyCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(ImportModelCfgCommand::kName, ImportModelCfgCommand::creator, ImportModelCfgCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(ExportModelCfgCommand::kName, ExportModelCfgCommand::creator, ExportModelCfgCommand::syntax))) return status;

    MGlobal::displayInfo("MayaObjectBuilder loaded");
    return MS::kSuccess;
}

MStatus uninitializePlugin(MObject obj)
{
    MFnPlugin plugin(obj);
    MStatus status = MS::kSuccess;

    status = deregisterCommand(plugin, ExportModelCfgCommand::kName);
    status = deregisterCommand(plugin, ImportModelCfgCommand::kName);
    status = deregisterCommand(plugin, ProxyCommand::kName);
    status = deregisterCommand(plugin, CreateLODCommand::kName);
    status = deregisterCommand(plugin, SetFlagCommand::kName);
    status = deregisterCommand(plugin, SetMaterialCommand::kName);
    status = deregisterCommand(plugin, SetMassCommand::kName);
    status = deregisterCommand(plugin, ValidateCommand::kName);

    status = plugin.deregisterFileTranslator(P3DTranslator::kTranslatorName);
    if (!status) {
        status.perror("deregisterFileTranslator Arma P3D");
        return status;
    }

    MGlobal::displayInfo("MayaObjectBuilder unloaded");
    return MS::kSuccess;
}
