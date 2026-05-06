#include "P3DTranslator.h"

#include "../formats/P3D.h"
#include "../maya/MayaMeshExport.h"
#include "../maya/MayaMeshImport.h"

#include <maya/MFileObject.h>
#include <maya/MGlobal.h>
#include <maya/MObjectArray.h>

#include <cstring>
#include <exception>

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

MStatus P3DTranslator::reader(const MFileObject& file, const MString&, FileAccessMode)
{
    try {
        const a3ob::p3d::MLOD mlod = a3ob::p3d::MLOD::readFile(file.expandedFullName().asChar());
        MObjectArray createdTransforms;
        a3ob::maya::MayaMeshImport importer;
        const MStatus status = importer.importMLOD(mlod, file.name(), createdTransforms);
        if (!status) {
            return status;
        }
        MGlobal::displayInfo(MString("Imported P3D MLOD LOD count: ") + static_cast<int>(createdTransforms.length()));
        return MS::kSuccess;
    } catch (const std::exception& error) {
        MGlobal::displayError(MString("P3D import failed: ") + error.what());
        return MS::kFailure;
    }
}

MStatus P3DTranslator::writer(const MFileObject& file, const MString&, FileAccessMode)
{
    const a3ob::maya::MayaMeshExport exporter;
    return exporter.exportMLOD(file.expandedFullName());
}
