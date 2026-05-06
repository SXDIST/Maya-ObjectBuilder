#include "MayaMeshImport.h"

#include <maya/MDagPath.h>
#include <maya/MFnDagNode.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MFloatArray.h>
#include <maya/MFnLambertShader.h>
#include <maya/MFnMesh.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnSet.h>
#include <maya/MFnSingleIndexedComponent.h>
#include <maya/MFnStringData.h>
#include <maya/MFnTransform.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MGlobal.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MPlug.h>
#include <maya/MIntArray.h>
#include <maya/MObject.h>
#include <maya/MPointArray.h>
#include <maya/MSelectionList.h>
#include <maya/MStringArray.h>
#include <maya/MVectorArray.h>

#include <algorithm>
#include <map>
#include <set>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace a3ob::maya
{
namespace
{
MString sanitizedName(MString value)
{
    if (value.length() == 0) {
        return "P3D";
    }

    MString result;
    for (unsigned int i = 0; i < value.length(); ++i) {
        const MString ch = value.substringW(i, i);
        if (ch == "." || ch == " " || ch == "-" || ch == ":" || ch == "/" || ch == "\\") {
            result += "_";
        } else {
            result += ch;
        }
    }
    return result;
}

MString lodName(const p3d::LodResolution& resolution)
{
    MString name = "LOD_";
    name += resolution.lod;
    name += "_";
    name += resolution.resolution;
    return name;
}

MString selectionSetName(const MString& transformName, const std::string& selectionName)
{
    MString name = transformName;
    name += "_SEL_";
    name += sanitizedName(selectionName.c_str());
    return name;
}

MString proxyTransformName(const MString& transformName, const std::string& proxyPath, int proxyIndex)
{
    MString name = transformName;
    name += "_PROXY_";
    name += sanitizedName(proxyPath.c_str());
    name += "_";
    name += proxyIndex;
    return name;
}

MString materialNodeName(const std::string& texture, const std::string& material)
{
    MString name = "a3ob_MAT_";
    if (texture.empty() && material.empty()) {
        name += "no_material";
    } else {
        name += sanitizedName(texture.c_str());
        name += "__";
        name += sanitizedName(material.c_str());
    }
    return name;
}

MString flagSetName(const MString& transformName, const char* componentType, std::uint32_t flag)
{
    MString name = transformName;
    name += "_";
    name += componentType;
    name += "FLAG_";
    name += static_cast<int>(flag);
    return name;
}

MString floatValuesString(const std::vector<float>& values)
{
    std::ostringstream stream;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) {
            stream << ';';
        }
        stream << values[i];
    }
    return stream.str().c_str();
}

MString vertexValuesString(const std::vector<p3d::Vertex>& vertices)
{
    std::ostringstream stream;
    for (std::size_t i = 0; i < vertices.size(); ++i) {
        if (i != 0) {
            stream << ';';
        }
        stream << vertices[i].position.x << ',' << vertices[i].position.y << ',' << vertices[i].position.z << ',' << vertices[i].flag;
    }
    return stream.str().c_str();
}

MString indexValuesString(const std::vector<std::uint32_t>& values)
{
    std::ostringstream stream;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) {
            stream << ';';
        }
        stream << values[i];
    }
    return stream.str().c_str();
}

MString sharpEdgesString(const p3d::SharpEdgesTaggData& edges)
{
    std::ostringstream stream;
    for (std::size_t i = 0; i < edges.edges.size(); ++i) {
        if (i != 0) {
            stream << ';';
        }
        stream << edges.edges[i].first << ',' << edges.edges[i].second;
    }
    return stream.str().c_str();
}

MString uvSetTaggsString(const std::vector<const p3d::UVSetTaggData*>& taggs)
{
    std::ostringstream stream;
    for (std::size_t i = 0; i < taggs.size(); ++i) {
        if (i != 0) {
            stream << '|';
        }
        stream << taggs[i]->id;
        for (const p3d::Vec2& uv : taggs[i]->uvs) {
            stream << ',' << uv.u << ',' << uv.v;
        }
    }
    return stream.str().c_str();
}

