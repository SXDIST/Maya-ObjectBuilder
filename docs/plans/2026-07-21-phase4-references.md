# Phase 4 — Reference assets ship with the plugin

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** *Add Male Character* works immediately after installation, without the user first
saving a reference of their own — and installing never destroys what the user already had.

**Architecture:** `assets/references/` carries the prepared `.ma` files under their own ADPL-SA
licence, separate from the MIT code. The release archive carries that directory, and the
installer seeds `references.default_directory()` from it, never overwriting a file already there.

**Tech Stack:** Maya 2027, Python 3, `maya.cmds`, `pathlib` + `shutil`, PowerShell for packaging.

## Global Constraints

- **`install/install_maya.py` may import only the stdlib and `maya.cmds`.** It is dragged into
  Maya and run standalone; importing a shared repo helper would break the one thing it is for.
  `pathlib`, `shutil`, `sys`, `traceback` are already there and satisfy this.
- **Never overwrite a reference the user has already saved.** Someone who customised their body
  must not lose it to an upgrade.
- **An absent `assets/references/` is a PASSING case**, not an error. The installer skips it
  silently. Contributors working from a git clone will not have the assets if they are pruned,
  and the installer must still complete normally.
- The `.ma` files are **Bohemia Interactive's**, under the Arma and DayZ Public License Share
  Alike (**ADPL-SA**): attribution required, non-commercial, Arma/DayZ only, share-alike. The
  plugin's own code is MIT. **The two must not be mixed in one undifferentiated tree.**
- **Never run `mayapy tests/golden.py capture`.** Only `verify`. This phase touches no export
  path, so `verify` is a regression check, not a gate you must move.
- The byte contract must not move: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.
- **Never run `python tests/run_all.py`** as an implementer. The controller runs the full suite.
- **Run every command in the FOREGROUND.**
- `mayapy` is `/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe`. Each mayapy test runs in its
  own process — `maya.standalone` cannot be initialized twice.
- **A test must never write into the user's real Maya folder.** Stub `_maya_documents_dir` /
  `references.default_directory` to a `mkdtemp` and restore every optionVar in a `finally`;
  `tests/mayapy/skin_transfer.py` and `tests/mayapy/texture_resolution_source.py` have the idiom.
  A Phase 3c test shipped without this and created a junk `dayz_skeleton.ma` in the author's real
  `Documents/maya/MayaObjectBuilder/references`.
- **Line endings:** the repo has no `.gitattributes` and genuinely mixed line endings. Edit in
  place; before committing confirm `git diff --shortstat` and `--ignore-cr-at-eol` agree.

## The data-loss bug this phase must fix first — measured, not suspected

`install()` calls `_copy_runtime_package(source, target)` with `target = _install_root()`, and
that function opens with:

```python
if target.exists():
    shutil.rmtree(target)
```

`_install_root()` is `<userAppDir>/MayaObjectBuilder`. Measured on the author's live Maya 2027:

| | |
|---|---|
| `cmds.internalVar(userAppDir=True)` | `C:/Users/targaryen/Documents/maya/` |
| `_install_root()` | `C:\Users\targaryen\Documents\maya\MayaObjectBuilder` |
| `references.default_directory()` | `…\MayaObjectBuilder\references` |
| `references_dir_is_inside_install_root` | **true** |
| actual contents of the install root | `backups`, `plug-ins`, `scripts` |

`backups/` is written by **no code in this repository** — it is the user's own folder, and on the
author's machine it holds `crash-2026-07-19/` and an 899 KB `2026-07-19-pants_weights_backup.json`.

So **re-running the installer today deletes the user's saved references and their weight backups.**
This is already shipped behaviour, independent of this phase. Seeding reference assets into a
directory the installer wipes would be worse than not shipping them at all, so Task 1 fixes it
before Task 3 puts anything there.

`_cleanup_legacy_install_roots` is **not** part of this bug: it only removes a child that itself
looks like a whole install (`child/plug-ins/MayaObjectBuilder.py` *and*
`child/scripts/objectBuilderMenu.py`), which `references/` and `backups/` never will. Leave it
alone.

## File structure

