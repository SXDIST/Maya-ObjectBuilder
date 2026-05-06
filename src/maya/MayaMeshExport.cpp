#include "MayaMeshExport.h"

#include <maya/MDagPath.h>
#include <maya/MFloatArray.h>
#include <maya/MFnDagNode.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MFnMesh.h>
#include <maya/MFnSet.h>
#include <maya/MFnSingleIndexedComponent.h>
#include <maya/MGlobal.h>
#include <maya/MItDag.h>
#include <maya/MItDependencyNodes.h>
#include <maya/MItMeshEdge.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MPlug.h>
#include <maya/MPointArray.h>
#include <maya/MSelectionList.h>
#include <maya/MStringArray.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace a3ob::maya
{
namespace
{
struct ExportLOD
{
    p3d::LOD lod;
    float sortKey = 0.0f;
};

bool boolPlugValue(const MObject& node, const char* name, bool defaultValue = false)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return defaultValue;
    }
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) {
        return defaultValue;
    }
    bool value = defaultValue;
    plug.getValue(value);
    return value;
}

int intPlugValue(const MObject& node, const char* name, int defaultValue = 0)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return defaultValue;
    }
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) {
        return defaultValue;
    }
    int value = defaultValue;
    plug.getValue(value);
    return value;
}

double doublePlugValue(const MObject& node, const char* name, double defaultValue = 0.0)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return defaultValue;
    }
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) {
        return defaultValue;
    }
    double value = defaultValue;
    plug.getValue(value);
    return value;
}

std::string stringPlugValue(const MObject& node, const char* name)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) {
        return {};
    }
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) {
        return {};
    }
    MString value;
    plug.getValue(value);
    return value.asChar();
}

std::vector<std::string> splitSemicolon(const std::string& value)
{
    std::vector<std::string> parts;
    std::stringstream stream(value);
    std::string part;
    while (std::getline(stream, part, ';')) {
        if (!part.empty()) {
            parts.push_back(part);
        }
    }
    return parts;
}

std::vector<float> splitFloatValues(const std::string& value)
{
    std::vector<float> values;
    for (const std::string& part : splitSemicolon(value)) {
        values.push_back(std::stof(part));
    }
    return values;
}

std::vector<std::uint32_t> splitIndexValues(const std::string& value)
{
    std::vector<std::uint32_t> values;
    for (const std::string& part : splitSemicolon(value)) {
        values.push_back(static_cast<std::uint32_t>(std::stoul(part)));
    }
    return values;
}

std::vector<p3d::Vertex> splitVertexValues(const std::string& value)
{
    std::vector<p3d::Vertex> vertices;
    for (const std::string& part : splitSemicolon(value)) {
        std::stringstream stream(part);
        std::string field;
        std::vector<std::string> fields;
        while (std::getline(stream, field, ',')) {
            fields.push_back(field);
        }
        if (fields.size() != 4) {
            continue;
        }
        p3d::Vertex vertex;
        vertex.position.x = std::stof(fields[0]);
        vertex.position.y = std::stof(fields[1]);
        vertex.position.z = std::stof(fields[2]);
        vertex.flag = static_cast<std::uint32_t>(std::stoul(fields[3]));
        vertices.push_back(vertex);
    }
    return vertices;
}

std::vector<std::pair<std::uint32_t, std::uint32_t>> splitSharpEdges(const std::string& value)
{
    std::vector<std::pair<std::uint32_t, std::uint32_t>> edges;
    for (const std::string& part : splitSemicolon(value)) {
        const std::size_t separator = part.find(',');
        if (separator == std::string::npos) {
            continue;
        }
        edges.emplace_back(static_cast<std::uint32_t>(std::stoul(part.substr(0, separator))), static_cast<std::uint32_t>(std::stoul(part.substr(separator + 1))));
    }
    return edges;
}

