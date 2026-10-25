"""Pinned CLASS 3.4.1, same C1Q adapter and physical conventions as freeze."""
from pathlib import Path
import time
import numpy as np
from classy import Class

REPO=Path(__file__).resolve().parents[1]

def parameters(kind='c1q',values=None,z_reio=None):
    ini=REPO/'config'/('class_c1q.ini' if kind=='c1q' else 'class_lcdm.ini')
    p={}
    for line in ini.read_text().splitlines():
        line=line.split('#')[0].strip()
        if '=' in line:
            k,v=line.split('=',1);p[k.strip()]=v.strip()
    for k in list(p):
        if k.startswith('write ') or k.endswith('_verbose') or k in ['root','output','lensing','l_max_scalars','P_k_max_1/Mpc','z_pk','k_output_values','non_linear','tol_perturbations_integration','perturbations_sampling_stepsize','k_per_decade_for_pk','l_logstep','modes','ic','gauge']:
            del p[k]
    if values is not None:
        h,wb,wc=values[:3]
        p.pop('Omega_b');p.pop('Omega_cdm')
        p.update(h=float(h),omega_b=float(wb),omega_cdm=float(wc))
        # The rectangular interpolation grid includes points outside the physical
        # prior polytope. Retain a_i=1e-8 and use the original Python gate
        # Omega_r(a_i)>0.999; all actual prior points also pass CLASS's tighter
        # default 0.9999 gate. This check changes no evolution equation.
        p['tol_initial_Omega_r']=0.001
        p['tol_thermo_integration']=1e-8
        p['thermo_integration_stepsize']=0.05
        if kind=='c1q':
            mu=10**float(values[3])
            p['scf_parameters']=f'{mu:.17g},0,0,0,{max(0.05,np.sqrt(6*max(.01,1-(wb+wc)/h**2))/mu):.17g},0'
    if z_reio is not None:p['z_reio']=float(z_reio)
    return p

def prediction(z,kind='c1q',values=None,z_reio=None,thermo=True):
    t=time.perf_counter(); c=Class();p=parameters(kind,values,z_reio)
    try:
        c.set(p);c.compute(['thermodynamics'] if thermo else ['background'])
        z=np.asarray(z,dtype=float)
        dm=np.asarray(c.angular_distance(z))*(1+z)
        hub=np.asarray(c.Hubble(z))*299792.458
        rd=float(c.rs_drag()) if thermo else None
        return dm,hub,rd,{'elapsed_seconds':time.perf_counter()-t,'parameters':p,
            'age_Gyr':float(c.age())}
    finally:
        c.struct_cleanup();c.empty()
