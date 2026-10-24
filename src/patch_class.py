"""Apply only to the pinned CLASS tree. Creates a transparent quadratic-potential adapter."""
from pathlib import Path
import argparse, hashlib, re

PIN='814ce59c380a5cccd0bed1747a384ff7bfc1f9cf'

def main():
    p=argparse.ArgumentParser();p.add_argument('class_directory');args=p.parse_args()
    root=Path(args.class_directory);f=root/'source/background.c';text=f.read_text()
    if 'C1Q_PATCH_V1' in text: raise SystemExit('Already patched; refusing duplicate patch')
    # Exact git-blob identity is recorded in config/class-source.json.
    import json
    expected=json.loads((Path(__file__).resolve().parents[1]/'config/class-source.json').read_text())['background_blob_sha']
    b=f.read_bytes();actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    if actual!=expected: raise SystemExit('Source mismatch: use pinned CLASS '+PIN)
    for name,body in [
      ('V_scf','return 0.5 * pow(pba->scf_parameters[0]*pba->H0,2) * phi*phi;'),
      ('dV_scf','return pow(pba->scf_parameters[0]*pba->H0,2) * phi;'),
      ('ddV_scf','return pow(pba->scf_parameters[0]*pba->H0,2);')]:
        pat=r'double '+name+r'\(\s*struct background \*pba,\s*double phi\) \{[^}]*\}'
        replacement='double '+name+'(struct background *pba, double phi) {\n  /* C1Q_PATCH_V1: x=phi/Mpl; potential units Mpc^-2; parameter[0]=m/H0. */\n  '+body+'\n}'
        text,n=re.subn(pat,replacement,text)
        if n!=1: raise SystemExit('Expected one '+name+' function; found '+str(n))
    background_text=text
    # Upstream copies explicit initial conditions before the shooting override.
    # When tuning index 4, refresh these two values after that override.
    fi=root/'source/input.c'; b=fi.read_bytes()
    meta=json.loads((Path(__file__).resolve().parents[1]/'config/class-source.json').read_text())
    if hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=meta['input_blob_sha']:
        raise SystemExit('input.c source mismatch; restore the pinned source before retrying')
    text=fi.read_text()
    needle='    class_read_double("scf_shooting_parameter",pba->scf_parameters[pba->scf_tuning_index]);'
    addition='\n    /* C1Q_PATCH_V1: refresh explicit initial conditions after shooting override. */\n    if (pba->attractor_ic_scf == _FALSE_) {\n      pba->phi_ini_scf = pba->scf_parameters[pba->scf_parameters_size-2];\n      pba->phi_prime_ini_scf = pba->scf_parameters[pba->scf_parameters_size-1];\n    }'
    if text.count(needle)!=1: raise SystemExit('Expected one initial-condition shooting hook')
    # Verify both source identities and replacement hooks before writing either file.
    input_text=text.replace(needle,needle+addition)
    f.write_text(background_text)
    fi.write_text(input_text)
    print('Applied C1Q potential/derivatives and scalar-initial-condition refresh to pinned CLASS.')

if __name__=='__main__':main()
