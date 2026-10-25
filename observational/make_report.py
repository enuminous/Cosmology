"""Build the auditable run report from completed machine-readable outputs."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from likelihood import ROOT

def read(name):return json.loads((ROOT/name).read_text())

def main():
    fid=read('fiducial_results.json');fit=read('family_fit_results.json')
    direct=read('fit_direct_verification.json');resid=read('residual_audit.json')
    post={k:read(f'posterior_{k}.json') for k in ['lcdm','c1q']}
    mocks=[json.loads(x) for x in (ROOT/'mock_results.jsonl').read_text().splitlines()]
    cal=fit['mock_calibration'];validation=read('surrogate/validation.json')
    # Four complementary views; no chart treats correlated rows as independent.
    fig,axes=plt.subplots(2,2,figsize=(11,8.2),layout='constrained')
    fig.suptitle('C1Q observational execution — Stage 1',fontweight='bold',fontsize=16)
    ax=axes[0,0];ts=np.array([m['T'] for m in mocks])
    ax.hist(ts,bins=24,color='#849ab8',edgecolor='white')
    ax.axvline(fit['T'],color='#b33e30',lw=2,label=f"Observed T = {fit['T']:.3f}")
    ax.set(xlabel='T = χ²(ΛCDM) − χ²(C1Q)',ylabel='Number of null mocks',title=f"200 ΛCDM mocks; p_MC = {cal['p_MC']:.4f}")
    ax.legend(frameon=False)
    ax=axes[0,1]
    for k,col in [('lcdm','#386c9b'),('c1q','#b33e30')]:
        r=np.array(resid['data'][k]['bao_marginal_standardized_residuals'])
        ax.plot(np.arange(1,14),r,'o-',color=col,label=k.upper(),ms=4)
    ax.axhline(0,color='.4',lw=.7);ax.set(xlabel='DESI observable index',ylabel='Residual / marginal σ',title='BAO residuals (inference uses full covariance)');ax.legend(frameon=False)
    ax=axes[1,0]
    for k,col,shift in [('lcdm','#386c9b',-.04),('c1q','#b33e30',.04)]:
        r=resid['data'][k]
        ax.errorbar(np.arange(5)+shift,r['sn_bin_offsets_mag'],yerr=r['sn_bin_conditional_standard_errors_mag'],fmt='o',capsize=3,color=col,label=k.upper())
    ax.axhline(0,color='.4',lw=.7);ax.set_xticks(range(5),['.01–.05','.05–.1','.1–.3','.3–.6','>.6'])
    ax.set(xlabel='Supernova redshift bin',ylabel='Magnitude residual',title='SN GLS bin offsets; conditional errors')
    ax=axes[1,1];chain=np.load(ROOT/'posterior_c1q.npz')['chain']
    ax.hist(chain[:,:,4].ravel(),bins=45,density=True,color='#b33e30',alpha=.75,label='Stage-1 posterior')
    ax.axhline(1/(np.log10(3)-np.log10(.05)),color='.3',ls='--',label='Uniform log-mass prior')
    ax.set_xlim(np.log10(.05),np.log10(3))
    ax.set(xlabel='log₁₀(μ), μ = m/H₀',ylabel='Density',title='Extra scalar parameter; no CMB training');ax.legend(frameon=False)
    for ax in axes.ravel():ax.spines[['top','right']].set_visible(False)
    fig.savefig(ROOT/'stage1_diagnostics.png',dpi=160);plt.close(fig)

    lines=['# C1Q observational execution: 25 October 2026','',
      'This run executes the DESI DR2 BAO + Pantheon+ training stage of the frozen C1Q protocol. It preserves the immutable point and reports the separately fitted family. Full posterior-predictive Planck validation and a future independent release remain incomplete.','',
      '## Fitted-family result','',
      '| Model | BAO χ² | SN χ² | Total χ² |','|---|---:|---:|---:|']
    for k in ['lcdm','c1q']:
        f=fit['fits'][k];lines.append(f"| {k.upper()} | {f['chi2_bao']:.6f} | {f['chi2_sn']:.6f} | {f['chi2_total']:.6f} |")
    lines.extend(['',f"For comparison, the immutable-point totals were ΛCDM {fid['lcdm']['chi2_total']:.6f} and C1Q {fid['c1q']['chi2_total']:.6f}, an improvement of {-fid['delta_chi2_C1Q_minus_LCDM']:.6f}. Only the common SN magnitude was profiled at those fixed points; that advantage is not the family-selection statistic.",'',f"T = {fit['T']:.6f}; ΔAIC(C1Q−ΛCDM) = {fit['delta_AIC_C1Q_minus_LCDM']:.6f}. AIC is descriptive, not a p-value. Direct CLASS evaluations at the fitted coordinates give T = {direct['T_direct']:.6f}; the direct checks {'passed' if direct['all_passed'] else 'FAILED'} the declared |Δχ²|<0.01 tolerance.",'',
      f"Of {cal['n']} full-covariance null mocks, {cal['exceedances']} had T at least as large as observed. p_MC = {cal['p_MC']:.8f}; the 95% binomial interval for the underlying tail probability is {cal['binomial_95pct_interval_for_tail_probability']}. The finite-resolution floor is 1/201 = {cal['resolution_floor']:.8f}. Every mock comparison passed the declared optimizer convergence checks: {cal['all_converged']}. Failed indices: {cal['failed_indices']}.",'',
      f"**The protocol's training screen {'passes' if cal['passes_training_screen'] else 'does not pass'}.** This alone cannot establish the protocol's full model-development signal, which also requires held-out predictive improvement and the other gates.",'',
      '## Posterior intervals','',
      'Uniform priors are exactly those in the original protocol. Primordial amplitude and tilt integrate out. Reionization is retained as a common parameter because its small effect on CLASS r_drag failed the initial numerical-invariance check; this distance-only stage is not a useful independent reionization measurement. Quoted intervals are conditional on the model, fixed physical conventions and chosen priors.','',
      '| Model | Parameter | Median | 68% interval | 95% interval |','|---|---|---:|---|---|'])
    for k in ['lcdm','c1q']:
        for n in ['H0','omega_b','omega_cdm','z_reio']+(['mu'] if k=='c1q' else []):
            q=post[k]['quantiles'][n]
            lines.append(f"| {k.upper()} | {n} | {q['median']:.6g} | [{q['q16']:.6g}, {q['q84']:.6g}] | [{q['q025']:.6g}, {q['q975']:.6g}] |")
    lines.extend(['', 'H0 is in km s^-1 Mpc^-1. Distance-scale estimates are conditional on the specified baryon-density prior. The best-fit omega_b values reach opposite prior boundaries (0.025 for LCDM and 0.020 for C1Q), while the posterior spans most of that prior.'])
    df=direct['fits']['c1q']
    lines.extend(['',f"The C1Q maximum-likelihood point has mu={df['mu']:.6f} and present scalar equation of state w_phi={df['w_phi_today']:.6f}. These point estimates are separate from the posterior intervals above.",''])
    for k in ['lcdm','c1q']:
        q=post[k];lines.append(f"{k.upper()} chain IAT/stability convergence gate: {q['converged']}; estimated effective samples {q['effective_samples_estimate']}. {q['diagnostic_limit']}")
    lines.extend(['','## Residuals and numerical validity','',
      'Full correlated BAO and SN residual tables are included. The predeclared residual summaries use marginal BAO standardization, a covariance-weighted SN log(1+z) trend and five GLS SN bins. Their Monte Carlo references reuse the matched-ΛCDM mocks; they are neither independent holdouts nor proof that no systematic remains.',''])
    for k in ['lcdm','c1q']:
        lines.append(f"- {k.upper()} residual diagnostic Monte Carlo tail fractions: {resid['data'][k]['diagnostic_p_MC_under_matched_LCDM']}.")
    lines.extend(['',f"Surrogate independent validation passed: {validation['passed']} ({validation['n_direct_comparisons']} direct full-thermodynamic comparisons). The original nine numerical background gates were rerun and passed. Three preselected family masses also passed an independent Python/CLASS H and w cross-check. These finite checks are not a global numerical proof.",'',
      'The first interpolation runs failed because of CLASS scalar-amplitude bracketing and an initialization check at grid points outside the physical prior. The accepted numerical adapter uses C1Q’s documented positive-amplitude bracket scan; equations, initial surface, potential and priors were unchanged. The immutable χ² changed by only 5.1e-11. A later validation rejected the initial distance/sound-horizon approximation before fitting. The corrected implementation factors exact H0 scaling, uses h^-2 for the remaining background dependence, retains the original common reionization parameter, and uses full thermodynamic correction tensors. See IMPLEMENTATION_REVISION_V2.md. Failure logs and corrections are retained.','',
      '![Stage-1 diagnostics](stage1_diagnostics.png)','',
      '## Planck scope',''])
    plans={}
    for k in ['lcdm','c1q']:
        path=ROOT/f'planck_diagnostic_{k}_jax.json'
        if path.exists():
            plans[k]=read(path.name);r=plans[k]
            lines.append(f"{k.upper()} immutable-point Planck nuisance-profile objective (−2 log likelihood plus stated nuisance-prior penalties): {r['tight_profile']['objective']:.6f}; nuisance convergence: {r['tight_profile']['converged']}; reference-to-tighter numerical objective change: {r['precision_objective_change']:.6f}.")
    if len(plans)==2:
        delta=plans['c1q']['tight_profile']['objective']-plans['lcdm']['tight_profile']['objective']
        lines.extend(['',f"Conditional fixed-point objective difference, C1Q−ΛCDM: {delta:.6f}. This is not a fitted-family comparison, marginalized evidence, or posterior-predictive score."])
    lines.extend(['',
      'All four public Planck likelihood packages loaded and their supplied checks ran. The additional point diagnostic holds the primordial/reionization parameters fixed, profiles the same Planck foreground/calibration prescription, and retains the original linear-theory setting. A full Stage-2 result still requires integration over the Stage-1 posterior and common nuisance priors, a defensible predictive-score uncertainty calculation, and assessment of nonlinear-lensing effects. A later independent distance/growth release has not been selected or tested.','',
      '## Evidence status and independence','',
      '- **Demonstrated computationally:** the numerical reproduction, verified data acquisition, fitted likelihoods and the completed mock calculations documented in this bundle.','- **Supported but incomplete:** any apparent training advantage is conditional on the specified priors, likelihood implementation and convergence diagnostics.','- **Unresolved:** full held-out posterior prediction and a future independently selected release.','- **Not demonstrated:** new fundamental physics, empirical proof of EFMW, or the full protocol’s model-development signal.','',
      'The frozen physical model is GR with a canonical quadratic quintessence field and standard minimally coupled matter. These calculations do not establish novelty of that model class. The normalization x_initial is solved from flatness and is not independent empirical validation or an extra fitted coordinate.','',
      'The protocol is an internal prospective record, not an independently registered or blinded experiment. These public datasets and their broad results were known. Training uses 13 correlated DESI observables and 1,590 selected Pantheon+ rows (1,473 unique objects); duplicate light-curve rows are kept with the full released covariance. SN absolute magnitude is analytically marginalized/profiled with the same flat prior; SH0ES Cepheid calibration is not used. Released DESI and SN blocks are treated as independent because a joint cross-survey covariance is not supplied. The mocks preserve the released covariance and fixed redshift selection, not an end-to-end survey simulation.','',
      'The two-family null calibration does not calibrate a broader search over EFMW equations. Neither a negative result nor an incomplete gate proves that every EFMW candidate is impossible.','',
      '## Provenance and reproduction','',
      'Source model: `enuminous/Cosmology@f457a1fc414257d5e4d2ddbeb8985db2cb714363`. CLASS: `lesgourg/class_public@814ce59c380a5cccd0bed1747a384ff7bfc1f9cf`, with the original adapter followed by the recorded numerical family-shooting patch. Clipy: `CobayaSampler/clipy@4260853bbc6a6e998896ef2b22b48161209562c5`. Exact data URLs and byte hashes are in the acquisition manifests. Runtime package versions and adapter hashes are included.','',
      'See `REPRODUCE.md` for commands. The bundle contains the new observational work, result tables, chains, accepted interpolation coefficients, manifests and failure logs. Original frozen repository files are unchanged. Public Planck data and raw interpolation training arrays are excluded from the compact bundle; their acquisition/build scripts and identities are retained.',''])
    (ROOT/'RUN_REPORT.md').write_text('\n'.join(lines))
    print('Report and diagnostic figure generated.')

if __name__=='__main__':main()