bool parseProxyName(const std::string& name, std::string& proxyPath, int& proxyIndex)
{
    static const std::regex proxyRegex(R"(^proxy:(.*)\.(\d+)$)");
    std::smatch match;
    if (!std::regex_match(name, match, proxyRegex)) {
        return false;
    }
    proxyPath = match[1].str();
    proxyIndex = std::stoi(match[2].str());
    return true;
}

MStatus addBoolAttribute(MObject node, const char* longName, const char* shortName, bool value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return status;
    }

    if (!dep.attribute(longName, &status).isNull() && status) {
        return dep.findPlug(longName, true, &status).setBool(value);
    }

    MFnNumericAttribute attr;
    MObject attrObj = attr.create(longName, shortName, MFnNumericData::kBoolean, value, &status);
    if (!status) {
        return status;
    }
    attr.setStorable(true);
    attr.setKeyable(false);
    status = dep.addAttribute(attrObj);
    if (!status) {
        return status;
    }
    return dep.findPlug(longName, true, &status).setBool(value);
}

MStatus addIntAttribute(MObject node, const char* longName, const char* shortName, int value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return status;
    }

    if (!dep.attribute(longName, &status).isNull() && status) {
        return dep.findPlug(longName, true, &status).setInt(value);
    }

    MFnNumericAttribute attr;
    MObject attrObj = attr.create(longName, shortName, MFnNumericData::kInt, value, &status);
    if (!status) {
        return status;
    }
    attr.setStorable(true);
    attr.setKeyable(false);
    status = dep.addAttribute(attrObj);
    if (!status) {
        return status;
    }
    return dep.findPlug(longName, true, &status).setInt(value);
}

MStatus addDoubleAttribute(MObject node, const char* longName, const char* shortName, double value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return status;
    }

    if (!dep.attribute(longName, &status).isNull() && status) {
        return dep.findPlug(longName, true, &status).setDouble(value);
    }

    MFnNumericAttribute attr;
    MObject attrObj = attr.create(longName, shortName, MFnNumericData::kDouble, value, &status);
    if (!status) {
        return status;
    }
    attr.setStorable(true);
    attr.setKeyable(false);
    status = dep.addAttribute(attrObj);
    if (!status) {
        return status;
    }
    return dep.findPlug(longName, true, &status).setDouble(value);
}

MStatus addStringAttribute(MObject node, const char* longName, const char* shortName, const MString& value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return status;
    }

    if (!dep.attribute(longName, &status).isNull() && status) {
        return dep.findPlug(longName, true, &status).setString(value);
    }

    MFnStringData stringData;
    MObject defaultValue = stringData.create(value, &status);
    if (!status) {
        return status;
    }

    MFnTypedAttribute attr;
    MObject attrObj = attr.create(longName, shortName, MFnData::kString, defaultValue, &status);
    if (!status) {
        return status;
    }
    attr.setStorable(true);
    attr.setKeyable(false);
    status = dep.addAttribute(attrObj);
    if (!status) {
        return status;
    }
    return dep.findPlug(longName, true, &status).setString(value);
}

MString joinValues(const std::set<std::string>& values)
{
    MString output;
    bool first = true;
    for (const std::string& value : values) {
        if (!first) {
            output += ";";
        }
        output += value.c_str();
        first = false;
    }
    return output;
}

MString joinValues(const std::vector<std::string>& values)
{
    MString output;
    bool first = true;
    for (const std::string& value : values) {
        if (!first) {
            output += ";";
        }
        output += value.c_str();
        first = false;
    }
    return output;
}

