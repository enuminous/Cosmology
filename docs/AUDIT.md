# Scope and evidence audit

Target: EFMW-COSMO-C1Q 1.0.0, the exact C1 restriction plus matter extension in MODEL.md. Inputs and the observational protocol were specified before evaluating an observational likelihood. Numerical diagnostics may expose implementation mistakes; correction records follow below.

The EFMW Zoo analysis skill's evidence separation, anti-circularity and novelty rules were applied. This is not a claimed full animal-by-animal Zoo run: no fixed animal I/O catalogue was loaded or invented for this task.

| Obligation | Criterion | Status |
|---|---|---|
| Action closure | Named fields, all couplings, signs, matter prescription, potential fixed | Demonstrated as an explicit definition |
| C1 relationship | Restriction made before variation; matter extension separately declared | Demonstrated algebraically |
| Dimensional consistency | Every action term dimension 4; numerical variables explicit | Demonstrated by dimensional accounting |
| Background closure | Friedmann constraint, KG equation, species laws and boundary rule specified | Demonstrated as an initial/boundary-value formulation |
| Linear closure | Scalar perturbations plus standard Einstein-Boltzmann matter and radiation | Specified; executed status in numerical reports |
| Kinetic and gradient signs | Canonical scalar and positive M^2; cs^2=cT^2=1 | Demonstrated for the action; no quantum-completion claim |
| Potential stability | V=m^2 phi^2/2>=0, m^2>0 | Demonstrated for retained sector |
| Radiation/matter transitions | Massive neutrinos integrated thermally | Numerical verification in results/verification.json |
| Continuum PDE existence | Global solution for arbitrary data | Unresolved; not implied by successful finite numerical runs |
| Novel physical law | Distinct from established quadratic quintessence | Rejected for this branch; active physical class is equivalent |
| Observational fit | Actual data, covariances, likelihood and declared inference | Unresolved; not performed |
| Full EFMW catalogue equivalence | All 585 parent source statements recovered | Not claimed; this is an explicit restriction |
| Formal proof | New Lean theorem or kernel-checked cosmological result | Not claimed |

## Independence and circularity

The scalar amplitude is solved to fill the chosen flatness budget; that cannot count as a prediction of the observed dark-energy fraction. H0 and ordinary density inputs are assumed, not discovered. The fiducial model contains no hidden Lambda, extra fitted w0/wa, or retuned sound horizon. Agreement between Python and CLASS is an implementation check sharing the same action and parameter choices. It is not two independent observations. Running deterministic equations with A_s and n_s inputs does not derive the primordial spectrum. The synthetic output is never labeled measured data.

The model deliberately retains conventional CDM. It neither demonstrates that dark matter is unnecessary nor simulates a particle dark-matter microphysics. The one-scalar restriction overlaps a mature literature; EFMW naming does not establish novelty. Relevant primary sources are in SOURCES.md.

## Implementation correction record

An initial CLASS run failed during scalar-amplitude shooting with the diagnostic "root must be bracketed in zriddr." Inspection showed that the explicit phi initial value was copied from scf_parameters before the shooting override changed parameter index 4. The adapter now refreshes the explicit phi and phi' initial values after that override. The action, mass and boundary target were not changed. The failed log was overwritten during the successful rerun; this paragraph records the observed failure rather than presenting a reconstructed log as an original artifact. No observational data were involved in the correction.

Any further numerical discrepancy, missing output or gate failure must be reported in results, not silently described as passing.

The first successful perturbation calculation used Newtonian gauge. A synchronous comparison found a 1.433% difference in lensed TT at ell=2 (maximum over ell=2..1200), while differences for ell>=30 were about 0.030% or less. Source inspection at pinned perturbations.c lines 10829-10835 found the scalar KG source uses only -metric_continuity*phi'. In Newtonian gauge metric_continuity=-3Phi', giving 3phi'Phi' but omitting phi'Psi'-2a^2 V_phi Psi from the required equation. The initialized Newtonian alpha_prime is also explicitly zero in the pinned source. Therefore that run is rejected as a complete implementation of this model; the mismatch is not interpreted as a physical gauge dependence. The synchronous scalar equation is the correct -h'phi'/2 form. Final reference, control and tightened runs use synchronous gauge, without changing the physical inputs or patching perturbations.c. Earlier configurations, logs, spectra and the numerical discrepancy are preserved under results/rejected_newtonian. We do not claim a passed independent-gauge check.

The optional single-mode time trace also exposes 82 infinite entries, confined to theta_scf (column 27) at early times. This diagnostic divides scalar momentum by rho_phi+p_phi, which rounds to zero through cancellation when the field is nearly frozen. That fluid velocity is ill-conditioned and is excluded from usable predictions. The underlying evolution integrates delta_phi and delta_phi', not theta_scf. All required background, thermodynamic, CMB, lensing, transfer and matter-power tables are finite. The raw diagnostic is retained unchanged; the count is in class_output_provenance.json. A regular scalar momentum variable, rather than division by rho_phi+p_phi, is required for any future use of the early-time trace.
