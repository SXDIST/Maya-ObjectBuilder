#include "StubCommands.h"

#include "formats/P3D.h"

#include <maya/MArgDatabase.h>
#include <maya/MArgList.h>
#include <maya/MDagPath.h>
#include <maya/MFnDagNode.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MFnMesh.h>
#include <maya/MFnLambertShader.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnSet.h>
#include <maya/MFnSingleIndexedComponent.h>
#include <maya/MFnStringData.h>
#include <maya/MFnTransform.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MGlobal.h>
#include <maya/MItDag.h>
#include <maya/MItDependencyNodes.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MObjectArray.h>
#include <maya/MPlug.h>
#include <maya/MStringArray.h>
#include <maya/MPointArray.h>
#include <maya/MSelectionList.h>
#include <maya/MVector.h>

#include <algorithm>
#include <map>
#include <regex>
#include <set>
#include <queue>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace
{
bool boolPlugValue(const MObject& node, const char* name, bool defaultValue = false)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return defaultValue;
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) return defaultValue;
    bool value = defaultValue;
    plug.getValue(value);
    return value;
}

int intPlugValue(const MObject& node, const char* name, int defaultValue = 0)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return defaultValue;
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) return defaultValue;
    int value = defaultValue;
    plug.getValue(value);
    return value;
}

double doublePlugValue(const MObject& node, const char* name, double defaultValue = 0.0)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return defaultValue;
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) return defaultValue;
    double value = defaultValue;
    plug.getValue(value);
    return value;
}

std::string stringPlugValue(const MObject& node, const char* name)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return {};
    MPlug plug = dep.findPlug(name, true, &status);
    if (!status) return {};
    MString value;
    plug.getValue(value);
    return value.asChar();
}

MStatus setBoolAttribute(MObject node, const char* longName, const char* shortName, bool value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return status;
    MPlug plug = dep.findPlug(longName, true, &status);
    if (!status) {
        MFnNumericAttribute attr;
        MObject attrObj = attr.create(longName, shortName, MFnNumericData::kBoolean, value, &status);
        if (!status) return status;
        attr.setKeyable(true);
        status = dep.addAttribute(attrObj);
        if (!status) return status;
        plug = dep.findPlug(longName, true, &status);
        if (!status) return status;
    }
    return plug.setValue(value);
}

MStatus setIntAttribute(MObject node, const char* longName, const char* shortName, int value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return status;
    MPlug plug = dep.findPlug(longName, true, &status);
    if (!status) {
        MFnNumericAttribute attr;
        MObject attrObj = attr.create(longName, shortName, MFnNumericData::kInt, value, &status);
        if (!status) return status;
        attr.setKeyable(true);
        status = dep.addAttribute(attrObj);
        if (!status) return status;
        plug = dep.findPlug(longName, true, &status);
        if (!status) return status;
    }
    return plug.setValue(value);
}

MStatus setDoubleAttribute(MObject node, const char* longName, const char* shortName, double value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return status;
    MPlug plug = dep.findPlug(longName, true, &status);
    if (!status) {
        MFnNumericAttribute attr;
        MObject attrObj = attr.create(longName, shortName, MFnNumericData::kDouble, value, &status);
        if (!status) return status;
        attr.setKeyable(true);
        status = dep.addAttribute(attrObj);
        if (!status) return status;
        plug = dep.findPlug(longName, true, &status);
        if (!status) return status;
    }
    return plug.setValue(value);
}

MStatus setStringAttribute(MObject node, const char* longName, const char* shortName, const MString& value)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    if (!status) return status;
    MPlug plug = dep.findPlug(longName, true, &status);
    if (!status) {
        MFnStringData data;
        MObject defaultValue = data.create(value, &status);
        if (!status) return status;
        MFnTypedAttribute attr;
        MObject attrObj = attr.create(longName, shortName, MFnData::kString, defaultValue, &status);
        if (!status) return status;
        attr.setKeyable(true);
        status = dep.addAttribute(attrObj);
        if (!status) return status;
        plug = dep.findPlug(longName, true, &status);
        if (!status) return status;
    }
    return plug.setValue(value);
}

MStatus markTechnicalSet(MObject set)
{
    MStatus status = setBoolAttribute(set, "a3obTechnicalSet", "a3ts", true);
    if (!status) return status;
    MFnDependencyNode dep(set, &status);
    if (!status) return status;
    MPlug plug = dep.findPlug("hiddenInOutliner", true, &status);
    if (status) status = plug.setBool(true);
    return status;
}

std::vector<std::string> splitSemicolon(const std::string& value)
{
    std::vector<std::string> parts;
    std::stringstream stream(value);
    std::string part;
    while (std::getline(stream, part, ';')) {
        if (!part.empty()) parts.push_back(part);
    }
    return parts;
}

std::vector<std::pair<std::string, std::string>> splitProperties(const std::string& value)
{
    std::vector<std::pair<std::string, std::string>> properties;
    for (const std::string& part : splitSemicolon(value)) {
        const std::size_t separator = part.find('=');
        if (separator == std::string::npos) {
            properties.emplace_back(part, "");
        } else {
            properties.emplace_back(part.substr(0, separator), part.substr(separator + 1));
        }
    }
    return properties;
}

MString propertiesString(const std::vector<std::pair<std::string, std::string>>& properties)
{
    MString result;
    bool first = true;
    for (const auto& [key, value] : properties) {
        if (key.empty()) continue;
        if (!first) result += ";";
        result += key.c_str();
        result += "=";
        result += value.c_str();
        first = false;
    }
    return result;
}

bool isAscii(const std::string& value)
{
    for (const unsigned char ch : value) {
        if (ch > 127) return false;
    }
    return true;
}

bool isProxySelectionName(const std::string& value)
{
    static const std::regex proxyRegex(R"(^proxy:.*\.\d+$)");
    return std::regex_match(value, proxyRegex);
}

bool isComponentSelectionName(const std::string& value)
{
    static const std::regex componentRegex(R"(^[Cc]omponent\d+$)");
    return std::regex_match(value, componentRegex);
}

MString proxySelectionName(const MString& proxyPath, int proxyIndex)
{
    MString selectionName = "proxy:";
    selectionName += proxyPath;
    selectionName += ".";
    selectionName += proxyIndex;
    return selectionName;
}

MObject firstMeshChild(const MObject& transform)
{
    MStatus status;
    MFnDagNode dag(transform, &status);
    if (!status) return MObject::kNullObj;
    for (unsigned int i = 0; i < dag.childCount(); ++i) {
        MObject child = dag.child(i, &status);
        if (status && child.hasFn(MFn::kMesh)) return child;
    }
    return MObject::kNullObj;
}

