"""C1Q reference background solver. Predictions are synthetic, not data fits.

N=ln(a), x=phi/Mpl, y=phi_dot/(Mpl H0), E=H/H0.
Density units: rho_critical(today)=3 Mpl^2 H0^2.
Only homogeneous cosmology is numerically implemented here. See the complete
linear specification in docs/PERTURBATIONS.md; no CMB spectrum is fabricated.
"""
from pathlib import Path
import json
import numpy as np
from scipy.integrate import solve_ivp, quad
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq
from numpy.polynomial.legendre import leggauss

ROOT = Path(__file__).resolve().parents[1]

def read_config():
    return (json.loads((ROOT/'config/model.json').read_text()),
            json.loads((ROOT/'config/numerics.json').read_text()))

class ThermalNeutrinos:
    """Decoupled FD distributions: comoving momentum q=p/Tnu(a)."""
    def __init__(self, model, numerics, omega_gamma):
        self.model, self.num = model, numerics
        self.ratio = (4/11)**(1/3) * (model['N_eff']/3)**0.25
        c = numerics['physical_constants']
        self.T_eV = model['T_gamma0_K']*self.ratio*c['kB_J_K']/c['eV_J']
        q, w = leggauss(numerics['fd_quadrature_nodes'])
        self.q = (q+1)*numerics['fd_q_max']/2
        self.w = w*numerics['fd_q_max']/2/(np.exp(self.q)+1)
        self.prefactor = omega_gamma*15/np.pi**4*self.ratio**4
        grid = np.linspace(np.log(model['a_initial']), 0, numerics['thermal_table_points'])
        rho, p = np.array([self.direct(np.exp(n)) for n in grid]).T
        self.logrho = CubicSpline(grid, np.log(rho))
        self.w_spline = CubicSpline(grid, p/rho)

    def direct(self, a):
        z = np.asarray(self.model['neutrino_masses_eV'])[:,None]*a/self.T_eV
        eps = np.sqrt(self.q[None,:]**2+z*z)
        r = np.sum(self.w[None,:]*self.q[None,:]**2*eps)
        p = np.sum(self.w[None,:]*self.q[None,:]**4/(3*eps))
        return self.prefactor*r/a**4, self.prefactor*p/a**4

    def at(self, N):
        rho = np.exp(self.logrho(N))
        return rho, rho*self.w_spline(N)

