# C1Q observational study — 25 October 2026

**Result: the training screen fails.** C1Q improves the DESI DR2 BAO + Pantheon+ fit by Δχ² = 4.871050, but the completed 200-mock calibration gives p_MC = 0.01990050, above the declared 0.01 threshold. Full Planck posterior prediction and a future independent-data test are incomplete.

Read [RUN_REPORT.md](RUN_REPORT.md) for the scientific result and limitations, [execution_status.json](execution_status.json) for the recorded completion state, and [REPRODUCE.md](REPRODUCE.md) for the original run instructions.

## Prepare this repository checkout

From the repository root, run:

```bash
python3 tools/verify_observational_publication.py --prepare
python3 src/check_freeze.py
```

Python's standard library is sufficient for these identity checks. The first command restores `data/Pantheon+SH0ES_STAT+SYS.cov` from its lossless `.gz` representation, verifies all 153 files listed in the original artifact manifest plus the manifest itself, and checks the saved fit/mock/posterior status. Existing covariance files must match the original hash; the helper refuses to replace a different file. Without `--prepare`, it verifies the compressed representation without writing data.

This directory includes the complete logical contents of the originally delivered result bundle. Only the covariance's storage encoding differs. Its decompressed bytes and every other original bundle file remain unchanged. [Publication provenance](../publication/observational-2026-10-25.json) records the original ZIP identity, the manifest identity, and the compressed representation. The README, publication helper, and CI workflow are later packaging additions and are outside the frozen analysis lock.

The pinned source-model commit in `REPRODUCE.md` identifies the original numerical baseline. This publication already includes that baseline and the study. After preparation, follow the environment and inference steps in that document. Preserve delivered outputs before rerunning scripts that write results.

## Included evidence

- [Fitted likelihoods and null calibration](family_fit_results.json), [individual mock fits](mock_results.jsonl), and [deterministic seeds](mock_seeds.json).
- [Direct CLASS verification](fit_direct_verification.json), [surrogate validation](surrogate/validation.json), and [independent family cross-check](family_crosscheck.json).
- Posterior chains (`posterior_lcdm.npz`, `posterior_c1q.npz`), summaries, residual tables, and [diagnostic figure](stage1_diagnostics.png).
- [Implementation lock](implementation_lock.json), [data receipts](data_manifest.json), the original [execution plan](EXECUTION_PLAN.md), and failed-attempt logs.
- [Conditional Planck diagnostic scope](PLANCK_POINT_DIAGNOSTIC.md), results, cached spectra, and backend checks.

Public Planck likelihood data and raw interpolation training arrays are excluded exactly as recorded in the original bundle; acquisition/build scripts and identities are included. The CI publication check validates recorded identities and consistency. It does not rerun the fits, 200 mock optimizations, posterior sampling, or Planck likelihood.

This remains a test of established GR plus canonical quadratic quintessence. Passing a numerical check is not a discovery claim; the full protocol signal and empirical validation of EFMW have not been demonstrated.