MObject firstMeshChild(const MObject& transform);

MObject selectedTransformOrNull()
{
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MDagPath path;
        MObject component;
        if (!selection.getDagPath(i, path, component)) continue;
        MObject node = path.node();
        if (node.hasFn(MFn::kTransform)) return node;
        if (node.hasFn(MFn::kMesh)) {
            MFnDagNode dag(node);
            return dag.parent(0);
        }
    }
    return MObject::kNullObj;
}

MObject lodTransformForPath(const MDagPath& path)
{
    MStatus status;
    MObject node = path.node();
    while (!node.isNull()) {
        if (node.hasFn(MFn::kTransform) && boolPlugValue(node, "a3obIsLOD")) return node;
        MFnDagNode dag(node, &status);
        if (!status || dag.parentCount() == 0) break;
        node = dag.parent(0, &status);
        if (!status) break;
    }
    return MObject::kNullObj;
}

MObject selectedLODOrNull()
{
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MDagPath path;
        MObject component;
        if (selection.getDagPath(i, path, component)) {
            MObject lod = lodTransformForPath(path);
            if (!lod.isNull()) return lod;
        }
    }
    return MObject::kNullObj;
}

std::vector<MObject> lodTransforms(bool selectionOnly)
{
    std::vector<MObject> lods;
    if (selectionOnly) {
        MSelectionList selection;
        MGlobal::getActiveSelectionList(selection);
        for (unsigned int i = 0; i < selection.length(); ++i) {
            MDagPath path;
            MObject component;
            if (selection.getDagPath(i, path, component) && path.node().hasFn(MFn::kTransform) && boolPlugValue(path.node(), "a3obIsLOD")) {
                lods.push_back(path.node());
            }
        }
        return lods;
    }

    MStatus status;
    MItDag it(MItDag::kDepthFirst, MFn::kTransform, &status);
    if (!status) return lods;
    for (; !it.isDone(); it.next()) {
        MObject node = it.currentItem(&status);
        if (status && boolPlugValue(node, "a3obIsLOD")) lods.push_back(node);
    }
    return lods;
}

MStatus setLODAttributes(MObject transform, int lodType, int resolution)
{
    const double signature = a3ob::p3d::LodResolution::encode(lodType, resolution);
    MStatus status = setBoolAttribute(transform, "a3obIsLOD", "a3lod", true);
    if (!status) return status;
    status = setIntAttribute(transform, "a3obLodType", "a3lt", lodType);
    if (!status) return status;
    status = setIntAttribute(transform, "a3obResolution", "a3res", resolution);
    if (!status) return status;
    status = setDoubleAttribute(transform, "a3obResolutionSignature", "a3sig", signature);
    if (!status) return status;
    status = setIntAttribute(transform, "a3obSourceVertexCount", "a3svc", 0);
    if (!status) return status;
    return setIntAttribute(transform, "a3obSourceFaceCount", "a3sfc", 0);
}

int vertexCountForLOD(const MObject& transform)
{
    MObject mesh = firstMeshChild(transform);
    if (!mesh.isNull()) {
        MStatus status;
        MFnMesh meshFn(mesh, &status);
        if (status) return meshFn.numVertices();
    }
    return intPlugValue(transform, "a3obSourceVertexCount", 0);
}

MObject proxyPlaceholder(MObject lod, const std::string& selectionName)
{
    MStatus status;
    MFnDagNode dag(lod, &status);
    if (!status) return MObject::kNullObj;
    for (unsigned int i = 0; i < dag.childCount(); ++i) {
        MObject child = dag.child(i, &status);
        if (status && child.hasFn(MFn::kTransform) && boolPlugValue(child, "a3obIsProxy") && stringPlugValue(child, "a3obProxySelection") == selectionName) {
            return child;
        }
    }
    return MObject::kNullObj;
}

bool proxySelectionSetExists(const std::string& selectionName)
{
    MStatus status;
    MItDependencyNodes it(MFn::kSet, &status);
    if (!status) return false;
    for (; !it.isDone(); it.next()) {
        MObject set = it.thisNode(&status);
        if (status && boolPlugValue(set, "a3obIsProxySelection") && stringPlugValue(set, "a3obSelectionName") == selectionName) return true;
    }
    return false;
}

bool setContainsMesh(const MObject& set, const MObject& mesh)
{
    MStatus status;
    MFnSet setFn(set, &status);
    if (!status) return false;
    MSelectionList members;
    status = setFn.getMembers(members, true);
    if (!status) return false;
    for (unsigned int i = 0; i < members.length(); ++i) {
        MDagPath path;
        MObject component;
        if (members.getDagPath(i, path, component) && path.node() == mesh) return true;
    }
    return false;
}

bool metadataSetHasLiveMembers(const MObject& set)
{
    MStatus status;
    MFnSet setFn(set, &status);
    if (!status) return false;
    MSelectionList members;
    status = setFn.getMembers(members, true);
    return status && members.length() > 0;
}

bool isObjectBuilderMetadataSet(const MObject& set)
{
    return !stringPlugValue(set, "a3obSelectionName").empty() || !stringPlugValue(set, "a3obFlagComponent").empty() || boolPlugValue(set, "a3obIsProxySelection");
}

void validateObjectSetsForMesh(const MObject& mesh, const MString& lodName, const std::set<std::string>& proxyPlaceholders, int& warnings, int& errors)
{
    MStatus status;
    MItDependencyNodes it(MFn::kSet, &status);
    if (!status) return;
    std::set<std::string> selectionNames;
    for (; !it.isDone(); it.next()) {
        MObject set = it.thisNode(&status);
        if (!status || !isObjectBuilderMetadataSet(set)) continue;
        MFnDependencyNode setDep(set, &status);
        const MString setName = status ? setDep.name() : MString("<unknown>");
        if (!metadataSetHasLiveMembers(set)) {
            MGlobal::displayWarning(MString("a3obValidate: Object Builder set has no live members and will be ignored: ") + setName);
            ++warnings;
            continue;
        }
        if (!setContainsMesh(set, mesh)) continue;

        const std::string selectionName = stringPlugValue(set, "a3obSelectionName");
        if (!selectionName.empty()) {
            if (!selectionNames.insert(selectionName).second) {
                MGlobal::displayWarning(MString("a3obValidate: duplicate selection name on ") + lodName);
                ++warnings;
            }
            if (boolPlugValue(set, "a3obIsProxySelection")) {
                if (!isProxySelectionName(selectionName)) {
                    MGlobal::displayError(MString("a3obValidate: invalid proxy selection name on ") + lodName);
                    ++errors;
                } else if (proxyPlaceholders.find(selectionName) == proxyPlaceholders.end()) {
                    MGlobal::displayWarning(MString("a3obValidate: proxy selection has no matching placeholder on ") + lodName);
                    ++warnings;
                }
            }
        }

        const std::string flagComponent = stringPlugValue(set, "a3obFlagComponent");
        if (!flagComponent.empty() && flagComponent != "vertex" && flagComponent != "face") {
            MGlobal::displayError(MString("a3obValidate: invalid flag component type on ") + lodName);
            ++errors;
        }
        if (!flagComponent.empty() && intPlugValue(set, "a3obFlagValue", 0) == 0) {
            MGlobal::displayError(MString("a3obValidate: invalid zero flag value on ") + lodName);
            ++errors;
        }
    }
}

