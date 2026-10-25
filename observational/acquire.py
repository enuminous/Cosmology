"""Acquire only the predeclared observational files; verify before any fit."""
from pathlib import Path
import concurrent.futures, hashlib, json, time, urllib.request

ROOT = Path(__file__).resolve().parent

def acquire(f):
    p = ROOT / f['local_path']
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        with urllib.request.urlopen(f['url'], timeout=120) as r:
            content = r.read()
        p.write_bytes(content)
    else:
        content = p.read_bytes()
    git_hash = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    if len(content) != f['bytes'] or git_hash != f['expected_git_blob_sha1']:
        raise RuntimeError('Frozen source mismatch: ' + f['key'])
    print(f['key'], len(content), 'verified', flush=True)
    return dict(f, sha256=hashlib.sha256(content).hexdigest(), verified=True)

if __name__ == '__main__':
    initial = ROOT / 'data_manifest.initial.json'
    manifest = json.loads(initial.read_text())
    manifest['initial_manifest_sha256'] = hashlib.sha256(initial.read_bytes()).hexdigest()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        manifest['data_files'] = list(pool.map(acquire, manifest['data_files']))
    manifest['stage'] = 'download_verified_before_likelihood_evaluation'
    manifest['acquired_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    (ROOT / 'data_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
