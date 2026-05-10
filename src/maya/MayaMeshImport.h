#pragma once

#include "formats/P3D.h"

#include <maya/MObject.h>
#include <maya/MObjectArray.h>
#include <maya/MStatus.h>
#include <maya/MString.h>

#include <map>
#include <string>

namespace a3ob::maya
{
class MayaMeshImport
{
public:
    MStatus importMLOD(p3d::MLOD&& mlod, const MString& sourceName, MObjectArray& createdTransforms);

private:
    struct MaterialKey
    {
        std::string texture;
        std::string material;

        bool operator<(const MaterialKey& other) const;
    };

    struct MaterialNodes
    {
        MObject shader;
        MObject shadingGroup;
    };

    MStatus importLOD(const p3d::LOD& lod, MObject parent, MObjectArray& createdTransforms);
    MStatus getOrCreateMaterial(const MaterialKey& key, MaterialNodes& nodes);
    MStatus assignMaterials(const MObject& mesh, const p3d::LOD& lod);

    std::map<MaterialKey, MaterialNodes> materials_;
};
}