std::vector<std::unique_ptr<p3d::UVSetTaggData>> splitUVSetTaggs(const std::string& value)
{
    std::vector<std::unique_ptr<p3d::UVSetTaggData>> taggs;
    std::stringstream groups(value);
    std::string group;
    while (std::getline(groups, group, '|')) {
        if (group.empty()) {
            continue;
        }
        std::stringstream stream(group);
        std::string field;
        std::vector<std::string> fields;
        while (std::getline(stream, field, ',')) {
            fields.push_back(field);
        }
        if (fields.empty() || (fields.size() - 1) % 2 != 0) {
            continue;
        }
        auto data = std::make_unique<p3d::UVSetTaggData>();
        data->id = static_cast<std::uint32_t>(std::stoul(fields[0]));
        for (std::size_t i = 1; i + 1 < fields.size(); i += 2) {
            data->uvs.push_back({std::stof(fields[i]), std::stof(fields[i + 1])});
        }
        taggs.push_back(std::move(data));
    }
    return taggs;
}

std::vector<std::pair<std::string, std::string>> splitProperties(const std::string& value)
{
    std::vector<std::pair<std::string, std::string>> properties;
    for (const std::string& part : splitSemicolon(value)) {
        const std::size_t separator = part.find('=');
        if (separator == std::string::npos) {
            continue;
        }
        properties.emplace_back(part.substr(0, separator), part.substr(separator + 1));
    }
    return properties;
}

std::vector<std::pair<std::string, std::string>> meshMaterialPairs(const MObject& mesh)
{
    MStatus status;
    MFnMesh meshFn(mesh, &status);
    if (!status) {
        return {};
    }

    MObjectArray shaders;
    MIntArray shaderIndices;
    status = meshFn.getConnectedShaders(0, shaders, shaderIndices);
    if (!status) {
        return {};
    }

    std::vector<std::pair<std::string, std::string>> pairs;
    pairs.reserve(shaderIndices.length());
    for (unsigned int faceIndex = 0; faceIndex < shaderIndices.length(); ++faceIndex) {
        const int shaderIndex = shaderIndices[faceIndex];
        if (shaderIndex >= 0 && static_cast<unsigned int>(shaderIndex) < shaders.length()) {
            pairs.emplace_back(stringPlugValue(shaders[shaderIndex], "a3obTexture"), stringPlugValue(shaders[shaderIndex], "a3obMaterial"));
        } else {
            pairs.emplace_back();
        }
    }
    return pairs;
}

void addPropertyTaggs(const MObject& transform, p3d::LOD& lod)
{
    for (const auto& [key, value] : splitProperties(stringPlugValue(transform, "a3obProperties"))) {
        p3d::Tagg tagg;
        tagg.name = "#Property#";
        auto data = std::make_unique<p3d::PropertyTaggData>();
        data->key = key;
        data->value = value;
        tagg.data = std::move(data);
        lod.taggs.push_back(std::move(tagg));
    }
}

void addMassTagg(const MObject& transform, p3d::LOD& lod)
{
    const std::string values = stringPlugValue(transform, "a3obMassValues");
    if (values.empty()) {
        return;
    }

    p3d::Tagg tagg;
    tagg.name = "#Mass#";
    auto data = std::make_unique<p3d::MassTaggData>();
    data->masses = splitFloatValues(values);
    if (data->masses.size() != lod.vertices.size()) {
        data->masses.resize(lod.vertices.size(), 0.0f);
    }
    tagg.data = std::move(data);
    lod.taggs.push_back(std::move(tagg));
}

void readSetComponents(const MObject& set, const MDagPath& meshPath, std::vector<int>& vertices, std::vector<int>& faces)
{
    MStatus status;
    MFnSet setFn(set, &status);
    if (!status) {
        return;
    }

    MSelectionList members;
    status = setFn.getMembers(members, true);
    if (!status) {
        return;
    }

    for (unsigned int i = 0; i < members.length(); ++i) {
        MDagPath memberPath;
        MObject component;
        status = members.getDagPath(i, memberPath, component);
        if (!status || memberPath.node() != meshPath.node() || component.isNull()) {
            continue;
        }

        MFnSingleIndexedComponent componentFn(component, &status);
        if (!status) {
            continue;
        }

        MIntArray elements;
        componentFn.getElements(elements);
        if (component.hasFn(MFn::kMeshVertComponent)) {
            for (unsigned int idx = 0; idx < elements.length(); ++idx) {
                vertices.push_back(elements[idx]);
            }
        } else if (component.hasFn(MFn::kMeshPolygonComponent)) {
            for (unsigned int idx = 0; idx < elements.length(); ++idx) {
                faces.push_back(elements[idx]);
            }
        }
    }
}

