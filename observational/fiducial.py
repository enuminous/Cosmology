"""Immutable-point observational comparison, not a cosmological parameter fit."""
import json,time
import numpy as np
from scipy.linalg import cho_solve
from scipy.stats import chi2
from likelihood import JointLikelihood,ROOT
from class_model import prediction

def main():
    l=JointLikelihood();reports={}
    # Validate magnitude profiling against an independent precision-matrix formula.
    rng=np.random.default_rng(20261016)
    r=rng.normal(size=len(l.sn_y))
    invr=cho_solve((l.Lsn,True),r)
    invone=cho_solve((l.Lsn,True),np.ones(len(r)))
    expected=float(r@invr-(r@invone)**2/np.sum(invone))
    got=l.evaluate((l.bao_y,l.sn_y-r))
    shifted=l.evaluate((l.bao_y,l.sn_y-r+17.0))
    assert abs(got-expected)<1e-6 and abs(got-shifted)<1e-6
    for kind in ['lcdm','c1q']:
        dm,h,rd,meta=prediction(l.z,kind)
        pred=l.predict(dm,h,rd);out=l.evaluate(pred,details=True)
        snwhite=out.pop('sn_whitened_residual')
        np.savetxt(ROOT/f'fiducial_{kind}_sn.csv',np.c_[l.sn_z,l.sn_y,pred[1]+out['M_profile'],snwhite],delimiter=',',header='zHD,m_b_observed,m_b_predicted,whitened_residual',comments='')
        np.savetxt(ROOT/f'fiducial_{kind}_bao.csv',np.c_[l.bao_z,l.bao_y,pred[0],np.sqrt(np.diag(l.bao_cov))],delimiter=',',header='z,observed,predicted,diagonal_sigma_for_display_only',comments='')
        out.update(r_drag_Mpc=rd,age_Gyr=meta['age_Gyr'],elapsed_seconds=meta['elapsed_seconds'],
          chi2_tail_probability_bao_fixed_point=float(chi2.sf(out['chi2_bao'],len(l.bao_y))),
          chi2_tail_probability_joint_fixed_point=float(chi2.sf(out['chi2_total'],len(l.bao_y)+len(l.sn_y)-1)))
        reports[kind]=out
        print(kind,json.dumps(out),flush=True)
    reports['delta_chi2_C1Q_minus_LCDM']=reports['c1q']['chi2_total']-reports['lcdm']['chi2_total']
    reports['scope']='Immutable fiducial physical points; only common SN magnitude offset profiled. This is not the fitted-family statistic or a mock-calibrated selection result.'
    reports['data_quality']=l.audit
    reports['likelihood_validation']={'precision_matrix_agreement_abs':abs(got-expected),'constant_magnitude_shift_invariance_abs':abs(got-shifted)}
    (ROOT/'fiducial_results.json').write_text(json.dumps(reports,indent=2)+'\n')

if __name__=='__main__':main()
