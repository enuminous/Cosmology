"""Uniform-prior Stage 1 ensemble posterior with explicit convergence gate."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import json,time
import numpy as np
import emcee
from likelihood import JointLikelihood,ROOT
from surrogate import Model,NAMES

SETTINGS={'walkers':40,'burn_in':2000,'block':1000,'maximum_production_steps':16000,
 'minimum_production_steps':4000,'minimum_chain_to_tau':50,'tau_relative_stability':.05,
 'seed':20261029,'prior':'uniform on the frozen coordinates h,omega_b,omega_cdm,z_reio,log10_mu'}

def run(kind):
    fits=json.loads((ROOT/'family_fit_results.json').read_text());l=JointLikelihood();m=Model(kind,l)
    ndim=len(m.bounds);rng=np.random.default_rng(SETTINGS['seed']);np.random.seed(SETTINGS['seed'])
    optimum=m.to_unit(fits['fits'][kind]['parameter_vector'])
    start=np.clip(optimum+rng.normal(scale=.04,size=(SETTINGS['walkers'],ndim)),1e-5,1-1e-5)
    # Jitter clipped coordinates to avoid duplicate walkers at prior boundaries.
    start=np.mod(start+rng.normal(scale=1e-5,size=start.shape),1.)
    def logp(u):
        if np.any(u<0) or np.any(u>1):return -np.inf
        try:return -.5*m.evaluate(m.from_unit(u))
        except (ValueError,FloatingPointError):return -np.inf
    sampler=emcee.EnsembleSampler(SETTINGS['walkers'],ndim,logp)
    t=time.monotonic();state=sampler.run_mcmc(start,SETTINGS['burn_in']);sampler.reset()
    previous=np.full(ndim,np.inf);history=[];converged=False
    for total in range(SETTINGS['block'],SETTINGS['maximum_production_steps']+1,SETTINGS['block']):
        state=sampler.run_mcmc(state,SETTINGS['block'])
        tau=sampler.get_autocorr_time(tol=0)
        stable=bool(np.all(abs(tau-previous)/tau<SETTINGS['tau_relative_stability']))
        converged=bool(total>=SETTINGS['minimum_production_steps'] and np.all(total>SETTINGS['minimum_chain_to_tau']*tau) and stable)
        history.append({'production_steps':total,'tau':tau.tolist(),'stable':stable,'converged':converged})
        print('POSTERIOR',kind,total,'tau',tau.tolist(),'converged',converged,flush=True)
        if converged:break
        previous=tau
    chain=sampler.get_chain();physical=m.bounds[:,0]+chain*np.diff(m.bounds,axis=1).ravel()
    np.savez_compressed(ROOT/f'posterior_{kind}.npz',chain=physical,log_prob=sampler.get_log_prob(),parameter_names=np.array(NAMES[:ndim]))
    flat=physical.reshape(-1,ndim);names=NAMES[:ndim]
    samples={n:flat[:,i] for i,n in enumerate(names)}
    samples['H0']=100*flat[:,0];samples['Omega_cb']=(flat[:,1]+flat[:,2])/flat[:,0]**2
    if kind=='c1q':samples['mu']=10**flat[:,4]
    summary={n:dict(zip(['q025','q16','median','q84','q975'],np.quantile(v,[.025,.16,.5,.84,.975]).tolist())) for n,v in samples.items()}
    report={'kind':kind,'settings':SETTINGS,'converged':converged,'history':history,'quantiles':summary,
      'effective_samples_estimate':(chain.shape[0]*chain.shape[1]/tau).tolist(),
      'mean_acceptance_fraction':float(np.mean(sampler.acceptance_fraction)),'elapsed_seconds':time.monotonic()-t,
      'prior_only_parameters':{'ln(10^10 As)':[2.5,3.5],'n_s':[.9,1.05]},
      'diagnostic_limit':'IAT and stability checks for one ensemble; not four independent-chain R-hat verification.'}
    (ROOT/f'posterior_{kind}.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['lcdm','c1q']);run(p.parse_args().kind)