MStatus setLODMetadata(MObject transform, const p3d::LOD& lod, const std::vector<std::uint32_t>* vertexMap = nullptr)
{
    MStatus status = addBoolAttribute(transform, "a3obIsLOD", "a3lod", true);
    if (!status) return status;
    status = addIntAttribute(transform, "a3obLodType", "a3lt", lod.resolution.lod);
    if (!status) return status;
    status = addIntAttribute(transform, "a3obResolution", "a3res", lod.resolution.resolution);
    if (!status) return status;
    status = addDoubleAttribute(transform, "a3obResolutionSignature", "a3sig", lod.resolution.source);
    if (!status) return status;
    status = addIntAttribute(transform, "a3obSourceVertexCount", "a3svc", static_cast<int>(lod.vertices.size()));
    if (!status) return status;
    status = addIntAttribute(transform, "a3obSourceFaceCount", "a3sfc", static_cast<int>(lod.faces.size()));
    if (!status) return status;
    if (vertexMap && !vertexMap->empty()) {
        status = addStringAttribute(transform, "a3obVertexSourceIndices", "a3vsi", indexValuesString(*vertexMap));
        if (!status) return status;
    }
    if (!lod.vertices.empty()) {
        status = addStringAttribute(transform, "a3obSourceVertices", "a3sv", vertexValuesString(lod.vertices));
        if (!status) return status;
    }

    std::set<std::string> textures;
    std::set<std::string> materials;
    for (const p3d::Face& face : lod.faces) {
        if (!face.texture.empty()) {
            textures.insert(face.texture);
        }
        if (!face.material.empty()) {
            materials.insert(face.material);
        }
    }

    std::vector<std::string> properties;
    std::vector<std::string> selections;
    std::vector<std::string> proxies;
    bool hasMass = false;
    bool hasSharpEdges = false;
    MString sharpEdges;
    int uvSetCount = 0;
    std::vector<const p3d::UVSetTaggData*> uvSetTaggs;
    for (const p3d::Tagg& tagg : lod.taggs) {
        if (!tagg.data) {
            continue;
        }

        switch (tagg.data->kind()) {
        case p3d::TaggKind::Property: {
            const auto* property = static_cast<const p3d::PropertyTaggData*>(tagg.data.get());
            properties.push_back(property->key + "=" + property->value);
            break;
        }
        case p3d::TaggKind::Selection:
            if (tagg.isProxy()) {
                proxies.push_back(tagg.name);
            } else {
                selections.push_back(tagg.name);
            }
            break;
        case p3d::TaggKind::Mass:
            hasMass = true;
            break;
        case p3d::TaggKind::SharpEdges: {
            hasSharpEdges = true;
            const auto* edges = static_cast<const p3d::SharpEdgesTaggData*>(tagg.data.get());
            sharpEdges = sharpEdgesString(*edges);
            break;
        }
        case p3d::TaggKind::UVSet:
            ++uvSetCount;
            uvSetTaggs.push_back(static_cast<const p3d::UVSetTaggData*>(tagg.data.get()));
            break;
        default:
            break;
        }
    }

    status = addStringAttribute(transform, "a3obTextures", "a3tex", joinValues(textures));
    if (!status) return status;
    status = addStringAttribute(transform, "a3obMaterials", "a3mat", joinValues(materials));
    if (!status) return status;
    status = addStringAttribute(transform, "a3obProperties", "a3prop", joinValues(properties));
    if (!status) return status;
    status = addStringAttribute(transform, "a3obSelections", "a3sel", joinValues(selections));
    if (!status) return status;
    status = addStringAttribute(transform, "a3obProxies", "a3prx", joinValues(proxies));
    if (!status) return status;
    status = addBoolAttribute(transform, "a3obHasMass", "a3mass", hasMass);
    if (!status) return status;
    for (const p3d::Tagg& tagg : lod.taggs) {
        if (tagg.data && tagg.data->kind() == p3d::TaggKind::Mass) {
            const auto* mass = static_cast<const p3d::MassTaggData*>(tagg.data.get());
            status = addStringAttribute(transform, "a3obMassValues", "a3mv", floatValuesString(mass->masses));
            if (!status) return status;
            break;
        }
    }
    status = addBoolAttribute(transform, "a3obHasSharpEdges", "a3sharp", hasSharpEdges);
    if (!status) return status;
    if (sharpEdges.length() > 0) {
        status = addStringAttribute(transform, "a3obSharpEdges", "a3se", sharpEdges);
        if (!status) return status;
    }
    status = addIntAttribute(transform, "a3obUVSetTaggCount", "a3uvtc", uvSetCount);
    if (!status) return status;
    if (!uvSetTaggs.empty()) {
        status = addStringAttribute(transform, "a3obUVSetTaggs", "a3uvt", uvSetTaggsString(uvSetTaggs));
        if (!status) return status;
    }
    return MS::kSuccess;
}

