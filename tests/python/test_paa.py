"""Pure-Python PAA decoder test — decodes the sample .paa in tests/paa/ when present.

The .paa fixtures are game assets and are gitignored, so this skips cleanly in CI where
they are absent; it validates the DXT1/DXT5 + LZO decoder locally. The in-memory
truncation cases below run unconditionally: they feed the reader synthetic headers cut
short at every fixed-count read site and assert it raises a clean ``PAA_Error`` rather
than returning garbage, looping, or blowing up with an unrelated ``ValueError`` /
``struct.error``.
"""

import glob
import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

from a3ob.formats.paa import PAA_Error, PAA_File, decode_largest_mip  # noqa: E402


# ---------------------------------------------------------------------------
# In-memory truncation cases — each proves one "read a fixed count, assume you
# got it" site raises a PAA_Error at the exact byte offset it was cut off.
# ---------------------------------------------------------------------------


def _assert_paa_error(payload, label, message_contains=None):
    try:
        PAA_File.read(BytesIO(payload))
    except PAA_Error as e:
        if message_contains and message_contains not in str(e).lower():
            raise AssertionError(
                "%s: PAA_Error raised but message %r does not mention %r"
                % (label, str(e), message_contains)
            )
        return
    except Exception as e:
        # Anything else (struct.error, ValueError from negative seek, ...) is exactly
        # the class of failure the fix is supposed to eliminate.
        raise AssertionError(
            "%s: expected PAA_Error, got %s: %s" % (label, type(e).__name__, e)
        )
    raise AssertionError(
        "%s: expected PAA_Error, reader returned successfully" % label
    )


def test_truncation_after_data_type():
    # DXT1 header, nothing else. The unfixed TAGG loop reads b"" (0 bytes) and then
    # seek(-4, 1) — which BytesIO clamps to position 0 instead of erroring — so the parse
    # then re-reads the data_type as the palette-count word and raises the misleading
    # "Indexed palettes are not supported". Fix-aware assertion checks the message.
    _assert_paa_error(b"\x01\xff", "truncation after data_type", message_contains="truncat")


def test_truncation_partial_tagg_marker():
    # DXT1 header + 3 bytes. The unfixed code seeked back 4 unconditionally, landing the
    # cursor 1 byte BEFORE the intended position, then read the palette from a misaligned
    # offset and produced the misleading "Indexed palettes are not supported" error.
    _assert_paa_error(
        b"\x01\xff\x00\x00\x00",
        "3-byte truncation at TAGG marker",
        message_contains="truncat",
    )


def test_truncation_short_tagg_name():
    # GGAT consumed, but the 4-byte TAGG name field is 2 bytes short. The unfixed code
    # accepted the short bytes as the name and then struct.error'd reading the length.
    _assert_paa_error(
        b"\x01\xff" + b"GGAT" + b"XX",
        "short TAGG name",
    )


def test_truncation_short_tagg_data():
    # TAGG declares length=100 but only 1 byte of payload follows. The unfixed code stored
    # a short bytes object as data and returned the TAGG; the parse then misaligned into
    # the mipmap section and eventually struct.error'd.
    payload = b"\x01\xff" + b"GGAT" + b"XXXX" + b"\x64\x00\x00\x00" + b"\x00"
    _assert_paa_error(payload, "short TAGG data")


def test_truncation_short_mipmap_data():
    # Mipmap declares length=100 but only 10 bytes of payload follow, then a valid (0, 0)
    # terminator. The unfixed code silently returned a PAA_File containing a corrupt mip —
    # no exception at all — which is the "returns garbage" outcome the bug report warns
    # about. Test explicitly requires the reader to reject this.
    payload = (
        b"\x01\xff"                       # DXT1
        + b"\x00\x00"                     # palette count = 0
        + b"\x04\x00" + b"\x04\x00"       # width=4, height=4
        + b"\x64\x00\x00"                 # length = 100 (3 bytes)
        + b"\x00" * 10                    # only 10 bytes of "data" (should be 100)
        + b"\x00\x00" + b"\x00\x00"       # mip terminator (0, 0)
    )
    _assert_paa_error(payload, "short mipmap data")


def test_truncation_short_mipmap_length_field():
    # Mipmap header present but only 1 of the 3 length-field bytes exists. Unfixed code
    # concatenated (short_bytes + b"\x00") and struct.error'd because the buffer was < 4.
    _assert_paa_error(
        b"\x01\xff\x00\x00\x04\x00\x04\x00\x64",
        "short mipmap length field",
    )


# ---------------------------------------------------------------------------
# Optional fixture files — only present on a dev machine with real .paa assets.
# ---------------------------------------------------------------------------


def _check_fixture_files():
    here = os.path.dirname(os.path.abspath(__file__))
    paa_dir = os.path.join(here, "..", "paa")
    files = sorted(glob.glob(os.path.join(paa_dir, "*.paa")))
    if not files:
        print("SKIP fixture decode: no .paa fixtures in tests/paa/")
        return 0

    for path in files:
        paa = PAA_File.read_file(path)
        width, height, (red, green, blue, alpha) = decode_largest_mip(path)
        assert width > 0 and height > 0, "bad dimensions for %s" % path
        assert len(red) == width * height, "channel size mismatch for %s" % path
        assert len(alpha) == width * height, "alpha size mismatch for %s" % path
        for channel in (red, green, blue, alpha):
            assert 0.0 <= channel[0] <= 1.0, "channel out of [0,1] for %s" % path
        print("OK %-34s type=%-5s %dx%d" % (os.path.basename(path), paa.type.name, width, height))

    return len(files)


def main():
    test_truncation_after_data_type()
    test_truncation_partial_tagg_marker()
    test_truncation_short_tagg_name()
    test_truncation_short_tagg_data()
    test_truncation_short_mipmap_data()
    test_truncation_short_mipmap_length_field()
    print("OK truncation cases (6)")

    fixtures = _check_fixture_files()
    if fixtures:
        print("PASS test_paa (%d fixtures + truncation)" % fixtures)
    else:
        print("PASS test_paa (truncation only)")


if __name__ == "__main__":
    main()
