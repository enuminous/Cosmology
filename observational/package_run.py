"""Package only this new observational work and its reproducibility evidence."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    required=['RUN_REPORT.md','family_fit_results.json','fit_direct_verification.json',
       'posterior_lcdm.json','posterior_c1q.json','mock_results.jsonl','residual_audit.json',
       'surrogate/validation.json','implementation_lock.json','stage1_diagnostics.png']
    for n in required:
        if not (ROOT/n).is_file():raise RuntimeError('Missing completed output: '+n)
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if '__pycache__' in rel.parts or str(rel).startswith('data/planck'):continue
        if p.name.endswith('_raw.npz') or p.name in ['ARTIFACT_MANIFEST.json']:continue
        files.append(p)
    manifest={'run':'C1Q-OBS-2026-10-25','files':{str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,
        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},
        'excluded':'Public Planck likelihood package and raw interpolation training arrays; acquisition/build code and hashes included. Original git repository not duplicated.'}
    (ROOT/'ARTIFACT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    files.append(ROOT/'ARTIFACT_MANIFEST.json')
    out=ROOT.parent.parent/'C1Q-observational-execution-2026-10-25.zip'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        for p in files:archive.write(p,'observational/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(out) as archive:
        bad=archive.testzip()
        if bad:raise RuntimeError('Archive verification failed: '+bad)
    print(json.dumps({'path':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(files)}))

if __name__=='__main__':main()