void addSelectionAndFlagData(const MDagPath& meshPath, p3d::LOD& lod)
{
    MStatus status;
    MItDependencyNodes it(MFn::kSet, &status);
    if (!status) {
        return;
    }

    for (; !it.isDone(); it.next()) {
        MObject set = it.thisNode(&status);
        if (!status) {
            continue;
        }

        std::vector<int> vertices;
        std::vector<int> faces;
        readSetComponents(set, meshPath, vertices, faces);
        if (vertices.empty() && faces.empty()) {
            continue;
        }

        const std::string selectionName = stringPlugValue(set, "a3obSelectionName");
        if (!selectionName.empty()) {
            p3d::Tagg tagg;
            tagg.name = selectionName;
            auto data = std::make_unique<p3d::SelectionTaggData>();
            data->countVerts = static_cast<std::uint32_t>(lod.vertices.size());
            data->countFaces = static_cast<std::uint32_t>(lod.faces.size());
            for (int vertex : vertices) {
                if (vertex >= 0 && static_cast<std::size_t>(vertex) < lod.vertices.size()) {
                    data->vertexWeights.emplace_back(static_cast<std::uint32_t>(vertex), 1.0f);
                }
            }
            for (int face : faces) {
                if (face >= 0 && static_cast<std::size_t>(face) < lod.faces.size()) {
                    data->faceWeights.emplace_back(static_cast<std::uint32_t>(face), 1.0f);
                }
            }
            tagg.data = std::move(data);
            lod.taggs.push_back(std::move(tagg));
            continue;
        }

        const int flagValue = intPlugValue(set, "a3obFlagValue", 0);
        const std::string flagComponent = stringPlugValue(set, "a3obFlagComponent");
        if (flagValue == 0 || flagComponent.empty()) {
            continue;
        }
        if (flagComponent == "vertex") {
            for (int vertex : vertices) {
                if (vertex >= 0 && static_cast<std::size_t>(vertex) < lod.vertices.size()) {
                    lod.vertices[vertex].flag = static_cast<std::uint32_t>(flagValue);
                }
            }
        } else if (flagComponent == "face") {
            for (int face : faces) {
                if (face >= 0 && static_cast<std::size_t>(face) < lod.faces.size()) {
                    lod.faces[face].flag = static_cast<std::uint32_t>(flagValue);
                }
            }
        }
    }
}

void addSharpEdgesTagg(const MObject& transform, const MDagPath& meshPath, p3d::LOD& lod)
{
    if (!boolPlugValue(transform, "a3obHasSharpEdges")) {
        return;
    }

    std::vector<std::pair<std::uint32_t, std::uint32_t>> savedEdges = splitSharpEdges(stringPlugValue(transform, "a3obSharpEdges"));
    if (!savedEdges.empty()) {
        p3d::Tagg tagg;
        tagg.name = "#SharpEdges#";
        auto data = std::make_unique<p3d::SharpEdgesTaggData>();
        data->edges = std::move(savedEdges);
        tagg.data = std::move(data);
        lod.taggs.push_back(std::move(tagg));
        return;
    }

    MStatus status;
    MItMeshEdge edgeIt(meshPath, MObject::kNullObj, &status);
    if (!status) {
        return;
    }

    auto data = std::make_unique<p3d::SharpEdgesTaggData>();
    for (; !edgeIt.isDone(); edgeIt.next()) {
        if (!edgeIt.isSmooth()) {
            const int first = edgeIt.index(0);
            const int second = edgeIt.index(1);
            if (first >= 0 && second >= 0 && static_cast<std::size_t>(first) < lod.vertices.size() && static_cast<std::size_t>(second) < lod.vertices.size()) {
                data->edges.emplace_back(static_cast<std::uint32_t>(first), static_cast<std::uint32_t>(second));
            }
        }
    }

    if (data->edges.empty()) {
        return;
    }

    p3d::Tagg tagg;
    tagg.name = "#SharpEdges#";
    tagg.data = std::move(data);
    lod.taggs.push_back(std::move(tagg));
}

