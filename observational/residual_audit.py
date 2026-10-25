"""Residual diagnostics specified before family fits; calibrated on same null mocks.

Prespecified summaries: maximum absolute BAO residual in marginal-sigma units;
SN covariance-weighted ln(1+z) slope after removing a constant; maximum absolute
standardized GLS SN-bin offset for boundaries .01,.05,.1,.3,.6,infinity.
These are diagnostics with a LambdaCDM parametric reference, not independent
validation or a proof that no systematic remains. No rejection threshold added.
"""
import json
import numpy as np
from scipy.linalg import solve_triangular
from likelihood import JointLikelihood,ROOT
from surrogate import Model

def main():
    l=JointLikelihood();models={k:Model(k,l) for k in ['lcdm','c1q']}
    results=json.loads((ROOT/'family_fit_results.json').read_text())
    bins=np.array([.01,.05,.1,.3,.6,np.inf]);ix=np.digitize(l.sn_z,bins)-1
    X=np.array([ix==i for i in range(len(bins)-1)],float).T
    WX=solve_triangular(l.Lsn,X,lower=True)
    bcov=np.linalg.inv(WX.T@WX);se=np.sqrt(np.diag(bcov))
    t=solve_triangular(l.Lsn,np.log1p(l.sn_z),lower=True)
    t-=l.ones_white*(l.ones_white@t/l.ones_norm);t/=np.sqrt(t@t)
    def diagnostics(kind,fit,observed):
        b,s=models[kind].prediction(fit['parameter_vector']);by,sy=observed
        white=solve_triangular(l.Lsn,sy-s-fit['M_profile'],lower=True,check_finite=False)
        coeff=bcov@WX.T@white
        rb=(by-b)/np.sqrt(np.diag(l.bao_cov))
        return {'max_abs_bao_marginal_sigma':float(max(abs(rb))),
          'abs_sn_log1pz_trend':float(abs(t@white)),
          'max_abs_sn_bin_standardized_offset':float(max(abs(coeff/se))),
          'sn_bin_offsets_mag':coeff.tolist(),'sn_bin_conditional_standard_errors_mag':se.tolist(),
          'bao_marginal_standardized_residuals':rb.tolist()}
    data={k:diagnostics(k,f,(l.bao_y,l.sn_y)) for k,f in results['fits'].items()}
    path=ROOT/'mock_results.jsonl'
    mocks=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    truth=results['fits']['lcdm'];b0,s0=models['lcdm'].prediction(truth['parameter_vector'])
    null={k:[] for k in models}
    for mock in mocks:
        rng=np.random.default_rng(np.random.SeedSequence(20261016,spawn_key=(mock['index'],)))
        observed=(b0+l.Lbao@rng.normal(size=13),s0+truth['M_profile']+l.Lsn@rng.normal(size=len(l.sn_y)))
        for k in models:null[k].append(diagnostics(k,mock['fits'][k],observed))
    for k in models:
        data[k]['diagnostic_p_MC_under_matched_LCDM']={name:(1+sum(r[name]>=data[k][name] for r in null[k]))/(len(mocks)+1)
            for name in ['max_abs_bao_marginal_sigma','abs_sn_log1pz_trend','max_abs_sn_bin_standardized_offset']} if mocks else None
    out={'scope':__doc__,'SN_bin_edges':[.01,.05,.1,.3,.6,'infinity'],'n_mocks':len(mocks),'data':data}
    (ROOT/'residual_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    for k,m in models.items():
        fit=results['fits'][k];b,s=m.prediction(fit['parameter_vector'])
        import pandas as pd
        pd.DataFrame({'z':l.bao_z,'observable':l.bao_type,'observed':l.bao_y,'predicted':b,
          'residual':l.bao_y-b,'marginal_sigma':np.sqrt(np.diag(l.bao_cov))}).to_csv(ROOT/f'fit_{k}_bao_residuals.csv',index=False)
        pd.DataFrame({'CID':l.sn.CID,'zHD':l.sn_z,'zHEL':l.sn_zhel,'m_b_corr':l.sn_y,
          'predicted_magnitude':s+fit['M_profile'],'residual':l.sn_y-s-fit['M_profile']}).to_csv(ROOT/f'fit_{k}_sn_residuals.csv',index=False)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
