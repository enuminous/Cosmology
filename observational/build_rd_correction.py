"""Full CLASS drag-ruler correction including the original reionization prior.

The 2D dense table captures dominant baryon/CDM dependence. This tensor captures
the smaller h, scalar and reionization dependence; independent validation gates
the complete ruler before fitting. No physical dependence is assumed absent.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import concurrent.futures,itertools,json,time
import numpy as np
from class_model import prediction
from likelihood import ROOT
from surrogate import Tensor
from build_surrogate import nodes,cheb_coeff

def task(job):
    kind,index,point=job;h,wb,wc=point[:3];zr=point[-1]
    p=[h,wb,wc]+([np.log10(point[3])] if kind=='c1q' else [])
    try:
        _,_,rd,_=prediction(np.array([.5]),kind,p,z_reio=zr)
        r=Tensor(ROOT/'surrogate/rd.npz');base=float(r.weights([wb,wc])[0])
        return kind,index,np.log(rd/base),None
    except Exception as e:return kind,index,None,str(e)

def main():
    shapes={'lcdm':(4,3,5,5),'c1q':(4,3,5,7,5)}
    bounds={'lcdm':np.array([[.55,.85],[.02,.025],[.08,.16],[5,12]]),
            'c1q':np.array([[.55,.85],[.02,.025],[.08,.16],[.05,3],[5,12]])}
    values={};jobs=[];out=ROOT/'surrogate';fails=[]
    for k,shape in shapes.items():
        points=list(itertools.product(*(nodes(n,b) for n,b in zip(shape,bounds[k]))))
        values[k]=np.empty((len(points),1))
        jobs.extend((k,i,p) for i,p in enumerate(points))
    print('RD_TRAINING',len(jobs),'direct full CLASS calls',flush=True);t=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
        for j,(k,i,v,e) in enumerate(pool.map(task,jobs,chunksize=1),1):
            if e:fails.append({'kind':k,'index':i,'error':e})
            else:values[k][i]=v
            if j%100==0:print('RD_PROGRESS',j,len(jobs),'seconds',time.monotonic()-t,'failures',len(fails),flush=True)
    (out/'rd_training_failures.json').write_text(json.dumps(fails,indent=2)+'\n')
    if fails:raise RuntimeError('Full sound-horizon table has failed solver points')
    for k,v in values.items():
        coeff=cheb_coeff(v,shapes[k])
        np.savez_compressed(out/f'rd_correction_{k}.npz',coeff=coeff,bounds=bounds[k])
        np.savez_compressed(out/f'rd_correction_{k}_raw.npz',values=v)
    (out/'rd_training.json').write_text(json.dumps({'shapes':shapes,'bounds':{k:b.tolist() for k,b in bounds.items()},
        'seconds':time.monotonic()-t,'n_direct_calls':len(jobs),'role':'full thermodynamics correction, including free reionization'},indent=2)+'\n')
    print('RD_TRAINING_COMPLETE',time.monotonic()-t,flush=True)

if __name__=='__main__':main()
