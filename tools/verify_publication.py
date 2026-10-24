"""Reproduce frozen calculations in a temporary copy; preserve delivered files."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_files():
    meta = json.loads((ROOT / "publication.json").read_text())["original_archive"]
    assert digest(ROOT / "MANIFEST.sha256") == meta["manifest_sha256"], "Manifest identity changed"
    assert digest(ROOT / "FREEZE.json") == meta["freeze_sha256"], "Freeze identity changed"
    paths = []
    for line in (ROOT / "MANIFEST.sha256").read_text().splitlines():
        wanted, name = line.split("  ", 1)
        path = ROOT / name
        assert path.resolve().is_relative_to(ROOT), name
        assert path.is_file() and digest(path) == wanted, "Original file changed: " + name
        paths.append(name)
    paths.append("MANIFEST.sha256")
    assert len(paths) == len(set(paths)) == meta["extracted_file_count"]
    return paths


def run_script(base, name):
    result = subprocess.run([sys.executable, name], cwd=base, capture_output=True,
                            text=True, timeout=600)
    if result.returncode:
        raise RuntimeError(f"{name} failed ({result.returncode})\n{result.stdout}\n{result.stderr}")
    return {"script": name, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def verify():
    paths = original_files()
    report = {
        "model_id": "EFMW-COSMO-C1Q", "version": "1.0.0",
        "executed_utc": datetime.now(timezone.utc).isoformat(),
        "original_file_count": len(paths), "original_file_identity_matches": True,
        "environment": {"python": sys.version.split()[0], **{
            name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")}},
        "evidence_scope": "Numerical reproduction and saved-table analysis; no observational fit",
        "full_CLASS_rebuilt": False, "new_CMB_prediction_seed_consumed": False,
        "steps": []}
    baseline = json.loads((ROOT / "results/reference.json").read_text())
    with tempfile.TemporaryDirectory(prefix="cosmology-reproduction-") as folder:
        base = Path(folder)
        for name in paths:
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        for script in ("src/check_freeze.py", "src/cosmology.py", "tests/verify.py", "src/analyze_class.py"):
            print("Running " + script, flush=True)
            report["steps"].append(run_script(base, script))
        checks = json.loads((base / "results/verification.json").read_text())
        assert checks["all_passed"] and len(checks["checks"]) == 9
        report["background_checks"] = checks
        comparison = json.loads((base / "results/class_comparison.json").read_text())
        assert comparison["background_crosscheck"]["passed"]
        assert comparison["finite_compared_tables"]
        report["saved_CLASS_analysis"] = comparison
        regenerated = json.loads((base / "results/reference.json").read_text())
        tolerance = json.loads((ROOT / "config/numerics.json").read_text())["validation"]["resolution_observable_rel"]
        keys = ("x_initial", "x_today", "y_today", "Omega_phi0", "w_phi_today", "age_since_ai_Gyr")
        changes = {k: abs(regenerated[k] / baseline[k] - 1) for k in keys}
        assert all(math.isfinite(v) and v < tolerance for v in changes.values()), changes
        report["reference_summary_relative_changes"] = changes
        report["reference_summary_relative_tolerance"] = tolerance
    original_files()
    report["original_files_unchanged_after_execution"] = True
    report["all_passed"] = True
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        raise SystemExit("Refusing to overwrite an existing verification report")
    # Never let a report replace a frozen file or a source script.
    if target.is_relative_to(ROOT) and target.parent != ROOT / "publication":
        raise SystemExit("Repository reports must be written under publication/")
    try:
        result = verify()
    except Exception as error:
        result = {"all_passed": False, "error": str(error),
                  "executed_utc": datetime.now(timezone.utc).isoformat()}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"all_passed": result["all_passed"], "report": str(target),
                      "error": result.get("error")}, indent=2))
    raise SystemExit(0 if result["all_passed"] else 1)
