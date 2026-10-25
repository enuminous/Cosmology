"""Validated numerical accelerator; never changes the physical parameters."""
import numpy as np
from scipy.linalg import solve_triangular
from likelihood import ROOT

BOUNDS=np.array([[.55,.85],[.020,.025],[.08,.16],[5.,12.],[np.log10(.05),np.log10(3)]])
NAMES=['h','omega_b','omega_cdm','z_reio','log10_mu']

class Tensor:
    def __init__(self,path):
        f=np.load(path);self.coeff=f['coeff'];self.bounds=f['bounds']
        self.mean=f['mean'] if 'mean' in f else None
        self.basis=f['basis'] if 'basis' in f else None
    def weights(self,point):
        x=2*(np.asarray(point)-self.bounds[:,0])/np.diff(self.bounds,axis=1).ravel()-1
        if np.max(abs(x))>1+1e-10:raise ValueError('Surrogate extrapolation prohibited')
        v=self.coeff
        for i,xi in enumerate(x):
            n=self.coeff.shape[i]; t=np.empty(n);t[0]=1
            if n>1:t[1]=xi
            for j in range(2,n):t[j]=2*xi*t[j-1]-t[j-2]
            v=np.tensordot(t,v,axes=(0,0))
        return v

class Model:
    def __init__(self,kind,likelihood):
        self.kind=kind;self.like=likelihood
        self.t=Tensor(ROOT/'surrogate'/f'{kind}.npz');self.r=Tensor(ROOT/'surrogate/rd.npz')
        self.rc=Tensor(ROOT/'surrogate'/f'rd_correction_{kind}.npz')
        self.bounds=BOUNDS[:5 if kind=='c1q' else 4]
        self.base_sn=self.t.mean[26:]+5*np.log10(1+likelihood.sn_zhel)+25
        self.basis_sn=self.t.basis[:,26:]
        wb=solve_triangular(likelihood.Lsn,self.basis_sn.T,lower=True,check_finite=False)
        self.basis_M=likelihood.ones_white@wb/likelihood.ones_norm
        self.W=wb-likelihood.ones_white[:,None]*self.basis_M
        self.G=self.W.T@self.W
        self.set_observed()

    def set_observed(self,observed=None):
        by,sy=(self.like.bao_y,self.like.sn_y) if observed is None else observed
        self.bao_y=by
        d=solve_triangular(self.like.Lsn,sy-self.base_sn,lower=True,check_finite=False)
        self.base_M=float(self.like.ones_white@d/self.like.ones_norm)
        d=d-self.like.ones_white*self.base_M
        self.q0=float(d@d);self.q1=self.W.T@d

    def components(self,pars):
        h,wb,wc=pars[:3];om=(wb+wc)/h**2
        point=[om,1/h**2]+([10**pars[4]] if self.kind=='c1q' else [])
        a=self.t.weights(point)
        v=self.t.mean[:26]+a@self.t.basis[:,:26]
        dm=np.exp(v[:13])/h;hub=np.exp(v[13:])*h;rd=self.sound_horizon(pars)
        dh=299792.458/hub;dv=(self.like.bao_z*dm*dm*dh)**(1/3)
        b=np.empty(13)
        for label,p in [('DM_over_rs',dm/rd),('DH_over_rs',dh/rd),('DV_over_rs',dv/rd)]:
            mask=self.like.bao_type==label;b[mask]=p[mask]
        return a,b,rd

    def sound_horizon(self,pars):
        h,wb,wc,zr=pars[:4]
        point=[h,wb,wc]+([10**pars[4]] if self.kind=='c1q' else [])+[zr]
        return float(self.r.weights([wb,wc])[0])*np.exp(float(self.rc.weights(point)[0]))

    def prediction(self,pars):
        a,b,rd=self.components(pars)
        return b,self.base_sn+a@self.basis_sn-5*np.log10(pars[0])

    def evaluate(self,pars,details=False):
        pars=np.asarray(pars)
        if np.any(pars<self.bounds[:,0]) or np.any(pars>self.bounds[:,1]):return np.inf
        a,b,rd=self.components(pars)
        r=solve_triangular(self.like.Lbao,self.bao_y-b,lower=True,check_finite=False)
        cb=float(r@r);cs=float(self.q0-2*a@self.q1+a@self.G@a)
        if not details:return cb+cs
        return {'chi2_bao':cb,'chi2_sn':cs,'chi2_total':cb+cs,'M_profile':float(self.base_M-self.basis_M@a+5*np.log10(pars[0])),'r_drag_Mpc':rd}

    def from_unit(self,u):return self.bounds[:,0]+np.asarray(u)*np.diff(self.bounds,axis=1).ravel()
    def to_unit(self,p):return (np.asarray(p)-self.bounds[:,0])/np.diff(self.bounds,axis=1).ravel()