std::set<std::string> proxyPlaceholderSelections(const MObject& lod, const MString& lodName, int& warnings, int& errors)
{
    std::set<std::string> proxySelections;
    MStatus status;
    MFnDagNode dag(lod, &status);
    if (!status) return proxySelections;
    for (unsigned int i = 0; i < dag.childCount(); ++i) {
        MObject child = dag.child(i, &status);
        if (!status || !child.hasFn(MFn::kTransform) || !boolPlugValue(child, "a3obIsProxy")) continue;
        const std::string path = stringPlugValue(child, "a3obProxyPath");
        const int index = intPlugValue(child, "a3obProxyIndex", -1);
        const std::string selection = stringPlugValue(child, "a3obProxySelection");
        if (path.empty() || index < 0 || !isProxySelectionName(selection)) {
            MGlobal::displayError(MString("a3obValidate: invalid proxy placeholder under ") + lodName);
            ++errors;
            continue;
        }
        if (!proxySelections.insert(selection).second) {
            MGlobal::displayWarning(MString("a3obValidate: duplicate proxy placeholder under ") + lodName);
            ++warnings;
        }
        if (!proxySelectionSetExists(selection)) {
            MGlobal::displayWarning(MString("a3obValidate: proxy placeholder has no matching selection set under ") + lodName);
            ++warnings;
        }
    }
    return proxySelections;
}

bool polygonHasRepeatedVertices(const MIntArray& vertices)
{
    std::set<int> seen;
    for (unsigned int i = 0; i < vertices.length(); ++i) {
        if (!seen.insert(vertices[i]).second) return true;
    }
    return false;
}

bool polygonHasNearZeroArea(const MPointArray& points)
{
    if (points.length() < 3) return true;
    const MPoint& origin = points[0];
    double area = 0.0;
    for (unsigned int i = 1; i + 1 < points.length(); ++i) {
        const MVector a = points[i] - origin;
        const MVector b = points[i + 1] - origin;
        area += (a ^ b).length() * 0.5;
    }
    return area < 1.0e-10;
}

MStatus createProxySelectionSet(const MString& selectionName)
{
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    MSelectionList members;
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MDagPath path;
        MObject component;
        if (selection.getDagPath(i, path, component) && path.node().hasFn(MFn::kMesh) && !component.isNull()) {
            members.add(path, component);
        }
    }
    if (members.length() == 0) return MS::kSuccess;

    MStatus status;
    MFnSet setFn;
    MObject set = setFn.create(members, MFnSet::kNone, &status);
    if (!status) return status;
    MString setName = "a3ob_";
    setName += selectionName;
    setName.substitute(":", "_");
    setName.substitute("/", "_");
    setName.substitute("\\", "_");
    setName.substitute(".", "_");
    setFn.setName(setName, false, &status);
    if (!status) return status;
    status = setStringAttribute(set, "a3obSelectionName", "a3sn", selectionName);
    if (!status) return status;
    status = setBoolAttribute(set, "a3obIsProxySelection", "a3ips", true);
    if (!status) return status;
    return markTechnicalSet(set);
}

MString repeatedMassValues(int count, double value)
{
    MString result;
    for (int i = 0; i < count; ++i) {
        if (i != 0) result += ";";
        result += value;
    }
    return result;
}

std::vector<double> massValuesForLOD(const MObject& transform, double defaultValue)
{
    const int count = vertexCountForLOD(transform);
    std::vector<double> values(static_cast<std::size_t>(std::max(count, 0)), defaultValue);
    const std::vector<std::string> existing = splitSemicolon(stringPlugValue(transform, "a3obMassValues"));
    for (std::size_t i = 0; i < existing.size() && i < values.size(); ++i) {
        values[i] = std::stod(existing[i]);
    }
    return values;
}

MString massValuesString(const std::vector<double>& values)
{
    MString result;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) result += ";";
        result += values[i];
    }
    return result;
}

MStatus selectedComponents(MSelectionList& members, MObject& lod)
{
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MDagPath path;
        MObject component;
        if (!selection.getDagPath(i, path, component) || component.isNull()) continue;
        MObject candidate = lodTransformForPath(path);
        if (candidate.isNull()) continue;
        if (lod.isNull()) lod = candidate;
        members.add(path, component);
    }
    return members.length() > 0 ? MS::kSuccess : MS::kFailure;
}

MStatus setSelectedMassValues(MObject lod, double value)
{
    MSelectionList members;
    MObject selectedLod = MObject::kNullObj;
    if (!selectedComponents(members, selectedLod)) return MS::kFailure;
    if (lod.isNull()) lod = selectedLod;

    std::vector<double> masses = massValuesForLOD(lod, 0.0);
    for (unsigned int i = 0; i < members.length(); ++i) {
        MDagPath path;
        MObject component;
        if (!members.getDagPath(i, path, component) || !component.hasFn(MFn::kMeshVertComponent)) continue;
        MFnSingleIndexedComponent componentFn(component);
        MIntArray elements;
        componentFn.getElements(elements);
        for (unsigned int j = 0; j < elements.length(); ++j) {
            const int index = elements[j];
            if (index >= 0 && static_cast<std::size_t>(index) < masses.size()) masses[static_cast<std::size_t>(index)] = value;
        }
    }

    MStatus status = setBoolAttribute(lod, "a3obHasMass", "a3mass", true);
    if (!status) return status;
    return setStringAttribute(lod, "a3obMassValues", "a3mv", massValuesString(masses));
}

MStatus createMetadataSet(const MString& setName, const char* component, int value)
{
    MSelectionList members;
    MObject lod;
    MStatus status = selectedComponents(members, lod);
    if (!status) return status;
    MFnSet setFn;
    MObject set = setFn.create(members, MFnSet::kNone, &status);
    if (!status) return status;
    setFn.setName(setName, false, &status);
    if (!status) return status;
    status = setStringAttribute(set, "a3obSelectionName", "a3sn", setName);
    if (!status) return status;
    status = setStringAttribute(set, "a3obFlagComponent", "a3fc", component);
    if (!status) return status;
    status = setIntAttribute(set, "a3obFlagValue", "a3fv", value);
    if (!status) return status;
    return markTechnicalSet(set);
}

