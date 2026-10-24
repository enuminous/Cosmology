/* Horizon Observatory: flat-FLRW background and null-ray calculations.
   Distances: Gly; time: Gyr; H: km s^-1 Mpc^-1. No observational fitting. */
(function (root) {
  'use strict';
  const MPC_KM = 3.0856775814913673e19;
  const GYR_S = 31557600e9;
  const HUNIT = MPC_KM / GYR_S;
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const exprel = x => Math.abs(x) < 1e-7 ? 1 + x / 2 + x * x / 6 + x * x * x / 24 : Math.expm1(x) / x;

  // Exact quadrature of the piecewise log-linear interpolant of E(N).
  // This is interpolation of a background, not a new scalar-field integration.
  function history(min, max, rows, H0) {
    const step = (max - min) / (rows.length - 1);
    const age = new Float64Array(rows.length), eta = new Float64Array(rows.length);
    function segment(i, d) {
      const n = min + i * step, l = rows[i][0];
      const slope = (rows[i + 1][0] - l) / step;
      return [Math.exp(-l) * d * exprel(-slope * d), Math.exp(-n - l) * d * exprel(-(1 + slope) * d)];
    }
    for (let i = 0; i < rows.length - 1; i++) {
      const [dt, de] = segment(i, step);
      age[i + 1] = age[i] + dt; eta[i + 1] = eta[i] + de;
    }
    const timeUnit = HUNIT / H0; // c = 1 Gly/Gyr by the Julian-year definitions.
    function at(n) {
      n = clamp(n, min, max);
      const i = Math.min(rows.length - 2, Math.max(0, Math.floor((n - min) / step)));
      const d = n - (min + i * step), f = d / step;
      const [dt, de] = segment(i, d), a = Math.exp(n);
      const values = rows[i].map((v, k) => v + f * (rows[i + 1][k] - v));
      const E = Math.exp(values[0]);
      return {n, a, z: 1 / a - 1, E, H: H0 * E, age: timeUnit * (age[i] + dt),
        eta: timeUnit * (eta[i] + de), rH: timeUnit / E,
        reach: a * timeUnit * (eta[i] + de), event: null,
        w: values[1], omega: values[2], q: values[3]};
    }
    return {at, min, max, timeUnit, etaEnd: timeUnit * eta[eta.length - 1]};
  }

  function c1q(data) {
    const h = history(data.min, data.max, data.rows, 67.4);
    return {...h, id: 'c1q', defaultN: 0, h0: 67.4,
      label: 'Frozen C1Q', eventStatus: 'Future not specified',
      at(n) { return {...h.at(n), event: null}; }};
  }

  function lcdm(H0 = 67.4, Om = 0.3154, count = 4001) {
    H0 = clamp(Number.isFinite(H0) ? H0 : 67.4, 50, 90);
    Om = clamp(Number.isFinite(Om) ? Om : 0.3154, 0.1, 0.5);
    const Or = 0.000092, Ol = 1 - Om - Or, min = Math.log(1e-8), integrationMax = Math.log(1e4);
    const rows = Array.from({length: count}, (_, i) => {
      const n = min + (integrationMax - min) * i / (count - 1), a = Math.exp(n);
      const r = Or / a ** 4, m = Om / a ** 3, E2 = r + m + Ol;
      return [Math.log(E2) / 2, -1, Ol / E2, (2 * r + m - 2 * Ol) / (2 * E2)];
    });
    const h = history(min, integrationMax, rows, H0);
    // Asymptotic de Sitter tail beyond a=10^4. Its omitted matter correction
    // is < 1e-12 of the tail over the permitted matter-density range.
    const etaInfinity = h.etaEnd + h.timeUnit * Math.exp(-integrationMax) / Math.sqrt(Ol);
    return {...h, max: Math.log(100), id: 'lcdm', defaultN: 0, h0: H0, Om, Or, Ol,
      etaInfinity, label: 'Flat ΛCDM', eventStatus: 'Asymptotic Λ > 0',
      at(n) { const s = h.at(clamp(n, min, Math.log(100))); return {...s, event: s.a * (etaInfinity - s.eta)}; }};
  }

  function bounce(tau = 5) {
    tau = clamp(Number.isFinite(tau) ? tau : 5, 1, 10);
    const min = -5, max = 5, etaStart = -tau * Math.asinh(5);
    return {id: 'bounce', label: 'Prescribed bounce', min, max, defaultN: 0, tau,
      etaEnd: 2 * tau * Math.asinh(5), eventStatus: 'None in eternal toy geometry',
      at(u) {
        u = clamp(u, min, max);
        const a = Math.hypot(1, u), h = u / (tau * (1 + u * u));
        const eta = tau * Math.asinh(u) - etaStart;
        return {n: u, a, z: null, E: null, H: HUNIT * h, age: tau * u, eta,
          rH: h === 0 ? Infinity : 1 / Math.abs(h), reach: a * eta,
          event: null, w: null, omega: null, q: u === 0 ? -Infinity : -1 / (u * u)};
      }};
  }

  function position(model, p) { return model.at(model.min + clamp(p, 0, 1) * (model.max - model.min)); }
  function progress(model, n) { return clamp((n - model.min) / (model.max - model.min), 0, 1); }
  function etaInverse(model, eta) {
    if (eta < model.at(model.min).eta || eta > model.at(model.max).eta) return null;
    let lo = model.min, hi = model.max;
    for (let i = 0; i < 60; i++) {
      const mid = (lo + hi) / 2;
      if (model.at(mid).eta < eta) lo = mid; else hi = mid;
    }
    return model.at((lo + hi) / 2);
  }
  function emit(model, p, distance) {
    if (!(Number.isFinite(distance) && distance > 0)) throw new RangeError('Emission distance must be positive and finite.');
    const s = position(model, p), chi = distance / s.a;
    const targetEta = s.eta + chi;
    return {p, eta: s.eta, a: s.a, distance, chi, arrival: etaInverse(model, targetEta),
      beyondEvent: model.id === 'lcdm' && targetEta >= model.etaInfinity};
  }
  function photonAt(photon, sample) {
    if (!photon) return null;
    if (sample.eta < photon.eta - 1e-10) return {status: 'before', proper: photon.distance};
    const chi = photon.chi - (sample.eta - photon.eta);
    return {status: chi <= 1e-10 ? 'arrived' : 'traveling', proper: sample.a * Math.max(0, chi), chi: Math.max(0, chi)};
  }
  root.HorizonPhysics = Object.freeze({MPC_KM, GYR_S, HUNIT, clamp, exprel, history, c1q, lcdm, bounce, position, progress, etaInverse, emit, photonAt});
  if (typeof module !== 'undefined' && module.exports) module.exports = root.HorizonPhysics;
})(globalThis);
