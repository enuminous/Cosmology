"""Preserve reference CLASS outputs losslessly and record their original hashes."""
from pathlib import Path
import argparse, gzip, hashlib, json, shutil
import numpy as np
from cosmology import ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('run_directory');args=p.parse_args()
    src=Path(args.run_directory);dst=ROOT/'results/class';dst.mkdir(exist_ok=True)
    logs=ROOT/'results/class_logs';logs.mkdir(exist_ok=True)
    records=[];nonfinite=[];required_finite=True
    for q in ['c1q','lcdm','c1q_precision']:
        files=sorted((src/'output').glob(q+'_00_*'))
        if not files:raise FileNotFoundError('Missing outputs '+q)
        for f in files:
            suffix=f.name.split('_00_',1)[1]
            if q=='c1q_precision' and suffix not in ['cl_lensed.dat','z1_pk.dat','unused_parameters','parameters.ini']:continue
            data=f.read_bytes();target=dst/f.name
            if suffix.endswith('.dat'):
                a=np.loadtxt(f);bad=np.argwhere(~np.isfinite(a))
                if len(bad):
                    nonfinite.append({'file':f.name,'count':int(len(bad)),'columns_1_based':sorted(set(int(x)+1 for x in bad[:,1]))})
                    if suffix!='perturbations_k0_s.dat':required_finite=False
            if len(data)>500000:
                target=Path(str(target)+'.gz');target.write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
            else:target.write_bytes(data)
            records.append({'original_name':f.name,'saved_name':target.name,'original_bytes':len(data),'original_sha256':hashlib.sha256(data).hexdigest()})
    for name in ['c1q-run.log','lcdm-run.log','c1q-precision-run.log']:shutil.copy2(src/name,logs/name)
    provenance={'compression':'gzip for files over 500000 bytes, lossless; original SHA256 recorded',
      'selection':'All reference C1Q and LambdaCDM outputs; tighter diagnostic retains lensed spectra, z=0 P(k), input and unused-parameter records.',
      'files':records,'finite_required_background_thermal_and_spectral_tables':required_finite,
      'optional_trace_nonfinite_entries':nonfinite,
      'optional_trace_caveat':'The optional early-time scalar fluid velocity theta_scf divides by rho_scf+p_scf, which rounds to zero for a frozen field. Infinite diagnostic entries are preserved and must not be used as physical predictions. The evolved variable is delta_phi, not this fluid velocity; see AUDIT.md.'}
    (ROOT/'results/class_output_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'saved_files':len(records),'required_finite':required_finite,'optional_nonfinite':nonfinite},indent=2))
    if not required_finite:raise SystemExit(1)

if __name__=='__main__':main()
