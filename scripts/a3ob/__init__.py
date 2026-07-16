"""MayaObjectBuilder — pure-Python port of the DayZ/Object Builder P3D toolkit.

This package replaces the former C++ plugin (``MayaObjectBuilder.mll``). It is split
into two layers:

* ``a3ob.formats`` — Maya-independent binary/text format code (P3D, model.cfg).
  Importable and testable with a plain system Python interpreter, no Maya required.
* ``a3ob.mayabridge`` — the Maya glue (``maya.api.OpenMaya``): mesh import/export,
  the ``Arma P3D`` file translator, the ``a3ob*`` commands and the attribute schema.

The Qt/menu UI still lives in ``scripts/objectBuilderMenu.py`` and drives this package
through the registered ``a3ob*`` commands and the file translator.
"""

__version__ = "0.1.0"