void addUVSetTaggs(const MObject& transform, const p3d::LOD& sourceLod, p3d::LOD& lod)
{
    std::vector<std::unique_ptr<p3d::UVSetTaggData>> savedTaggs = splitUVSetTaggs(stringPlugValue(transform, "a3obUVSetTaggs"));
    if (!savedTaggs.empty()) {
        for (std::unique_ptr<p3d::UVSetTaggData>& data : savedTaggs) {
            p3d::Tagg tagg;
            tagg.name = "#UVSet#";
            tagg.data = std::move(data);
            lod.taggs.push_back(std::move(tagg));
        }
        return;
    }

    const int count = intPlugValue(transform, "a3obUVSetTaggCount", 0);
    if (count <= 0) {
        return;
    }

    std::vector<p3d::Vec2> uvs;
    for (const p3d::Face& face : sourceLod.faces) {
        uvs.insert(uvs.end(), face.uvs.begin(), face.uvs.end());
    }
    if (uvs.empty()) {
        return;
    }

    for (int i = 0; i < count; ++i) {
        p3d::Tagg tagg;
        tagg.name = "#UVSet#";
        auto data = std::make_unique<p3d::UVSetTaggData>();
        data->id = static_cast<std::uint32_t>(i + 1);
        data->uvs = uvs;
        tagg.data = std::move(data);
        lod.taggs.push_back(std::move(tagg));
    }
}

MStatus exportMeshLOD(const MDagPath& transformPath, ExportLOD& output)
{
    MStatus status;
    MFnDagNode transformFn(transformPath, &status);
    if (!status) {
        return status;
    }

    const int lodType = intPlugValue(transformPath.node(), "a3obLodType", 0);
    const int resolution = intPlugValue(transformPath.node(), "a3obResolution", 0);
    const double signature = doublePlugValue(transformPath.node(), "a3obResolutionSignature", p3d::LodResolution::encode(lodType, resolution));
    output.lod.resolution = p3d::LodResolution::fromFloat(static_cast<float>(signature));
    output.sortKey = static_cast<float>(signature);

    MDagPath meshPath;
    bool foundMesh = false;
    for (unsigned int i = 0; i < transformFn.childCount(); ++i) {
        MObject child = transformFn.child(i, &status);
        if (!status) {
            return status;
        }
        if (child.hasFn(MFn::kMesh)) {
            meshPath = transformPath;
            status = meshPath.extendToShapeDirectlyBelow(i);
            if (!status) {
                return status;
            }
            foundMesh = true;
            break;
        }
    }

    if (!foundMesh) {
        output.lod.vertices = splitVertexValues(stringPlugValue(transformPath.node(), "a3obSourceVertices"));
        if (output.lod.vertices.empty()) {
            const int sourceVertexCount = intPlugValue(transformPath.node(), "a3obSourceVertexCount", 0);
            if (sourceVertexCount > 0) {
                output.lod.vertices.resize(static_cast<std::size_t>(sourceVertexCount));
            }
        }
        addPropertyTaggs(transformPath.node(), output.lod);
        addMassTagg(transformPath.node(), output.lod);
        return MS::kSuccess;
    }

    MFnMesh meshFn(meshPath, &status);
    if (!status) {
        return status;
    }

    MPointArray points;
    status = meshFn.getPoints(points, MSpace::kObject);
    if (!status) {
        return status;
    }

    const std::vector<std::uint32_t> vertexSourceIndices = splitIndexValues(stringPlugValue(transformPath.node(), "a3obVertexSourceIndices"));
    const std::vector<p3d::Vertex> sourceVertices = splitVertexValues(stringPlugValue(transformPath.node(), "a3obSourceVertices"));
    if (vertexSourceIndices.size() == points.length() && !sourceVertices.empty()) {
        output.lod.vertices = sourceVertices;
        for (unsigned int i = 0; i < points.length(); ++i) {
            const std::uint32_t sourceIndex = vertexSourceIndices[i];
            if (sourceIndex < output.lod.vertices.size()) {
                output.lod.vertices[sourceIndex].position = {static_cast<float>(points[i].x), static_cast<float>(points[i].y), static_cast<float>(points[i].z)};
            }
        }
    } else {
        output.lod.vertices.reserve(points.length());
        for (unsigned int i = 0; i < points.length(); ++i) {
            output.lod.vertices.push_back({{static_cast<float>(points[i].x), static_cast<float>(points[i].y), static_cast<float>(points[i].z)}, 0});
        }
    }

    const std::vector<std::pair<std::string, std::string>> materialPairs = meshMaterialPairs(meshPath.node());

    MFloatArray uArray;
    MFloatArray vArray;
    meshFn.getUVs(uArray, vArray);

    MItMeshPolygon polygonIt(meshPath, MObject::kNullObj, &status);
    if (!status) {
        return status;
    }
    for (; !polygonIt.isDone(); polygonIt.next()) {
        MIntArray vertexIds;
        status = polygonIt.getVertices(vertexIds);
        if (!status) {
            return status;
        }

        p3d::Face face;
        const int faceIndex = polygonIt.index();
        if (faceIndex >= 0 && static_cast<std::size_t>(faceIndex) < materialPairs.size()) {
            face.texture = materialPairs[faceIndex].first;
            face.material = materialPairs[faceIndex].second;
        }
        for (unsigned int i = 0; i < vertexIds.length(); ++i) {
            std::uint32_t vertexIndex = static_cast<std::uint32_t>(vertexIds[i]);
            if (vertexSourceIndices.size() == points.length() && static_cast<std::size_t>(vertexIds[i]) < vertexSourceIndices.size()) {
                vertexIndex = vertexSourceIndices[static_cast<std::size_t>(vertexIds[i])];
            }
            face.vertices.push_back(vertexIndex);
            face.normals.push_back(static_cast<std::uint32_t>(output.lod.normals.size()));

            MVector normal;
            status = polygonIt.getNormal(i, normal, MSpace::kObject);
            if (!status) {
                normal = MVector(0.0, 1.0, 0.0);
            }
            output.lod.normals.push_back({static_cast<float>(normal.x), static_cast<float>(normal.y), static_cast<float>(normal.z)});

            int uvId = -1;
            if (uArray.length() > 0 && polygonIt.getUVIndex(i, uvId) && uvId >= 0 && static_cast<unsigned int>(uvId) < uArray.length()) {
                face.uvs.push_back({uArray[uvId], vArray[uvId]});
            } else {
                face.uvs.push_back({0.0f, 0.0f});
            }
        }
        output.lod.faces.push_back(std::move(face));
    }

    addPropertyTaggs(transformPath.node(), output.lod);
    addMassTagg(transformPath.node(), output.lod);
    addSelectionAndFlagData(meshPath, output.lod);
    addSharpEdgesTagg(transformPath.node(), meshPath, output.lod);
    addUVSetTaggs(transformPath.node(), output.lod, output.lod);

    output.lod.renormalizeNormals();
    return MS::kSuccess;
}
}

