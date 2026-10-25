"""Numerical-only family adapter: original C1Q positive bracketing rule.

Apply after the frozen src/patch_class.py to pinned CLASS. Other CLASS targets
retain their original root finder. The physical action and initial surface stay
unchanged. Stops at the first sign-changing bracket on the original grid because
later brackets cannot change the prescribed first-positive-root selection.
"""
from pathlib import Path
import hashlib,json,sys
source=Path(sys.argv[1])/'source/input.c'
old=source.read_text()
needle='  dx = 1.5*f1*dxdy;'
assert old.count(needle)==1 and 'C1Q_FAMILY_BRACKET_V1' not in old
addition='''  /* C1Q_FAMILY_BRACKET_V1: numerical first-positive-root rule of
     Cosmology/src/cosmology.py; no change to action or boundary condition. */
  if (pfzw->target_name[0] == Omega_scf) {
    double left = 0.0, right, fleft, fright;
    int grid_index;
    class_call(input_fzerofun_1d(left, pfzw, &fleft, errmsg), errmsg, errmsg);
    (*fevals)++;
    for (grid_index = 0; grid_index < 37; grid_index++) {
      right = pow(10.0, -4.0 + 7.0 * grid_index / 36.0);
      class_call(input_fzerofun_1d(right, pfzw, &fright, errmsg), errmsg, errmsg);
      (*fevals)++;
      if (fright == 0.0) { *xzero = right; return _SUCCESS_; }
      if (fleft * fright < 0.0) {
        class_call(input_fzero_ridder(input_fzerofun_1d, left, right,
                     1.e-11, pfzw, &fleft, &fright, xzero, fevals, errmsg),
                     errmsg, errmsg);
        return _SUCCESS_;
      }
      left = right; fleft = fright;
    }
    class_stop(errmsg, "C1Q frozen positive-root grid has no sign-changing bracket");
  }
'''
new=old.replace(needle,addition+needle)
source.write_text(new)
report={'base_commit':'814ce59c380a5cccd0bed1747a384ff7bfc1f9cf','prerequisite':'C1Q_PATCH_V1',
 'before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(new.encode()).hexdigest(),
 'scope':'Numerical root selection only for Omega_scf; no physical change','grid':'0, 37 log-spaced values 1e-4 through 1000; first positive bracket','absolute_root_tolerance':1e-11}
(Path(__file__).resolve().parent/'family_shooting_adapter.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
