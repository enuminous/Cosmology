# Cosmology package publication — 23 October 2026

This repository publishes Matthew Chenoweth Wright's **EFMW-COSMO-C1Q v1.0.0**, frozen on 16 October 2026. The original 92 package files are preserved byte for byte, including numerical outputs, rejected calculations, source provenance, and the original freeze and manifest. Publication tooling and this note are additions outside that original freeze.

## Start here

- [Original package overview and reproduction commands](README.md)
- [Covariant action, matter prescription, parameters and initial conditions](docs/MODEL.md)
- [Linear perturbations and CLASS mapping](docs/PERTURBATIONS.md)
- [Calculated predictions and numerical limits](docs/NUMERICAL_RESULTS.md)
- [Audit, failed implementations and unresolved obligations](docs/AUDIT.md)
- [Prospective empirical protocol](docs/TEST_PROTOCOL.md)
- [Prediction figure](results/predictions.png)
- [Primary sources](SOURCES.md)
- [Publication verification record](publication/verification-2026-10-23.json)
- [HORIZON standalone universe-recursion observatory](index.html) — download the single HTML file and open it locally; [controls, numerical method and evidence boundaries](webapp/README.md). This interface is an addition outside the original freeze.

The model is GR plus a minimally coupled canonical scalar with a quadratic potential, baryons, photons, cold dark matter and three thermal neutrino species. The supplied integration covers a=10^-8 to 1 and includes linear perturbation predictions. Its reference parameters are fixed assumptions, and its scalar amplitude is fixed by the flatness boundary condition. No observational likelihood or posterior fit is included. The physical class is established quadratic quintessence; the publication is an executable model instance, not evidence of a new physical law.

## Archive identity and preservation

Original archive: `EFMW-Cosmology-C1Q-v1.0.0.zip`, 22,231,006 bytes.

SHA-256: `515ebaa0eb07244aa34bd1a224ae190a6d889b44ee9408ba5ad6ad5c6ce07a5f`.

That hash independently matches the archive identity recorded in the [18 October prediction lock](https://github.com/enuminous/papers/blob/a7ecd9b31306a17658599a3c4728b853ab12bf38/research/cmb-alignment/prediction-lock/v1/lock.json). All 92 extracted files are committed here. GitHub-generated ZIP downloads have their own archive bytes and are not expected to share the original archive's hash; verify their extracted files with the original manifest.

```bash
python3 src/check_freeze.py
python3 -m pip install -r requirements.txt
python3 tools/verify_publication.py --output /tmp/cosmology-verification.json
```

The second check runs the original background solver, all nine numerical checks, and analysis of the saved CLASS outputs in a temporary copy. It preserves the original results in the repository. It does not rebuild CLASS or perform observational fitting. The workflow repeats those checks; a workflow pass concerns reproducibility, not physical validation.

The complete CLASS build instructions remain in the original README. The pinned source and adapter are required. Preserve the synchronous-gauge requirement, the rejected Newtonian-gauge results, and the documented ill-conditioned early-time `theta_scf` diagnostic; those limitations have not been removed by publication.

## Relation to the wider cosmology program

These companions remain at their own pinned source versions. They have distinct assumptions and are not silently added to the C1Q action:

| Companion | Scope and relation |
| --- | --- |
| [R-001 primordial recursion boundary](https://github.com/enuminous/papers/blob/a7ecd9b31306a17658599a3c4728b853ab12bf38/EFMW-Zoo-R001-Primordial-Recursion-Boundary.md) | Prescribed regular bounce; its required flat-GR NEC violation is not provided by the canonical C1Q matter content. |
| [CMB assessment](https://github.com/enuminous/papers/blob/a7ecd9b31306a17658599a3c4728b853ab12bf38/research/cmb-alignment/README.md) | Statistical controls and a specified WMAP measurement; no derived EFMW sky transfer or global-rotation detection. |
| [C1Q prediction lock](https://github.com/enuminous/papers/blob/a7ecd9b31306a17658599a3c4728b853ab12bf38/research/cmb-alignment/prediction-lock/v1/LOCK.md) | Zero background/retained linear-scalar vorticity and an isotropic Gaussian directional null. The frozen new seed is not consumed by this publication. |
| [Two-field local-vorticity derivation](https://github.com/enuminous/papers/blob/a7ecd9b31306a17658599a3c4728b853ab12bf38/research/cmb-alignment/nonzero-vorticity/v1/DERIVATION.md) | Fixed-background, two-field construction with specified inhomogeneous initial data; different from C1Q's one-field linear cosmology. |
| [Universe5](https://github.com/enuminous/Universe5/tree/8a4e71274abc905b75293f7c26049004f5921ab5) | Newtonian toy simulations and an educational dashboard; not a relativistic cosmological solution. |

A coupled bounce/rotation extension, inflation, baryogenesis and nonlinear structure are not part of this frozen model. A physical extension needs its own action, initial data, equations, constraint and stability checks, and versioned observable predictions. The original hypothesis and negative results remain available for comparison.

## Publication verification

The recorded local check verifies original file identity, reruns the background and nine scientific numerical checks, recalculates diagnostics from saved CLASS tables, and compares reference summary quantities at the original convergence tolerance. Re-analysis of saved tables is distinguished from a new CLASS evolution. The EFMW Zoo analysis skill's provenance and evidence-status discipline guided this publication; no new Lean theorem or full Zoo certification is claimed.

Changes to physics require a new model version under the original freeze policy. Additional publication notes may be amended without changing the frozen original files. Repository commit and tag addresses record this publication; they do not establish empirical confirmation.