struct MeshTarget
{
    MDagPath meshPath;
    MObject lod;
};

std::string dagNodeName(const MObject& node)
{
    MStatus status;
    MFnDependencyNode dep(node, &status);
    return status ? dep.name().asChar() : std::string();
}

bool sameNode(const MObject& a, const MObject& b)
{
    return !a.isNull() && !b.isNull() && a == b;
}

void addMeshTarget(const MDagPath& meshPath, const MObject& lod, std::vector<MeshTarget>& targets)
{
    if (meshPath.isValid() && meshPath.node().hasFn(MFn::kMesh)) {
        for (const MeshTarget& target : targets) {
            if (target.meshPath.node() == meshPath.node() && (target.lod == lod || sameNode(target.lod, lod))) return;
        }
        targets.push_back({meshPath, lod});
    }
}

void addChildMeshTargets(const MObject& lod, std::vector<MeshTarget>& targets)
{
    MStatus status;
    MFnDagNode dag(lod, &status);
    if (!status) return;
    for (unsigned int i = 0; i < dag.childCount(); ++i) {
        MObject child = dag.child(i, &status);
        if (!status) continue;
        if (child.hasFn(MFn::kMesh)) {
            MDagPath path;
            MFnDagNode childDag(child, &status);
            if (status && childDag.getPath(path)) addMeshTarget(path, lod, targets);
        } else if (child.hasFn(MFn::kTransform)) {
            MObject mesh = firstMeshChild(child);
            if (!mesh.isNull()) {
                MFnDagNode meshDag(mesh, &status);
                MDagPath path;
                if (status && meshDag.getPath(path)) addMeshTarget(path, lod, targets);
            }
        }
    }
}

std::vector<MeshTarget> selectedMeshTargets()
{
    std::vector<MeshTarget> targets;
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MDagPath path;
        MObject component;
        if (!selection.getDagPath(i, path, component)) continue;
        MObject node = path.node();
        if (node.hasFn(MFn::kMesh)) {
            MObject lod = lodTransformForPath(path);
            addMeshTarget(path, lod, targets);
            continue;
        }
        if (node.hasFn(MFn::kTransform) && boolPlugValue(node, "a3obIsLOD")) {
            addChildMeshTargets(node, targets);
            continue;
        }
        if (node.hasFn(MFn::kTransform)) {
            MObject mesh = firstMeshChild(node);
            if (!mesh.isNull()) {
                MFnDagNode meshDag(mesh);
                MDagPath meshPath;
                if (meshDag.getPath(meshPath)) addMeshTarget(meshPath, lodTransformForPath(meshPath), targets);
            }
        }
    }
    return targets;
}

using EdgeKey = std::pair<int, int>;

EdgeKey edgeKey(int a, int b)
{
    return a < b ? EdgeKey(a, b) : EdgeKey(b, a);
}

struct FaceIsland
{
    std::set<int> faces;
    std::set<int> vertices;
    bool closed = true;
};

std::vector<FaceIsland> closedFaceIslands(MFnMesh& meshFn)
{
    MStatus status;
    MItMeshPolygon it(meshFn.object(), &status);
    std::map<EdgeKey, std::vector<int>> edgeFaces;
    std::vector<std::vector<EdgeKey>> faceEdges(static_cast<std::size_t>(meshFn.numPolygons()));
    for (; status && !it.isDone(); it.next()) {
        MIntArray vertices;
        it.getVertices(vertices);
        const int faceIndex = it.index();
        for (unsigned int i = 0; i < vertices.length(); ++i) {
            const int a = vertices[i];
            const int b = vertices[(i + 1) % vertices.length()];
            EdgeKey key = edgeKey(a, b);
            edgeFaces[key].push_back(faceIndex);
            faceEdges[static_cast<std::size_t>(faceIndex)].push_back(key);
        }
    }

    std::vector<std::vector<int>> adjacency(static_cast<std::size_t>(meshFn.numPolygons()));
    for (const auto& [key, faces] : edgeFaces) {
        if (faces.size() == 2) {
            adjacency[static_cast<std::size_t>(faces[0])].push_back(faces[1]);
            adjacency[static_cast<std::size_t>(faces[1])].push_back(faces[0]);
        }
    }

    std::vector<bool> visited(static_cast<std::size_t>(meshFn.numPolygons()), false);
    std::vector<FaceIsland> islands;
    for (int start = 0; start < meshFn.numPolygons(); ++start) {
        if (visited[static_cast<std::size_t>(start)]) continue;
        FaceIsland island;
        std::queue<int> queue;
        queue.push(start);
        visited[static_cast<std::size_t>(start)] = true;
        while (!queue.empty()) {
            const int face = queue.front();
            queue.pop();
            island.faces.insert(face);
            for (const EdgeKey& key : faceEdges[static_cast<std::size_t>(face)]) {
                island.vertices.insert(key.first);
                island.vertices.insert(key.second);
            }
            for (const int next : adjacency[static_cast<std::size_t>(face)]) {
                if (!visited[static_cast<std::size_t>(next)]) {
                    visited[static_cast<std::size_t>(next)] = true;
                    queue.push(next);
                }
            }
        }
        for (const int face : island.faces) {
            for (const EdgeKey& key : faceEdges[static_cast<std::size_t>(face)]) {
                int count = 0;
                for (const int edgeFace : edgeFaces[key]) {
                    if (island.faces.count(edgeFace)) ++count;
                }
                if (count != 2) island.closed = false;
            }
        }
        islands.push_back(std::move(island));
    }
    return islands;
}

bool componentSetBelongsToTarget(const MObject& set, const MObject& lod, const MDagPath& meshPath)
{
    MStatus status;
    MFnSet setFn(set, &status);
    if (!status) return false;
    MSelectionList members;
    if (!setFn.getMembers(members, true)) return false;
    for (unsigned int i = 0; i < members.length(); ++i) {
        MDagPath path;
        MObject component;
        if (!members.getDagPath(i, path, component)) continue;
        if (!lod.isNull() && sameNode(lodTransformForPath(path), lod)) return true;
        if (lod.isNull() && path.node() == meshPath.node()) return true;
    }
    return false;
}

