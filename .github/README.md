# C1Q Horizons: cosmology and observational tests

C1Q studies a spatially flat universe in general relativity with a canonical quadratic quintessence field. The repository contains the frozen physical specification, numerical predictions, the HORIZON interactive observatory, and a separately fitted observational study.

**25 October 2026 observational result:** C1Q improves the DESI DR2 BAO + Pantheon+ fit, but does **not** pass the declared training threshold. Full external predictive validation remains incomplete. This work does not demonstrate new fundamental physics or empirical proof of EFMW.

| Fitted model | Total χ² |
|---|---:|
| ΛCDM | 1416.169529 |
| C1Q | 1411.298479 |

The improvement is Δχ² = 4.871050 with one additional parameter. Three of 200 ΛCDM mock comparisons matched or exceeded it, giving **p_MC = 4/201 = 0.01990050**, above the declared 0.01 threshold. Direct numerical checks and both ensemble posterior convergence gates passed; those gates are not independent-chain R-hat verification.

The separate **fixed-point** Planck nuisance-profile objective is about 911.91 higher for C1Q. This conditional diagnostic is not the fitted family's posterior-predictive test. That test and a future independent release remain unfinished.

## Read the study

- [Observational study and reproduction entry point](../observational/README.md)
- [Full results, intervals, diagnostics, and limitations](../observational/RUN_REPORT.md)
- [Machine-readable execution status](../observational/execution_status.json)
- [All 200 mock comparisons](../observational/mock_results.jsonl)
- [Original run manifest](../observational/ARTIFACT_MANIFEST.json) and [publication provenance](../publication/observational-2026-10-25.json)

The complete study is included: source code, data receipts, posterior chains, accepted interpolation coefficients, residual tables, numerical checks, and failed-attempt logs. Public Planck likelihood data and raw interpolation training arrays are reacquired or rebuilt using the included scripts. One large covariance file is stored losslessly compressed.

![Stage-1 observational diagnostics](../observational/stage1_diagnostics.png)

## Verify a checkout

```bash
git clone https://github.com/enuminous/Cosmology.git
cd Cosmology
python3 tools/verify_observational_publication.py --prepare
python3 src/check_freeze.py
```

The first command verifies every delivered study file and restores the compressed covariance for analysis. It also checks the saved mock calibration and result status. It does not rerun inference; use the [reproduction instructions](../observational/REPRODUCE.md) for that work.

## Original model and observatory

- [Frozen v1.0.0 README](../README.md)
- [Physical model](../docs/MODEL.md), [numerical results](../docs/NUMERICAL_RESULTS.md), and [original test protocol](../docs/TEST_PROTOCOL.md)
- [Audit and scientific limitations](../docs/AUDIT.md)
- [HORIZON standalone observatory](../index.html) and [application instructions](../webapp/README.md)

The original README describes the immutable numerical package before observational fitting. All original freeze identities remain unchanged. The observational family and its results are a separate, dated addition; the displayed frozen cosmology is not a posterior estimate.
