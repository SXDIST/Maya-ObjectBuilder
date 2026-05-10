#pragma once

#include "formats/P3D.h"

#include <maya/MStatus.h>
#include <maya/MString.h>

namespace a3ob::maya
{
struct ExportOptions
{
    bool selectedOnly = false;
    bool visibleOnly = true;
    bool applyTransforms = true;
    bool applyModifiers = true;
};

class MayaMeshExport
{
public:
    MStatus exportMLOD(const MString& path, const ExportOptions& options = {}) const;
};
}
