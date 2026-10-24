# Executed numerical results

Status: **demonstrated numerical outputs of a specified hypothesis**. No observational likelihood has been evaluated. Full precision values and diagnostics are in the adjacent machine-readable reports.

## Background

The independent Python integrator shoots phi_i/M=2.24004071597258 to satisfy the chosen flat density budget. This gives phi_0/M=1.952974674, phi_dot_0/(M H0)=-0.541448007, Omega_phi0=0.684546004, w_phi0=-0.857245560, q0=-0.380201955, and acceleration onset z=0.664006535. The local slope -dw/dln(a)|0=-0.234425465 is not a fitted CPL parameter. The integrated age from a=1e-8 is 13.595158032 Gyr. The extrapolated earlier radiation-era tail is negligible and is separately labeled in reference.json.

At z=0.5 the model predicts H=91.399915 km/s/Mpc and D_M=1916.5645 Mpc. Compared with the same-input LambdaCDM model, H is 2.5301% larger and D_M is 1.7680% smaller. These differences are predictions conditional on the reference point; they are not measured residuals.

All nine background checks pass their declared gates. Maximum relative H disagreement between Python and CLASS is 1.4230e-8 over 0<=z<=100, and maximum absolute w disagreement is 1.7071e-10 over 0<=z<=10. The codes share the same physical assumptions; their agreement is not independent empirical evidence.

## Radiation and structure

The reference uses synchronous-gauge CLASS 3.4.1 with the adapter and numerical settings recorded in config. CMB spectra cover ell=2..1200; linear matter spectra and density transfers are stored at z=0,1,2. Lensing is enabled, nonlinear matter corrections are disabled, and primordial tensors are zero. Lensed BB is produced by lensing rather than a primordial tensor signal.

The drag horizon is 147.131060 Mpc; 100 theta_s at the maximum of visibility is 1.050331. The matched LambdaCDM values are 147.131069 Mpc and 1.042628 respectively. The latter angle is specifically defined at visibility maximum and should not be substituted without checking definitions into another experiment's acoustic-scale parameter. Reionization optical depth is derived as 0.053992 for C1Q versus 0.054203 for the same-midpoint control.

At k=0.1 h/Mpc and z=0, the linear C1Q/LambdaCDM matter-power ratio is 0.961361960, about 3.864% suppression for the same primordial amplitude. This is not a directly measured growth anomaly. High-k linear output is not valid as a nonlinear galaxy prediction.

## Numerical precision actually checked

Reference integration tolerance is 1e-7, perturbation sampling step 0.05, l_logstep=1.04 and k_per_decade_for_pk=40; the tighter run uses 1e-8, 0.025, 1.02 and 80 respectively. Both use background tolerance 1e-12. Maximum differences relative to the tighter run are:

| Quantity and checked range | Difference |
|---|---:|
| Lensed TT, ell=2..1200 | 0.1376% |
| Lensed EE, same range | 0.2354% |
| Lensed TE difference / sqrt(TT EE) | 0.1355% |
| Lensed BB, same range | 0.5604% |
| Lensing potential power, same range | 0.01829% |
| Linear matter P(k), 0.01..0.2 h/Mpc, z=0 | 1.848e-7 relative |

These are observed differences under one numerical refinement, not rigorous error bounds or universal likelihood accuracy. More stringent likelihood-specific convergence, start-time sensitivity and an independent correct perturbation implementation remain to be done. Optional theta_scf diagnostics have an early-time division/cancellation issue documented in AUDIT.md; they are excluded from valid predictions and retained as raw evidence. No numerical warning or failed gauge check is interpreted as new physics.
