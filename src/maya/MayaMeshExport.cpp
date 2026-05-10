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
#include <maya/MItSelectionList.h>
#include <maya/MMatrix.h>
#include <maya/MPlug.h>
#include <maya/MPointArray.h>
#include <maya/MSelectionList.h>
#include <maya/MString.h>
#include <maya/MStringArray.h>
#include <maya/MTransformationMatrix.h>
#include <maya/MVector.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace a3ob::maya
{
namespace
{
p3d::Vec3 mayaToCorePoint(const MPoint& value)
{
    return {static_cast<float>(value.x), static_cast<float>(-value.z), static_cast<float>(value.y)};
}

p3d::Vec3 mayaToCoreVector(MVector value)
{
    value.normalize();
    return {static_cast<float>(value.x), static_cast<float>(-value.z), static_cast<float>(value.y)};
}

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

bool resolveLODPath(MDagPath path, MDagPath& lodPath)
{
    if (path.node().hasFn(MFn::kTransform) && boolPlugValue(path.node(), "a3obIsLOD")) {
        lodPath = path;
        return true;
    }

    if (path.hasFn(MFn::kMesh)) {
        path.pop();
    }

    while (path.length() > 0) {
        if (path.node().hasFn(MFn::kTransform) && boolPlugValue(path.node(), "a3obIsLOD")) {
            lodPath = path;
            return true;
        }
        path.pop();
    }
    return false;
}

bool findFirstMeshPath(const MDagPath& transformPath, MDagPath& meshPath)
{
    MStatus status;
    MFnDagNode transformFn(transformPath, &status);
    if (!status) {
        return false;
    }

    for (unsigned int i = 0; i < transformFn.childCount(); ++i) {
        MObject child = transformFn.child(i, &status);
        if (!status) {
            continue;
        }
        if (child.hasFn(MFn::kMesh)) {
            meshPath = transformPath;
            status = meshPath.extendToShapeDirectlyBelow(i);
            return static_cast<bool>(status);
        }
        if (!child.hasFn(MFn::kTransform)) {
            continue;
        }

        MFnDagNode childTransform(child, &status);
        if (!status) {
            continue;
        }
        for (unsigned int j = 0; j < childTransform.childCount(); ++j) {
            MObject grandchild = childTransform.child(j, &status);
            if (status && grandchild.hasFn(MFn::kMesh)) {
                MFnDagNode meshDag(grandchild, &status);
                return status && meshDag.getPath(meshPath);
            }
        }
    }
    return false;
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
            std::string tex = stringPlugValue(shaders[shaderIndex], "a3obTexture");
            std::string mat = stringPlugValue(shaders[shaderIndex], "a3obMaterial");
            std::replace(tex.begin(), tex.end(), '/', '\\');
            std::replace(mat.begin(), mat.end(), '/', '\\');
            auto stripDrive = [](std::string& p) {
                if (p.size() >= 2 && p[1] == ':') {
                    p = p.substr(2);
                    while (!p.empty() && p.front() == '\\') p.erase(p.begin());
                }
            };
            stripDrive(tex);
            stripDrive(mat);
            pairs.emplace_back(std::move(tex), std::move(mat));
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

bool componentStringMatchesPath(const std::string& item, const std::vector<std::string>& pathNames, std::size_t markerPosition)
{
    const std::string objectName = item.substr(0, markerPosition);
    return std::find(pathNames.begin(), pathNames.end(), objectName) != pathNames.end();
}

bool itemMatchesPath(const std::string& item, const std::vector<std::string>& pathNames)
{
    return std::find(pathNames.begin(), pathNames.end(), item) != pathNames.end();
}

void addPathNameAlias(std::vector<std::string>& pathNames, const MString& path)
{
    const std::string value = path.asChar();
    if (value.empty()) {
        return;
    }
    pathNames.push_back(value);
    const std::size_t separator = value.find_last_of('|');
    if (separator != std::string::npos && separator + 1 < value.size()) {
        pathNames.push_back(value.substr(separator + 1));
    }
}

void addComponentStringIndex(const std::string& item, const std::vector<std::string>& pathNames, const char* token, std::set<int>& indices)
{
    const std::string marker = std::string(".") + token + "[";
    const std::size_t markerPosition = item.find(marker);
    if (markerPosition == std::string::npos || !componentStringMatchesPath(item, pathNames, markerPosition)) {
        return;
    }
    const std::size_t begin = markerPosition + marker.size();
    const std::size_t end = item.find(']', begin);
    if (end == std::string::npos) {
        return;
    }

    const std::string range = item.substr(begin, end - begin);
    const std::size_t separator = range.find(':');
    if (separator == std::string::npos) {
        indices.insert(std::stoi(range));
        return;
    }

    const int first = std::stoi(range.substr(0, separator));
    const int last = std::stoi(range.substr(separator + 1));
    for (int index = first; index <= last; ++index) {
        indices.insert(index);
    }
}

void addAllVertexIndices(const MDagPath& meshPath, std::set<int>& vertices)
{
    MStatus status;
    const MFnMesh meshFn(meshPath, &status);
    if (!status) {
        return;
    }
    const int count = meshFn.numVertices(&status);
    if (!status) {
        return;
    }
    for (int index = 0; index < count; ++index) {
        vertices.insert(index);
    }
}

void deriveFacesFromVertices(const MDagPath& meshPath, const std::set<int>& vertices, std::set<int>& faces)
{
    if (vertices.empty()) {
        return;
    }
    MStatus status;
    MItMeshPolygon it(meshPath.node(), &status);
    if (!status) {
        return;
    }
    for (; !it.isDone(); it.next()) {
        MIntArray faceVertices;
        if (!it.getVertices(faceVertices)) {
            continue;
        }
        bool selected = faceVertices.length() > 0;
        for (unsigned int i = 0; i < faceVertices.length(); ++i) {
            if (vertices.find(faceVertices[i]) == vertices.end()) {
                selected = false;
                break;
            }
        }
        if (selected) {
            faces.insert(it.index());
        }
    }
}

void readSetComponents(const MObject& set, const MDagPath& meshPath, std::set<int>& vertices, std::set<int>& faces)
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

    std::vector<std::string> pathNames;
    addPathNameAlias(pathNames, meshPath.fullPathName());
    addPathNameAlias(pathNames, meshPath.partialPathName());
    MDagPath transformPath = meshPath;
    transformPath.pop();
    addPathNameAlias(pathNames, transformPath.fullPathName());
    addPathNameAlias(pathNames, transformPath.partialPathName());

    MStringArray memberStrings;
    members.getSelectionStrings(memberStrings);
    for (unsigned int i = 0; i < memberStrings.length(); ++i) {
        const std::string item = memberStrings[i].asChar();
        addComponentStringIndex(item, pathNames, "vtx", vertices);
        addComponentStringIndex(item, pathNames, "f", faces);
        if (itemMatchesPath(item, pathNames)) {
            addAllVertexIndices(meshPath, vertices);
        }
    }
}

void addSelectionAndFlagData(const MDagPath& meshPath, const std::vector<std::uint32_t>& vertexSourceIndices, p3d::LOD& lod)
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

        std::set<int> vertices;
        std::set<int> faces;
        readSetComponents(set, meshPath, vertices, faces);
        if (vertices.empty() && faces.empty()) {
            continue;
        }

        const std::string selectionName = stringPlugValue(set, "a3obSelectionName");
        if (!selectionName.empty()) {
            deriveFacesFromVertices(meshPath, vertices, faces);
            p3d::Tagg tagg;
            tagg.name = selectionName;
            auto data = std::make_unique<p3d::SelectionTaggData>();
            data->countVerts = static_cast<std::uint32_t>(lod.vertices.size());
            data->countFaces = static_cast<std::uint32_t>(lod.faces.size());
            for (int vertex : vertices) {
                if (vertex < 0) {
                    continue;
                }
                std::uint32_t sourceIndex = static_cast<std::uint32_t>(vertex);
                if (static_cast<std::size_t>(vertex) < vertexSourceIndices.size()) {
                    sourceIndex = vertexSourceIndices[static_cast<std::size_t>(vertex)];
                }
                if (sourceIndex < lod.vertices.size()) {
                    data->vertexWeights.emplace_back(sourceIndex, 1.0f);
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
                if (vertex < 0) {
                    continue;
                }
                std::uint32_t sourceIndex = static_cast<std::uint32_t>(vertex);
                if (static_cast<std::size_t>(vertex) < vertexSourceIndices.size()) {
                    sourceIndex = vertexSourceIndices[static_cast<std::size_t>(vertex)];
                }
                if (sourceIndex < lod.vertices.size()) {
                    lod.vertices[sourceIndex].flag = static_cast<std::uint32_t>(flagValue);
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

    const int count = std::max(1, intPlugValue(transform, "a3obUVSetTaggCount", 0));

    std::vector<p3d::Vec2> uvs;
    uvs.reserve(sourceLod.faces.size() * 4);
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
        data->id = static_cast<std::uint32_t>(i);
        data->uvs = (i == count - 1) ? std::move(uvs) : uvs;
        tagg.data = std::move(data);
        lod.taggs.push_back(std::move(tagg));
    }
}

bool hasDirectLocatorShape(const MFnDagNode& dagFn)
{
    MStatus status;
    for (unsigned int j = 0; j < dagFn.childCount(); ++j) {
        MObject child = dagFn.child(j, &status);
        if (status && child.hasFn(MFn::kLocator)) {
            return true;
        }
    }
    return false;
}

bool collectLocatorsFromMemoryLOD(const MDagPath& transformPath, const ExportOptions& options, p3d::LOD& lod)
{
    MStatus status;
    MFnDagNode lodDagFn(transformPath, &status);
    if (!status) {
        return false;
    }

    struct LocatorPoint {
        std::string selectionName;
        std::uint32_t vertexIndex;
    };
    std::vector<LocatorPoint> points;

    auto addLocatorVertex = [&](const MDagPath& locPath, const std::string& selName) {
        MMatrix bakeMatrix;
        if (options.applyTransforms) {
            bakeMatrix = locPath.inclusiveMatrix();
        } else {
            bakeMatrix = locPath.inclusiveMatrix() * transformPath.inclusiveMatrix().inverse();
        }
        const MPoint worldPos = MPoint(0.0, 0.0, 0.0) * bakeMatrix;
        const std::uint32_t vertexIndex = static_cast<std::uint32_t>(lod.vertices.size());
        lod.vertices.push_back({mayaToCorePoint(worldPos), 0});
        points.push_back({selName, vertexIndex});
    };

    for (unsigned int i = 0; i < lodDagFn.childCount(); ++i) {
        MObject childObj = lodDagFn.child(i, &status);
        if (!status || !childObj.hasFn(MFn::kTransform)) {
            continue;
        }
        if (boolPlugValue(childObj, "a3obIsProxy")) {
            continue;
        }

        MFnDagNode childDagFn(childObj, &status);
        if (!status) {
            continue;
        }

        if (hasDirectLocatorShape(childDagFn)) {
            // Single-point locator directly under Memory LOD
            MDagPath childPath;
            status = childDagFn.getPath(childPath);
            if (!status) {
                continue;
            }
            std::string selName = stringPlugValue(childObj, "a3obSelectionName");
            if (selName.empty()) {
                selName = childDagFn.name().asChar();
            }
            addLocatorVertex(childPath, selName);
        } else {
            // Group container: named transform with locator-bearing child transforms
            std::string groupSelName = stringPlugValue(childObj, "a3obSelectionName");
            if (groupSelName.empty()) {
                groupSelName = childDagFn.name().asChar();
            }
            for (unsigned int j = 0; j < childDagFn.childCount(); ++j) {
                MObject grandchild = childDagFn.child(j, &status);
                if (!status || !grandchild.hasFn(MFn::kTransform)) {
                    continue;
                }
                if (boolPlugValue(grandchild, "a3obIsProxy")) {
                    continue;
                }
                MFnDagNode grandchildDagFn(grandchild, &status);
                if (!status || !hasDirectLocatorShape(grandchildDagFn)) {
                    continue;
                }
                MDagPath grandchildPath;
                status = grandchildDagFn.getPath(grandchildPath);
                if (!status) {
                    continue;
                }
                addLocatorVertex(grandchildPath, groupSelName);
            }
        }
    }

    if (points.empty()) {
        return false;
    }

    std::vector<std::string> orderedNames;
    std::map<std::string, std::vector<std::uint32_t>> selectionVertices;
    for (const auto& point : points) {
        if (selectionVertices.find(point.selectionName) == selectionVertices.end()) {
            orderedNames.push_back(point.selectionName);
        }
        selectionVertices[point.selectionName].push_back(point.vertexIndex);
    }

    const std::uint32_t totalVerts = static_cast<std::uint32_t>(lod.vertices.size());
    for (const auto& name : orderedNames) {
        p3d::Tagg tagg;
        tagg.name = name;
        auto data = std::make_unique<p3d::SelectionTaggData>();
        data->countVerts = totalVerts;
        data->countFaces = 0;
        for (const std::uint32_t idx : selectionVertices.at(name)) {
            data->vertexWeights.emplace_back(idx, 1.0f);
        }
        tagg.data = std::move(data);
        lod.taggs.push_back(std::move(tagg));
    }

    return true;
}

float lodSortKey(const MDagPath& transformPath)
{
    const int lodType = intPlugValue(transformPath.node(), "a3obLodType", 0);
    const int resolution = intPlugValue(transformPath.node(), "a3obResolution", 0);
    const double signature = doublePlugValue(transformPath.node(), "a3obResolutionSignature",
        p3d::LodResolution::encode(lodType, resolution));
    return static_cast<float>(signature);
}

MStatus exportMeshLOD(const MDagPath& transformPath, const ExportOptions& options, ExportLOD& output)
{
    MStatus status;
    const int lodType = intPlugValue(transformPath.node(), "a3obLodType", 0);
    const int resolution = intPlugValue(transformPath.node(), "a3obResolution", 0);
    const double signature = doublePlugValue(transformPath.node(), "a3obResolutionSignature", p3d::LodResolution::encode(lodType, resolution));
    output.lod.resolution = p3d::LodResolution::fromFloat(static_cast<float>(signature));
    output.sortKey = static_cast<float>(signature);

    MDagPath meshPath;
    if (!findFirstMeshPath(transformPath, meshPath)) {
        if (lodType == 9 && collectLocatorsFromMemoryLOD(transformPath, options, output.lod)) {
            addPropertyTaggs(transformPath.node(), output.lod);
            return MS::kSuccess;
        }
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

    MMatrix bakeMatrix;
    MMatrix normalMatrix;
    if (options.applyTransforms) {
        bakeMatrix = meshPath.inclusiveMatrix();
        normalMatrix = bakeMatrix.inverse().transpose();
    }
    for (unsigned int i = 0; i < points.length(); ++i) {
        points.set(points[i] * bakeMatrix, i);
    }

    const std::vector<std::uint32_t> vertexSourceIndices = splitIndexValues(stringPlugValue(transformPath.node(), "a3obVertexSourceIndices"));
    const std::vector<p3d::Vertex> sourceVertices = splitVertexValues(stringPlugValue(transformPath.node(), "a3obSourceVertices"));
    if (vertexSourceIndices.size() == points.length() && !sourceVertices.empty()) {
        output.lod.vertices = sourceVertices;
        for (unsigned int i = 0; i < points.length(); ++i) {
            const std::uint32_t sourceIndex = vertexSourceIndices[i];
            if (sourceIndex < output.lod.vertices.size()) {
                output.lod.vertices[sourceIndex].position = mayaToCorePoint(points[i]);
            }
        }
    } else {
        output.lod.vertices.reserve(points.length());
        for (unsigned int i = 0; i < points.length(); ++i) {
            output.lod.vertices.push_back({mayaToCorePoint(points[i]), 0});
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
        auto emitFaceCorner = [&](p3d::Face& f, unsigned int localIdx, int mayaVertexId) {
            std::uint32_t vertexIndex = static_cast<std::uint32_t>(mayaVertexId);
            if (vertexSourceIndices.size() == points.length() && static_cast<std::size_t>(mayaVertexId) < vertexSourceIndices.size()) {
                vertexIndex = vertexSourceIndices[static_cast<std::size_t>(mayaVertexId)];
            }
            f.vertices.push_back(vertexIndex);
            f.normals.push_back(static_cast<std::uint32_t>(output.lod.normals.size()));

            MVector normal;
            if (!polygonIt.getNormal(localIdx, normal, MSpace::kObject)) {
                normal = MVector(0.0, 1.0, 0.0);
            }
            if (options.applyTransforms) {
                normal = normal * normalMatrix;
            }
            output.lod.normals.push_back(mayaToCoreVector(normal));

            int uvId = -1;
            if (uArray.length() > 0 && polygonIt.getUVIndex(localIdx, uvId) && uvId >= 0 && static_cast<unsigned int>(uvId) < uArray.length()) {
                f.uvs.push_back({uArray[uvId], vArray[uvId]});
            } else {
                f.uvs.push_back({0.0f, 0.0f});
            }
        };

        if (vertexIds.length() <= 4) {
            for (unsigned int i = 0; i < vertexIds.length(); ++i) {
                emitFaceCorner(face, i, vertexIds[i]);
            }
            output.lod.faces.push_back(std::move(face));
        } else {
            // N-gon: triangulate via Maya API so Object Builder (tri/quad only) can save
            int numTris = 0;
            polygonIt.numTriangles(numTris);
            for (int triIdx = 0; triIdx < numTris; ++triIdx) {
                MPointArray triPoints;
                MIntArray triVertices;
                polygonIt.getTriangle(triIdx, triPoints, triVertices);

                p3d::Face triFace;
                triFace.texture = face.texture;
                triFace.material = face.material;

                for (unsigned int j = 0; j < triVertices.length(); ++j) {
                    // Map object-space Maya vertex index back to local polygon index for UV/normal lookup
                    unsigned int localIdx = 0;
                    for (unsigned int k = 0; k < vertexIds.length(); ++k) {
                        if (vertexIds[k] == triVertices[j]) {
                            localIdx = k;
                            break;
                        }
                    }
                    emitFaceCorner(triFace, localIdx, triVertices[j]);
                }
                output.lod.faces.push_back(std::move(triFace));
            }
        }
    }

    addPropertyTaggs(transformPath.node(), output.lod);
    addMassTagg(transformPath.node(), output.lod);
    addSelectionAndFlagData(meshPath, vertexSourceIndices, output.lod);
    addSharpEdgesTagg(transformPath.node(), meshPath, output.lod);
    addUVSetTaggs(transformPath.node(), output.lod, output.lod);

    output.lod.renormalizeNormals();
    return MS::kSuccess;
}
}

MStatus MayaMeshExport::exportMLOD(const MString& path, const ExportOptions& options) const
{
    // Pass 1: collect DAG paths + sort keys only (no mesh data loaded)
    std::vector<std::pair<float, MDagPath>> lodEntries;

    MStatus status;
    if (options.selectedOnly) {
        MSelectionList selection;
        MGlobal::getActiveSelectionList(selection);

        std::vector<std::string> exportedPaths;
        MStringArray selectedNames;
        selection.getSelectionStrings(selectedNames);

        for (unsigned int i = 0; i < selection.length(); ++i) {
            MDagPath selectedPath;
            MObject component;
            status = selection.getDagPath(i, selectedPath, component);
            if (!status) {
                continue;
            }

            MDagPath lodPath;
            if (!resolveLODPath(selectedPath, lodPath)) {
                continue;
            }

            const std::string fullPath = lodPath.fullPathName().asChar();
            if (std::find(exportedPaths.begin(), exportedPaths.end(), fullPath) != exportedPaths.end()) {
                continue;
            }
            exportedPaths.push_back(fullPath);

            lodEntries.emplace_back(lodSortKey(lodPath), lodPath);
        }

        if (lodEntries.empty() && selectedNames.length() > 0) {
            MString message("P3D export failed: selection does not contain an Object Builder LOD, LOD mesh, or mesh component: ");
            for (unsigned int i = 0; i < selectedNames.length(); ++i) {
                if (i > 0) {
                    message += ", ";
                }
                message += selectedNames[i];
            }
            MGlobal::displayError(message);
            return MS::kFailure;
        }
    } else {
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

            if (options.visibleOnly && !transformPath.isVisible()) {
                continue;
            }

            lodEntries.emplace_back(lodSortKey(transformPath), transformPath);
        }
    }

    if (lodEntries.empty()) {
        MGlobal::displayError(options.selectedOnly ? "P3D export failed: select an Object Builder LOD or its mesh" : "P3D export failed: no transforms with a3obIsLOD found");
        return MS::kFailure;
    }

    std::sort(lodEntries.begin(), lodEntries.end(), [](const auto& a, const auto& b) {
        return a.first < b.first;
    });

    // Pass 2: export and write each LOD immediately; only one LOD in memory at a time
    p3d::MLOD mlodHeader;
    try {
        BinaryWriter writer(std::filesystem::path(path.asChar()));
        mlodHeader.beginWrite(writer, static_cast<std::uint32_t>(lodEntries.size()));
        for (const auto& [sortKey, dagPath] : lodEntries) {
            ExportLOD exportLod;
            status = exportMeshLOD(dagPath, options, exportLod);
            if (!status) {
                MGlobal::displayError(MString("P3D export failed: could not export LOD ") + dagPath.fullPathName());
                return status;
            }
            mlodHeader.writeLOD(writer, exportLod.lod);
        }
    } catch (const std::exception& error) {
        MGlobal::displayError(MString("P3D export failed: ") + error.what());
        return MS::kFailure;
    }

    MGlobal::displayInfo(MString("Exported P3D MLOD LOD count: ") + static_cast<int>(lodEntries.size()));
    return MS::kSuccess;
}
}
