"""Compare executed CLASS outputs with the background solver and make figures.

Input may be a CLASS output directory or the compressed outputs bundled here.
No observational data are used. Run from the package root.
"""
from pathlib import Path
import argparse, json, re
import numpy as np
from scipy.interpolate import CubicSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cosmology import Background, ROOT

def main():
    p=argparse.ArgumentParser()
    p.add_argument('output_directory',nargs='?',default=str(ROOT/'results/class'))
    args=p.parse_args(); directory=Path(args.output_directory)
    def find(prefix,suffix):
        f=directory/(prefix+'_00_'+suffix)
        if not f.exists(): f=Path(str(f)+'.gz')
        if not f.exists(): raise FileNotFoundError(f)
        return f
    def table(prefix,suffix):
        a=np.loadtxt(find(prefix,suffix))
        if not np.isfinite(a).all():raise ValueError('Nonfinite output '+prefix+suffix)
        return a
    bg=Background().shoot()
    b=table('c1q','background.dat'); N=-np.log1p(b[:,0])
    ng=np.linspace(-np.log(101),0,501)
    hc=CubicSpline(N,np.log(b[:,3]))(ng)
    hp=bg.at(ng)['E']*bg.m['H0_km_s_Mpc']/299792.458
    H_error=float(np.max(abs(np.exp(hc)/hp-1)))
    nw=np.linspace(-np.log(11),0,301)
    w_error=float(np.max(abs(CubicSpline(N,b[:,18]/b[:,17])(nw)-bg.at(nw)['w_phi'])))
    spectra={q:table(q,'cl_lensed.dat') for q in ['c1q','lcdm','c1q_precision']}
    powers={q:table(q,'z1_pk.dat') for q in spectra}
    ell=spectra['c1q'][:,0]
    def spectral_error(q):
        a=spectra['c1q'];r=spectra[q]
        if not np.array_equal(a[:,0],r[:,0]):raise ValueError('Multipole grids differ')
        # TE has zero crossings: use a finite auto-spectrum normalization.
        return {'lensed_TT_max_relative':float(np.max(abs(a[:,1]/r[:,1]-1))),
                'lensed_EE_max_relative':float(np.max(abs(a[:,2]/r[:,2]-1))),
                'lensed_TE_max_abs_over_sqrt_TT_EE':float(np.max(abs(a[:,3]-r[:,3])/np.sqrt(r[:,1]*r[:,2]))),
                'lensed_BB_max_relative':float(np.max(abs(a[:,4]/r[:,4]-1))),
                'lensing_phiphi_max_relative':float(np.max(abs(a[:,5]/r[:,5]-1)))}
    k=np.geomspace(.01,.2,301)
    def pk_at(q,k):
        a=powers[q];return np.exp(CubicSpline(np.log(a[:,0]),np.log(a[:,1]))(np.log(k)))
    diagnostics={}
    for q in ['c1q_precision']:
        diagnostics[q]=spectral_error(q)
        diagnostics[q]['matter_Pk_max_relative_0p01_to_0p2_h_Mpc']=float(np.max(abs(pk_at('c1q',k)/pk_at(q,k)-1)))
    logdir=ROOT/'results/class_logs'
    thermal={}
    for name,filename in [('c1q','c1q-run.log'),('lcdm','lcdm-run.log')]:
        txt=(logdir/filename).read_text()
        thermal[name]={
            'age_Gyr':float(re.search(r'-> age = ([0-9.eE+-]+)',txt)[1]),
            'r_drag_Mpc':float(re.search(r'with comoving sound horizon rs = ([0-9.eE+-]+)',txt)[1]),
            '100_theta_s_at_visibility_max':float(re.search(r'100\*theta_s = ([0-9.eE+-]+)',txt)[1]),
            'tau_reionization':float(re.search(r'reionization with optical depth = ([0-9.eE+-]+)',txt)[1])}
    unused={}
    for q in spectra:
        f=find(q,'unused_parameters')
        lines=[l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')]
        unused[q]=lines
    report={
      'status':'synthetic model predictions and numerical diagnostics; no data likelihood',
      'background_crosscheck':{'max_H_relative_z_0_to_100':H_error,'max_w_absolute_z_0_to_10':w_error,
          'limit_each':2e-4,'passed':H_error<2e-4 and w_error<2e-4},
      'finite_compared_tables':True,'unused_input_parameters':unused,
      'precision_diagnostics':diagnostics,
      'diagnostic_scope':'Synchronous gauge. CMB l=2..1200; linear matter k=0.01..0.2 h/Mpc, z=0. One tighter run does not certify all possible likelihoods.',
      'gauge_audit':'Earlier Newtonian scalar-field run rejected because the pinned scalar KG implementation omits required Newtonian lapse sources. Details and measured discrepancy preserved in results/rejected_newtonian and docs/AUDIT.md. No successful independent-gauge validation is claimed.',
      'thermal_outputs':thermal,
      'C1Q_vs_matched_LCDM':{'matter_power_ratio_at_k_0p1_h_Mpc_z0':float(pk_at('c1q',.1)/pk_at('lcdm',.1)),
          '100_theta_s_relative_shift':thermal['c1q']['100_theta_s_at_visibility_max']/thermal['lcdm']['100_theta_s_at_visibility_max']-1},
      'constant_conventions':'Python uses the explicit SI constants in numerics.json. CLASS uses its pinned constants, thermal quadrature and streaming approximations. Neither was retuned to force agreement.'}
    (ROOT/'results/class_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    z=np.linspace(0,3,301);n=-np.log1p(z);s=bg.at(n)
    ax[0,0].plot(z,s['w_phi'],color='#005c8a',label='C1Q')
    ax[0,0].axhline(-1,color='#777777',linestyle='--',label=r'$\Lambda$CDM')
    ax[0,0].set(xlabel='Redshift z',ylabel=r'$w_\phi$',title='Scalar equation of state');ax[0,0].legend()
    ax[0,1].plot(z,100*(s['E']/bg.E_lcdm(n)-1),color='#005c8a')
    ax[0,1].set(xlabel='Redshift z',ylabel='Expansion-rate difference (%)',title=r'$H_{\rm C1Q}/H_{\Lambda{\rm CDM}}-1$')
    unit=(bg.m['T_gamma0_K']*1e6)**2
    ax[1,0].plot(ell,spectra['c1q'][:,1]*unit,color='#005c8a',label='C1Q')
    ax[1,0].plot(ell,spectra['lcdm'][:,1]*unit,color='#a04b00',linestyle='--',label=r'$\Lambda$CDM')
    ax[1,0].set(xlabel=r'Multipole $\ell$',ylabel=r'$\ell(\ell+1)C_\ell^{TT}/2\pi$ ($\mu$K$^2$)',title='Lensed CMB temperature');ax[1,0].legend()
    kg=np.geomspace(.001,.3,301)
    ax[1,1].semilogx(kg,100*(pk_at('c1q',kg)/pk_at('lcdm',kg)-1),color='#005c8a')
    ax[1,1].set(xlabel=r'$k$ ($h$/Mpc)',ylabel='Linear matter power difference (%)',title='z=0; identical primordial amplitude')
    for a in ax.flat:a.grid(alpha=.18)
    fig.suptitle('EFMW-COSMO-C1Q v1.0.0 | chosen reference parameters\nSynthetic predictions; no observations fitted',fontsize=15)
    fig.savefig(ROOT/'results/predictions.png',dpi=160)
    fig.savefig(ROOT/'results/predictions.pdf')
    print(json.dumps(report,indent=2))
    if not report['background_crosscheck']['passed'] or any(unused.values()):raise SystemExit(1)

if __name__=='__main__':main()
