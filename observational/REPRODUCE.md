# Reproduce this observational run

Use a fresh workspace. Preserve the delivered result files before rerunning: the scripts intentionally refuse a changed Stage-1 implementation lock, but several result writers otherwise replace their named outputs.

1. Check out `https://github.com/enuminous/Cosmology` at `f457a1fc414257d5e4d2ddbeb8985db2cb714363`. Put this bundle's `observational/` directory inside that checkout. Run `python src/check_freeze.py` to verify the original source freeze.
2. Create a Python 3.12 environment. Install the versions recorded in `observational/environment.json`, including NumPy, SciPy, pandas, matplotlib, emcee, Cython, PyYAML and astropy. Clone `https://github.com/lesgourg/class_public` at `814ce59c380a5cccd0bed1747a384ff7bfc1f9cf` into a separate directory. Run the following from the Cosmology checkout, substituting its actual path:

```bash
python src/patch_class.py /absolute/path/class_public
python observational/patch_family_shooting.py /absolute/path/class_public
make -C /absolute/path/class_public -j2 class libclass.a
CC=gcc CXX=g++ python -m pip install --no-build-isolation --no-deps /absolute/path/class_public
```

The original potential adapter and the subsequent numerical bracketing adapter are separate. Do not apply either twice. The combined source diff and hashes are included.

3. Set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. The compact bundle includes the four Stage-1 observational files and their receipts. `python observational/acquire.py` can reacquire them from the exact pinned URLs; it verifies byte lengths and Git object hashes. SHA256 is also verified whenever `JointLikelihood` loads the data.
4. The accepted interpolation coefficients are included. To rebuild them, move the delivered `observational/surrogate` directory aside, recreate it, and run:

```bash
python observational/build_surrogate.py --shape 18 5 24 --workers 8
python observational/build_rd_correction.py
python observational/validate_surrogate.py
python observational/family_crosscheck.py
```

Any revised grid or failed validation requires a separate, documented run before fitting. Do not silently overwrite a frozen implementation lock. The original failed numerical attempts are retained for audit, not for use in inference.

5. To rerun inference with the delivered accepted coefficients, preserve the delivered outputs and then run:

```bash
python observational/fit_stage1.py
python observational/verify_fit.py
python observational/posterior.py lcdm
python observational/posterior.py c1q
python observational/residual_audit.py
```

The fit script uses the recorded equal optimization budget, generates 200 deterministic mock realizations, and refits both models. `mock_results.jsonl` is resumable; move it aside for a clean reproduction. Do not reuse a mock stream after changing its fitted generating model, code or covariance. `implementation_lock.json` records the analysis identity. Small cross-platform floating-point changes are possible; compare full convergence and validation diagnostics.

6. The optional conditional Planck diagnostic needs the public Planck data and Clipy. Install `CobayaSampler/clipy` at `4260853bbc6a6e998896ef2b22b48161209562c5` (distribution `clipy-like` 0.16) and the recorded JAX CPU version. Preserve the delivered Planck manifests, acquire the public data with `python observational/acquire_planck.py`, and compare the new SHA256 with the delivered receipt. Run:

```bash
python observational/planck_jax_profile.py lcdm
python observational/planck_jax_profile.py c1q
```

Existing spectra are cached. Move those files aside to repeat the Boltzmann calculations. The JAX implementation uses 64-bit precision and checks the same objective against recorded NumPy evaluations and finite-difference gradients. The slower NumPy implementation remains in `planck_diagnostic.py`. The diagnostic fixes cosmological parameters and profiles common Planck nuisance parameters; it does not implement the full Stage-2 posterior-predictive integral. It retains the frozen linear-theory prescription and reports a numerical-resolution comparison. The complete Planck likelihood data are excluded from the compact bundle, but their official download URL and exact received hash are included.

7. After all required outputs exist, `python observational/make_report.py` regenerates the report and figure. The original nine background checks can be rerun with `tests/verify.py` in a separate copy of the original checkout so its frozen reference outputs are not overwritten.

The accepted run's report, source hashes, data receipts, residuals, posterior chains, mock fits, numerical checks and failure logs should be assessed together. Successful execution is not evidence of new physics by itself.
