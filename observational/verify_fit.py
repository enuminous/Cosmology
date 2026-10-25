"""Direct full-thermodynamic solver check of both fitted points."""
import json
import numpy as np
from classy import Class
from class_model import prediction,parameters
from likelihood import JointLikelihood,ROOT

def main():
    fits=json.loads((ROOT/'family_fit_results.json').read_text());l=JointLikelihood();out={}
    for kind,f in fits['fits'].items():
        p=f['parameter_vector'];physical=p[:3]+([p[4]] if kind=='c1q' else [])
        dm,h,rd,meta=prediction(l.z,kind,physical,z_reio=p[3])
        d=l.evaluate(l.predict(dm,h,rd),details=True)
        d={k:v for k,v in d.items() if np.isscalar(v)}
        delta=d['chi2_total']-f['chi2_total']
        d.update(parameters=f['parameters'],r_drag_Mpc=rd,age_Gyr=meta['age_Gyr'],
            surrogate_chi2_difference=delta,passed=abs(delta)<.01)
        if kind=='c1q':
            c=Class()
            try:
                c.set(parameters(kind,physical,z_reio=p[3]));c.compute(['background']);t=c.get_background()
                d['w_phi_today']=float(t['(.)p_scf'][-1]/t['(.)rho_scf'][-1])
                d['x_initial']=float(t['phi_scf'][0]);d['mu']=10**p[4]
            finally:c.struct_cleanup();c.empty()
        out[kind]=d
    report={'all_passed':all(x['passed'] for x in out.values()),'fits':out,
       'T_direct':out['lcdm']['chi2_total']-out['c1q']['chi2_total'],
       'T_surrogate':fits['T'],'scope':'Final fitted coordinates, evaluated directly; optimizer itself uses validated surrogate'}
    (ROOT/'fit_direct_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if not report['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
