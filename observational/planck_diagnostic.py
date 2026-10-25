"""Full released Planck likelihood, conditional fixed-cosmology diagnostic only."""
import os
os.environ.setdefault('CLIPY_NOJAX','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import json,time,hashlib
from pathlib import Path
import numpy as np
import yaml
from scipy.optimize import minimize
from classy import Class
import clipy
from class_model import parameters
from likelihood import ROOT

PATHS={
 'highl':'hi_l/plik/plik_rd12_HM_v22b_TTTEEE.clik',
 'lowTT':'low_l/commander/commander_dx12_v3_2_29.clik',
 'lowEE':'low_l/simall/simall_100x143_offlike5_EE_Aplanck_B.clik',
 'lensing':'lensing/smicadx12_Dec5_ftl_mv2_ndclpp_p_teb_consext8.clik_lensing'}

def spectrum(kind,tight=False):
    path=ROOT/f'planck_{kind}_{"tight" if tight else "reference"}_spectra.npz'
    if path.exists():
        f=np.load(path);return {k:f[k] for k in f.files}
    p=parameters(kind)
    p.update(output='tCl,pCl,lCl,mPk',lensing='yes',l_max_scalars=3000,
        **{'P_k_max_1/Mpc':2.,'non_linear':'none','modes':'s','ic':'ad','gauge':'synchronous',
        'tol_perturbations_integration':1e-8 if tight else 1e-7,
        'perturbations_sampling_stepsize':.025 if tight else .05,
        'k_per_decade_for_pk':80 if tight else 40,'l_logstep':1.02 if tight else 1.04})
    c=Class();start=time.monotonic()
    try:
        c.set(p);c.compute()
        cl=c.lensed_cl(2508);raw=c.raw_cl(2508)
        out={k:np.asarray(cl[k])*(2.7255e6)**2 for k in ['tt','ee','bb','te']}
        out['pp']=np.asarray(raw['pp']);out['ell']=np.arange(2509)
        assert all(np.all(np.isfinite(v)) for v in out.values())
        np.savez_compressed(path,**out)
        (path.with_suffix('.json')).write_text(json.dumps({'parameters':p,'seconds':time.monotonic()-start,
           'finite':True,'theta_s_100':c.get_current_derived_parameters(['100*theta_s'])['100*theta_s'],
           'sigma8':float(c.sigma8()),'rd':float(c.rs_drag())},indent=2)+'\n')
        print('SPECTRUM',kind,tight,'seconds',time.monotonic()-start,flush=True)
        return out
    finally:c.struct_cleanup();c.empty()

class Planck:
    def __init__(self):
        root=ROOT/'data/planck/baseline/plc_3.0'
        self.likes={k:clipy.clik(str(root/p)) for k,p in PATHS.items()}
        for k,l in self.likes.items():
            if l._prior:raise RuntimeError(f'Unexpected embedded prior: {k} {l._prior}')
        specs={}
        for name in ['params_TT','params_TE','params_EE','params_calib_temp','params_calib_pol','planck_calib']:
            specs.update(yaml.safe_load((ROOT/'planck-reference'/f'{name}.yaml').read_text()))
        self.fixed={};self.free=[];self.center=[];self.scale=[];self.bounds=[];self.prior=[]
        for n,v in specs.items():
            if isinstance(v,(int,float)):self.fixed[n]=float(v);continue
            if 'value' in v:self.fixed[n]=float(v['value']);continue
            pr=v['prior'];self.free.append(n);self.prior.append(pr)
            if pr['dist']=='norm':
                self.center.append(pr['loc']);self.scale.append(pr['scale']);self.bounds.append((None,None))
            else:
                lo=pr['min'];hi=pr['max'];self.center.append((lo+hi)/2);self.scale.append((hi-lo)/2);self.bounds.append((-1.,1.))
        self.center=np.array(self.center);self.scale=np.array(self.scale)
        required=set(n for l in self.likes.values() for n in l.extra_parameter_names)
        assert required==set(self.fixed)|set(self.free),(required-(set(self.fixed)|set(self.free)))
        self.specs=specs

    def vector(self,l,cl,nuis):
        order=['tt','ee','bb','te','tb','eb']
        if len(l.lmax)==7:order=['pp']+order
        return np.r_[np.concatenate([cl[k][:n+1] if k in cl else np.zeros(n+1)
             for k,n in zip(order,l.lmax) if n>=0]),[nuis[n] for n in l.extra_parameter_names]]

    def evaluate(self,cl,u,details=False):
        vals=self.center+self.scale*np.asarray(u)
        nuis=self.fixed|dict(zip(self.free,vals))
        penalty=0.
        for x,pr in zip(vals,self.prior):
            if pr['dist']=='norm':penalty+=((x-pr['loc'])/pr['scale'])**2
            elif x<pr['min'] or x>pr['max']:return np.inf
        penalty+=((nuis['ksz_norm']+1.6*nuis['A_sz']-9.5)/3.)**2
        terms={k:-2*float(l(self.vector(l,cl,nuis))) for k,l in self.likes.items()}
        total=sum(terms.values())+penalty
        if details:return {'minus2_loglike_terms':terms,'nuisance_prior_penalty':float(penalty),
             'objective':float(total),'nuisance_parameters':{k:float(v) for k,v in nuis.items()}}
        return total

    def profile(self,cl):
        starts=[np.zeros(len(self.free))]
        ref=np.array([(self.specs[n]['ref'].get('loc',self.center[i])-self.center[i])/self.scale[i] for i,n in enumerate(self.free)])
        starts.extend([ref,.5*ref]);runs=[]
        for i,start in enumerate(starts):
            r=minimize(lambda u:self.evaluate(cl,u),start,method='L-BFGS-B',bounds=self.bounds,
                 options={'maxfun':20000,'maxiter':400,'maxls':30,'ftol':1e-11,'gtol':1e-5})
            runs.append({'success':bool(r.success),'message':str(r.message),'calls':int(r.nfev),
               'objective':float(r.fun),'unit':r.x.tolist()})
            print('PLANCK_PROFILE',i,r.success,r.fun,r.nfev,flush=True)
        best=min(runs,key=lambda r:r['objective'])
        result=self.evaluate(cl,best['unit'],True)
        result.update(optimizer_runs=runs,restart_spread=max(r['objective'] for r in runs)-best['objective'])
        result['converged']=bool(all(r['success'] for r in runs) and result['restart_spread']<.05)
        return result,best['unit']

def main(kind):
    cl=spectrum(kind);tight=spectrum(kind,True);p=Planck()
    profile,u=p.profile(tight)
    old=p.evaluate(cl,u,True)
    sl=slice(2,None)
    errors={k:float(np.max(abs(cl[k][sl]/tight[k][sl]-1))) for k in ['tt','ee','bb','pp']}
    errors['te_over_sqrt_tt_ee']=float(np.max(abs(cl['te'][sl]-tight['te'][sl])/np.sqrt(tight['tt'][sl]*tight['ee'][sl])))
    out={'kind':kind,'scope':'immutable cosmology, common Planck nuisance profile; NOT posterior predictive',
       'tight_profile':profile,'reference_at_tight_nuisance':old,
       'precision_objective_change':old['objective']-profile['objective'],'spectral_precision_differences':errors,
       'linear_theory_only':True,'full_stage2_completed':False}
    (ROOT/f'planck_diagnostic_{kind}.json').write_text(json.dumps(out,indent=2)+'\n')
    print('PLANCK_DIAGNOSTIC',kind,json.dumps(out),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['lcdm','c1q']);a=p.parse_args();main(a.kind)
