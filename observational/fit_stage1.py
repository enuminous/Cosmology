"""Equal-budget fitted-family comparison and 200 covariance-preserving mocks."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import concurrent.futures,hashlib,json,time
import numpy as np
from scipy.optimize import differential_evolution,minimize
from scipy.stats import qmc,beta
from likelihood import JointLikelihood,ROOT
from surrogate import Model,BOUNDS,NAMES

SETTINGS={'initial_population':60,'de_maxiter':80,'de_tol':1e-7,'de_atol':1e-7,
 'local_starts':3,'max_objective_calls':12000,'local_maxfun':2000,'local_ftol':1e-12,
 'local_gtol':1e-6,'optimizer_seed':20261028,'mock_seed':20261016,'mock_count':200,
 'models':['lcdm','c1q'],'nuisance':'same analytically profiled SN magnitude',
 'flat_prior_parameters_integrated_out':['ln(10^10 As)','n_s'],
 'reionization':'retained as common free parameter with original uniform [5,12] prior',
 'nominal_extra_cosmological_parameters_C1Q':1}

def lock():
    validation=json.loads((ROOT/'surrogate/validation.json').read_text())
    if not validation['passed']:raise RuntimeError('Surrogate validation has not passed')
    paths=['likelihood.py','class_model.py','surrogate.py','build_surrogate.py','build_rd_correction.py','validate_surrogate.py','fit_stage1.py','run_remaining.py','posterior.py','residual_audit.py','verify_fit.py','patch_family_shooting.py','family_shooting_adapter.json','data_manifest.json','environment.json','family_crosscheck.json','likelihood_independent_check.json','surrogate/training.json','surrogate/rd_training.json','EXECUTION_PLAN.md','IMPLEMENTATION_REVISION_V2.md','surrogate/rd_correction_lcdm.npz','surrogate/rd_correction_c1q.npz','surrogate/lcdm.npz','surrogate/c1q.npz','surrogate/rd.npz','surrogate/validation.json']
    payload={'settings':SETTINGS,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'frozen_before_family_fit'}
    p=ROOT/'implementation_lock.json'
    if p.exists():
        old=json.loads(p.read_text())
        if old['source_sha256']!=payload['source_sha256'] or old['settings']!=SETTINGS:raise RuntimeError('Implementation changed after lock; retain old fit and version the run')
    else:p.write_text(json.dumps(payload,indent=2)+'\n')

def fit(model):
    ndim=len(model.bounds);calls=0;best=[np.inf,None]
    def objective(u):
        nonlocal calls
        if calls>=SETTINGS['max_objective_calls']:return 1e100
        calls+=1
        try:v=model.evaluate(model.from_unit(u))
        except (ValueError,FloatingPointError):v=np.inf
        if v<best[0]:best[:]=[float(v),np.array(u)]
        return v
    # Same projected five-dimensional design in both families and every mock.
    pop=qmc.LatinHypercube(5,seed=SETTINGS['optimizer_seed']).random(SETTINGS['initial_population'])[:,:ndim]
    fid=np.array([.674,.049*.674**2,.265*.674**2,7.7,0.])[:ndim]
    pop[0]=model.to_unit(fid)
    start=time.monotonic()
    de=differential_evolution(objective,[(0,1)]*ndim,init=pop,maxiter=SETTINGS['de_maxiter'],
      tol=SETTINGS['de_tol'],atol=SETTINGS['de_atol'],polish=False,rng=np.random.default_rng(SETTINGS['optimizer_seed']))
    order=np.argsort(de.population_energies)[:SETTINGS['local_starts']]
    local=[]
    for i in order:
        if calls>=SETTINGS['max_objective_calls']-ndim-2:break
        result=minimize(objective,de.population[i],method='L-BFGS-B',bounds=[(0,1)]*ndim,
          options={'ftol':SETTINGS['local_ftol'],'gtol':SETTINGS['local_gtol'],'maxfun':min(SETTINGS['local_maxfun'],SETTINGS['max_objective_calls']-calls-ndim-2),'maxiter':300,'maxls':30})
        local.append({'success':bool(result.success),'message':str(result.message),'chi2':float(result.fun),'unit':result.x.tolist()})
    p=model.from_unit(best[1]);details=model.evaluate(p,True)
    good=[r['chi2'] for r in local if np.isfinite(r['chi2']) and r['chi2']<1e90]
    consistency=float(max(good)-min(good)) if len(good)>1 else None
    return {'kind':model.kind,'parameters':dict(zip(NAMES,p.tolist())),
      'parameter_vector':p.tolist(),'objective_calls':calls,'elapsed_seconds':time.monotonic()-start,
      'de_success':bool(de.success),'de_message':str(de.message),'local_runs':local,
      'restart_chi2_spread':consistency,'converged':bool(any(r['success'] for r in local) and consistency is not None and consistency<.01),**details}

WORK=None
def init_worker():
    global WORK
    l=JointLikelihood();WORK=(l,{k:Model(k,l) for k in SETTINGS['models']})

def mock_job(job):
    idx,seed_state,truth=job
    l,models=WORK;rng=np.random.default_rng(np.random.SeedSequence(SETTINGS['mock_seed'],spawn_key=(idx,)))
    p=np.asarray(truth['parameter_vector']);mu=models['lcdm'].prediction(p)
    observed=(mu[0]+l.Lbao@rng.normal(size=13),mu[1]+truth['M_profile']+l.Lsn@rng.normal(size=len(l.sn_y)))
    out={'index':idx,'seed_state':seed_state,'fits':{}}
    for k,m in models.items():m.set_observed(observed);out['fits'][k]=fit(m)
    out['T']=out['fits']['lcdm']['chi2_total']-out['fits']['c1q']['chi2_total']
    out['converged']=all(f['converged'] for f in out['fits'].values())
    return out

def main(mocks=True,reuse_fits=False):
    lock()
    if reuse_fits:
        result=json.loads((ROOT/'family_fit_results.json').read_text());fits=result['fits'];T=result['T']
    else:
        l=JointLikelihood();fits={}
        for kind in SETTINGS['models']:
            fits[kind]=fit(Model(kind,l));print('FIT',kind,json.dumps(fits[kind]),flush=True)
        T=fits['lcdm']['chi2_total']-fits['c1q']['chi2_total']
        result={'fits':fits,'T':T,'delta_AIC_C1Q_minus_LCDM':-T+2,'all_fits_converged':all(f['converged'] for f in fits.values()),
          'scope':'Stage 1 DESI DR2 + Pantheon+, common full covariance and priors; no CMB used'}
        (ROOT/'family_fit_results.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['all_fits_converged']:raise RuntimeError('Data optimization convergence gate failed')
    if not mocks:return
    seeds=np.random.SeedSequence(SETTINGS['mock_seed']).spawn(SETTINGS['mock_count'])
    states=[s.generate_state(4).tolist() for s in seeds]
    (ROOT/'mock_seeds.json').write_text(json.dumps({'root_seed':SETTINGS['mock_seed'],'child_spawn_keys':[list(s.spawn_key) for s in seeds],'child_states':states},indent=2)+'\n')
    path=ROOT/'mock_results.jsonl';existing={}
    if path.exists():
        for line in path.read_text().splitlines():
            r=json.loads(line);existing[r['index']]=r
    jobs=[(i,s,fits['lcdm']) for i,s in enumerate(states) if i not in existing]
    with path.open('a') as stream,concurrent.futures.ProcessPoolExecutor(max_workers=6,initializer=init_worker) as pool:
        for r in pool.map(mock_job,jobs,chunksize=1):
            stream.write(json.dumps(r)+'\n');stream.flush();existing[r['index']]=r
            print('MOCK',r['index']+1,'T',r['T'],'converged',r['converged'],flush=True)
    vals=[existing[i] for i in range(SETTINGS['mock_count'])]
    exceed=sum(r['T']>=T for r in vals);n=len(vals)
    interval=[0. if exceed==0 else float(beta.ppf(.025,exceed,n-exceed+1)),1. if exceed==n else float(beta.ppf(.975,exceed+1,n-exceed))]
    result['mock_calibration']={'n':n,'exceedances':exceed,'p_MC':(1+exceed)/(n+1),'binomial_95pct_interval_for_tail_probability':interval,
      'resolution_floor':1/(n+1),'all_converged':all(r['converged'] for r in vals),'failed_indices':[r['index'] for r in vals if not r['converged']],
      'passes_training_screen':bool((1+exceed)/(n+1)<=.01 and all(r['converged'] for r in vals))}
    (ROOT/'family_fit_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('CALIBRATION',json.dumps(result['mock_calibration']),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--no-mocks',action='store_true');g.add_argument('--mocks-only',action='store_true');a=p.parse_args();main(not a.no_mocks,a.mocks_only)
