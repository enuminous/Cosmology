/* Scientific regression and standalone-bundle checks. Run: node webapp/test.cjs */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const P = require('./physics.js');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const data = JSON.parse(html.match(/<script id="c1q-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const ref = JSON.parse(fs.readFileSync(path.join(root, 'results/reference.json'), 'utf8'));
let passed = 0;
function check(name, fn) {fn(); passed++; console.log('PASS ' + name);}
function near(got, expected, tol, label = '') {assert.ok(Math.abs(got - expected) <= tol, `${label}: ${got} vs ${expected}, tolerance ${tol}`);}
const c1q = P.c1q(data), now = c1q.at(0);

check('embedded frozen background has exact source identity and all 1,001 nodes', () => {
  const source = fs.readFileSync(path.join(root, 'results/background.csv'));
  assert.equal(crypto.createHash('sha256').update(source).digest('hex'), data.source_sha256);
  assert.equal(data.rows.length, 1001);
  const rows = source.toString().trim().split('\n').slice(1).map(line => line.split(',').map(Number));
  rows.forEach((row, i) => {
    near(Math.exp(data.rows[i][0]) / row[3], 1, 1e-13);
    near(data.rows[i][1], row[6], 1e-14);
    near(data.min + i * (data.max - data.min) / 1000, row[0], 1e-12);
  });
});
check('C1Q endpoint recovers the frozen scalar and Hubble parameters', () => {
  near(now.H, 67.4, 1e-10); near(now.w, ref.w_phi_today, 1e-13);
  near(now.omega, ref.Omega_phi0, 1e-13);
  near(now.age / ref.age_since_ai_Gyr, 1, 3e-5);
  near(now.rH, 14.507302992, 1e-7);
  assert.equal(now.event, null); assert.equal(c1q.max, 0);
});
check('C1Q interpolated H(z) agrees with the frozen solver to 0.005%', () => {
  for (const point of ref.distances) near(c1q.at(-Math.log1p(point.z)).H / point.H_km_s_Mpc, 1, 5e-5);
});
const edsMin = Math.log(1e-6), edsMax = Math.log(100);
const eds = {...P.history(edsMin, edsMax, Array.from({length: 301}, (_, i) => {
  const n = edsMin + i / 300 * (edsMax - edsMin); return [-1.5 * n, 0, 0, .5];
}), 70), id: 'eds'};
check('independent Einstein–de Sitter analytic age and light-reach limits', () => {
  for (const n of [-10, -2, 0, 2]) {
    const s = eds.at(n), a = Math.exp(n), ai = Math.exp(edsMin);
    near(s.age / eds.timeUnit, 2 / 3 * (a ** 1.5 - ai ** 1.5), 5e-12);
    near(s.reach / eds.timeUnit, 2 * a * (Math.sqrt(a) - Math.sqrt(ai)), 5e-12);
  }
});
check('de Sitter analytic limits and zero-slope integration are finite', () => {
  const d = P.history(-3, 3, [[0, -1, 1, -1], [0, -1, 1, -1]], 70), s = d.at(.8);
  near(s.age / d.timeUnit, 3.8, 1e-12);
  near(s.reach / d.timeUnit, Math.expm1(3.8), 1e-11);
  near(P.exprel(0), 1, 0);
});
check('a photon outside the Hubble sphere can first recede and later arrive', () => {
  const atOne = eds.at(0), ray = P.emit(eds, P.progress(eds, 0), 1.1 * atOne.rH);
  assert.ok(P.photonAt(ray, eds.at(.001)).proper > ray.distance);
  assert.ok(ray.arrival);
  near(ray.arrival.a, (1 + 1.1 / 2) ** 2, 1e-11);
  assert.equal(P.photonAt(ray, ray.arrival).status, 'arrived');
  near(P.photonAt(ray, ray.arrival).proper, 0, 1e-10);
});
check('C1Q finite history is not silently extrapolated into a future event horizon', () => {
  const ray = P.emit(c1q, 1, 4); assert.equal(ray.arrival, null); assert.equal(ray.beyondEvent, false);
  const example = P.emit(c1q, P.progress(c1q, -Math.log(2)), 4);
  assert.ok(example.arrival.age < now.age); assert.equal(P.photonAt(example, now).status, 'arrived');
  assert.equal(P.photonAt(example, c1q.at(-2)).status, 'before');
});
const lcdm = P.lcdm();
check('ΛCDM tail, late-time de Sitter limit, and resolution convergence', () => {
  const fine = P.lcdm(67.4, .3154, 8001);
  for (const n of [-12, -7, -2, 0, Math.log(100)]) {
    const a = lcdm.at(n), b = fine.at(n);
    for (const k of ['age', 'reach', 'rH', 'event']) near(a[k] / b[k], 1, 2e-5, k);
  }
  const late = lcdm.at(Math.log(100)); near(late.event / late.rH, 1, 1e-6);
  assert.ok(lcdm.at(0).event > 15 && lcdm.at(0).event < 18);
  const ray = P.emit(lcdm, P.progress(lcdm, 0), 30); assert.equal(ray.arrival, null); assert.equal(ray.beyondEvent, true);
});
check('bounce is regular in a and conformal time; its Hubble scale diverges at t=0', () => {
  const b = P.bounce(5), s = b.at(0); near(s.a, 1, 0); near(s.H, 0, 0); assert.equal(s.rH, Infinity);
  near(s.eta, 5 * Math.asinh(5), 1e-12); near(b.at(-5).reach, 0, 1e-12);
  assert.ok(b.at(-1).H < 0 && b.at(1).H > 0); assert.equal(s.event, null);
  const ray = P.emit(b, P.progress(b, -1), 4); assert.ok(ray.arrival); assert.equal(P.photonAt(ray, b.at(5)).status, 'arrived');
});
check('all displayed backgrounds have monotonic conformal time and valid distances', () => {
  for (const m of [c1q, lcdm, P.bounce(1), P.bounce(10), P.lcdm(50, .1), P.lcdm(90, .5)]) {
    let last = -1;
    for (let i = 0; i <= 1000; i++) {
      const s = P.position(m, i / 1000);
      assert.ok(s.eta >= last); last = s.eta; assert.ok(s.a > 0 && s.reach >= 0 && s.rH > 0);
      assert.ok(Number.isFinite(s.age) && Number.isFinite(s.H));
      if (s.event !== null) assert.ok(Number.isFinite(s.event) && s.event > 0);
    }
  }
});
check('invalid photon distances fail explicitly', () => {for (const d of [NaN, -1, 0, Infinity]) assert.throws(() => P.emit(c1q, .8, d), RangeError);});
check('one standalone HTML file has valid scripts and no runtime network dependencies', () => {
  assert.doesNotMatch(html, /<script[^>]+src=|<link[^>]+(?:stylesheet|preload)|@import|\bfetch\s*\(|XMLHttpRequest|WebSocket/);
  assert.doesNotMatch(html, /\{\{(?:APP|STYLE|DATA|PHYSICS)\}\}/);
  for (const id of ['physics-core', 'application']) new vm.Script(html.match(new RegExp('<script id="' + id + '">([\\s\\S]*?)<\\/script>'))[1]);
  const shell = fs.readFileSync(path.join(__dirname, 'shell.html'), 'utf8');
  const ids = Array.from(shell.matchAll(/\bid="([^"]+)"/g), m => m[1]); assert.equal(ids.length, new Set(ids).size);
  const app = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  for (const [, id] of app.matchAll(/\$\('([^']+)'\)/g)) assert.ok(ids.includes(id), 'Missing UI element: ' + id);
});
console.log(JSON.stringify({passed, C1Q_age_Gyr: now.age, C1Q_past_reach_Gly: now.reach, Hubble_Gly: now.rH,
  LCDM_event_Gly: lcdm.at(0).event, evidence_scope: 'Numerical and packaging checks; not observational validation.'}, null, 2));
