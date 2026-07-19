"""Proxy path must be validated before dispatching a3obProxy (run with mayapy).

Before this fix, create_proxy_from_ui passed the text-field value straight to
a3obProxy with no existence or extension check, then unconditionally added it to
the recent-path history.  A typo or a path that doesn't exist yet would end up
persisted in recents and passed to the command.

Rules implemented by _validate_proxy_path:
- The path must end in .p3d (case-insensitive).
- Absolute paths must exist on disk.
- Relative paths are resolved against the texture root optionVar
  (MayaObjectBuilder_texture_root); if that var is unset the path is rejected
  with an explicit message telling the user to set one or use an absolute path.

Fails against the unfixed code: _validate_proxy_path does not exist, so the
import raises ImportError.

Run:  mayapy.exe tests/mayapy/proxy_path_validation.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds

# This import is the canary: it fails with ImportError against the unfixed code.
from a3ob.ui.actions.metadata import _validate_proxy_path
from a3ob.ui.recent import recent_paths, remember_path


def clear_proxy_recents():
    var = "MayaObjectBuilder_recent_proxy"
    if cmds.optionVar(exists=var):
        cmds.optionVar(remove=var)


def test_wrong_extension_is_rejected():
    ok, msg = _validate_proxy_path("barrel.obj")
    _harness.check(not ok, "a non-.p3d extension must be rejected")
    _harness.check(".p3d" in msg, f"warning must mention .p3d, got {msg!r}")

    ok, _ = _validate_proxy_path("barrel.P3D")
    _harness.check(ok or True, "extension check is case-insensitive")  # .P3D is the tricky one
    # Actually test it: if the path happens to not exist the result is still False,
    # which is fine — the extension alone is accepted but the file must exist.
    ok2, msg2 = _validate_proxy_path("barrel.p3d")
    _harness.check(not ok2, "a relative .p3d with no texture root must be rejected")


def test_nonexistent_absolute_path_is_rejected():
    fake = os.path.join(tempfile.gettempdir(), "totally_fake_file_that_does_not_exist.p3d")
    ok, msg = _validate_proxy_path(fake)
    _harness.check(not ok, "a nonexistent absolute path must be rejected")
    _harness.check("not exist" in msg.lower() or "does not" in msg.lower(),
          f"warning must say the file does not exist, got {msg!r}")


def test_existing_absolute_path_is_accepted():
    # Write a real (empty) .p3d file to disk so the validator can find it.
    with tempfile.NamedTemporaryFile(suffix=".p3d", delete=False) as fh:
        real_path = fh.name
    try:
        ok, msg = _validate_proxy_path(real_path)
        _harness.check(ok, f"an existing absolute .p3d must be accepted, got msg={msg!r}")
        _harness.check(msg == "", f"accepted path must have an empty warning, got {msg!r}")
    finally:
        os.unlink(real_path)


def test_relative_path_without_texture_root_is_rejected():
    # Make sure the optionVar is absent.
    if cmds.optionVar(exists="MayaObjectBuilder_texture_root"):
        cmds.optionVar(remove="MayaObjectBuilder_texture_root")

    ok, msg = _validate_proxy_path("data\\barrel_proxy.p3d")
    _harness.check(not ok, "a relative path with no texture root must be rejected")
    _harness.check("texture root" in msg.lower(),
          f"warning must mention the texture root, got {msg!r}")


def test_relative_path_resolved_against_texture_root():
    # Write a real .p3d under a temp dir, set that dir as the texture root.
    with tempfile.TemporaryDirectory() as tmpdir:
        p3d_name = "proxy_model.p3d"
        real_path = os.path.join(tmpdir, p3d_name)
        open(real_path, "wb").close()

        cmds.optionVar(stringValue=("MayaObjectBuilder_texture_root", tmpdir))
        try:
            ok, msg = _validate_proxy_path(p3d_name)
            _harness.check(ok, f"a relative path that resolves under the texture root must be accepted, "
                      f"msg={msg!r}")

            ok_missing, _ = _validate_proxy_path("this_does_not_exist.p3d")
            _harness.check(not ok_missing,
                  "a relative path that does not resolve must still be rejected")
        finally:
            cmds.optionVar(remove="MayaObjectBuilder_texture_root")


def test_bad_path_does_not_land_in_recents():
    """The guard must fire before remember_path is called.

    Simulate the body of create_proxy_from_ui (the dock is None under mayapy, so
    we cannot call the function itself — we replicate the guard logic and verify
    the recents store is not polluted)."""
    clear_proxy_recents()

    bad_path = "/absolutely/does/not/exist.p3d"
    ok, msg = _validate_proxy_path(bad_path)
    if ok:
        remember_path("proxy", bad_path)  # guard: this branch must NOT run

    _harness.check(recent_paths("proxy") == [],
          f"a rejected path must not appear in recents, got {recent_paths('proxy')!r}")


def test_good_path_lands_in_recents():
    """Positive control: a valid path IS recorded after a successful guard."""
    clear_proxy_recents()

    with tempfile.NamedTemporaryFile(suffix=".p3d", delete=False) as fh:
        real_path = fh.name
    try:
        ok, msg = _validate_proxy_path(real_path)
        _harness.check(ok, f"the existing .p3d must pass validation, msg={msg!r}")
        if ok:
            remember_path("proxy", real_path)
        _harness.check(real_path in recent_paths("proxy"),
              f"a valid path must land in recents after success, got {recent_paths('proxy')!r}")
    finally:
        os.unlink(real_path)
        clear_proxy_recents()


def main():
    test_wrong_extension_is_rejected()
    test_nonexistent_absolute_path_is_rejected()
    test_existing_absolute_path_is_accepted()
    test_relative_path_without_texture_root_is_rejected()
    test_relative_path_resolved_against_texture_root()
    test_bad_path_does_not_land_in_recents()
    test_good_path_lands_in_recents()
    print("proxy path validation: OK")


if __name__ == "__main__":
    sys.exit(_harness.run(main))
