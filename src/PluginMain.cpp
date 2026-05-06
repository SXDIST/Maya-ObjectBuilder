#include "commands/ModelCfgCommands.h"
#include "commands/StubCommands.h"
#include "translators/P3DTranslator.h"

#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>
#include <maya/MStatus.h>

namespace
{
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

    MStatus status = plugin.registerFileTranslator(
        P3DTranslator::kTranslatorName,
        "",
        P3DTranslator::creator,
        "",
        "",
        false);
    if (!status) {
        status.perror("registerFileTranslator Arma P3D");
        return status;
    }

    if (!(status = plugin.registerCommand(ValidateCommand::kName, ValidateCommand::creator, ValidateCommand::syntax))) return status;
    if (!(status = plugin.registerCommand(SetMassCommand::kName, SetMassCommand::creator, SetMassCommand::syntax))) return status;
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
