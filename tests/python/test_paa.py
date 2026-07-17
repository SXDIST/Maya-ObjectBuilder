"""Pure-Python PAA decoder test — decodes the sample .paa in tests/paa/ when present.

The .paa fixtures are game assets and are gitignored, so this skips cleanly in CI where
they are absent; it validates the DXT1/DXT5 + LZO decoder locally.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

from a3ob.formats.paa import PAA_File, decode_largest_mip  # noqa: E402


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    paa_dir = os.path.join(here, "..", "paa")
    files = sorted(glob.glob(os.path.join(paa_dir, "*.paa")))
    if not files:
        print("SKIP test_paa: no .paa fixtures in tests/paa/")
        return

    for path in files:
        paa = PAA_File.read_file(path)
        width, height, (red, green, blue, alpha) = decode_largest_mip(path)
        assert width > 0 and height > 0, "bad dimensions for %s" % path
        assert len(red) == width * height, "channel size mismatch for %s" % path
        assert len(alpha) == width * height, "alpha size mismatch for %s" % path
        for channel in (red, green, blue, alpha):
            assert 0.0 <= channel[0] <= 1.0, "channel out of [0,1] for %s" % path
        print("OK %-34s type=%-5s %dx%d" % (os.path.basename(path), paa.type.name, width, height))

    print("PASS test_paa (%d fixtures)" % len(files))


if __name__ == "__main__":
    main()