void deleteExistingComponentSets(const MObject& lod, const MDagPath& meshPath)
{
    MStatus status;
    MObjectArray toDelete;
    MItDependencyNodes it(MFn::kSet, &status);
    for (; status && !it.isDone(); it.next()) {
        MObject set = it.thisNode(&status);
        if (!status) continue;
        const std::string selectionName = stringPlugValue(set, "a3obSelectionName");
        if (isComponentSelectionName(selectionName) && componentSetBelongsToTarget(set, lod, meshPath)) toDelete.append(set);
    }
    for (unsigned int i = 0; i < toDelete.length(); ++i) {
        MFnDependencyNode dep(toDelete[i], &status);
        if (status) MGlobal::deleteNode(toDelete[i]);
    }
}

MStatus createComponentSet(const MDagPath& meshPath, int componentIndex, const std::set<int>& vertices)
{
    MStatus status;
    MFnSingleIndexedComponent componentFn;
    MObject component = componentFn.create(MFn::kMeshVertComponent, &status);
    if (!status) return status;
    MIntArray elements;
    for (const int vertex : vertices) elements.append(vertex);
    status = componentFn.addElements(elements);
    if (!status) return status;
    MSelectionList members;
    members.add(meshPath, component);
    MFnSet setFn;
    MObject set = setFn.create(members, MFnSet::kNone, &status);
    if (!status) return status;
    MString componentName;
    componentName += "Component";
    if (componentIndex < 10) componentName += "0";
    componentName += componentIndex;
    MString setName = "a3ob_";
    setName += componentName;
    setFn.setName(setName, false, &status);
    if (!status) return status;
    return setStringAttribute(set, "a3obSelectionName", "a3sn", componentName);
}

MObject createMaterialNodes(const MString& texture, const MString& material, MStatus& status)
{
    MFnLambertShader shaderFn;
    MObject shader = shaderFn.create(true, &status);
    if (!status) return MObject::kNullObj;
    shaderFn.setName("a3ob_material#", false, &status);
    if (!status) return MObject::kNullObj;

    MFnSet shadingGroupFn;
    MObject shadingGroup = shadingGroupFn.create(MSelectionList(), MFnSet::kRenderableOnly, &status);
    if (!status) return MObject::kNullObj;
    MString shadingGroupName = shaderFn.name();
    shadingGroupName += "SG";
    shadingGroupFn.setName(shadingGroupName, false, &status);
    if (!status) return MObject::kNullObj;
    status = setStringAttribute(shader, "a3obTexture", "a3tx", texture);
    if (!status) return MObject::kNullObj;
    status = setStringAttribute(shader, "a3obMaterial", "a3mt", material);
    if (!status) return MObject::kNullObj;
    status = setStringAttribute(shadingGroup, "a3obTexture", "a3sgtx", texture);
    if (!status) return MObject::kNullObj;
    status = setStringAttribute(shadingGroup, "a3obMaterial", "a3sgmt", material);
    if (!status) return MObject::kNullObj;
    return shadingGroup;
}

bool parseIntArg(const MArgList& args, const char* flag, int& value)
{
    for (unsigned int i = 0; i + 1 < args.length(); ++i) {
        if (args.asString(i) == flag) {
            value = args.asInt(i + 1);
            return true;
        }
    }
    return false;
}

bool parseDoubleArg(const MArgList& args, const char* flag, double& value)
{
    for (unsigned int i = 0; i + 1 < args.length(); ++i) {
        if (args.asString(i) == flag) {
            value = args.asDouble(i + 1);
            return true;
        }
    }
    return false;
}

bool parseStringArg(const MArgList& args, const char* flag, MString& value)
{
    for (unsigned int i = 0; i + 1 < args.length(); ++i) {
        if (args.asString(i) == flag) {
            value = args.asString(i + 1);
            return true;
        }
    }
    return false;
}

bool hasFlag(const MArgList& args, const char* flag)
{
    for (unsigned int i = 0; i < args.length(); ++i) {
        if (args.asString(i) == flag) return true;
    }
    return false;
}
}

void* ValidateCommand::creator()
{
    return new ValidateCommand();
}

MSyntax ValidateCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-so", "-selectionOnly");
    return syntax;
}

MStatus ValidateCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    const bool selectionOnly = argData.isFlagSet("-selectionOnly") || argData.isFlagSet("-so");
    const std::vector<MObject> lods = lodTransforms(selectionOnly);
    int warnings = 0;
    int errors = 0;

    if (lods.empty()) {
        MGlobal::displayError("a3obValidate: no LOD transforms found");
        return MS::kFailure;
    }

    std::map<double, int> signatures;
    for (const MObject& lod : lods) {
        MFnDependencyNode dep(lod);
        const MString name = dep.name();
        const double signature = doublePlugValue(lod, "a3obResolutionSignature", 0.0);
        if (++signatures[signature] > 1) {
            MGlobal::displayWarning(MString("a3obValidate: duplicate LOD resolution signature on ") + name);
            ++warnings;
        }

        const MObject mesh = firstMeshChild(lod);
        const int sourceVertexCount = intPlugValue(lod, "a3obSourceVertexCount", 0);
        const int sourceFaceCount = intPlugValue(lod, "a3obSourceFaceCount", 0);
        if (mesh.isNull() && sourceVertexCount == 0 && sourceFaceCount > 0) {
            MGlobal::displayWarning(MString("a3obValidate: LOD has source faces but no mesh/source vertices: ") + name);
            ++warnings;
        }

        const std::vector<std::string> masses = splitSemicolon(stringPlugValue(lod, "a3obMassValues"));
        if (!masses.empty() && static_cast<int>(masses.size()) != vertexCountForLOD(lod)) {
            MGlobal::displayWarning(MString("a3obValidate: mass count does not match vertex count on ") + name);
            ++warnings;
        }
        for (const std::string& mass : masses) {
            try {
                if (std::stod(mass) < 0.0) {
                    MGlobal::displayError(MString("a3obValidate: negative mass value on ") + name);
                    ++errors;
                    break;
                }
            } catch (const std::exception&) {
                MGlobal::displayError(MString("a3obValidate: invalid mass value on ") + name);
                ++errors;
                break;
            }
        }

        const std::set<std::string> proxySelections = proxyPlaceholderSelections(lod, name, warnings, errors);

        if (!mesh.isNull()) {
            MStatus status;
            MFnMesh meshFn(mesh, &status);
            if (status) {
                MDagPath meshPath;
                MFnDagNode meshDag(mesh, &status);
                if (status) meshDag.getPath(meshPath);
                MItMeshPolygon polyIt(meshPath, MObject::kNullObj, &status);
                if (status) {
                    for (; !polyIt.isDone(); polyIt.next()) {
                        if (polyIt.polygonVertexCount() < 3) {
                            MGlobal::displayError(MString("a3obValidate: face with fewer than 3 vertices on ") + name);
                            ++errors;
                            break;
                        }
                        if (polyIt.polygonVertexCount() > 4) {
                            MGlobal::displayWarning(MString("a3obValidate: N-gon face (") + polyIt.polygonVertexCount() + MString(" verts) on ") + name + MString(" — will be auto-triangulated on export"));
                            ++warnings;
                        }
                        MIntArray vertexIds;
                        if (polyIt.getVertices(vertexIds) && polygonHasRepeatedVertices(vertexIds)) {
                            MGlobal::displayError(MString("a3obValidate: face uses repeated vertices on ") + name);
                            ++errors;
                            break;
                        }
                        if (sourceFaceCount == 0) {
                            MPointArray points;
                            polyIt.getPoints(points, MSpace::kObject);
                            if (polygonHasNearZeroArea(points)) {
                                MGlobal::displayWarning(MString("a3obValidate: near-zero-area face on ") + name);
                                ++warnings;
                            }
                        }
                    }
                }

                MObjectArray shaders;
                MIntArray indices;
                if (meshFn.getConnectedShaders(0, shaders, indices)) {
                    for (unsigned int i = 0; i < shaders.length(); ++i) {
                        const std::string texture = stringPlugValue(shaders[i], "a3obTexture");
                        const std::string material = stringPlugValue(shaders[i], "a3obMaterial");
                        if (!isAscii(texture) || !isAscii(material)) {
                            MGlobal::displayWarning(MString("a3obValidate: non-ASCII texture/material path on ") + name);
                            ++warnings;
                        }
                    }
                }
                validateObjectSetsForMesh(mesh, name, proxySelections, warnings, errors);
            }
        }
    }

    MGlobal::displayInfo(MString("a3obValidate: checked LODs=") + static_cast<int>(lods.size()) + ", warnings=" + warnings + ", errors=" + errors);
    return errors == 0 ? MS::kSuccess : MS::kFailure;
}

