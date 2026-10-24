# Frozen validation and prospective empirical protocol

Written 16 October 2026 after reviewing published gravity summaries. This is a prospective internal protocol, **not an independently registered preregistration**. No raw observational likelihood has been evaluated for this model in this work.

## What must pass now

1. Solve the positive expanding Friedmann branch and the flatness boundary to the recorded tolerance. Do not count this calibration as validation.
2. Check scalar and thermal-neutrino conservation against independent finite differences, reproduce the massless-neutrino limit, and check -1<=w_phi<=1.
3. Compare a different evolution variable and integrator: Radau for (x,dx/dln a) versus DOP853 for (x,phi_dot/(M H0)).
4. Re-shoot with tighter tolerances, a denser thermal table and higher-order momentum quadrature. Required reference-observable relative change <2e-6.
5. Build the pinned CLASS source with the explicit adapter. Require finite background, thermodynamic, linear perturbation, CMB, lensing and matter-power outputs.
6. Compare Python and CLASS H(a) over z<=100 and scalar equation of state where dark energy is appreciable. Target relative H disagreement <2e-4; absolute w disagreement <2e-4. Different physical-constant conventions and numerical approximations must be documented rather than erased by retuning the physics.
7. For precision claims on the CLASS spectra, repeat a targeted tighter-resolution run and report actual differences. Default execution alone is not a precision certificate.

All failures stay in the audit trail. Fixing an implementation error before final freeze is permitted; fitting away a physical failure is not. The initial CLASS shooting failure and its cause are recorded in AUDIT.md.

## Statistical family, if subsequently authorized for fitting

The point in model.json is immutable. A fit is a separately identified C1Q family with free parameters [h, omega_b, omega_cdm, ln(10^10 A_s), n_s, z_reio, log10(mu)] and x_i derived by the same shooting rule. All masses, Neff, YHe, curvature, Lambda, potential shape and mode choices remain fixed. Suggested uniform prior bounds are h:[0.55,0.85], omega_b:[0.020,0.025], omega_cdm:[0.08,0.16], ln(10^10 A_s):[2.5,3.5], n_s:[0.90,1.05], z_reio:[5,12], log10(mu):[log10(0.05),log10(3)]. Record any revised bounds as a new protocol before fitting. Failed integration points receive zero prior support and retain their failure reason.

The matched LambdaCDM family has the same first six parameters and fixed neutrino/thermal conventions. C1Q therefore adds one fitted shape parameter, mu; x_i is a deterministic boundary normalization, not an additional free coordinate. Dataset nuisance parameters are counted identically in both models. Fixed illustrative inputs must not be described as inferred values. An unrestricted quintessence implementation with the same quadratic potential is an implementation control, not a distinct rival model.

## Observations and acceptance rules

Stage 1: use DESI DR2 BAO and Pantheon+ with their full published covariance and likelihood conventions for training. Before download and fitting, record release identifiers, exact files, hashes, nuisance treatment, likelihood code version and common priors in a new data manifest. No numerical likelihood is authorized to run with an empty manifest. These are existing public datasets already discussed in the literature; an analyst cannot claim to be blind to their broad results.

Stage 2: test the frozen posterior predictions on independent observables, initially Planck CMB TT/TE/EE+lensing with its full likelihood, and a later independent distance/growth release selected before viewing its values. Planck is a complementary check using a known dataset, not genuinely unseen future data. Shared sky, selection and calibration covariances must be audited. Do not treat DESI points used for training as holdout observations. Do not reuse a LambdaCDM-calibrated sound horizon or compressed CMB prior as a model-independent measurement.

Report posterior intervals, best-fit residuals, chi-square and predictive log scores. AIC=chi2_min+2k is descriptive. BIC additionally requires a defended effective sample-size convention; its N must not be selected after seeing which model wins. Avoid interpreting either as a p-value. Explicitly retain null and negative results.

For search calibration, use 200 independent synthetic data realizations generated from the matched LambdaCDM fit, with each realization preserving the chosen likelihood covariance and observational selection model. Refit both families with the same priors and optimization budget on every mock. Record seed 20261016 and the full deterministic child-seed sequence. Use T=chi2_min(LambdaCDM)-chi2_min(C1Q) as the preselected statistic, with all nuisance parameters refitted. Report p_MC=(1+#(T_mock>=T_data))/(201), its binomial uncertainty, and the finite resolution floor 1/201. If a larger equation search is performed, repeat that entire search on every mock; a two-family mock cannot calibrate a many-model selection procedure.

A model-development signal requires: all numerical gates passed; no unexplained systematic residual; a positive held-out predictive-score difference whose uncertainty excludes zero under the declared resampling scheme; and mock-calibrated p_MC<=0.01 for the preselected training statistic. This is a proposed screening criterion, not a discovery standard. A result failing these criteria is inconclusive or negative, not proof that all EFMW candidates are impossible. A genuinely incompatible measured w_phi<-1, a repeatable background mismatch, or unacceptable perturbation spectra can reject this particular branch. Any flexibility added after failure is a new model and restarts the test.

No data manifest, fitted likelihood, posterior chain or calibrated mock ensemble is supplied in this release. The numerical reference files are predictions of the fiducial model only.
