"""Deterministic CLASS training grid, independent validation before inference.

Distances depend on the sum of baryon+CDM density at background level. We use
(Omega_cb,h,mu) for distances and (omega_b,omega_cdm) for rd. The latter neglect
of late-time parameters is explicitly validated against full C1Q thermodynamics.
No observations enter training, basis construction, or validation-point selection.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from pathlib import Path
import concurrent.futures, itertools, json, time
import numpy as np
from scipy.fft import dct
from scipy.linalg import svd
from class_model import prediction
from likelihood import JointLikelihood, ROOT

BOUNDS=np.array([[.1/.85**2,.185/.55**2],[.55,.85],[.05,3.]])

def nodes(n,b):
    return (b[0]+b[1])/2+(b[1]-b[0])/2*np.cos(np.pi*np.arange(n)/(n-1))

def task(spec):
    kind,idx,point,z=spec
    try:
        if kind=='rd':
            wb,wc=point
            _,_,rd,_=prediction(np.array([.5]),'lcdm',[.674,wb,wc],thermo=True)
            return kind,idx,np.array([rd]),None
        om,h=point[:2];mu=point[2] if kind=='c1q' else 0
        pars=[h,.0225,om*h*h-.0225]+([np.log10(mu)] if kind=='c1q' else [])
        dm,hub,_,_=prediction(z,kind,pars,thermo=False)
        out=np.r_[np.log(dm[:13]*h),np.log(hub[:13]/h),5*np.log10(dm[13:]*h)]
        return kind,idx,out,None
    except Exception as e:return kind,idx,None,str(e)

def cheb_coeff(values,shape,inverse_h=False):
    out=values.reshape(tuple(shape)+values.shape[1:])
    for axis,n in enumerate(shape):
        if inverse_h and axis==1:
            # After exact H0 factors are removed, radiation/neutrino density
            # dependence is naturally linear in h^-2. Fit this small remaining
            # dependence in that coordinate using the existing direct nodes.
            hs=nodes(n,BOUNDS[1]);u=1/hs**2
            lo,hi=1/BOUNDS[1,1]**2,1/BOUNDS[1,0]**2
            x=2*(u-lo)/(hi-lo)-1
            vandermonde=np.polynomial.chebyshev.chebvander(x,n-1)
            moved=np.moveaxis(out,axis,0);original=moved.shape
            moved=np.linalg.solve(vandermonde,moved.reshape(n,-1)).reshape(original)
            out=np.moveaxis(moved,0,axis)
            continue
        out=dct(out,type=1,axis=axis)/(n-1)
        sl=[slice(None)]*out.ndim;sl[axis]=[0,n-1];out[tuple(sl)]*=.5
    return out

def compress(values,rank=24):
    mean=values.mean(axis=0);a=values-mean
    r=min(rank+12,min(a.shape))
    random=np.random.default_rng(20261026).normal(size=(a.shape[1],r))
    q,_=np.linalg.qr(a@random,mode='reduced')
    _,_,vt=svd(q.T@a,full_matrices=False)
    basis=vt[:min(rank,len(vt))]
    weights=a@basis.T
    err=float(np.max(abs(a-weights@basis)))
    return mean,basis,weights,err

def build(shape=(18,5,24),workers=6):
    l=JointLikelihood();output=ROOT/'surrogate';output.mkdir(exist_ok=True)
    shapes={'lcdm':shape[:2],'c1q':shape,'rd':(12,14)}
    bounds={'lcdm':BOUNDS[:2],'c1q':BOUNDS,'rd':np.array([[.020,.025],[.08,.16]])}
    jobs=[];tables={};cached={};fails=[]
    for kind,sz in shapes.items():
        points=list(itertools.product(*(nodes(n,b) for n,b in zip(sz,bounds[kind]))))
        shapeid='x'.join(map(str,sz))
        cache=output/f'{kind}_{shapeid}_raw.npz'
        if cache.exists() and not (kind=='rd' and 'tight_thermo' not in np.load(cache)):
            old=np.load(cache);tables[kind]=old['values'].copy();cached[kind]=True
            if kind!='rd' and 'h_factored' not in old:
                hs=np.array([p[1] for p in points])
                tables[kind][:,:13]+=np.log(hs)[:,None]
                tables[kind][:,13:26]-=np.log(hs)[:,None]
                tables[kind][:,26:]+=5*np.log10(hs)[:,None]
                np.savez_compressed(cache,values=tables[kind],h_factored=True)
        else:
            tables[kind]=np.empty((len(points),1 if kind=='rd' else 26+len(l.sn_z)))
            for i,p in enumerate(points):jobs.append((kind,i,p,l.z))
    print('PROGRESS training',len(jobs),'direct CLASS calculations',flush=True)
    start=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for j,(kind,idx,value,error) in enumerate(pool.map(task,jobs,chunksize=1),1):
            if error:fails.append({'kind':kind,'index':idx,'error':error})
            else:tables[kind][idx]=value
            if j%100==0:print('PROGRESS',j,'/',len(jobs),'elapsed',round(time.monotonic()-start,1),'failures',len(fails),flush=True)
    (output/'training_failures.json').write_text(json.dumps(fails,indent=2)+'\n')
    if fails:raise RuntimeError(f'{len(fails)} CLASS grid failures; no surrogate accepted')
    reports={}
    for kind,values in tables.items():
        sz=shapes[kind];shapeid='x'.join(map(str,sz))
        if kind not in cached:np.savez_compressed(output/f'{kind}_{shapeid}_raw.npz',values=values,h_factored=True,tight_thermo=True)
        if kind=='rd':
            coeff=cheb_coeff(values,sz)
            np.savez_compressed(output/f'{kind}.npz',coeff=coeff,bounds=bounds[kind])
            reports[kind]={'shape':sz}
        else:
            mean,basis,weights,error=compress(values)
            if error>1e-8:raise RuntimeError(f'Compression error {kind} {error}')
            coeff=cheb_coeff(weights,sz,inverse_h=True)
            transformed=bounds[kind].copy();transformed[1]=[1/.85**2,1/.55**2]
            np.savez_compressed(output/f'{kind}.npz',coeff=coeff,bounds=transformed,mean=mean,basis=basis,h_factored=True,inverse_h_coordinate=True)
            reports[kind]={'shape':sz,'max_training_compression_error':error,'rank':len(basis)}
    (output/'training.json').write_text(json.dumps({'models':reports,'elapsed_seconds':time.monotonic()-start,'observation_values_used':False},indent=2)+'\n')
    print('PROGRESS training complete',json.dumps(reports),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--shape',nargs=3,type=int,default=[18,5,24]);p.add_argument('--workers',type=int,default=6)
    a=p.parse_args();build(tuple(a.shape),a.workers)