void* SetMassCommand::creator()
{
    return new SetMassCommand();
}

MSyntax SetMassCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-v", "-value", MSyntax::kDouble);
    syntax.addFlag("-c", "-clear");
    syntax.addFlag("-sc", "-selectedComponents");
    return syntax;
}

MStatus SetMassCommand::doIt(const MArgList& args)
{
    MObject transform = selectedTransformOrNull();
    if (transform.isNull()) {
        MGlobal::displayError("a3obSetMass: select a LOD transform or mesh");
        return MS::kFailure;
    }

    MArgDatabase argData(syntax(), args);
    if (argData.isFlagSet("-clear") || argData.isFlagSet("-c")) {
        MStatus status = setBoolAttribute(transform, "a3obHasMass", "a3mass", false);
        if (!status) return status;
        status = setStringAttribute(transform, "a3obMassValues", "a3mv", "");
        if (!status) return status;
        MGlobal::displayInfo("a3obSetMass: cleared mass values");
        return MS::kSuccess;
    }

    double value = 1.0;
    if (argData.isFlagSet("-value")) {
        argData.getFlagArgument("-value", 0, value);
    } else if (argData.isFlagSet("-v")) {
        argData.getFlagArgument("-v", 0, value);
    }
    if (argData.isFlagSet("-selectedComponents") || argData.isFlagSet("-sc")) {
        MStatus status = setSelectedMassValues(transform, value);
        if (!status) {
            MGlobal::displayError("a3obSetMass: select LOD mesh vertex components");
            return MS::kFailure;
        }
        MGlobal::displayInfo("a3obSetMass: set selected vertex mass values");
        return MS::kSuccess;
    }

    const int count = vertexCountForLOD(transform);
    if (count <= 0) {
        MGlobal::displayError("a3obSetMass: selected LOD has no vertices");
        return MS::kFailure;
    }

    MStatus status = setBoolAttribute(transform, "a3obHasMass", "a3mass", true);
    if (!status) return status;
    status = setStringAttribute(transform, "a3obMassValues", "a3mv", repeatedMassValues(count, value));
    if (!status) return status;
    MGlobal::displayInfo(MString("a3obSetMass: set mass values count=") + count);
    return MS::kSuccess;
}

void* SetMaterialCommand::creator()
{
    return new SetMaterialCommand();
}

MSyntax SetMaterialCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-t", "-texture", MSyntax::kString);
    syntax.addFlag("-m", "-material", MSyntax::kString);
    return syntax;
}

MStatus SetMaterialCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MString texture;
    MString material;
    if (argData.isFlagSet("-texture")) {
        argData.getFlagArgument("-texture", 0, texture);
    } else if (argData.isFlagSet("-t")) {
        argData.getFlagArgument("-t", 0, texture);
    }
    if (argData.isFlagSet("-material")) {
        argData.getFlagArgument("-material", 0, material);
    } else if (argData.isFlagSet("-m")) {
        argData.getFlagArgument("-m", 0, material);
    }

    MSelectionList members;
    MObject lod;
    MStatus status = selectedComponents(members, lod);
    if (!status) {
        MGlobal::displayError("a3obSetMaterial: select mesh faces");
        return MS::kFailure;
    }

    MObject shadingGroup = createMaterialNodes(texture, material, status);
    if (!status) return status;
    MFnDependencyNode shadingGroupDep(shadingGroup, &status);
    if (!status) return status;
    status = MGlobal::executeCommand(MString("sets -e -forceElement ") + shadingGroupDep.name(), false, false);
    if (!status) return status;
    MGlobal::displayInfo("a3obSetMaterial: assigned material metadata");
    return MS::kSuccess;
}

void* SetFlagCommand::creator()
{
    return new SetFlagCommand();
}

MSyntax SetFlagCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-c", "-component", MSyntax::kString);
    syntax.addFlag("-v", "-value", MSyntax::kLong);
    syntax.addFlag("-n", "-name", MSyntax::kString);
    return syntax;
}

MStatus SetFlagCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MString component = "face";
    if (argData.isFlagSet("-component")) {
        argData.getFlagArgument("-component", 0, component);
    } else if (argData.isFlagSet("-c")) {
        argData.getFlagArgument("-c", 0, component);
    }
    int value = 0;
    if (argData.isFlagSet("-value")) {
        argData.getFlagArgument("-value", 0, value);
    } else if (argData.isFlagSet("-v")) {
        argData.getFlagArgument("-v", 0, value);
    }
    MString name = "a3ob_flag#";
    if (argData.isFlagSet("-name")) {
        argData.getFlagArgument("-name", 0, name);
    } else if (argData.isFlagSet("-n")) {
        argData.getFlagArgument("-n", 0, name);
    }
    if (component != "vertex" && component != "face") {
        MGlobal::displayError("a3obSetFlag: -component must be vertex or face");
        return MS::kFailure;
    }
    if (value == 0) {
        MGlobal::displayError("a3obSetFlag: -value must be non-zero");
        return MS::kFailure;
    }

    MStatus status = createMetadataSet(name, component.asChar(), value);
    if (!status) {
        MGlobal::displayError("a3obSetFlag: select mesh vertex or face components");
        return MS::kFailure;
    }
    MGlobal::displayInfo("a3obSetFlag: created flag set");
    return MS::kSuccess;
}