MStatus applyUVs(MFnMesh& meshFn, const p3d::LOD& lod)
{
    MStatus status;
    MFloatArray uValues;
    MFloatArray vValues;
    MIntArray uvCounts;
    MIntArray uvIds;

    for (const p3d::Face& face : lod.faces) {
        uvCounts.append(static_cast<int>(face.uvs.size()));
        for (const p3d::Vec2& uv : face.uvs) {
            uValues.append(uv.u);
            vValues.append(uv.v);
            uvIds.append(static_cast<int>(uvIds.length()));
        }
    }

    if (uValues.length() == 0) {
        return MS::kSuccess;
    }

    status = meshFn.setUVs(uValues, vValues);
    if (!status) {
        return status;
    }
    return meshFn.assignUVs(uvCounts, uvIds);
}

MStatus applyNormals(MFnMesh& meshFn, const p3d::LOD& lod, const std::map<std::uint32_t, int>& vertexRemap)
{
    MStatus status;
    MVectorArray normals;
    MIntArray faceIds;
    MIntArray vertexIds;

    for (unsigned int faceIndex = 0; faceIndex < lod.faces.size(); ++faceIndex) {
        const p3d::Face& face = lod.faces[faceIndex];
        for (unsigned int corner = 0; corner < face.vertices.size(); ++corner) {
            if (corner >= face.normals.size()) {
                continue;
            }
            const std::uint32_t normalIndex = face.normals[corner];
            if (normalIndex >= lod.normals.size()) {
                continue;
            }
            const auto mappedVertex = vertexRemap.find(face.vertices[corner]);
            if (mappedVertex == vertexRemap.end()) {
                continue;
            }
            const p3d::Vec3& normal = lod.normals[normalIndex];
            normals.append(MVector(normal.x, normal.y, normal.z));
            faceIds.append(static_cast<int>(faceIndex));
            vertexIds.append(mappedVertex->second);
        }
    }

    if (normals.length() == 0) {
        return MS::kSuccess;
    }

    status = meshFn.setFaceVertexNormals(normals, faceIds, vertexIds);
    if (!status) {
        return status;
    }
    return meshFn.updateSurface();
}

MStatus createFlagSet(const MDagPath& meshPath, const MString& name, const char* componentType, std::uint32_t flag, MFn::Type mayaComponentType, const MIntArray& indices)
{
    if (indices.length() == 0) {
        return MS::kSuccess;
    }

    MStatus status;
    MFnSingleIndexedComponent componentFn;
    MObject component = componentFn.create(mayaComponentType, &status);
    if (!status) {
        return status;
    }
    MIntArray mutableIndices = indices;
    status = componentFn.addElements(mutableIndices);
    if (!status) {
        return status;
    }

    MSelectionList members;
    status = members.add(meshPath, component);
    if (!status) {
        return status;
    }

    MFnSet setFn;
    MObject set = setFn.create(members, MFnSet::kNone, &status);
    if (!status) {
        return status;
    }
    setFn.setName(name, false, &status);
    if (!status) {
        return status;
    }
    status = addIntAttribute(set, "a3obFlagValue", "a3fv", static_cast<int>(flag));
    if (!status) return status;
    return addStringAttribute(set, "a3obFlagComponent", "a3fc", componentType);
}

