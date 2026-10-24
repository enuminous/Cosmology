"""Build the offline, single-file index.html using frozen background data.

Run from any directory: python3 webapp/build.py
No dependencies outside Python's standard library; no network access.
"""
from pathlib import Path
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def build():
    source = ROOT / 'results/background.csv'
    sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    expected = next(line.split('  ')[0] for line in (ROOT / 'MANIFEST.sha256').read_text().splitlines()
                    if line.split('  ')[1] == 'results/background.csv')
    if sha256 != expected:
        raise SystemExit('Frozen background identity differs from the original manifest.')
    import math
    with source.open() as handle:
        records = list(csv.DictReader(handle))
    data = dict(min=float(records[0]['ln_a']), max=float(records[-1]['ln_a']),
                source_sha256=sha256,
                source_commit='d2efa843e44ae2bf72c0bd9a4322532d606acb5f',
                columns=['ln_E', 'w_phi', 'Omega_phi', 'q'],
                rows=[[math.log(float(r['E'])), *[float(r[k]) for k in ['w_phi', 'Omega_phi', 'q']]]
                      for r in records])
    for i, r in enumerate(records):
        n = data['min'] + i * (data['max'] - data['min']) / (len(records) - 1)
        if abs(n - float(r['ln_a'])) > 1e-12:
            raise SystemExit('Background must have a uniform log-scale-factor grid.')
    html = (HERE / 'shell.html').read_text()
    parts = {'STYLE': (HERE / 'style.css').read_text(),
             'DATA': json.dumps(data, separators=(',', ':'), allow_nan=False),
             'PHYSICS': (HERE / 'physics.js').read_text(),
             'APP': (HERE / 'app.js').read_text()}
    for key, value in parts.items():
        token = '{{' + key + '}}'
        if html.count(token) != 1:
            raise SystemExit('Expected one template token: ' + token)
        html = html.replace(token, value)
    (ROOT / 'index.html').write_text(html)
    print(f'Built index.html: {len(html.encode()):,} bytes; {len(records)} frozen background samples; SHA256 {sha256}')


if __name__ == '__main__':
    build()
