#pragma once

#include "formats/P3D.h"

#include <maya/MStatus.h>
#include <maya/MString.h>

namespace a3ob::maya
{
class MayaMeshExport
{
public:
    MStatus exportMLOD(const MString& path, bool selectedOnly = false) const;
};
}