| File | Responsibility after this phase |
|------|-------------------------------|
| `install/install_maya.py` | replaces only the runtime dirs it owns; seeds references without overwriting |
| `assets/references/` | **new** — the prepared `.ma` files |
| `assets/references/LICENSE` | **new** — ADPL-SA, with attribution to Bohemia Interactive |
| `tools/package_release.ps1` | ships `assets/` in the release archive |
| `scripts/a3ob/mayabridge/references.py` | docstring corrected — the assets DO ship now |
| `README.md` | states MIT code / ADPL-SA assets and what that implies |
| `.gitignore` | stops ignoring the assets at their new home |
| `tests/mayapy/installer_preserves_user_data.py` | **new** |
| `tests/mayapy/installer_seeds_references.py` | **new** |

Three tasks. Task 1 stops the data loss. Task 2 puts the assets in the repo and the archive.
Task 3 makes the installer seed them.

---

### Task 1: installing stops destroying the user's own files

**Files:**
- Modify: `install/install_maya.py:60-66`
- Create: `tests/mayapy/installer_preserves_user_data.py`

**Interfaces:**
- Produces: `_copy_runtime_package(source, target)` — unchanged signature. It now removes and
  re-copies **only** the directories in `RUNTIME_PACKAGE_DIRS`, leaving every other entry in
  `target` untouched.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/installer_preserves_user_data.py`:

```python
"""Installing must not delete the user's own files from the install root (mayapy).

_copy_runtime_package opened with `shutil.rmtree(target)`, and target is
<userAppDir>/MayaObjectBuilder — the SAME directory that holds references.default_directory()
and, on the author's machine, a `backups/` folder with an 899 KB weights backup written by no
code in this repo. Re-running the installer deleted all of it.

install_maya.py may import only the stdlib and maya.cmds, so it is loaded here by path rather
than imported as a package.

Run:  mayapy.exe tests/mayapy/installer_preserves_user_data.py
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import _harness

_harness.bootstrap()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_installer():
    """Load install_maya.py by path. It is a drag-into-Maya script, not an importable module."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "install", "install_maya.py")
    spec = importlib.util.spec_from_file_location("install_maya_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_package(source):
    """A minimal stand-in for an extracted release: the two runtime dirs with one file each."""
    for relative in ("plug-ins", "scripts"):
        os.makedirs(os.path.join(source, relative))
        with open(os.path.join(source, relative, "marker.txt"), "w") as handle:
            handle.write(relative)


def test_user_files_beside_the_runtime_dirs_survive():
    installer = load_installer()
    source = tempfile.mkdtemp()
    target = tempfile.mkdtemp()
    make_package(source)

    # The user's own data, in the same folder the installer targets.
    os.makedirs(os.path.join(target, "references"))
    with open(os.path.join(target, "references", "dayz_male_body.ma"), "w") as handle:
        handle.write("the user's customised body")
    os.makedirs(os.path.join(target, "backups"))
    with open(os.path.join(target, "backups", "weights.json"), "w") as handle:
        handle.write("{}")

    installer._copy_runtime_package(Path(source), Path(target))

    body = os.path.join(target, "references", "dayz_male_body.ma")
    check(os.path.isfile(body), "the user's saved reference was deleted by the installer")
    with open(body) as handle:
        check(handle.read() == "the user's customised body", "the saved reference was overwritten")
    check(os.path.isfile(os.path.join(target, "backups", "weights.json")),
          "the user's backups folder was deleted by the installer")


def test_the_runtime_dirs_are_still_replaced_wholesale():
    """The point of the rmtree was to drop files a previous version shipped and this one does
    not. That must survive the fix, or an upgrade leaves orphans behind."""
    installer = load_installer()
    source = tempfile.mkdtemp()
    target = tempfile.mkdtemp()
    make_package(source)

    os.makedirs(os.path.join(target, "scripts"))
    with open(os.path.join(target, "scripts", "removed_last_version.py"), "w") as handle:
        handle.write("stale")

    installer._copy_runtime_package(Path(source), Path(target))

    check(not os.path.exists(os.path.join(target, "scripts", "removed_last_version.py")),
          "a stale file from a previous version survived the install")
    check(os.path.isfile(os.path.join(target, "scripts", "marker.txt")),
          "the new scripts/ was not copied")


def main():
    for test in (test_user_files_beside_the_runtime_dirs_survive,
                 test_the_runtime_dirs_are_still_replaced_wholesale):
        test()
        print("ok:", test.__name__, flush=True)
    print("INSTALLER PRESERVES USER DATA: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 2: Run it and WITNESS the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/installer_preserves_user_data.py
```

Expected: `FAIL: the user's saved reference was deleted by the installer`. Paste it.

- [ ] **Step 3: Replace the blanket rmtree**

In `install/install_maya.py`, replace the body of `_copy_runtime_package`:

```python
def _copy_runtime_package(source, target):
    # Remove only the directories this package OWNS. `target` is
    # <userAppDir>/MayaObjectBuilder, which also holds references/ (the user's saved reference
    # assets) and whatever else they keep there — an rmtree of the whole root deleted those on
    # every upgrade. The per-directory removal keeps the reason the rmtree existed: a file a
    # previous version shipped and this one dropped must not survive as an orphan.
    target.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    for relative_dir in RUNTIME_PACKAGE_DIRS:
        destination = target / relative_dir
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source / relative_dir, destination, ignore=ignore)
```

- [ ] **Step 4: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/installer_preserves_user_data.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
```

- [ ] **Step 5: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add install/install_maya.py tests/mayapy/installer_preserves_user_data.py
git commit -m "fix: installing no longer deletes the user's references and backups"
```

---

### Task 2: the assets live in the repo, under their own licence, and reach the archive

The two prepared `.ma` files are already in the worktree root (`dayz_male_body.ma`, 3.0 MB;
`dayz_skeleton.ma`, 172 KB), where `.gitignore` line 27 (`/dayz_*.ma`) keeps them untracked.
That ignore is anchored to the root, so moving them under `assets/references/` is enough to make
them trackable — do **not** weaken the root rule, which still protects files dropped there by
`a3obReference`'s Save action.

`KINDS` defines three kinds; only two files exist. `female_body` having no asset is a normal
state and must stay one.

**Files:**
- Create: `assets/references/dayz_male_body.ma`, `assets/references/dayz_skeleton.ma` (moved)
- Create: `assets/references/LICENSE`
- Modify: `.gitignore`, `README.md`, `tools/package_release.ps1`,
  `scripts/a3ob/mayabridge/references.py` (module docstring only)

- [ ] **Step 1: Move the assets and give them their licence**

```bash
mkdir -p assets/references
git mv --force dayz_male_body.ma assets/references/dayz_male_body.ma 2>/dev/null || mv dayz_male_body.ma assets/references/dayz_male_body.ma
mv dayz_skeleton.ma assets/references/dayz_skeleton.ma
```

(The files are untracked, so a plain `mv` is what will actually run.)

`assets/references/LICENSE` states ADPL-SA and attributes Bohemia Interactive. It must name the
source (`BohemiaInteractive/DayZ-Misc`, *Rig and Animations*) and the four obligations:
attribution, non-commercial, Arma/DayZ only, share-alike. Add a line saying the plugin's own code
is MIT and lives outside this directory.

- [ ] **Step 2: Stop ignoring them at the new location**

Extend the comment already at `.gitignore:22-27` to say that the root rule stays because
`a3obReference` still drops files there, and that `assets/references/` is the shipped home.
Verify with:

```bash
git check-ignore -v assets/references/dayz_male_body.ma; echo "exit=$?"
```

Expected: no output, `exit=1` — meaning it is **not** ignored.

- [ ] **Step 3: Ship the directory in the release archive**

`tools/package_release.ps1` stages `plug-ins/`, `scripts/`, `install/`, `README.md` and `LICENSE`
only. The installer reads the assets from the extracted release folder (`_package_root()` is the
parent of `install/`), so without this the shipped installer finds nothing and silently skips —
the feature would never work for any user while every test passed.

After the `scripts` copy (around line 52), add a copy of `assets` that is **conditional**, since
a clone without the assets must still package:

```powershell
$AssetsDir = Join-Path $RepoRoot "assets"
if (Test-Path $AssetsDir) {
    Copy-Item $AssetsDir (Join-Path $StageDir "assets") -Recurse -Exclude $exclude
} else {
    Write-Host "assets/ not present - packaging without reference assets"
}
```

Do **not** add the `.ma` files to `REQUIRED_PACKAGE_FILES` in `install/install_maya.py`: that
list is what `_validate_package` refuses to install without, and an absent asset is a passing
case.

- [ ] **Step 4: Correct the docstring that now states the opposite of the truth**

`scripts/a3ob/mayabridge/references.py:1-9` says "These are Bohemia assets, so they are NOT
stored in the repository." That premise was wrong and is now also factually stale. Rewrite the
docstring to say the assets ship in `assets/references/` under ADPL-SA, that the installer seeds
them into the user's Maya folder without overwriting, and keep the existing explanation of the
save-once/add-many workflow.

- [ ] **Step 5: README**

Add the licensing note: the code is MIT, `assets/references/` is ADPL-SA, and what that implies —
non-commercial, Arma/DayZ only, share-alike, attribution to Bohemia Interactive. Put it where the
existing MIT statement is, so a reader cannot see one without the other.

- [ ] **Step 6: Verify the packaging change actually stages the assets**

```bash
powershell -File tools/package_release.ps1 -Version 0.0.0-test
ls dist/*/assets/references/
```

Expected: both `.ma` files listed. Then remove the test artifact: `rm -rf dist/`.

- [ ] **Step 7: Check line endings, then commit**

`.ma` files are large text. Confirm the shortstat comparison over the whole range, then:

```bash
git add assets .gitignore README.md tools/package_release.ps1 scripts/a3ob/mayabridge/references.py
git commit -m "feat: ship the DayZ reference assets under their own ADPL-SA licence"
```

---

### Task 3: the installer seeds the references without ever overwriting

**Files:**
- Modify: `install/install_maya.py`
- Create: `tests/mayapy/installer_seeds_references.py`

**Interfaces:**
- Consumes: `_maya_documents_dir()`, `_package_root()`, `PLUGIN_NAME` — all existing.
- Produces: `_seed_reference_assets(source)` → the list of destination paths it wrote (empty when
  the source directory is absent or every file was already present). Called from `install()`
  after `_copy_runtime_package`.

The optionVars are the ones in `references.KINDS`, and `install_maya.py` may not import that
module — so the names are duplicated deliberately, the same way `_module_text` duplicates
`tools/dev_install.py`. Say so in a comment, or the next reader will "fix" it.

| kind | optionVar | file stem |
|---|---|---|
| `male_body` | `MayaObjectBuilder_ref_male_body` | `dayz_male_body` |
| `female_body` | `MayaObjectBuilder_ref_female_body` | `dayz_female_body` |
| `skeleton` | `MayaObjectBuilder_ref_skeleton` | `dayz_skeleton` |

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/installer_seeds_references.py`. It **must** snapshot and restore all three
optionVars in a `finally`, including the never-existed case, and must stub the documents dir to a
`mkdtemp` — a Phase 3c test wrote a junk reference into the author's real Maya folder.

Test NAMES and docstrings are given, not full bodies — the same deliberate trade Phase 3d made.
Plan-authored test code was wrong eight times across this branch (missing `load_plugin` three
times, missing `noExpand` twice, a fixture whose geometry made its own assertion unreachable, a
fixture that selected the reference out of candidacy, and three tests that would have passed
vacuously). Naming the property and pointing at the real fixture beats inventing one. **You must
still witness each red.** Cover exactly these:

```python
def test_a_fresh_install_copies_the_shipped_assets():
    """Both .ma files land in <documents>/MayaObjectBuilder/references."""

def test_the_optionvars_point_at_what_was_copied():
    """Add Male Character works immediately after installation — that is the whole point."""

def test_a_reference_the_user_already_saved_is_never_overwritten():
    """The file's CONTENT must be unchanged, not merely present. Someone who customised their
    body must not lose it to an upgrade."""

def test_an_optionvar_the_user_already_set_is_left_alone():
    """A user pointing at a reference OUTSIDE the default directory must keep pointing there."""

def test_a_missing_assets_directory_is_not_an_error():
    """A git clone without the assets must still install cleanly, writing nothing."""

def test_a_kind_with_no_shipped_file_is_skipped():
    """female_body has no asset today and that is a normal state, not a failure."""
```

Load the installer by path, as Task 1's test does — reuse that helper's shape.

- [ ] **Step 2: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/installer_seeds_references.py
```

Expected: `AttributeError: module has no attribute '_seed_reference_assets'`.

- [ ] **Step 3: Implement the seeding**

Add to `install/install_maya.py`, near `_copy_runtime_package`:

```python
# kind -> (optionVar, file stem). DUPLICATED from a3ob.mayabridge.references.KINDS on purpose:
# this file is dragged into Maya and run standalone, so it may import only the stdlib and
# maya.cmds. Change KINDS and you must edit this too.
REFERENCE_ASSETS = [
    ("MayaObjectBuilder_ref_male_body", "dayz_male_body"),
    ("MayaObjectBuilder_ref_female_body", "dayz_female_body"),
    ("MayaObjectBuilder_ref_skeleton", "dayz_skeleton"),
]


def _seed_reference_assets(source):
    """Copy shipped reference assets into the user's Maya folder and point the optionVars there.

    Never overwrites: a user who customised their body must not lose it to an upgrade, and a
    user whose optionVar points somewhere else entirely must keep pointing there. An absent
    assets/ directory is a normal state (a git clone, or a build with the assets pruned) and
    must not fail the install."""
    shipped = source / "assets" / "references"
    if not shipped.is_dir():
        return []
    destination_dir = _maya_documents_dir() / PLUGIN_NAME / "references"
    destination_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for option_var, stem in REFERENCE_ASSETS:
        asset = shipped / f"{stem}.ma"
        if not asset.is_file():
            continue
        destination = destination_dir / asset.name
        if not destination.exists():
            shutil.copy2(asset, destination)
            written.append(destination)
        existing = cmds.optionVar(query=option_var) if cmds.optionVar(exists=option_var) else ""
        if not existing or not Path(existing).is_file():
            cmds.optionVar(stringValue=(option_var, destination.as_posix()))
    return written
```

Then call it in `install()`, after `_copy_runtime_package(source, target)`:

```python
    seeded = _seed_reference_assets(source)
    if seeded:
        print(f"Reference assets installed: {', '.join(p.name for p in seeded)}")
```

- [ ] **Step 4: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/installer_seeds_references.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/installer_preserves_user_data.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/reference_overwrite_guard.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

- [ ] **Step 5: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add install/install_maya.py tests/mayapy/installer_seeds_references.py
git commit -m "feat: the installer seeds reference assets without overwriting"
```

---

## Decisions carried from the spec — do not relitigate

- **Save Selection as … stays in the menu.** Shipping the assets removes the argument that saving
  is the only way to *obtain* a reference, but not the reason to keep it: it is how a reference
  gets *changed* when a DayZ update alters the rig or paths need fixing. Without it a shipped
  reference is frozen.
- **The assets get their own directory and `LICENSE`.** A prepared `.ma` with materials and
  `a3obTexture` / `a3obMaterial` paths set up is an adaptation of Bohemia's mesh and falls under
  ADPL-SA's share-alike clause. The plugin's code is MIT and is not a derivative of the mesh.
  *This records what the licences say, not legal advice; the compatibility call is the author's.*
- **`female_body` shipping no asset is normal**, not a gap to fill.

## Verification for the controller between tasks

```bash
python tests/run_all.py
```

Expected after Task 3: the Phase 3d baseline of 62 plus two new files
(`installer_preserves_user_data`, `installer_seeds_references`), all green, with the byte gate
printing real per-fixture lines.

## Left for a live Maya session

The installer cannot be exercised end to end headlessly — `install()` unloads and reloads the
plugin and writes a `.mod`. After Task 3, in a real session: drag `install_maya.py` in, confirm
`references/` and `backups/` survive, confirm *Add Male Character* works with no prior save, then
re-run the installer and confirm a reference edited by hand is still the edited one.
