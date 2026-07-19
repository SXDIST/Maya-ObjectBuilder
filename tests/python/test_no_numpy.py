"""The pure-Python fallbacks must actually work.

`paa.py` picks a numpy path at import time and falls back to pure Python when
numpy is missing, and `lzo1x_decompress` does the same with `python-lzo`. Maya
ships neither, so on a user's machine the fallbacks are the DEFAULT path — but on
a developer machine numpy is usually installed, so the whole suite exercises only
the fast path and the fallback can rot unnoticed.

This test blocks both modules at import time and re-imports, so the slow paths are
covered on a machine that has them.
"""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


class _Blocker:
    """Meta-path hook that makes the named top-level packages unimportable."""

    def __init__(self, *names):
        self.names = names

    def find_module(self, name, path=None):
        top = name.split(".")[0]
        return self if top in self.names else None

    def load_module(self, name):
        raise ImportError(f"{name} is blocked by test_no_numpy")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def _reimport_without(*blocked):
    blocker = _Blocker(*blocked)
    sys.meta_path.insert(0, blocker)
    try:
        for module in [m for m in sys.modules if m.split(".")[0] in blocked]:
            del sys.modules[module]
        sys.modules.pop("a3ob.formats.paa", None)
        return importlib.import_module("a3ob.formats.paa")
    finally:
        sys.meta_path.remove(blocker)


def test_paa_imports_without_numpy_or_lzo():
    paa = _reimport_without("numpy", "lzo")
    check(paa._np is None, "paa must not hold a numpy handle when numpy is unimportable")
    check(paa.dxt1_decompress is paa._dxt1_python,
          "without numpy the DXT1 entry point must be the pure-Python decoder")
    check(paa.dxt5_decompress is paa._dxt5_python,
          "without numpy the DXT5 entry point must be the pure-Python decoder")
    print("OK paa falls back to the pure-Python decoders when numpy and lzo are blocked")


def _reimport_normally():
    """Fresh import with nothing blocked. The blocked import above poisons sys.modules,
    so this has to evict it rather than trust importlib's cache."""
    sys.modules.pop("a3ob.formats.paa", None)
    return importlib.import_module("a3ob.formats.paa")


def test_pure_python_dxt_matches_numpy():
    """The fallback is only useful if it agrees with the fast path byte for byte."""
    import io

    with_numpy = _reimport_normally()
    if with_numpy._np is None:
        print("SKIP numpy absent — nothing to compare against")
        return

    # Four DXT1 blocks (8x8): two endpoints plus every interpolation index, so all
    # four colour cases and both the c0>c1 and c0<=c1 branches get exercised.
    block = bytes([0x00, 0xF8, 0x00, 0x1F, 0b00011011, 0b00011011, 0b00011011, 0b00011011])
    payload = block + bytes([0x1F, 0x00, 0xF8, 0x00, 0xE4, 0xE4, 0xE4, 0xE4]) + block * 2

    fast = with_numpy._dxt1_numpy(io.BytesIO(payload), 8, 8)

    without = _reimport_without("numpy", "lzo")
    slow = without._dxt1_python(io.BytesIO(payload), 8, 8)

    # Both return a tuple of four float channel planes (R, G, B, A).
    check(len(fast) == len(slow) == 4,
          f"both decoders must return four channel planes, got {len(fast)} and {len(slow)}")
    fast_values = [list(channel) for channel in fast]
    slow_values = [list(channel) for channel in slow]
    check(fast_values == slow_values,
          "the numpy and pure-Python DXT1 decoders disagree — a user without numpy "
          "would get different pixels than the developer who tested it. First "
          f"mismatching channel: {next((i for i, (a, b) in enumerate(zip(fast_values, slow_values)) if a != b), None)}")
    print(f"OK numpy and pure-Python DXT1 decoders agree exactly "
          f"({sum(len(c) for c in slow_values)} values)")


def main():
    test_paa_imports_without_numpy_or_lzo()
    test_pure_python_dxt_matches_numpy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