MStatus createFlagSets(const MObject& mesh, const MString& transformName, const p3d::LOD& lod, const std::map<std::uint32_t, int>& vertexRemap)
{
    MStatus status;
    MFnDagNode meshDag(mesh, &status);
    if (!status) {
        return status;
    }
    MDagPath meshPath;
    status = meshDag.getPath(meshPath);
    if (!status) {
        return status;
    }

    std::map<std::uint32_t, MIntArray> vertexFlags;
    for (const auto& [sourceIndex, importedIndex] : vertexRemap) {
        if (sourceIndex < lod.vertices.size()) {
            const std::uint32_t flag = lod.vertices[sourceIndex].flag;
            if (flag != 0) {
                vertexFlags[flag].append(importedIndex);
            }
        }
    }

    for (const auto& [flag, indices] : vertexFlags) {
        status = createFlagSet(meshPath, flagSetName(transformName, "VERTEX_", flag), "vertex", flag, MFn::kMeshVertComponent, indices);
        if (!status) {
            return status;
        }
    }

    std::map<std::uint32_t, MIntArray> faceFlags;
    for (unsigned int faceIndex = 0; faceIndex < lod.faces.size(); ++faceIndex) {
        const std::uint32_t flag = lod.faces[faceIndex].flag;
        if (flag != 0) {
            faceFlags[flag].append(static_cast<int>(faceIndex));
        }
    }

    for (const auto& [flag, indices] : faceFlags) {
        status = createFlagSet(meshPath, flagSetName(transformName, "FACE_", flag), "face", flag, MFn::kMeshPolygonComponent, indices);
        if (!status) {
            return status;
        }
    }

    return MS::kSuccess;
}

MStatus createSelectionSet(const MDagPath& meshPath, const MString& transformName, const p3d::Tagg& tagg, const std::map<std::uint32_t, int>& vertexRemap)
{
    if (!tagg.data || tagg.data->kind() != p3d::TaggKind::Selection) {
        return MS::kSuccess;
    }

    const auto* selection = static_cast<const p3d::SelectionTaggData*>(tagg.data.get());
    MSelectionList members;
    MStatus status;

    if (!selection->vertexWeights.empty()) {
        MFnSingleIndexedComponent componentFn;
        MObject vertices = componentFn.create(MFn::kMeshVertComponent, &status);
        if (!status) {
            return status;
        }
        for (const auto& [sourceIndex, weight] : selection->vertexWeights) {
            const auto mappedVertex = vertexRemap.find(sourceIndex);
            if (mappedVertex != vertexRemap.end()) {
                componentFn.addElement(mappedVertex->second);
            }
        }
        if (componentFn.elementCount() > 0) {
            members.add(meshPath, vertices);
        }
    }

    if (!selection->faceWeights.empty()) {
        MFnSingleIndexedComponent componentFn;
        MObject faces = componentFn.create(MFn::kMeshPolygonComponent, &status);
        if (!status) {
            return status;
        }
        for (const auto& [faceIndex, weight] : selection->faceWeights) {
            componentFn.addElement(static_cast<int>(faceIndex));
        }
        if (componentFn.elementCount() > 0) {
            members.add(meshPath, faces);
        }
    }

    if (members.length() == 0) {
        return MS::kSuccess;
    }

    MFnSet setFn;
    MObject set = setFn.create(members, MFnSet::kNone, &status);
    if (!status) {
        return status;
    }
    setFn.setName(selectionSetName(transformName, tagg.name), false, &status);
    if (!status) {
        return status;
    }
    status = addStringAttribute(set, "a3obSelectionName", "a3sn", tagg.name.c_str());
    if (!status) return status;
    return addBoolAttribute(set, "a3obIsProxySelection", "a3ips", tagg.isProxy());
}

MStatus createSelectionSets(const MObject& mesh, const MString& transformName, const p3d::LOD& lod, const std::map<std::uint32_t, int>& vertexRemap)
{
    MStatus status;
    MFnDagNode meshDag(mesh, &status);
    if (!status) {
        return status;
    }
    MDagPath meshPath;
    status = meshDag.getPath(meshPath);
    if (!status) {
        return status;
    }

    for (const p3d::Tagg& tagg : lod.taggs) {
        if (!tagg.data || tagg.data->kind() != p3d::TaggKind::Selection) {
            continue;
        }
        status = createSelectionSet(meshPath, transformName, tagg, vertexRemap);
        if (!status) {
            return status;
        }
    }
    return MS::kSuccess;
}

