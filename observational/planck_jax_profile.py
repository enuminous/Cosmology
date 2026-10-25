"""Same fixed-point Planck objective, using Clipy's supported JAX derivatives.

Numerical performance revision only. Validate 64-bit objective against the
original NumPy backend and finite-difference gradients before optimization.
"""
import os
os.environ['CLIPY_NOJAX']=''
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('XLA_FLAGS','--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1')
import json,time
import numpy as np
import jax
import jax.numpy as jnp
from scipy.optimize import minimize
from planck_diagnostic import Planck,ROOT,spectrum

def objective(p,cl):
    def fun(u):
        vals=jnp.asarray(p.center)+jnp.asarray(p.scale)*u
        nuisance=p.fixed|dict(zip(p.free,vals))
        penalty=sum(u[i]**2 for i,pr in enumerate(p.prior) if pr['dist']=='norm')
        penalty+=((nuisance['ksz_norm']+1.6*nuisance['A_sz']-9.5)/3)**2
        total=penalty
        for l in p.likes.values():
            order=['tt','ee','bb','te','tb','eb']
            if len(l.lmax)==7:order=['pp']+order
            vector=jnp.concatenate([*[jnp.asarray(cl[k][:n+1]) if k in cl else jnp.zeros(n+1)
                 for k,n in zip(order,l.lmax) if n>=0],jnp.array([nuisance[n] for n in l.extra_parameter_names])])
            total-=2*l(vector)
        return total
    return jax.jit(jax.value_and_grad(fun)),jax.jit(fun)

def validate(p,fg,f):
    ref=json.loads((ROOT/'planck_backend_validation_reference.json').read_text());errors=[]
    for r in ref:
        u=np.array(r['unit']);v,g=fg(jnp.array(u));errors.append(abs(float(v)-r['objective']))
    u=np.array(ref[0]['unit']);v,g=fg(jnp.array(u));fd=[]
    for i in range(len(u)):
        step=np.zeros(len(u));step[i]=1e-5
        fd.append((float(f(u+step))-float(f(u-step)))/2e-5)
    derivative=float(np.max(abs(np.array(fd)-np.asarray(g))/np.maximum(1,abs(np.asarray(g)))))
    out={'maximum_numpy_objective_difference':max(errors),'maximum_relative_scaled_gradient_error':derivative,
        'jax_64bit':bool(jax.config.jax_enable_x64),'passed':max(errors)<1e-6 and derivative<1e-4 and bool(jax.config.jax_enable_x64)}
    (ROOT/'planck_backend_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print('JAX_VALIDATION',out,flush=True)
    if not out['passed']:raise RuntimeError('Planck backend validation failed')

def main(kind):
    p=Planck();lcdm=spectrum('lcdm',True);fg,f=objective(p,lcdm);validate(p,fg,f)
    tight=spectrum(kind,True);cl=spectrum(kind)
    if kind!='lcdm':fg,f=objective(p,tight)
    starts=[np.zeros(len(p.free))]
    ref=np.array([(p.specs[n]['ref'].get('loc',p.center[i])-p.center[i])/p.scale[i] for i,n in enumerate(p.free)])
    starts.extend([ref,.5*ref]);runs=[];start=time.monotonic()
    def call(u):
        v,g=fg(jnp.asarray(u));return float(v),np.asarray(g,dtype=float)
    for i,u in enumerate(starts):
        r=minimize(call,u,jac=True,method='L-BFGS-B',bounds=p.bounds,
           options={'maxfun':20000,'maxiter':400,'maxls':30,'ftol':1e-11,'gtol':1e-5})
        runs.append({'success':bool(r.success),'message':str(r.message),'calls':int(r.nfev),'iterations':int(r.nit),'objective':float(r.fun),'unit':r.x.tolist()})
        print('PLANCK_JAX_PROFILE',kind,i,r.success,r.fun,r.nfev,flush=True)
    best=min(runs,key=lambda r:r['objective']);profile=p.evaluate(tight,best['unit'],True)
    profile.update(optimizer_runs=runs,restart_spread=max(r['objective'] for r in runs)-best['objective'])
    profile['converged']=bool(all(r['success'] for r in runs) and profile['restart_spread']<.05)
    old=p.evaluate(cl,best['unit'],True);sl=slice(2,None)
    errors={k:float(np.max(abs(cl[k][sl]/tight[k][sl]-1))) for k in ['tt','ee','bb','pp']}
    errors['te_over_sqrt_tt_ee']=float(np.max(abs(cl['te'][sl]-tight['te'][sl])/np.sqrt(tight['tt'][sl]*tight['ee'][sl])))
    out={'kind':kind,'scope':'immutable cosmology, common Planck nuisance profile; NOT posterior predictive',
       'tight_profile':profile,'reference_at_tight_nuisance':old,
       'precision_objective_change':old['objective']-profile['objective'],'spectral_precision_differences':errors,
       'linear_theory_only':True,'full_stage2_completed':False,'backend':'Clipy JAX float64 with analytic derivatives',
       'optimization_seconds':time.monotonic()-start}
    (ROOT/f'planck_diagnostic_{kind}_jax.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PLANCK_JAX_DONE',kind,profile['objective'],profile['converged'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['lcdm','c1q']);main(p.parse_args().kind)
