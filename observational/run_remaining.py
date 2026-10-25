"""Sequential accuracy/fit gates, then parallel numerical calibration and chains."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(script,log,*args):
    print('START',script,*args,flush=True)
    with (ROOT/log).open('w') as stream:
        subprocess.run([sys.executable,'-u',str(ROOT/script),*args],stdout=stream,stderr=subprocess.STDOUT,check=True)
    print('COMPLETE',script,*args,flush=True)

def main():
    start=time.monotonic()
    while not (ROOT/'surrogate/rd_training.json').exists():
        if time.monotonic()-start>1800:raise TimeoutError('Sound-horizon training did not complete')
        time.sleep(5)
    run('validate_surrogate.py','surrogate-validation-v2.log')
    if not json.loads((ROOT/'surrogate/validation.json').read_text())['passed']:raise RuntimeError('Validation gate failed')
    run('fit_stage1.py','family-fit.log','--no-mocks')
    run('verify_fit.py','fit-direct-verification.log')
    jobs=[('fit_stage1.py','mock-calibration.log',['--mocks-only']),
          ('posterior.py','posterior-lcdm.log',['lcdm']),('posterior.py','posterior-c1q.log',['c1q'])]
    processes=[];streams=[]
    try:
        for script,log,args in jobs:
            stream=(ROOT/log).open('w');streams.append(stream)
            processes.append(subprocess.Popen([sys.executable,'-u',str(ROOT/script),*args],stdout=stream,stderr=subprocess.STDOUT))
            print('START',script,*args,flush=True)
        while any(p.poll() is None for p in processes):
            for p in processes:
                if p.poll() not in [None,0]:raise RuntimeError('A calibration/posterior process failed')
            time.sleep(2)
        for k in ['lcdm','c1q']:
            if not json.loads((ROOT/f'posterior_{k}.json').read_text())['converged']:raise RuntimeError(f'{k} posterior convergence gate failed')
    finally:
        for p in processes:
            if p.poll() is None:p.terminate()
        for p in processes:p.wait()
        for s in streams:s.close()
    print('COMPLETE mocks and posteriors',flush=True)
    run('residual_audit.py','residual-audit.log')
    run('make_report.py','report-generation.log')
    print('PIPELINE_COMPLETE',flush=True)

if __name__=='__main__':main()