MStatus createProxyPlaceholders(MObject parentTransform, const MString& transformName, const p3d::LOD& lod)
{
    MStatus status;
    for (const p3d::Tagg& tagg : lod.taggs) {
        if (!tagg.isProxy()) {
            continue;
        }

        std::string proxyPath;
        int proxyIndex = 0;
        if (!parseProxyName(tagg.name, proxyPath, proxyIndex)) {
            continue;
        }

        MFnTransform proxyTransformFn;
        MObject proxyTransform = proxyTransformFn.create(parentTransform, &status);
        if (!status) {
            return status;
        }
        proxyTransformFn.setName(proxyTransformName(transformName, proxyPath, proxyIndex), false, &status);
        if (!status) {
            return status;
        }

        status = addBoolAttribute(proxyTransform, "a3obIsProxy", "a3pr", true);
        if (!status) return status;
        status = addStringAttribute(proxyTransform, "a3obProxyPath", "a3pp", proxyPath.c_str());
        if (!status) return status;
        status = addIntAttribute(proxyTransform, "a3obProxyIndex", "a3pi", proxyIndex);
        if (!status) return status;
        status = addStringAttribute(proxyTransform, "a3obProxySelection", "a3ps", tagg.name.c_str());
        if (!status) return status;
    }
    return MS::kSuccess;
}
}

bool MayaMeshImport::MaterialKey::operator<(const MaterialKey& other) const
{
    if (texture != other.texture) {
        return texture < other.texture;
    }
    return material < other.material;
}

MStatus MayaMeshImport::getOrCreateMaterial(const MaterialKey& key, MaterialNodes& nodes)
{
    const auto existing = materials_.find(key);
    if (existing != materials_.end()) {
        nodes = existing->second;
        return MS::kSuccess;
    }

    MStatus status;
    MFnLambertShader shaderFn;
    nodes.shader = shaderFn.create(true, &status);
    if (!status) {
        return status;
    }
    shaderFn.setName(materialNodeName(key.texture, key.material), false, &status);
    if (!status) {
        return status;
    }

    MFnSet shadingGroupFn;
    nodes.shadingGroup = shadingGroupFn.create(MSelectionList(), MFnSet::kRenderableOnly, &status);
    if (!status) {
        return status;
    }
    MString shadingGroupName = shaderFn.name();
    shadingGroupName += "SG";
    shadingGroupFn.setName(shadingGroupName, false, &status);
    if (!status) {
        return status;
    }

    status = addStringAttribute(nodes.shader, "a3obTexture", "a3tx", key.texture.c_str());
    if (!status) return status;
    status = addStringAttribute(nodes.shader, "a3obMaterial", "a3mt", key.material.c_str());
    if (!status) return status;
    status = addStringAttribute(nodes.shadingGroup, "a3obTexture", "a3sgtx", key.texture.c_str());
    if (!status) return status;
    status = addStringAttribute(nodes.shadingGroup, "a3obMaterial", "a3sgmt", key.material.c_str());
    if (!status) return status;

    materials_[key] = nodes;
    return MS::kSuccess;
}

MStatus MayaMeshImport::assignMaterials(const MObject& mesh, const p3d::LOD& lod)
{
    MStatus status;
    MFnDagNode meshDag(mesh, &status);
    if (!status) {
        return status;
    }
    MDagPath meshPath;
    status = meshDag.getPath(meshPath);
    if (!status) {
        return status;
    }

    std::map<MaterialKey, MIntArray> faceGroups;
    for (unsigned int faceIndex = 0; faceIndex < lod.faces.size(); ++faceIndex) {
        const p3d::Face& face = lod.faces[faceIndex];
        faceGroups[{face.texture, face.material}].append(static_cast<int>(faceIndex));
    }

    for (const auto& [key, faceIndices] : faceGroups) {
        MaterialNodes nodes;
        status = getOrCreateMaterial(key, nodes);
        if (!status) {
            return status;
        }

        MFnSingleIndexedComponent componentFn;
        MObject faces = componentFn.create(MFn::kMeshPolygonComponent, &status);
        if (!status) {
            return status;
        }
        MIntArray mutableFaceIndices = faceIndices;
        status = componentFn.addElements(mutableFaceIndices);
        if (!status) {
            return status;
        }

        MSelectionList members;
        status = members.add(meshPath, faces);
        if (!status) {
            return status;
        }

        MFnSet shadingGroupFn(nodes.shadingGroup, &status);
        if (!status) {
            return status;
        }
        status = shadingGroupFn.addMembers(members);
        if (!status) {
            return status;
        }
    }

    return MS::kSuccess;
}