void* FindComponentsCommand::creator()
{
    return new FindComponentsCommand();
}

MSyntax FindComponentsCommand::syntax()
{
    return MSyntax();
}

MStatus FindComponentsCommand::doIt(const MArgList&)
{
    const std::vector<MeshTarget> targets = selectedMeshTargets();
    if (targets.empty()) {
        MGlobal::displayError("a3obFindComponents: select an Object Builder LOD, mesh, or mesh component");
        return MS::kFailure;
    }

    std::set<std::string> cleanedTargets;
    int createdTotal = 0;
    int skipped = 0;
    for (const MeshTarget& target : targets) {
        std::string targetName = dagNodeName(target.lod);
        if (targetName.empty()) targetName = target.meshPath.fullPathName().asChar();
        if (!cleanedTargets.count(targetName)) {
            deleteExistingComponentSets(target.lod, target.meshPath);
            cleanedTargets.insert(targetName);
        }

        int createdForTarget = 0;
        MStatus status;
        MFnMesh meshFn(target.meshPath, &status);
        if (!status) continue;
        for (const FaceIsland& island : closedFaceIslands(meshFn)) {
            if (!island.closed || island.vertices.empty()) {
                ++skipped;
                continue;
            }
            status = createComponentSet(target.meshPath, createdForTarget + 1, island.vertices);
            if (!status) return status;
            ++createdForTarget;
            ++createdTotal;
        }
    }

    if (createdTotal == 0) {
        MGlobal::displayError(MString("a3obFindComponents: no closed components found, skipped=") + skipped);
        return MS::kFailure;
    }
    if (skipped > 0) {
        MGlobal::displayWarning(MString("a3obFindComponents: created components=") + createdTotal + ", skipped open/non-manifold islands=" + skipped);
    } else {
        MGlobal::displayInfo(MString("a3obFindComponents: created components=") + createdTotal);
    }
    return MS::kSuccess;
}

void* CreateLODCommand::creator()
{
    return new CreateLODCommand();
}

MSyntax CreateLODCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-lt", "-lodType", MSyntax::kLong);
    syntax.addFlag("-r", "-resolution", MSyntax::kLong);
    syntax.addFlag("-n", "-name", MSyntax::kString);
    return syntax;
}

MStatus CreateLODCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    int lodType = 0;
    int resolution = 0;
    if (argData.isFlagSet("-lodType")) {
        argData.getFlagArgument("-lodType", 0, lodType);
    } else if (argData.isFlagSet("-lt")) {
        argData.getFlagArgument("-lt", 0, lodType);
    }
    if (argData.isFlagSet("-resolution")) {
        argData.getFlagArgument("-resolution", 0, resolution);
    } else if (argData.isFlagSet("-r")) {
        argData.getFlagArgument("-r", 0, resolution);
    }

    MString name;
    if (argData.isFlagSet("-name")) {
        argData.getFlagArgument("-name", 0, name);
    } else if (argData.isFlagSet("-n")) {
        argData.getFlagArgument("-n", 0, name);
    }

    MStatus status;
    MObject transform = selectedTransformOrNull();
    if (transform.isNull()) {
        MFnTransform transformFn;
        transform = transformFn.create(MObject::kNullObj, &status);
        if (!status) return status;
        transformFn.setName(name.length() > 0 ? name : "a3ob_LOD#", false, &status);
        if (!status) return status;
    }

    status = setLODAttributes(transform, lodType, resolution);
    if (!status) return status;
    MFnDependencyNode dep(transform, &status);
    if (status) {
        setResult(dep.name());
    }
    MGlobal::displayInfo(MString("a3obCreateLOD: marked LOD signature=") + a3ob::p3d::LodResolution::encode(lodType, resolution));
    return MS::kSuccess;
}

MObject selectedDependencyNodeOrNull()
{
    MSelectionList selection;
    MGlobal::getActiveSelectionList(selection);
    for (unsigned int i = 0; i < selection.length(); ++i) {
        MObject node;
        if (selection.getDependNode(i, node) && !node.isNull()) return node;
        MDagPath path;
        MObject component;
        if (selection.getDagPath(i, path, component)) return path.node();
    }
    return MObject::kNullObj;
}

MStatus updateProxySelectionSet(MObject set, const MString& path, int index)
{
    const MString selectionName = proxySelectionName(path, index);
    MStatus status = setStringAttribute(set, "a3obSelectionName", "a3sn", selectionName);
    if (!status) return status;
    status = setBoolAttribute(set, "a3obIsProxySelection", "a3ips", true);
    if (!status) return status;
    status = markTechnicalSet(set);
    if (!status) return status;
    MFnDependencyNode dep(set, &status);
    if (!status) return status;
    MString setName = "a3ob_";
    setName += selectionName;
    setName.substitute(":", "_");
    setName.substitute("/", "_");
    setName.substitute("\\", "_");
    setName.substitute(".", "_");
    dep.setName(setName, false, &status);
    return status;
}

MStatus updateProxyPlaceholder(MObject proxy, const MString& path, int index)
{
    const MString selectionName = proxySelectionName(path, index);
    MStatus status = setBoolAttribute(proxy, "a3obIsProxy", "a3px", true);
    if (!status) return status;
    status = setStringAttribute(proxy, "a3obProxyPath", "a3pp", path);
    if (!status) return status;
    status = setIntAttribute(proxy, "a3obProxyIndex", "a3pi", index);
    if (!status) return status;
    return setStringAttribute(proxy, "a3obProxySelection", "a3ps", selectionName);
}

void* UpdateProxyCommand::creator()
{
    return new UpdateProxyCommand();
}

MSyntax UpdateProxyCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-p", "-path", MSyntax::kString);
    syntax.addFlag("-i", "-index", MSyntax::kLong);
    return syntax;
}

