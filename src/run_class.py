"""Build a fresh pinned CLASS checkout and execute the frozen configurations.

Usage: python3 src/run_class.py /absolute/path/to/fresh/class_public
Requires git checkout at the pinned commit, C/C++ compiler, make, Python deps.
Run in a working copy of this package: regenerated outputs can differ by platform.
"""
from pathlib import Path
import argparse, json, subprocess, sys
from cosmology import ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('class_directory');p.add_argument('--jobs',type=int,default=2)
    args=p.parse_args();source=Path(args.class_directory).resolve()
    pin=json.loads((ROOT/'config/class-source.json').read_text())['commit']
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if head!=pin:raise SystemExit('Wrong CLASS commit; expected '+pin)
    runs=ROOT/'reproduction_class'
    if runs.exists():raise SystemExit('reproduction_class already exists; move it aside to preserve previous runs')
    subprocess.run([sys.executable,str(ROOT/'src/patch_class.py'),str(source)],check=True)
    (runs/'output').mkdir(parents=True)
    with (runs/'build.log').open('w') as f:subprocess.run(['make','-j'+str(args.jobs),'class'],cwd=source,stdout=f,stderr=subprocess.STDOUT,check=True)
    for config,log in [('class_c1q.ini','c1q-run.log'),('class_lcdm.ini','lcdm-run.log'),('class_c1q_precision.ini','c1q-precision-run.log')]:
        with (runs/log).open('w') as f:subprocess.run([str(source/'class'),str(ROOT/'config'/config)],cwd=runs,stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run([sys.executable,str(ROOT/'src/collect_class.py'),str(runs)],check=True)
    subprocess.run([sys.executable,str(ROOT/'src/analyze_class.py')],check=True)
    print('Reference and control runs complete. Compare with the delivered manifest; do not describe synthetic outputs as observations.')

if __name__=='__main__':main()
