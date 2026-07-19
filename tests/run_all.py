"""Run the whole validation suite: pure-Python tests, py_compile, mayapy workflows.

Runs under a plain system Python interpreter — it shells out to mayapy for the
Maya half. Each mayapy test gets its OWN process: ``maya.standalone`` cannot be
initialized twice in one interpreter, and ``plugin_teardown`` / ``scene_watch``
need a clean Maya anyway.

    python tests/run_all.py
    python tests/run_all.py --only python
    python tests/run_all.py --filter 'weight*'
"""

import argparse
import fnmatch
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAYAPY = r"C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe"


def _run(label, argv, cwd=ROOT):
    started = time.time()
    completed = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True)
    elapsed = time.time() - started
    ok = completed.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'} {label} ({elapsed:.1f}s)")
    if not ok:
        for stream in (completed.stdout, completed.stderr):
            tail = (stream or "").strip().splitlines()[-25:]
            for line in tail:
                print(f"     {line}")
    return ok


def python_tests(pattern):
    tests = sorted(ROOT.glob("tests/python/test_*.py"))
    return [_run(t.name, [sys.executable, str(t)])
            for t in tests if _matches(t, pattern)]


def compile_check(pattern):
    if pattern:
        return []
    sources = []
    for directory in ("scripts", "plug-ins", "tests", "install"):
        sources.extend(str(p) for p in (ROOT / directory).rglob("*.py"))
    return [_run(f"py_compile ({len(sources)} files)",
                 [sys.executable, "-m", "py_compile"] + sources)]


def mayapy_tests(mayapy, pattern):
    if not Path(mayapy).exists():
        print(f"SKIP mayapy workflows — {mayapy} not found")
        return []
    tests = sorted(p for p in ROOT.glob("tests/mayapy/*.py")
                   if not p.name.startswith("_"))
    return [_run(t.name, [mayapy, str(t)])
            for t in tests if _matches(t, pattern)]


def golden_gate(mayapy, pattern):
    if pattern or not Path(mayapy).exists():
        return []
    if not (ROOT / "build" / "golden" / "manifest.json").exists():
        print("SKIP golden byte gate — no manifest (run: mayapy tests/golden.py capture)")
        return []
    return [_run("golden.py verify (P3D byte contract)",
                 [mayapy, str(ROOT / "tests" / "golden.py"), "verify"])]


def _matches(path, pattern):
    return not pattern or fnmatch.fnmatch(path.name, pattern)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["python", "compile", "mayapy", "golden"],
                        help="run just one stage")
    parser.add_argument("--filter", help="glob over test filenames, e.g. 'weight*'")
    parser.add_argument("--mayapy", default=os.environ.get("MAYAPY", DEFAULT_MAYAPY))
    args = parser.parse_args()

    stages = {
        "python": lambda: python_tests(args.filter),
        "compile": lambda: compile_check(args.filter),
        "mayapy": lambda: mayapy_tests(args.mayapy, args.filter),
        "golden": lambda: golden_gate(args.mayapy, args.filter),
    }
    selected = [args.only] if args.only else ["python", "compile", "mayapy", "golden"]

    results = []
    for stage in selected:
        print(f"\n--- {stage} ---")
        results.extend(stages[stage]())

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} passed"
          + (f", {failed} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
