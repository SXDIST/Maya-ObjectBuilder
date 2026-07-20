"""Serialization primitives for the ``a3ob*`` string attributes stored on Maya nodes.

Import writes these strings onto the LOD transform (source vertices, the vertex remap, the
UVSet TAGGs, named properties, mass values) and export parses them back out — so the two
sides have to agree character for character or the bytes written to the ``.p3d`` move. That
made three copies of the same one-line split, one of them inline, a genuine hazard.

This module is the single definition, and it lives in ``formats/`` on purpose: that is the
Maya-free layer both the command helpers and the export parser may import without either
depending on the other, and it is reachable from the plain-interpreter ``tests/python``
suite.
"""


def split_semicolon(value):
    """The non-empty ``;``-separated fields of ``value``.

    Empty fields are dropped rather than yielded as ``""`` — the serializers append a
    trailing separator, so a value always ends in one and a naive ``split`` would hand back
    a phantom final field for every stored attribute.
    """
    return [part for part in value.split(";") if part]


__all__ = ["split_semicolon"]
