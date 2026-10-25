"""Independent prior-space validation; never select points using fit results."""
import concurrent.futures,itertools,json
import numpy as np
from scipy.stats import qmc
from class_model import prediction
from likelihood import JointLikelihood,ROOT
from surrogate import BOUNDS,Model

def direct(job):
    kind,pars,z=job
    physical=list(pars[:3])+([pars[4]] if kind=='c1q' else [])
    try:return kind,pars,prediction(z,kind,physical,z_reio=pars[3]),None
    except Exception as e:return kind,pars,None,str(e)

def main():
    l=JointLikelihood();models={k:Model(k,l) for k in ['lcdm','c1q']}
    u=qmc.LatinHypercube(5,seed=20261101).random(50)
    corners=np.array(list(itertools.product([0.,1.],repeat=5)))
    u=np.r_[u,corners]
    pars=BOUNDS[:,0]+u*np.diff(BOUNDS,axis=1).ravel()
    jobs=[(kind,p if kind=='c1q' else p[:4],l.z) for p in pars for kind in ['lcdm','c1q']]
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:
        for kind,p,d,error in pool.map(direct,jobs):
            row={'kind':kind,'parameters':np.asarray(p).tolist(),'error':error}
            if d is not None:
                dm,h,rd,_=d;model=models[kind]
                h0,wb,wc=p[:3]
                point=[(wb+wc)/h0**2,1/h0**2]+([10**p[4]] if kind=='c1q' else [])
                a=model.t.weights(point);v=model.t.mean+a@model.t.basis
                ed=np.r_[np.exp(v[:13]),10**(v[26:]/5)]/h0
                eh=np.exp(v[13:26])*h0;er=model.sound_horizon(p)
                cp=l.evaluate(l.predict(dm,h,rd));ce=model.evaluate(p)
                row.update(max_distance_relative=float(np.max(abs(ed/dm-1))),
                    max_hubble_relative=float(np.max(abs(eh/h[:13]-1))),rd_relative=abs(er/rd-1),
                    chi2_abs_error=abs(cp-ce),direct_chi2=cp)
                row['passed']=bool(max(row['max_distance_relative'],row['max_hubble_relative'],row['rd_relative'])<2e-6 and row['chi2_abs_error']<.01)
            else:row['passed']=False
            results.append(row)
    # Reionization is explicitly retained as a common free parameter after the
    # original invariance assumption failed. The new 5D validation covers it.
    reio=[]
    for kind in models:
        values=[]
        for zr in [5.,7.7,12.]:
            _,_,rd,_=prediction(np.array([.5]),kind,[.674,.0223,.1204,0.] if kind=='c1q' else [.674,.0223,.1204],z_reio=zr)
            values.append(rd)
        reio.append({'kind':kind,'z_reio':[5.,7.7,12.],'rd_values':values,'max_relative':float(np.ptp(values)/np.mean(values))})
    report={'passed':all(r['passed'] for r in results),
      'independent_seed':20261101,'n_direct_comparisons':len(results),'results':results,'reionization':reio,
      'reionization_treatment':'sampled as original common free parameter, not assumed absent'}
    (ROOT/'surrogate/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VALIDATION',report['passed'],'worst', {k:max(r.get(k,np.inf) for r in results) for k in ['max_distance_relative','max_hubble_relative','rd_relative','chi2_abs_error']},flush=True)
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
