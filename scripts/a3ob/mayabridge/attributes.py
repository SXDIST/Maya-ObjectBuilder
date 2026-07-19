"""Object Builder metadata attribute schema and helpers (OpenMaya 2.0).

Every piece of Object Builder state is stored as a dynamic attribute on a Maya node.
The long+short names below are the on-scene data contract shared by import, export,
the ``a3ob*`` commands and the Python UI; they are copied verbatim from the former
C++ layer so existing ``.ma`` scenes keep round-tripping.

Ported from the duplicated attribute helpers in ``src/commands/StubCommands.cpp`` and
``src/maya/MayaMeshImport.cpp`` — collapsed here into one place.

Known C++ inconsistency, unified here: the proxy "is proxy" flag used short name
``a3px`` in the commands but ``a3pr`` on import. We write ``a3px`` and read either
(:func:`get_bool_any`) so older imported scenes still resolve.
"""

import maya.api.OpenMaya as om

__all__ = ["A", "get_bool", "get_int", "get_double", "get_string",
           "get_bool_any", "set_bool", "set_int", "set_double", "set_string",
           "mark_technical_set"]


class A:
    """Attribute (long, short) name pairs, grouped by the node they live on."""

    # LOD transform
    IS_LOD = ("a3obIsLOD", "a3lod")
    LOD_TYPE = ("a3obLodType", "a3lt")
    RESOLUTION = ("a3obResolution", "a3res")
    RESOLUTION_SIGNATURE = ("a3obResolutionSignature", "a3sig")
    SOURCE_VERTEX_COUNT = ("a3obSourceVertexCount", "a3svc")
    SOURCE_FACE_COUNT = ("a3obSourceFaceCount", "a3sfc")
    HAS_MASS = ("a3obHasMass", "a3mass")
    MASS_VALUES = ("a3obMassValues", "a3mv")
    BAKED_WEIGHTS = ("a3obBakedWeights", "a3bw")
    # The copy the last overwrite replaced. Anything that rewrites BAKED_WEIGHTS stashes the
    # old value here first: the sync-on-save otherwise replaced a good bake with a fresh
    # bind's defaults, silently and unrecoverably.
    BAKED_WEIGHTS_PREVIOUS = ("a3obBakedWeightsPrevious", "a3bwp")
    PROPERTIES = ("a3obProperties", "a3prop")

    # LOD transform, import-preserved round-trip metadata (short names verbatim
    # from src/maya/MayaMeshImport.cpp so export reads back exactly what import wrote)
    TEXTURES = ("a3obTextures", "a3tex")
    MATERIALS = ("a3obMaterials", "a3mat")
    SELECTIONS = ("a3obSelections", "a3sel")
    PROXIES = ("a3obProxies", "a3prx")
    HAS_SHARP_EDGES = ("a3obHasSharpEdges", "a3sharp")
    SHARP_EDGES = ("a3obSharpEdges", "a3se")
    UVSET_TAGG_COUNT = ("a3obUVSetTaggCount", "a3uvtc")
    UVSET_TAGGS = ("a3obUVSetTaggs", "a3uvt")
    SOURCE_VERTICES = ("a3obSourceVertices", "a3sv")
    VERTEX_SOURCE_INDICES = ("a3obVertexSourceIndices", "a3vsi")

    # proxy transform
    IS_PROXY = ("a3obIsProxy", "a3px")
    IS_PROXY_ALT_SHORT = "a3pr"  # legacy short name written by the C++ importer
    PROXY_PATH = ("a3obProxyPath", "a3pp")
    PROXY_INDEX = ("a3obProxyIndex", "a3pi")
    PROXY_SELECTION = ("a3obProxySelection", "a3ps")

    # objectSet
    SELECTION_NAME = ("a3obSelectionName", "a3sn")
    FLAG_COMPONENT = ("a3obFlagComponent", "a3fc")
    FLAG_VALUE = ("a3obFlagValue", "a3fv")
    IS_PROXY_SELECTION = ("a3obIsProxySelection", "a3ips")
    TECHNICAL_SET = ("a3obTechnicalSet", "a3ts")

    # shader
    TEXTURE = ("a3obTexture", "a3tx")
    MATERIAL = ("a3obMaterial", "a3mt")

    # shading group
    SG_TEXTURE = ("a3obTexture", "a3sgtx")
    SG_MATERIAL = ("a3obMaterial", "a3sgmt")

    # joint
    SKELETON_NAME = ("a3obSkeletonName", "a3sk")


