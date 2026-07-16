"""Maya-independent file-format layer (P3D binary, model.cfg text).

Ported 1:1 from the former C++ ``src/formats/`` layer, using the Blender add-on's
``io/data_p3d.py`` as a cross-reference. Nothing here imports ``maya`` — the modules
run under a plain system Python interpreter so the format can be unit-tested cheaply.
"""
