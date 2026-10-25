"""DESI DR2 Gaussian BAO + Pantheon+ SN-only, with full covariances.

Conventions follow the pinned public Cobaya and Pantheon+ source in the manifest.
The output chi2 profiles the common constant SN magnitude; the marginalized
log likelihood differs by a parameter-independent normalization only.
"""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
from scipy.linalg import cholesky, solve_triangular

ROOT=Path(__file__).resolve().parent

class JointLikelihood:
    def __init__(self):
        self.manifest=json.loads((ROOT/'data_manifest.json').read_text())
        assert self.manifest['stage']=='download_verified_before_likelihood_evaluation'
        for f in self.manifest['data_files']:
            b=(ROOT/f['local_path']).read_bytes()
            assert hashlib.sha256(b).hexdigest()==f['sha256']
        d=ROOT/'data'
        bao=np.genfromtxt(d/'desi_gaussian_bao_ALL_GCcomb_mean.txt',dtype=None,encoding='utf-8')
        self.bao_z=np.array([r[0] for r in bao])
        self.bao_y=np.array([r[1] for r in bao])
        self.bao_type=np.array([r[2] for r in bao])
        self.bao_cov=np.loadtxt(d/'desi_gaussian_bao_ALL_GCcomb_cov.txt')
        sn=pd.read_csv(d/'Pantheon+SH0ES.dat',sep=r'\s+')
        mask=(sn.zHD.to_numpy()>0.01)
        self.sn=sn.loc[mask].copy()
        raw=np.loadtxt(d/'Pantheon+SH0ES_STAT+SYS.cov')
        n=int(raw[0]); assert n==len(sn) and raw.size==1+n*n
        self.sn_cov=raw[1:].reshape(n,n)[np.ix_(mask,mask)]
        self.sn_y=self.sn.m_b_corr.to_numpy()
        self.sn_z=self.sn.zHD.to_numpy()
        self.sn_zhel=self.sn.zHEL.to_numpy()
        assert np.max(abs(self.sn_cov-self.sn_cov.T))<1e-10
        assert np.max(abs(self.bao_cov-self.bao_cov.T))<1e-10
        self.Lbao=cholesky(self.bao_cov,lower=True)
        self.Lsn=cholesky(self.sn_cov,lower=True)
        self.ones_white=solve_triangular(self.Lsn,np.ones(len(self.sn)),lower=True)
        self.ones_norm=float(self.ones_white@self.ones_white)
        self.z=np.r_[self.bao_z,self.sn_z]
        self.audit={'bao_observables':len(self.bao_y),'sn_rows_all':n,'sn_rows_used':len(self.sn),
          'sn_unique_objects':int(self.sn.CID.nunique()),'selection':'zHD>0.01',
          'sn_z_range':[float(self.sn_z.min()),float(self.sn_z.max())],
          'covariance_cholesky_passed':True,'nuisance':'one constant absolute magnitude, analytically profiled/marginalized',
          'sigma_M_conditional':self.ones_norm**-.5}

    def predict(self,dm,hubble,rd):
        dm=np.asarray(dm);hubble=np.asarray(hubble)
        bdm=dm[:len(self.bao_z)];bh=hubble[:len(self.bao_z)]
        dh=299792.458/bh
        dv=(self.bao_z*bdm**2*dh)**(1/3)
        out=np.empty(len(bdm))
        for t,values in [('DM_over_rs',bdm/rd),('DH_over_rs',dh/rd),('DV_over_rs',dv/rd)]:
            out[self.bao_type==t]=values[self.bao_type==t]
        assert set(self.bao_type)<=set(['DM_over_rs','DH_over_rs','DV_over_rs'])
        sn_mu=5*np.log10((1+self.sn_zhel)*dm[len(bdm):])+25
        return out,sn_mu

    def evaluate(self,prediction,observed=None,details=False):
        b,s=prediction
        by,sy=(self.bao_y,self.sn_y) if observed is None else observed
        rb=solve_triangular(self.Lbao,by-b,lower=True,check_finite=False)
        rs=solve_triangular(self.Lsn,sy-s,lower=True,check_finite=False)
        M=float(rs@self.ones_white/self.ones_norm)
        rs=rs-M*self.ones_white
        cb=float(rb@rb);cs=float(rs@rs)
        if not details:return cb+cs
        return {'chi2_bao':cb,'chi2_sn':cs,'chi2_total':cb+cs,'M_profile':M,
                'bao_residual':(by-b).tolist(),'bao_whitened_residual':rb.tolist(),
                'sn_whitened_residual':rs.tolist()}