MStatus UpdateProxyCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MString path;
    if (argData.isFlagSet("-path")) {
        argData.getFlagArgument("-path", 0, path);
    } else if (argData.isFlagSet("-p")) {
        argData.getFlagArgument("-p", 0, path);
    }
    if (path.length() == 0) {
        MGlobal::displayError("a3obUpdateProxy: -path is required");
        return MS::kFailure;
    }
    int index = 1;
    if (argData.isFlagSet("-index")) {
        argData.getFlagArgument("-index", 0, index);
    } else if (argData.isFlagSet("-i")) {
        argData.getFlagArgument("-i", 0, index);
    }

    MObject node = selectedDependencyNodeOrNull();
    if (node.isNull()) {
        MGlobal::displayError("a3obUpdateProxy: select a proxy placeholder or proxy selection set");
        return MS::kFailure;
    }
    if (boolPlugValue(node, "a3obIsProxy")) {
        return updateProxyPlaceholder(node, path, index);
    }
    if (boolPlugValue(node, "a3obIsProxySelection") || node.hasFn(MFn::kSet)) {
        return updateProxySelectionSet(node, path, index);
    }
    MGlobal::displayError("a3obUpdateProxy: selected node is not a proxy placeholder or proxy selection set");
    return MS::kFailure;
}

void* ProxyCommand::creator()
{
    return new ProxyCommand();
}

MSyntax ProxyCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-p", "-path", MSyntax::kString);
    syntax.addFlag("-i", "-index", MSyntax::kLong);
    syntax.addFlag("-u", "-update");
    syntax.addFlag("-fs", "-fromSelection");
    syntax.addFlag("-ss", "-selectionSet");
    return syntax;
}

MStatus namedPropertyResult(const MObject& lod)
{
    MStringArray output;
    for (const auto& [key, value] : splitProperties(stringPlugValue(lod, "a3obProperties"))) {
        MString item = key.c_str();
        item += "=";
        item += value.c_str();
        output.append(item);
    }
    MPxCommand::setResult(output);
    return MS::kSuccess;
}

void* NamedPropertyCommand::creator()
{
    return new NamedPropertyCommand();
}

MSyntax NamedPropertyCommand::syntax()
{
    MSyntax syntax;
    syntax.addFlag("-l", "-list");
    syntax.addFlag("-s", "-set", MSyntax::kString, MSyntax::kString);
    syntax.addFlag("-r", "-remove", MSyntax::kString);
    return syntax;
}

MStatus NamedPropertyCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MObject lod = selectedLODOrNull();
    if (lod.isNull()) {
        MGlobal::displayError("a3obNamedProperty: select a LOD transform, LOD mesh, or mesh components");
        return MS::kFailure;
    }

    if (argData.isFlagSet("-list") || argData.isFlagSet("-l")) {
        return namedPropertyResult(lod);
    }

    std::vector<std::pair<std::string, std::string>> properties = splitProperties(stringPlugValue(lod, "a3obProperties"));
    if (argData.isFlagSet("-set") || argData.isFlagSet("-s")) {
        MString key;
        MString value;
        if (argData.isFlagSet("-set")) {
            argData.getFlagArgument("-set", 0, key);
            argData.getFlagArgument("-set", 1, value);
        } else {
            argData.getFlagArgument("-s", 0, key);
            argData.getFlagArgument("-s", 1, value);
        }
        if (key.length() == 0) {
            MGlobal::displayError("a3obNamedProperty: property key cannot be empty");
            return MS::kFailure;
        }
        const std::string keyString = key.asChar();
        properties.erase(std::remove_if(properties.begin(), properties.end(), [&](const auto& item) { return item.first == keyString; }), properties.end());
        properties.emplace_back(keyString, value.asChar());
        const MStatus status = setStringAttribute(lod, "a3obProperties", "a3prop", propertiesString(properties));
        if (!status) return status;
        return namedPropertyResult(lod);
    }

    if (argData.isFlagSet("-remove") || argData.isFlagSet("-r")) {
        MString key;
        if (argData.isFlagSet("-remove")) {
            argData.getFlagArgument("-remove", 0, key);
        } else {
            argData.getFlagArgument("-r", 0, key);
        }
        const std::string keyString = key.asChar();
        properties.erase(std::remove_if(properties.begin(), properties.end(), [&](const auto& item) { return item.first == keyString; }), properties.end());
        const MStatus status = setStringAttribute(lod, "a3obProperties", "a3prop", propertiesString(properties));
        if (!status) return status;
        return namedPropertyResult(lod);
    }

    return namedPropertyResult(lod);
}

MStatus ProxyCommand::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    MString proxyPath;
    if (argData.isFlagSet("-path")) {
        argData.getFlagArgument("-path", 0, proxyPath);
    } else if (argData.isFlagSet("-p")) {
        argData.getFlagArgument("-p", 0, proxyPath);
    }
    if (proxyPath.length() == 0) {
        MGlobal::displayError("a3obProxy: -path is required");
        return MS::kFailure;
    }
    int proxyIndex = 1;
    if (argData.isFlagSet("-index")) {
        argData.getFlagArgument("-index", 0, proxyIndex);
    } else if (argData.isFlagSet("-i")) {
        argData.getFlagArgument("-i", 0, proxyIndex);
    }

    MObject lod = selectedLODOrNull();
    if (lod.isNull()) {
        MGlobal::displayError("a3obProxy: select a LOD transform, LOD mesh, or mesh components");
        return MS::kFailure;
    }

    const bool update = argData.isFlagSet("-update") || argData.isFlagSet("-u");
    const bool fromSelection = argData.isFlagSet("-fromSelection") || argData.isFlagSet("-fs") || argData.isFlagSet("-selectionSet") || argData.isFlagSet("-ss");
    MString selectionName = proxySelectionName(proxyPath, proxyIndex);
    const std::string selectionNameString = selectionName.asChar();

    MObject proxy = update ? proxyPlaceholder(lod, selectionNameString) : MObject::kNullObj;
    MStatus status;
    MFnTransform proxyFn;
    if (proxy.isNull()) {
        proxy = proxyFn.create(lod, &status);
        if (!status) return status;
        proxyFn.setName("a3ob_proxy#", false, &status);
        if (!status) return status;
    }

    status = setBoolAttribute(proxy, "a3obIsProxy", "a3px", true);
    if (!status) return status;
    status = setStringAttribute(proxy, "a3obProxyPath", "a3pp", proxyPath);
    if (!status) return status;
    status = setIntAttribute(proxy, "a3obProxyIndex", "a3pi", proxyIndex);
    if (!status) return status;
    status = setStringAttribute(proxy, "a3obProxySelection", "a3ps", selectionName);
    if (!status) return status;

    if (fromSelection && !proxySelectionSetExists(selectionNameString)) {
        status = createProxySelectionSet(selectionName);
        if (!status) return status;
    }

    MGlobal::displayInfo(MString("a3obProxy: created ") + selectionName);
    return MS::kSuccess;
}
