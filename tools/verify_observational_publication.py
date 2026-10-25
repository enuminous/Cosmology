"""Verify the delivered observational run; optionally restore compressed data.

Uses only the standard library. This checks identities and consistency of saved
results, not scientific correctness or a fresh numerical reproduction.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "observational"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_bytes(data, identity, label):
    require(len(data) == identity["bytes"], f"Length changed: {label}")
    require(sha256(data) == identity["sha256"], f"SHA256 changed: {label}")


def safe_path(base, name):
    path = (base / name).resolve()
    require(path.is_relative_to(base.resolve()), f"Unsafe path: {name}")
    return path


def close(left, right, label, tolerance=1e-8):
    require(math.isfinite(left) and math.isfinite(right), f"Nonfinite {label}")
    require(abs(left - right) <= tolerance, f"Inconsistent {label}: {left} vs {right}")


def verify(prepare=False):
    meta = read_json(ROOT / "publication/observational-2026-10-25.json")
    manifest_path = safe_path(ROOT, meta["artifact_manifest"]["path"])
    manifest_bytes = manifest_path.read_bytes()
    check_bytes(manifest_bytes, meta["artifact_manifest"], "artifact manifest")
    manifest = json.loads(manifest_bytes)
    require(manifest["run"] == meta["run"], "Run identity mismatch")
    require(len(manifest["files"]) == meta["artifact_manifest"]["listed_files"] == 153,
            "Unexpected artifact inventory")
    restored = []
    for name, identity in manifest["files"].items():
        target = safe_path(OBS, name)
        if name in meta["compressed_files"]:
            packed = meta["compressed_files"][name]
            require(packed["format"] == "gzip", f"Unsupported encoding: {name}")
            stored = safe_path(OBS, packed["path"]).read_bytes()
            check_bytes(stored, packed, packed["path"])
            data = gzip.decompress(stored)
            check_bytes(data, identity, name)
            if target.exists():
                check_bytes(target.read_bytes(), identity, name)
            elif prepare:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(data)
                restored.append(name)
        else:
            check_bytes(target.read_bytes(), identity, name)

    lock = read_json(OBS / "implementation_lock.json")
    for name, wanted in lock["source_sha256"].items():
        require(sha256(safe_path(OBS, name).read_bytes()) == wanted,
                f"Analysis lock changed: {name}")

    fit = read_json(OBS / "family_fit_results.json")
    status = read_json(OBS / "execution_status.json")
    direct = read_json(OBS / "fit_direct_verification.json")
    mocks = [json.loads(line) for line in (OBS / "mock_results.jsonl").read_text().splitlines()
             if line.strip()]
    calibration = fit["mock_calibration"]
    require(len(mocks) == calibration["n"] == status["mock_count"] == 200, "Mock count changed")
    require(sorted(row["index"] for row in mocks) == list(range(200)), "Mock index coverage changed")
    require(all(row["converged"] for row in mocks), "A mock convergence gate failed")
    require(calibration["all_converged"] and calibration["failed_indices"] == [],
            "Mock convergence summary inconsistent")
    for row in mocks:
        require(all(row["fits"][model]["converged"] for model in ("lcdm", "c1q")),
                f"Mock fit gate failed: {row['index']}")
        close(row["fits"]["lcdm"]["chi2_total"] - row["fits"]["c1q"]["chi2_total"],
              row["T"], f"mock {row['index']} improvement")
    for model in ("lcdm", "c1q"):
        values = fit["fits"][model]
        close(values["chi2_bao"] + values["chi2_sn"], values["chi2_total"], f"{model} total")
        require(values["converged"], f"{model} fit convergence failed")
        require(read_json(OBS / f"posterior_{model}.json")["converged"], f"{model} posterior gate failed")
        require(status["posterior_convergence_checks"][model], f"{model} posterior status mismatch")
    observed = fit["fits"]["lcdm"]["chi2_total"] - fit["fits"]["c1q"]["chi2_total"]
    close(observed, fit["T"], "observed improvement")
    exceedances = sum(row["T"] >= observed for row in mocks)
    require(exceedances == calibration["exceedances"] == 3, "Exceedance count inconsistent")
    p_mc = (1 + exceedances) / (1 + len(mocks))
    close(p_mc, calibration["p_MC"], "calibration p_MC", 1e-14)
    close(p_mc, status["p_MC"], "status p_MC", 1e-14)
    close(1 / (1 + len(mocks)), calibration["resolution_floor"], "resolution floor", 1e-14)
    require((p_mc <= 0.01) == calibration["passes_training_screen"] == status["training_screen_passed"] is False,
            "Training-screen verdict inconsistent")
    close(direct["T_direct"], observed, "direct CLASS comparison", 0.01)
    require(direct["all_passed"] and status["direct_fit_verification_passed"], "Direct verification failed")
    require(read_json(OBS / "surrogate/validation.json")["passed"], "Surrogate validation failed")
    require(status["training_execution_complete"] and fit["all_fits_converged"], "Training not complete")
    require(status["original_freeze_identity_matches"] and status["implementation_lock_identity_matches"],
            "Recorded identity check failed")
    for field in ("full_Planck_posterior_predictive_complete", "future_independent_release_test_complete",
                  "full_protocol_signal_demonstrated"):
        require(status[field] is False, f"Unexpected completed claim: {field}")
    require(status["conditional_fixed_point_Planck_diagnostic_complete"], "Missing conditional diagnostic")
    return {
        "run": meta["run"], "all_passed": True, "original_bundle_files_checked": 154,
        "locked_analysis_files_checked": len(lock["source_sha256"]), "restored": restored,
        "mock_count": len(mocks), "exceedances": exceedances, "p_MC": p_mc,
        "training_screen_passed": False,
        "scope": "Publication identity and saved-result consistency; inference was not rerun."
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Restore verified compressed data if absent")
    args = parser.parse_args()
    try:
        result = verify(args.prepare)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"all_passed": False, "error": str(error)}, indent=2))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