# -- readers -------------------------------------------------------------------
def _find_plug(node, long_name):
    dep = om.MFnDependencyNode(node)
    if not dep.hasAttribute(long_name):
        return None
    return dep.findPlug(long_name, True)


def get_bool(node, attr, default=False):
    plug = _find_plug(node, attr[0])
    return plug.asBool() if plug is not None else default


def get_int(node, attr, default=0):
    plug = _find_plug(node, attr[0])
    return plug.asInt() if plug is not None else default


def get_double(node, attr, default=0.0):
    plug = _find_plug(node, attr[0])
    return plug.asDouble() if plug is not None else default


def get_string(node, attr, default=""):
    plug = _find_plug(node, attr[0])
    return plug.asString() if plug is not None else default


def get_bool_any(node, attr, alt_short, default=False):
    """Read a bool by its long name, falling back to a legacy short name."""
    dep = om.MFnDependencyNode(node)
    if dep.hasAttribute(attr[0]):
        return dep.findPlug(attr[0], True).asBool()
    if dep.hasAttribute(alt_short):
        return dep.findPlug(alt_short, True).asBool()
    return default


# -- writers (create-if-missing, keyable to match the C++ helpers) -------------
#
# Every setter takes an optional ``modifier`` (an MDGModifier). Pass one from an undoable
# MPxCommand and the write lands in Maya's undo queue; omit it and the value is set straight
# on the plug as before. Plug setters bypass undo entirely, which is why Ctrl+Z used to do
# nothing after a3ob* commands.
#
# The modifier's doIt() runs immediately rather than being deferred: the attribute has to
# exist before its value can be queued, and the command's undoIt() replays the whole
# modifier in reverse regardless.
def _ensure_numeric(node, attr, data_type, modifier=None):
    dep = om.MFnDependencyNode(node)
    if dep.hasAttribute(attr[0]):
        return dep.findPlug(attr[0], True)
    nattr = om.MFnNumericAttribute()
    obj = nattr.create(attr[0], attr[1], data_type)
    nattr.keyable = True
    if modifier is not None:
        modifier.addAttribute(node, obj)
        modifier.doIt()
    else:
        dep.addAttribute(obj)
    return dep.findPlug(attr[0], True)


def set_bool(node, attr, value, modifier=None):
    plug = _ensure_numeric(node, attr, om.MFnNumericData.kBoolean, modifier)
    if modifier is not None:
        modifier.newPlugValueBool(plug, bool(value))
        modifier.doIt()
    else:
        plug.setBool(bool(value))


def set_int(node, attr, value, modifier=None):
    plug = _ensure_numeric(node, attr, om.MFnNumericData.kInt, modifier)
    if modifier is not None:
        modifier.newPlugValueInt(plug, int(value))
        modifier.doIt()
    else:
        plug.setInt(int(value))


def set_double(node, attr, value, modifier=None):
    plug = _ensure_numeric(node, attr, om.MFnNumericData.kDouble, modifier)
    if modifier is not None:
        modifier.newPlugValueDouble(plug, float(value))
        modifier.doIt()
    else:
        plug.setDouble(float(value))


def set_string(node, attr, value, modifier=None):
    dep = om.MFnDependencyNode(node)
    if dep.hasAttribute(attr[0]):
        plug = dep.findPlug(attr[0], True)
    else:
        string_data = om.MFnStringData()
        default = string_data.create(value or "")
        tattr = om.MFnTypedAttribute()
        obj = tattr.create(attr[0], attr[1], om.MFnData.kString, default)
        tattr.keyable = True
        if modifier is not None:
            modifier.addAttribute(node, obj)
            modifier.doIt()
        else:
            dep.addAttribute(obj)
        plug = dep.findPlug(attr[0], True)
    if modifier is not None:
        modifier.newPlugValueString(plug, value or "")
        modifier.doIt()
    else:
        plug.setString(value or "")


def mark_technical_set(node):
    """Flag an objectSet as internal Object Builder bookkeeping and hide it."""
    set_bool(node, A.TECHNICAL_SET, True)
    dep = om.MFnDependencyNode(node)
    if dep.hasAttribute("hiddenInOutliner"):
        dep.findPlug("hiddenInOutliner", True).setBool(True)
