"""User-facing PAA texture settings, backed by Maya optionVars."""

import maya.cmds as cmds

TEXTURE_ROOT_VAR = "MayaObjectBuilder_texture_root"
ALPHA_VAR = "MayaObjectBuilder_paa_alpha_transparency"


def texture_root():
    if cmds.optionVar(exists=TEXTURE_ROOT_VAR):
        return cmds.optionVar(query=TEXTURE_ROOT_VAR) or ""
    return ""


def set_texture_root(path):
    cmds.optionVar(stringValue=(TEXTURE_ROOT_VAR, path or ""))


def alpha_transparency_enabled():
    # Off by default: a DayZ _ca alpha is often a data channel (chainmail, spec) rather than
    # a geometry cut-out, and wiring it makes solid armour see-through. Opt-in for foliage.
    return bool(cmds.optionVar(query=ALPHA_VAR)) if cmds.optionVar(exists=ALPHA_VAR) else False


def set_alpha_transparency(enabled):
    cmds.optionVar(intValue=(ALPHA_VAR, 1 if enabled else 0))