MStatus MayaMeshExport::exportMLOD(const MString& path) const
{
    std::vector<ExportLOD> exportLods;

    MStatus status;
    MItDag it(MItDag::kDepthFirst, MFn::kTransform, &status);
    if (!status) {
        return status;
    }

    for (; !it.isDone(); it.next()) {
        MDagPath transformPath;
        status = it.getPath(transformPath);
        if (!status) {
            return status;
        }

        if (!boolPlugValue(transformPath.node(), "a3obIsLOD")) {
            continue;
        }

        ExportLOD exportLod;
        status = exportMeshLOD(transformPath, exportLod);
        if (!status) {
            return status;
        }
        exportLods.push_back(std::move(exportLod));
    }

    if (exportLods.empty()) {
        MGlobal::displayError("P3D export failed: no transforms with a3obIsLOD found");
        return MS::kFailure;
    }

    std::sort(exportLods.begin(), exportLods.end(), [](const ExportLOD& left, const ExportLOD& right) {
        return left.sortKey < right.sortKey;
    });

    p3d::MLOD mlod;
    mlod.lods.reserve(exportLods.size());
    for (ExportLOD& exportLod : exportLods) {
        mlod.lods.push_back(std::move(exportLod.lod));
    }

    try {
        mlod.writeFile(std::filesystem::path(path.asChar()));
    } catch (const std::exception& error) {
        MGlobal::displayError(MString("P3D export failed: ") + error.what());
        return MS::kFailure;
    }

    MGlobal::displayInfo(MString("Exported P3D MLOD LOD count: ") + static_cast<int>(mlod.lods.size()));
    return MS::kSuccess;
}
}
