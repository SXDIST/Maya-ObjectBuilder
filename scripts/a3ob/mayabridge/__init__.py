"""Maya glue layer: mesh conversion, file translator, a3ob* commands, attribute schema.

Everything here depends on ``maya.api.OpenMaya`` / ``maya.cmds`` and only loads inside
Maya (or ``mayapy``). The pure format code lives in ``a3ob.formats`` instead.
"""
