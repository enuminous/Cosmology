"""Verify delivered file identity without re-running the scientific calculations."""
from pathlib import Path
import hashlib, json

root=Path(__file__).resolve().parents[1]
failed=[];checked=0
for line in (root/'MANIFEST.sha256').read_text().splitlines():
    wanted,name=line.split('  ',1);p=root/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=wanted:failed.append(name)
    checked+=1
freeze=json.loads((root/'FREEZE.json').read_text())
for name,wanted in freeze['specification_sha256'].items():
    p=root/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=wanted:failed.append(name)
print(json.dumps({'model':freeze['model_id'],'version':freeze['version'],'files_checked':checked,'identity_matches':not failed,'mismatches':sorted(set(failed))},indent=2))
raise SystemExit(bool(failed))
