#include "P3DTranslator.h"

#include "../formats/P3D.h"
#include "../maya/MayaMeshExport.h"
#include "../maya/MayaMeshImport.h"

#include <maya/MFileObject.h>
#include <maya/MGlobal.h>
#include <maya/MObjectArray.h>
#include <maya/MStringArray.h>

#include <cstring>
#include <exception>
#include <map>
#include <string>

namespace
{
std::map<std::string, std::string> parseOptions(const MString& optionsString)
{
    MStringArray optionList;
    optionsString.split(';', optionList);
    std::map<std::string, std::string> options;
    for (unsigned int i = 0; i < optionList.length(); ++i) {
        MStringArray pair;
        optionList[i].split('=', pair);
        if (pair.length() == 2) {
            options[pair[0].asChar()] = pair[1].asChar();
        }
    }
    return options;
}

bool optionEnabled(const std::map<std::string, std::string>& options, const char* key, bool fallback)
{
    const auto it = options.find(key);
    if (it == options.end()) {
        return fallback;
    }
    return it->second == "1" || it->second == "true";
}
}

void* P3DTranslator::creator()
{
    return new P3DTranslator();
}

bool P3DTranslator::haveReadMethod() const
{
    return true;
}

bool P3DTranslator::haveWriteMethod() const
{
    return true;
}

bool P3DTranslator::haveReferenceMethod() const
{
    return false;
}

bool P3DTranslator::haveNamespaceSupport() const
{
    return true;
}

bool P3DTranslator::canBeOpened() const
{
    return true;
}

MString P3DTranslator::defaultExtension() const
{
    return "p3d";
}

MString P3DTranslator::filter() const
{
    return "*.p3d";
}

MPxFileTranslator::MFileKind P3DTranslator::identifyFile(const MFileObject& fileName, const char* buffer, short size) const
{
    if (size >= 4 && std::memcmp(buffer, "MLOD", 4) == 0) {
        return kIsMyFileType;
    }

    const MString path = fileName.name();
    if (path.length() >= 4 && path.substringW(path.length() - 4, path.length() - 1).toLowerCase() == ".p3d") {
        return kCouldBeMyFileType;
    }

    return kNotMyFileType;
}

MStatus P3DTranslator::reader(const MFileObject& file, const MString& optionsString, FileAccessMode)
{
    try {
        a3ob::p3d::MLOD mlod = a3ob::p3d::MLOD::readFile(file.expandedFullName().asChar());
        const std::map<std::string, std::string> options = parseOptions(optionsString);
        if (optionEnabled(options, "firstLodOnly", false) && mlod.lods.size() > 1) {
            mlod.lods.erase(mlod.lods.begin() + 1, mlod.lods.end());
        }

        MObjectArray createdTransforms;
        a3ob::maya::MayaMeshImport importer;
        const MStatus status = importer.importMLOD(std::move(mlod), file.name(), createdTransforms);
        if (!status) {
            return status;
        }
        if (optionEnabled(options, "validateMeshes", false)) {
            MGlobal::executeCommand("a3obValidate", false, false);
        }
        MGlobal::displayInfo(MString("Imported P3D MLOD LOD count: ") + static_cast<int>(createdTransforms.length()));
        return MS::kSuccess;
    } catch (const std::exception& error) {
        MGlobal::displayError(MString("P3D import failed: ") + error.what());
        return MS::kFailure;
    }
}

MStatus P3DTranslator::writer(const MFileObject& file, const MString& optionsString, FileAccessMode mode)
{
    const std::map<std::string, std::string> options = parseOptions(optionsString);
    a3ob::maya::ExportOptions exportOptions;
    exportOptions.selectedOnly = mode == MPxFileTranslator::kExportActiveAccessMode || optionEnabled(options, "selectedOnly", false);
    exportOptions.visibleOnly = optionEnabled(options, "visibleOnly", true);
    exportOptions.applyTransforms = optionEnabled(options, "applyTransforms", true);
    exportOptions.applyModifiers = optionEnabled(options, "applyModifiers", true);
    if (optionEnabled(options, "validateMeshes", false) || optionEnabled(options, "exportValidateMeshes", false) || optionEnabled(options, "validateLods", false)) {
        MGlobal::executeCommand(MString("a3obValidate") + (exportOptions.selectedOnly ? " -selectionOnly" : ""), false, false);
    }
    const a3ob::maya::MayaMeshExport exporter;
    return exporter.exportMLOD(file.expandedFullName(), exportOptions);
}
