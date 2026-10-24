"""Scientific checks of limits, constraints and independent formulations."""
import sys,json,copy
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cosmology import Background, ROOT

def verify():
    bg=Background().shoot(); checks=[]; tolerances=bg.n['validation']
    def check(name,value,limit,meaning):
        passed=bool(value<=limit)
        checks.append(dict(name=name,value=float(value),limit=limit,pass_=passed,meaning=meaning))
    N=np.linspace(bg.Ni+0.03,-0.03,700);s=bg.at(N)
    check('flatness_boundary',abs(bg.at(0)['E']**2-1),tolerances['flatness_abs'],
          'Shooting boundary condition; not empirical evidence.')
    eps=1e-4
    # Five-point finite-difference identities do not reuse the RHS derivative.
    def fd5(fun):return (-fun(N+2*eps)+8*fun(N+eps)-8*fun(N-eps)+fun(N-2*eps))/(12*eps)
    dlnH=fd5(lambda n:np.log(bg.at(n)['E']))
    check('Raychaudhuri_from_finite_difference',np.max(np.abs(dlnH-s['dlnH_dN'])),
          tolerances['raychaudhuri_independent_rel'],'Check independent acceleration equation from H(a).')
    drphi=fd5(lambda n:bg.at(n)['rho_phi'])
    check('scalar_energy_continuity',np.max(abs(drphi+s['y']**2)/(s['rho_phi']+1e-30)),
          tolerances['scalar_energy_continuity_rel'],'rho_phi_N + 3(rho_phi+p_phi)=0.')
    rn,pn=bg.nu.at(N)
    rel=np.abs(bg.nu.logrho.derivative()(N)+3*(1+pn/rn))
    check('thermal_neutrino_continuity',np.max(rel),tolerances['neutrino_continuity_rel'],
          'Direct thermal integral is consistent with covariant continuity.')
    rad=(bg.at(bg.Ni)['rho_gamma']+bg.at(bg.Ni)['rho_nu'])/bg.at(bg.Ni)['E']**2
    check('initial_radiation_dominance',1-rad,1-tolerances['radiation_fraction_at_initial_min'],
          'Chosen initial surface lies in radiation domination.')
    w=bg.at(np.linspace(bg.Ni,0,1000))['w_phi']
    check('canonical_scalar_w_bounds',max(0,float(np.max(w-1)),float(np.max(-1-w))),
          tolerances['scalar_w_bound_abs'],'Positive canonical kinetic and quadratic potential imply -1<=w<=1.')
    # Alternative coordinate u=dx/dN and implicit Friedmann expression.
    def rhs_alt(n,state):
        x,u=state; rm,rg,rn,pn=bg.components(n)
        E2=(rm+rg+rn+bg.mu**2*x*x/6)/(1-u*u/6)
        hN=-(3*rm+4*rg+3*(rn+pn)+E2*u*u)/(2*E2)
        return [u,-(3+hN)*u-bg.mu**2*x/E2]
    alt=solve_ivp(rhs_alt,(bg.Ni,0),[bg.xi,0],method='Radau',rtol=5e-11,atol=5e-13,
                  max_step=.025,dense_output=True)
    assert alt.success
    na=np.linspace(bg.Ni,0,401);x,u=alt.sol(na);ref=bg.at(na)
    check('independent_variable_and_integrator',max(np.max(abs(x-ref['x'])),
          np.max(abs(u-ref['y']/ref['E']))),2e-8,
          'Radau on (phi,dphi/dln a) vs DOP853 on (phi,phi_dot).')
    # FD radiation limit with all masses explicitly zero.
    old=bg.nu.model
    bg.nu.model=copy.deepcopy(old);bg.nu.model['neutrino_masses_eV']=[0,0,0]
    measured=bg.nu.direct(1)[0]/bg.Og
    expected=7/8*(4/11)**(4/3)*bg.m['N_eff']
    bg.nu.model=old
    check('massless_neutrino_limit',abs(measured/expected-1),1e-10,
          'FD density reproduces (7/8)(4/11)^(4/3) Neff rho_gamma.')
    # Change both numerical resolution and quadrature, not physical parameters.
    tight=copy.deepcopy(bg.n);tight.update(rtol=2e-12,atol=2e-14,max_step_log_a=.025,
                                         fd_quadrature_nodes=192,thermal_table_points=4001)
    bg2=Background(copy.deepcopy(bg.m),tight).shoot()
    a,b=bg.summary(),bg2.summary()
    changes=[abs(a[k]/b[k]-1) for k in ['x_initial','w_phi_today','age_since_ai_Gyr']]
    changes += [abs(x['DM_Mpc']/y['DM_Mpc']-1) for x,y in zip(a['distances'],b['distances'])]
    check('resolution_and_quadrature_convergence',max(changes),tolerances['resolution_observable_rel'],
          'Re-shoot with tighter integration, interpolation, and thermal quadrature.')
    report={'all_passed':all(c['pass_'] for c in checks),'checks':checks,
            'evidence_scope':'Internal numerical checks; not independent experimental validation or a Lean proof.'}
    (ROOT/'results/verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['all_passed']:raise SystemExit(1)

if __name__=='__main__':verify()
