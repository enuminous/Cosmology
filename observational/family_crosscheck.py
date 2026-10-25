"""Independent Python/CLASS background check at three preselected family points."""
import sys,json,time
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from classy import Class
from class_model import parameters
from likelihood import ROOT
sys.path.insert(0,str(ROOT.parent/'src'))
from cosmology import Background,read_config

def main():
    rows=[]
    for mu in [.05,1.,3.]:
        start=time.monotonic();m,n=read_config()
        h=.674;wb=.0224;wc=.12
        m.update(H0_km_s_Mpc=100*h,Omega_b0=wb/h**2,Omega_cdm0=wc/h**2,mu_m_over_H0=mu)
        bg=Background(m,n).shoot();z=np.expm1(np.linspace(0,np.log(101),301));N=-np.log1p(z)
        c=Class()
        try:
            c.set(parameters('c1q',[h,wb,wc,np.log10(mu)]));c.compute(['background'])
            tab=c.get_background();hz=np.asarray(c.Hubble(z))*299792.458
            w=CubicSpline(tab['z'][::-1],(tab['(.)p_scf']/tab['(.)rho_scf'])[::-1])(z)
            py=bg.at(N);relevant=py['Omega_phi']>.001
            eh=float(np.max(abs(hz/(100*h*py['E'])-1)))
            ew=float(np.max(abs(w[relevant]-py['w_phi'][relevant])))
            row={'mu':mu,'parameters':[h,wb,wc,float(np.log10(mu))],
              'max_H_relative_z0_100':eh,'max_w_absolute_where_Omega_phi_gt_0p001':ew,
              'passed':eh<2e-4 and ew<2e-4,'python_x_initial':float(bg.xi),
              'class_x_initial':float(tab['phi_scf'][0]),'seconds':time.monotonic()-start}
            print('CROSSCHECK',json.dumps(row),flush=True);rows.append(row)
        finally:c.struct_cleanup();c.empty()
    (ROOT/'family_crosscheck.json').write_text(json.dumps({'all_passed':all(r['passed'] for r in rows),'points':rows,
        'scope':'Three preselected masses at common middle-of-prior matter parameters; not a global proof'},indent=2)+'\n')
    if not all(r['passed'] for r in rows):raise SystemExit(1)

if __name__=='__main__':main()