MStatus MayaMeshImport::importMLOD(const p3d::MLOD& mlod, const MString& sourceName, MObjectArray& createdTransforms)
{
    MStatus status;
    for (unsigned int i = 0; i < mlod.lods.size(); ++i) {
        status = importLOD(mlod.lods[i], i, sourceName, createdTransforms);
        if (!status) {
            return status;
        }
    }
    return MStatus::kSuccess;
}

MStatus MayaMeshImport::importLOD(const p3d::LOD& lod, unsigned int index, const MString& sourceName, MObjectArray& createdTransforms)
{
    MStatus status;

    MFnTransform transformFn;
    MObject transform = transformFn.create(MObject::kNullObj, &status);
    if (!status) {
        return status;
    }

    MString transformName = sanitizedName(sourceName);
    transformName += "_";
    transformName += lodName(lod.resolution);
    transformName += "#";
    transformFn.setName(transformName, false, &status);
    if (!status) {
        return status;
    }

    std::vector<std::uint32_t> vertexSourceIndices;
    if (!lod.faces.empty()) {
        std::map<std::uint32_t, int> vertexRemap;
        for (const p3d::Face& face : lod.faces) {
            for (std::uint32_t vertexIndex : face.vertices) {
                if (vertexRemap.find(vertexIndex) == vertexRemap.end()) {
                    vertexRemap[vertexIndex] = static_cast<int>(vertexRemap.size());
                }
            }
        }

        vertexSourceIndices.resize(vertexRemap.size());
        for (const auto& [sourceIndex, importedIndex] : vertexRemap) {
            vertexSourceIndices[static_cast<std::size_t>(importedIndex)] = sourceIndex;
        }

        MPointArray points;
        for (const auto& [sourceIndex, importedIndex] : vertexRemap) {
            if (sourceIndex >= lod.vertices.size()) {
                MGlobal::displayError("P3D face references a vertex outside the LOD vertex table");
                return MS::kFailure;
            }
            const p3d::Vertex& vertex = lod.vertices[sourceIndex];
            points.append(MPoint(vertex.position.x, vertex.position.y, vertex.position.z));
        }

        MIntArray faceCounts;
        MIntArray faceConnects;
        for (const p3d::Face& face : lod.faces) {
            faceCounts.append(static_cast<int>(face.vertices.size()));
            for (std::uint32_t vertexIndex : face.vertices) {
                faceConnects.append(vertexRemap[vertexIndex]);
            }
        }

        MFnMesh meshFn;
        MObject mesh = meshFn.create(points.length(), faceCounts.length(), points, faceCounts, faceConnects, transform, &status);
        if (!status) {
            MGlobal::displayError("Failed to create Maya mesh for P3D LOD");
            return status;
        }

        MFnDagNode meshDag(mesh, &status);
        if (status) {
            MString shapeName = transformFn.name();
            shapeName += "Shape";
            meshDag.setName(shapeName, false, &status);
        }

        status = applyUVs(meshFn, lod);
        if (!status) {
            return status;
        }

        status = applyNormals(meshFn, lod, vertexRemap);
        if (!status) {
            return status;
        }

        status = assignMaterials(mesh, lod);
        if (!status) {
            return status;
        }

        status = createSelectionSets(mesh, transformFn.name(), lod, vertexRemap);
        if (!status) {
            return status;
        }

        status = createFlagSets(mesh, transformFn.name(), lod, vertexRemap);
        if (!status) {
            return status;
        }
    }

    status = createProxyPlaceholders(transform, transformFn.name(), lod);
    if (!status) {
        return status;
    }

    status = setLODMetadata(transform, lod, vertexSourceIndices.empty() ? nullptr : &vertexSourceIndices);
    if (!status) {
        return status;
    }

    createdTransforms.append(transform);
    return MStatus::kSuccess;
}
}
