# EFMW-COSMO-C1Q v1.0.0

Frozen 16 October 2026 (Pacific) for Matthew Chenoweth Wright.

This package specifies and executes a **post-BBN cosmological candidate**: spatially flat general relativity, one canonical scalar with V(phi)=m^2 phi^2/2, ordinary photons and baryons, cold dark matter, and three thermal neutrino species. Lambda and direct scalar-matter couplings are zero. The reference chooses m/H0=1 and fixes all inputs, initial data and numerical conventions. The active physics is established quadratic quintessence; this branch does not establish a new physical law or validate EFMW experimentally.

The homogeneous equations, full linear perturbation prescription, CLASS adapter, calculated CMB and matter spectra, baseline comparison, audit, and prospective empirical protocol are included. Primordial perturbations and abundances are supplied as inputs. Inflation, baryogenesis, quantum gravity and nonlinear galaxy formation remain outside the model.

## Read first

- `docs/MODEL.md`: covariant action, field content, parameter point, background and observables.
- `docs/PERTURBATIONS.md`: metric/scalar equations, Einstein-Boltzmann closure and exact code mapping.
- `docs/NUMERICAL_RESULTS.md`: executed results and numerical limits.
- `docs/TEST_PROTOCOL.md`: declared comparison family and prospective data tests.
- `docs/AUDIT.md`: proof obligations, novelty, circularity, rejected implementations and unresolved issues.
- `config/model.json`: machine-readable physical freeze.
- `results/predictions.pdf` and `results/predictions.png`: synthetic prediction figures.
- `SOURCES.md`: pinned primary sources and attribution.

## Reference predictions

These are chosen-input model outputs, not fitted estimates or measurements:

| Quantity | Prediction |
|---|---:|
| Scalar mass | 1.43772e-33 eV |
| Initial phi/M | 2.240040716, derived from flatness |
| Present scalar equation of state | -0.85724556 |
| Present scalar density fraction | 0.68454600, determined by the chosen density budget |
| Age since a=1e-8 | 13.595158 Gyr |
| Acceleration onset | z=0.664007 |
| Drag sound horizon | 147.131060 Mpc |
| Linear P(k=0.1 h/Mpc,z=0) / matched LambdaCDM | 0.961362 |

Nine background checks pass. Python and CLASS H(z) agree to 1.43e-8 over 0<=z<=100. The reference/tighter CLASS comparison changes lensed TT by at most 0.138% over ell=2..1200; other spectra have different errors, including BB up to 0.561%. These checks test implementation, not the universe.

**Use synchronous gauge with this pinned CLASS scalar module.** The rejected Newtonian diagnostic and its missing-source explanation are preserved. The optional early-time theta_scf trace contains ill-conditioned infinite values; do not use that column as an observable. Core background and spectral products are finite. Read the audit before precision inference.

## Reproduce the background

Reference environment: Python 3.12.14, with the versions in requirements.txt. Work in a copy of the package when regenerating results.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 src/cosmology.py
python3 tests/verify.py
```

This writes reference.json, background.csv and verification.json. Tests cover conservation, radiation limits, a different integrator/coordinate system and higher numerical resolution. They do not compare to observational data.

## Reproduce CLASS and the figures

Requires git, make, C/C++ compilers, and a fresh checkout of the pinned public source. Third-party CLASS source and binaries are not bundled.

```bash
git clone https://github.com/lesgourg/class_public.git /your/path/class_public
git -C /your/path/class_public checkout 814ce59c380a5cccd0bed1747a384ff7bfc1f9cf
python3 src/run_class.py /your/path/class_public
```

The runner verifies the revision, applies the two-file adapter, builds CLASS, executes C1Q, the matched LambdaCDM control and a tighter C1Q run, then collects and compares outputs. Run it only on a fresh checkout; it refuses duplicate patching and an existing reproduction directory. The adapter checks exact source blob hashes before writing. Physics is never altered to obtain convergence.

To regenerate the comparison and plots directly from bundled numerical tables:

```bash
python3 src/analyze_class.py
```

Large raw CLASS tables are gzip-compressed losslessly. `results/class_output_provenance.json` records original hashes and all retained files. Headers give units and column definitions. CMB tables use dimensionless l(l+1)C_l/(2pi); matter P(k) uses (Mpc/h)^3 with k in h/Mpc. Class filenames z1,z2,z3 correspond to z=0,1,2; read each header. Precision diagnostics retain only the spectra needed for comparison. Original full runs can be regenerated.

## Freeze and revision rule

`FREEZE.json` hashes the specification, configurations, code, tests and provenance. `MANIFEST.sha256` also hashes numerical products. Check the delivered package with:

```bash
python3 src/check_freeze.py
```

These hashes establish byte identity, not mathematical or physical truth. Regenerated results can differ across platforms. A change to the action, parameters, initial data, species, source terms or empirical acceptance criteria requires a new version. No likelihood, fitted posterior, observational discovery or new Lean theorem is included.