class Background:
    def __init__(self, model=None, numerics=None):
        m, n = read_config()
        self.m = model if model is not None else m
        self.n = numerics if numerics is not None else n
        self.c = self.n['physical_constants']
        self.Ni = np.log(self.m['a_initial'])
        self.mu = self.m['mu_m_over_H0']
        if self.mu <= 0 or self.m['curvature_K'] != 0:
            raise ValueError('C1Q requires mu>0 and flat geometry')
        self.H0si = self.m['H0_km_s_Mpc']*1000/self.c['Mpc_m']
        rho_c_mass = 3*self.H0si**2/(8*np.pi*self.c['G_m3_kg_s2'])
        rho_gamma_mass = (np.pi**2/15*(self.c['kB_J_K']*self.m['T_gamma0_K'])**4 /
                          (self.c['hbar_J_s']**3*self.c['c_m_s']**5))
        self.Og = rho_gamma_mass/rho_c_mass
        self.nu = ThermalNeutrinos(self.m, self.n, self.Og)
        self.Om_cb = self.m['Omega_b0']+self.m['Omega_cdm0']
        self.O_de = 1-self.Om_cb-self.Og-self.nu.at(0)[0]
        if self.O_de <= 0: raise ValueError('No positive dark-energy budget')
        self.sol = None

    def components(self, N):
        a = np.exp(N)
        rn, pn = self.nu.at(N)
        return self.Om_cb/a**3, self.Og/a**4, rn, pn

    def E(self, N, x, y):
        rm, rg, rn, pn = self.components(N)
        return np.sqrt(rm+rg+rn+(y*y+self.mu**2*x*x)/6)

    def rhs(self, N, state):
        x,y = state
        e = self.E(N,x,y)
        return np.array([y/e, -3*y-self.mu**2*x/e])

    def integrate(self, xi, dense=True, method=None):
        sol=solve_ivp(self.rhs,(self.Ni,0),(xi,self.m['y_initial']),
                      method=method or self.n['background_method'],
                      rtol=self.n['rtol'],atol=self.n['atol'],
                      max_step=self.n['max_step_log_a'],dense_output=dense)
        if not sol.success: raise RuntimeError(sol.message)
        return sol

    def shoot(self):
        def residual(x):
            end = self.integrate(x,False).y[:,-1]
            return float(self.E(0,*end)**2-1)
        grid=np.r_[0,np.geomspace(1e-4,1000,37)]
        vals=np.array([residual(x) for x in grid])
        intervals=[(float(a),float(b)) for a,b,fa,fb in zip(grid[:-1],grid[1:],vals[:-1],vals[1:]) if fa*fb<0]
        if not intervals: raise RuntimeError('No root in frozen admissible range; do not retune the model')
        roots=[brentq(residual,a,b,xtol=self.n['root_xtol']) for a,b in intervals]
        self.root_scan={'range':[0,1000], 'grid_points':len(grid),'sign_change_brackets':intervals,
                        'roots_found':roots,'uniqueness_proved':False}
        self.xi=min(roots)
        self.sol=self.integrate(self.xi)
        return self

    def at(self,N):
        x,y=self.sol.sol(N)
        rm,rg,rn,pn=self.components(N)
        rp=(y*y+self.mu**2*x*x)/6
        pp=(y*y-self.mu**2*x*x)/6
        e=np.sqrt(rm+rg+rn+rp)
        eps=-(3*rm+4*rg+3*(rn+pn)+y*y)/(2*e*e)
        return dict(x=x,y=y,E=e,rho_m=rm,rho_gamma=rg,rho_nu=rn,p_nu=pn,
                    rho_phi=rp,p_phi=pp,w_phi=pp/rp,Omega_phi=rp/e**2,
                    dlnH_dN=eps,q=-1-eps)

    def E_lcdm(self,N):
        rm,rg,rn,pn=self.components(N)
        return np.sqrt(rm+rg+rn+self.O_de)

    def distance(self,z,lcdm=False):
        ef=(lambda n:self.E_lcdm(n)) if lcdm else (lambda n:self.at(n)['E'])
        integ=quad(lambda u: 1/ef(-np.log1p(u)),0,z,epsabs=1e-9,epsrel=1e-9)[0]
        return self.c['c_m_s']/1000/self.m['H0_km_s_Mpc']*integ

    def summary(self):
        s=self.at(0)
        dx,dy=self.rhs(0,[s['x'],s['y']])
        den=(s['y']**2+self.mu**2*s['x']**2)**2
        wN=4*self.mu**2*s['x']*s['y']*(s['x']*dy-s['y']*dx)/den
        age=quad(lambda n:1/self.at(n)['E'],self.Ni,0,epsabs=2e-10)[0]
        rad0=self.Og*(1+7/8*(4/11)**(4/3)*self.m['N_eff'])
        tail=self.m['a_initial']**2/(2*np.sqrt(rad0))
        qgrid=np.linspace(self.Ni,0,1001)
        qvals=self.at(qgrid)['q']
        crossings=[brentq(lambda n:self.at(n)['q'],a,b) for a,b,fa,fb in zip(qgrid[:-1],qgrid[1:],qvals[:-1],qvals[1:]) if fa*fb<0]
        distances=[]
        for z in [0.1,0.5,1.0,2.0,3.0]:
            st=self.at(-np.log1p(z)); dm=self.distance(z); dml=self.distance(z,True)
            distances.append(dict(z=z,H_km_s_Mpc=float(st['E']*self.m['H0_km_s_Mpc']),
                DM_Mpc=dm,DL_Mpc=(1+z)*dm,w_phi=float(st['w_phi']),
                delta_H_percent=float(100*(st['E']/self.E_lcdm(-np.log1p(z))-1)),
                delta_DM_percent=100*(dm/dml-1)))
        return dict(model_id=self.m['model_id'],version=self.m['version'],
            status='synthetic fiducial prediction; no observational likelihood evaluated',
            x_initial=float(self.xi),x_today=float(s['x']),y_today=float(s['y']),
            mu=self.mu,m_eV=self.mu*self.c['hbar_J_s']*self.H0si/self.c['eV_J'],
            Omega_gamma0=self.Og,Omega_nu0=float(self.nu.at(0)[0]),Omega_cb0=self.Om_cb,
            Omega_phi0=float(s['Omega_phi']),E_today=float(s['E']),
            w_phi_today=float(s['w_phi']),wa_local=float(-wN),
            wa_note='local slope -dw/dln(a) at a=1, not a fitted CPL model',
            q_today=float(s['q']),age_since_ai_Gyr=age/self.H0si/self.c['julian_year_s']/1e9,
            age_with_radiation_tail_Gyr=(age+tail)/self.H0si/self.c['julian_year_s']/1e9,
            acceleration_transition_redshifts=[float(np.exp(-n)-1) for n in crossings],
            root_scan=self.root_scan,distances=distances)

def main():
    bg=Background().shoot(); out=ROOT/'results'; out.mkdir(exist_ok=True)
    sm=bg.summary(); (out/'reference.json').write_text(json.dumps(sm,indent=2)+'\n')
    N=np.linspace(bg.Ni,0,bg.n['report_grid_points']); s=bg.at(N)
    rows=np.column_stack([N,np.exp(N),np.exp(-N)-1,s['E'],s['x'],s['y'],s['w_phi'],
                          s['Omega_phi'],s['q'],s['rho_m']/s['E']**2,
                          s['rho_gamma']/s['E']**2,s['rho_nu']/s['E']**2])
    np.savetxt(out/'background.csv',rows,delimiter=',',comments='',
               header='ln_a,a,z,E,x,y,w_phi,Omega_phi,q,Omega_cb,Omega_gamma,Omega_nu')
    print(json.dumps(sm,indent=2))

if __name__=='__main__': main()
