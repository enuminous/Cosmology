(function () {
  'use strict';
  const P = HorizonPhysics;
  const $ = id => document.getElementById(id);
  const data = JSON.parse($('c1q-data').textContent);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const palette = {
    aurora: {rgb: '130,234,212', accent: '#82ead4', second: '#7da9f2', gold: '#dfb87c'},
    violet: {rgb: '183,163,250', accent: '#b7a3fa', second: '#69cdd9', gold: '#e3bf91'},
    ember: {rgb: '247,183,122', accent: '#f7b77a', second: '#d990b3', gold: '#b2c5e4'}
  };
  const state = {model: 'c1q', view: 'atlas', p: 1, h0: 67.4, om: 0.3154, tau: 5,
    depth: 6, ratio: 0.62, palette: 'aurora', yaw: -0.3, pitch: 0.36, zoom: 1,
    orbit: !reduced, still: reduced, playing: false, speed: 1,
    layers: {hubble: true, past: true, event: true, tracers: true}};
  let model = P.c1q(data), sample = P.position(model, state.p), photon = null;
  let visualTime = 12, lastTime = 0, lastPaint = 0, lastUI = 0, dirty = true, chartDirty = true;
  let toastTimer = 0, dragging = null, focus = false, curves = [];
  const cvs = $('universe'), ctx = cvs.getContext('2d', {alpha: false});
  const chart = $('timeline-chart'), chartCtx = chart.getContext('2d');
  if (!ctx || !chartCtx) {
    $('scene-title').textContent = 'Canvas is unavailable.';
    $('scene-subtitle').textContent = 'Open this file in a browser with Canvas 2D enabled.';
    return;
  }
  let W = 1, H = 1, dpr = 1, backdrop, nebula, cloudSprites = [], chartW = 1, chartH = 1;
  const themes = () => palette[state.palette];
  const alpha = (rgb, opacity) => `rgba(${rgb},${Math.max(0, Math.min(1, opacity))})`;
  function rgba(hex, a) { return `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a})`; }
  function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t ^= t + Math.imul(t ^ t >>> 7, 61 | t); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const random = rng(102001);
  const normal = () => Math.sqrt(-2 * Math.log(Math.max(random(), 1e-9))) * Math.cos(2 * Math.PI * random());
  const stars = Array.from({length: 950}, () => ({x: random(), y: random(), r: .2 + random() ** 5 * 1.7, a: .15 + random() * .6, hue: random()}));
  const anchors = Array.from({length: 55}, () => {
    const z = 2 * random() - 1, t = Math.PI * 2 * random(), r = 1.3 * Math.cbrt(random());
    return [r * Math.sqrt(1 - z * z) * Math.cos(t), r * z, r * Math.sqrt(1 - z * z) * Math.sin(t)];
  });
  const links = [], seen = new Set();
  anchors.forEach((a, i) => {
    const nearest = anchors.map((b, j) => ({j, d: Math.hypot(...a.map((v, k) => v - b[k]))})).filter(v => v.j !== i).sort((a, b) => a.d - b.d).slice(0, 3);
    for (const {j} of nearest) {
      const key = [i, j].sort((a, b) => a - b).join(':');
      if (!seen.has(key)) { seen.add(key); links.push([a, anchors[j]]); }
    }
  });
  const motes = [];
  for (const [a, b] of links) for (let i = 0; i < 17; i++) {
    const f = random(), jitter = .018 + .027 * Math.sin(f * Math.PI);
    motes.push({v: a.map((v, k) => v * (1 - f) + b[k] * f + normal() * jitter), r: .25 + random() ** 3 * 1.2, tint: random(), phase: random() * 6.28});
  }
  for (let i = 0; i < 500; i++) {
    const t = random() * 6.283, z = 2 * random() - 1, r = 1.3 * Math.cbrt(random());
    motes.push({v: [r * Math.sqrt(1 - z * z) * Math.cos(t), r * z, r * Math.sqrt(1 - z * z) * Math.sin(t)], r: .25 + random() * .65, tint: random(), phase: random() * 6.28});
  }

  function fmt(v, digits = 3) {
    if (v === Infinity) return '∞';
    if (v === -Infinity) return '−∞';
    if (v == null || !Number.isFinite(v)) return '—';
    if (Math.abs(v) > 0 && (Math.abs(v) < 0.001 || Math.abs(v) >= 1e5)) return v.toExponential(2).replace('e+', 'e');
    return v.toFixed(digits).replace('-', '−');
  }
  function short(v) { return Math.abs(v) >= 100 ? fmt(v, 1) : fmt(v, 2); }
  function announce(text) {
    $('toast').textContent = text; $('toast').classList.add('visible');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('visible'), 4700);
  }
  function syncRange(el) { el.style.setProperty('--fill', 100 * (Number(el.value) - Number(el.min)) / (Number(el.max) - Number(el.min)) + '%'); }
  function setText(id, text) { const node = $(id); if (node.textContent !== text) node.textContent = text; }
  function setPlaying(playing) {
    state.playing = playing;
    $('play-icon').setAttribute('href', playing ? '#i-pause' : '#i-play');
    $('play').setAttribute('aria-label', playing ? 'Pause cosmic time' : 'Play cosmic time');
    dirty = chartDirty = true;
    updateUI();
  }
  function setP(p, stop = true) {
    state.p = P.clamp(p, 0, 1); if (stop) setPlaying(false);
    sample = P.position(model, state.p); dirty = chartDirty = true; updateUI();
  }
  function recalcCurves() {
    curves = Array.from({length: 321}, (_, i) => P.position(model, i / 320));
    const end = Math.max(...curves.map(s => Number.isFinite(s.rH) ? s.rH : 0));
    const points = curves.filter((_, i) => i % 4 === 0).map((s, i, a) => `${i === 0 ? 'M' : 'L'}${(i / (a.length - 1) * 210).toFixed(1)},${(24 - 22 * Math.log1p(Math.min(s.rH, end)) / Math.log1p(end)).toFixed(1)}`);
    $('spark-line').setAttribute('d', points.join(' '));
    chartDirty = true;
  }
  function buildModel(resetEpoch = true) {
    model = state.model === 'c1q' ? P.c1q(data) : state.model === 'lcdm' ? P.lcdm(state.h0, state.om) : P.bounce(state.tau);
    if (resetEpoch) state.p = P.progress(model, model.defaultN);
    photon = null; setPlaying(false); recalcCurves(); updateControls(); updateUI(); dirty = true;
  }
  function updateControls() {
    document.querySelectorAll('[data-model]').forEach(b => { const active = b.dataset.model === state.model; b.classList.toggle('selected', active); b.setAttribute('aria-pressed', active); });
    document.querySelectorAll('[data-view]').forEach(b => { const active = b.dataset.view === state.view; b.classList.toggle('active', active); b.setAttribute('aria-pressed', active); });
    document.querySelectorAll('[data-palette]').forEach(b => { const active = b.dataset.palette === state.palette; b.classList.toggle('active', active); b.setAttribute('aria-pressed', active); });
    $('lcdm-controls').hidden = state.model !== 'lcdm'; $('bounce-controls').hidden = state.model !== 'bounce';
    $('layer-event').disabled = state.model !== 'lcdm';
    $('layer-event').title = state.model === 'c1q' ? 'C1Q has no supplied future history.' : state.model === 'bounce' ? 'The eternal toy geometry has no finite event horizon.' : 'Show the future event horizon.';
    for (const k of Object.keys(state.layers)) $('layer-' + k).checked = state.layers[k];
    for (const [id, val] of [['depth', state.depth], ['ratio', state.ratio], ['h0', state.h0], ['matter', state.om], ['tau', state.tau], ['speed', state.speed]]) $(id).value = val;
    setText('depth-out', state.depth + ' layers'); setText('ratio-out', state.ratio.toFixed(2));
    setText('h0-out', state.h0.toFixed(1)); setText('matter-out', state.om.toFixed(4)); setText('tau-out', state.tau.toFixed(1) + ' Gyr');
    $('auto-orbit').setAttribute('aria-pressed', state.orbit); $('motion-toggle').setAttribute('aria-pressed', state.still);
    setText('recursion-number', String(state.depth).padStart(2, '0'));
    document.documentElement.style.setProperty('--accent', themes().accent);
    document.documentElement.style.setProperty('--accent-rgb', themes().rgb);
    document.documentElement.style.setProperty('--gold', themes().gold);
    const bounce = state.model === 'bounce', c1q = state.model === 'c1q';
    setText('model-tag', c1q ? 'FROZEN v1.0.0 · HYPOTHESIS' : bounce ? 'PRESCRIBED · NOT A C1Q SOLUTION' : 'EDITABLE · SIMPLIFIED FLUIDS');
    setText('model-equation', c1q ? 'V(φ) = ½m²φ²' : bounce ? 'a(t) = √[1 + (t/τ)²]' : 'E² = Ωᵣa⁻⁴ + Ωₘa⁻³ + ΩΛ');
    setText('model-description', c1q ? 'The published C1Q expansion history. Fixed parameters; no observational fit.' : bounce ? 'A smooth scale factor, imposed by hand. Its sustaining matter is not supplied.' : 'Radiation, pressureless matter and Λ. Flatness fixes ΩΛ; no parameter fitting.');
    $('parameter-label').innerHTML = bounce ? 'a at bounce <small>dimensionless</small>' : 'H₀ <small>km s⁻¹ Mpc⁻¹</small>';
    $('parameter-value').innerHTML = bounce ? '1.000 <span class="lock-label">NORMALIZATION</span>' : `${c1q ? '67.4' : state.h0.toFixed(1)} <span class="lock-label">${c1q ? 'FIXED' : 'EDITABLE'}</span>`;
    setText('epoch-heading', bounce ? 'TIME FROM BOUNCE' : 'TIME SINCE aᵢ');
    setText('past-note', bounce ? 'Proper light reach since t = −5τ.' : 'Proper distance since aᵢ = 10⁻⁸.');
    setText('event-note', c1q ? 'C1Q stops at a = 1. No future extrapolation.' : bounce ? 'The eternal toy has divergent conformal time.' : 'Integral to infinite future, including the Λ tail.');
    setText('w-label', c1q ? 'Scalar wφ' : bounce ? 'Epoch' : 'Dark energy w');
    setText('model-footer', c1q ? 'EFMW-COSMO-C1Q v1.0.0' : bounce ? 'PRESCRIBED BOUNCE · NO MATTER SOLUTION' : 'FLAT ΛCDM · FLUID COMPARISON');
    setText('timeline-coordinate', bounce ? 't / τ · LOG DISTANCE OVERVIEW' : 'ln a · LOG DISTANCE OVERVIEW');
    setText('probe-example', bounce ? 'Try t = −τ' : 'Try z = 1');
    $('probe-example').title = bounce ? 'Emit before the bounce at t = −τ' : 'Emit from a source at redshift 1';
    const ticks = bounce ? ['−5τ', '−2.5τ', '0', '+2.5τ', '+5τ'] : c1q ? ['10⁻⁸', '10⁻⁶', '10⁻⁴', '10⁻²', '1.0'] : ['10⁻⁸', '10⁻⁵·⁵', '10⁻³', '10⁻⁰·⁵', '100'];
    Array.from($('timeline-ticks').children).forEach((e, i) => e.textContent = ticks[i]);
    const labels = bounce ? ['Contracting', 't = −τ', 'Bounce', 'Expanding'] : ['Radiation era', 'z ≈ 1,100', 'z = 1', 'Today'];
    document.querySelectorAll('[data-epoch]').forEach((b, i) => b.textContent = labels[i]);
    document.querySelectorAll('input[type=range]').forEach(syncRange);
    setViewText();
  }
  function setViewText() {
    const rec = state.view === 'recursion', spacetime = state.view === 'spacetime';
    setText('scene-kicker', rec ? 'A GEOMETRIC THOUGHT EXPERIMENT' : spacetime ? 'FOLLOW THE NULL GEODESICS' : 'A WINDOW INTO EXPANSION');
    $('scene-title').innerHTML = rec ? 'Worlds within<br><em>worlds.</em>' : spacetime ? 'The shape of <em>causal contact.</em>' : 'The edge of<br><em>the observable.</em>';
    setText('scene-subtitle', rec ? 'Recursive structure. No asserted new physics.' : spacetime ? 'Conformal coordinates · light follows dχ / dη = ±1.' : 'One observer. An evolving causal landscape.');
    setText('scene-scale', rec ? '+ GEOMETRIC NESTING · ILLUSTRATIVE' : spacetime ? '+ COMOVING DISTANCE × CONFORMAL TIME' : '+ SCHEMATIC · COMPRESSED RADIAL SCALE');
    setText('camera-hint', spacetime ? 'Scrub time to move the light cone' : rec ? 'Drag to turn · Scroll to dive' : 'Drag to orbit · Scroll to zoom');
    setText('render-status', rec ? 'OFFLINE · VISUAL RECURSION' : spacetime ? 'OFFLINE · COMPUTED CONFORMAL COORDINATES' : 'OFFLINE · SYNTHETIC SPATIAL VIEW');
    $('recursion-badge').hidden = !rec;
    $('auto-orbit').hidden = spacetime;
    $('universe-panel').classList.toggle('spacetime', spacetime);
    dirty = true;
  }
  function setView(view) { state.view = view; updateControls(); updateUI(); dirty = true; }
  function updateUI() {
    sample = P.position(model, state.p);
    setText('epoch-value', fmt(sample.age, 3));
    setText('epoch-detail', `a = ${fmt(sample.a, 4)}` + (sample.z == null ? ` · t/τ = ${fmt(sample.n, 2)}` : ` · z = ${fmt(sample.z, 3)}`));
    setText('metric-hubble', fmt(sample.rH, 3)); setText('metric-past', fmt(sample.reach, 3));
    const hasEvent = sample.event !== null;
    setText('metric-event', hasEvent ? fmt(sample.event, 3) : state.model === 'bounce' ? 'No finite horizon' : 'Unspecified');
    $('metric-event').classList.toggle('text-value', !hasEvent); setText('event-unit', hasEvent ? 'Gly' : '');
    setText('metric-h', fmt(sample.H, 3)); setText('metric-w', state.model === 'bounce' ? Math.abs(sample.n) < 1e-8 ? 'Bounce' : sample.n < 0 ? 'Contracting' : 'Expanding' : fmt(sample.w, 4));
    setText('hubble-label-value', short(sample.rH) + ' Gly'); setText('past-label-value', short(sample.reach) + ' Gly');
    setText('scale-value', fmt(sample.a, 4));
    const atRef = Math.abs(sample.n - model.defaultN) < 1e-8;
    setText('play-state', state.playing ? 'EVOLVING' : atRef ? 'REFERENCE EPOCH' : 'EPOCH HELD');
    $('epoch').value = Math.round(state.p * 10000); syncRange($('epoch'));
    $('epoch').setAttribute('aria-valuetext', state.model === 'bounce' ? `Time ${fmt(sample.age)} billion years from bounce` : `Scale factor ${fmt(sample.a, 4)}, redshift ${fmt(sample.z, 3)}`);
    document.querySelectorAll('[data-epoch]').forEach(b => b.classList.toggle('active', Math.abs(state.p - epochProgress(b.dataset.epoch)) < .0001));
    $('hubble-label').hidden = state.view !== 'atlas' || !state.layers.hubble || !Number.isFinite(sample.rH);
    $('past-label').hidden = state.view !== 'atlas' || !state.layers.past || sample.reach === 0;
    updateProbe();
  }
  function epochProgress(which) {
    const n = state.model === 'bounce' ? {radiation: -3, recombination: -1, one: 0, today: 3}[which] : {radiation: Math.log(1e-5), recombination: -Math.log(1101), one: -Math.log(2), today: 0}[which];
    return P.progress(model, n);
  }
  function updateProbe() {
    $('clear-probe').hidden = !photon;
    if (!photon) { setText('probe-status', 'Ready for emission'); setText('probe-message', 'Choose an epoch, emit, then scrub forward.'); return; }
    const current = P.photonAt(photon, sample);
    let title, message;
    if (current.status === 'before') { title = 'Before emission'; message = 'Move forward to the saved emission epoch to follow this photon.'; }
    else if (current.status === 'arrived') { title = 'Signal received'; message = `Arrival: ${state.model === 'bounce' ? 't' : 'elapsed'} = ${fmt(photon.arrival?.age, 3)} Gyr. The photon reached χ = 0.`; }
    else {
      title = 'Inward photon · ' + short(current.proper) + ' Gly';
      if (photon.arrival) message = `Arrival predicted at ${state.model === 'bounce' ? 't' : 'elapsed'} = ${fmt(photon.arrival.age, 3)} Gyr. Play or scrub forward.`;
      else if (photon.beyondEvent) message = 'Beyond this ΛCDM event horizon. No arrival at finite future time in this model.';
      else message = 'Arrival lies beyond the available time window; permanent disconnection is not established.';
    }
    setText('probe-status', title); setText('probe-message', message);
  }
  function emit(example = false) {
    if (example) setP(P.progress(model, state.model === 'bounce' ? -1 : -Math.log(2)));
    photon = P.emit(model, state.p, Number($('probe-distance').value));
    updateProbe(); dirty = true;
    if (state.p > .9999) announce('Photon placed. Scrub to an earlier epoch and emit again to trace motion within this history.');
    else announce('Inward light signal emitted. Press Space or move the timeline forward.');
  }

  function resize() {
    const r = cvs.getBoundingClientRect();
    W = Math.max(1, r.width); H = Math.max(1, r.height); dpr = Math.min(devicePixelRatio || 1, 2);
    cvs.width = Math.round(W * dpr); cvs.height = Math.round(H * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const cr = chart.getBoundingClientRect(); chartW = Math.max(1, cr.width); chartH = Math.max(1, cr.height);
    chart.width = Math.round(chartW * dpr); chart.height = Math.round(chartH * dpr); chartCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildBackdrop(); dirty = chartDirty = true;
  }
  function buildBackdrop() {
    backdrop = document.createElement('canvas'); backdrop.width = Math.round(W * dpr); backdrop.height = Math.round(H * dpr);
    const c = backdrop.getContext('2d'); c.scale(dpr, dpr); c.fillStyle = '#060b13'; c.fillRect(0, 0, W, H);
    function haze(x, y, r, col) { const g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, col); g.addColorStop(1, 'transparent'); c.fillStyle = g; c.fillRect(x - r, y - r, 2 * r, 2 * r); }
    haze(W * .58, H * .63, W * .65, 'rgba(25,58,74,.30)');
    haze(W * .2, H * .82, W * .45, 'rgba(45,28,62,.16)');
    haze(W * .88, H * .26, W * .35, 'rgba(49,57,76,.13)');
    for (const s of stars) {
      const x = s.x * W, y = s.y * H;
      c.fillStyle = s.hue > .78 ? `rgba(220,188,149,${s.a * .7})` : `rgba(155,190,211,${s.a * .65})`;
      c.beginPath(); c.arc(x, y, s.r, 0, Math.PI * 2); c.fill();
      if (s.r > 1.55) { haze(x, y, s.r * 7, 'rgba(157,201,224,.12)'); c.strokeStyle = 'rgba(155,190,211,.18)'; c.lineWidth = .5; c.beginPath(); c.moveTo(x - 4, y); c.lineTo(x + 4, y); c.moveTo(x, y - 4); c.lineTo(x, y + 4); c.stroke(); }
    }
    c.strokeStyle = '#15212c'; c.lineWidth = .5;
    for (let x = 30; x < W; x += 73) for (let y = 34; y < H; y += 73) {
      c.beginPath(); c.moveTo(x - 2, y); c.lineTo(x + 2, y); c.moveTo(x, y - 2); c.lineTo(x, y + 2); c.stroke();
    }
    buildNebula();
  }
  function buildNebula() {
    const cols = [themes().accent, themes().second, themes().gold];
    cloudSprites = cols.map(col => {
      const sprite = document.createElement('canvas'); sprite.width = sprite.height = 96;
      const c = sprite.getContext('2d'), g = c.createRadialGradient(48, 48, 0, 48, 48, 48);
      g.addColorStop(0, rgba(col, .7)); g.addColorStop(.18, rgba(col, .28)); g.addColorStop(.5, rgba(col, .06)); g.addColorStop(1, rgba(col, 0));
      c.fillStyle = g; c.fillRect(0, 0, 96, 96); return sprite;
    });
    nebula = document.createElement('canvas'); nebula.width = nebula.height = 768;
    const c = nebula.getContext('2d'), rand = rng(41102);
    c.globalCompositeOperation = 'screen';
    for (let i = 0; i < 3300; i++) {
      const r = 345 * Math.sqrt(rand()), arm = i % 3;
      const twist = 1.7 * Math.log1p(r / 25) + arm * Math.PI * 2 / 3;
      const width = (rand() + rand() + rand() - 1.5) * (.12 + .38 * r / 345);
      const t = twist + width, x = 384 + Math.cos(t) * r, y = 384 + Math.sin(t) * r;
      const size = 5 + rand() * 28;
      c.globalAlpha = .14 * (1 - r / 410);
      c.drawImage(cloudSprites[arm], x - size, y - size, size * 2, size * 2);
      if (i % 3 === 0) {c.globalAlpha = .2 + rand() * .55; c.fillStyle = i % 7 === 0 ? '#fff0ce' : '#d9f9ef'; c.fillRect(x, y, .5 + rand(), .5 + rand());}
    }
    c.globalAlpha = .7; c.drawImage(cloudSprites[0], 328, 328, 112, 112); c.globalAlpha = 1;
  }
  function project(v, cx, cy, scale, yaw = state.yaw, pitch = state.pitch) {
    const c = Math.cos(yaw), s = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const x = v[0] * c + v[2] * s, z = -v[0] * s + v[2] * c;
    return {x: cx + x * scale, y: cy + (v[1] * cp - z * sp) * scale, z: v[1] * sp + z * cp};
  }
  function glow(x, y, r, color, strength) {
    if (!(r > 0 && Number.isFinite(r))) return;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(color, strength)); g.addColorStop(.23, rgba(color, strength * .35)); g.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function sphere(r, cx, cy, scale, color, opacity, detailed = true, tilt = 0) {
    if (!(r > 0 && Number.isFinite(r))) return;
    const path = (fn, bright) => {
      for (let side = 0; side < 2; side++) {
        ctx.beginPath(); let active = false;
        for (let j = 0; j <= 100; j++) {
          const p = project(fn(j / 100 * Math.PI * 2), cx, cy, scale, state.yaw + tilt, state.pitch);
          if ((p.z >= 0) === Boolean(side)) { if (active) ctx.lineTo(p.x, p.y); else {ctx.moveTo(p.x, p.y); active = true;} } else active = false;
        }
        ctx.strokeStyle = rgba(color, opacity * (side ? 1 : .24) * bright); ctx.lineWidth = side ? .7 : .5; ctx.stroke();
      }
    };
    if (detailed) {
      for (let i = -4; i <= 4; i++) {
        const lat = i / 5 * Math.PI / 2, q = r * Math.cos(lat), y = r * Math.sin(lat);
        path(t => [q * Math.cos(t), y, q * Math.sin(t)], i === 0 ? 1.2 : .5);
      }
      for (let i = 0; i < 10; i++) { const az = i / 10 * Math.PI; path(t => [r * Math.cos(t) * Math.cos(az), r * Math.sin(t), r * Math.cos(t) * Math.sin(az)], .45); }
    }
    ctx.beginPath(); ctx.arc(cx, cy, r * scale, 0, Math.PI * 2); ctx.strokeStyle = rgba(color, opacity * .7); ctx.lineWidth = .9; ctx.stroke();
    if (detailed) {
      ctx.beginPath(); ctx.arc(cx, cy, r * scale + 3, 0, Math.PI * 2); ctx.strokeStyle = rgba(color, opacity * .13); ctx.lineWidth = 3; ctx.stroke();
      path(t => [r * Math.cos(t), 0, r * Math.sin(t)], 1.7);
    }
  }
  function orbitalRing(cx, cy, base, angle, opacity, color) {
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(angle);
    const g = ctx.createLinearGradient(-base, 0, base, 0); g.addColorStop(0, rgba(color, 0)); g.addColorStop(.35, rgba(color, opacity * .35)); g.addColorStop(.8, rgba(color, opacity)); g.addColorStop(1, rgba(color, opacity * .1));
    ctx.strokeStyle = g; ctx.lineWidth = 1.1; ctx.beginPath(); ctx.ellipse(0, 0, base, base * .28, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = .5; ctx.strokeStyle = rgba(color, opacity * .16); ctx.beginPath(); ctx.ellipse(0, 0, base * 1.04, base * .3, 0, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  }
  function visualGeometry() {
    const finiteH = Number.isFinite(sample.rH) ? Math.min(sample.rH, Math.max(sample.reach, 1) * 10) : 0;
    const maxR = Math.max(finiteH, sample.reach, sample.event || 0, 1e-30);
    const radius = r => Number.isFinite(r) ? 1.13 * Math.log1p(4 * Math.max(0, r) / maxR) / Math.log(5) : null;
    return {cx: W * .51, cy: H * .585, scale: Math.min(W * .36, H * .335) * state.zoom, radius, maxR};
  }
  function drawAtlas() {
    const {cx, cy, scale, radius} = visualGeometry(), theme = themes();
    const rh = radius(sample.rH), rp = radius(sample.reach), re = sample.event == null ? null : radius(sample.event);
    const orb = rh == null ? .7 : Math.min(rh, 1.3);
    ctx.globalCompositeOperation = 'screen';
    glow(cx, cy, scale * 1.55, theme.accent, .08);
    glow(cx - scale * .2, cy + scale * .14, scale * .9, theme.second, .08);
    if (state.layers.hubble && rh != null) {
      const g = ctx.createRadialGradient(cx - orb * scale * .32, cy - orb * scale * .3, 0, cx, cy, orb * scale);
      g.addColorStop(0, rgba(theme.accent, .035)); g.addColorStop(.85, rgba(theme.accent, .015)); g.addColorStop(.99, rgba(theme.accent, .06)); g.addColorStop(1, 'transparent');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, orb * scale, 0, Math.PI * 2); ctx.fill();
    }
    if (state.layers.tracers) {
      // Seeded, decorative dust follows the generated filament network.
      // It carries no density measurement or nonlinear structure calculation.
      ctx.globalAlpha = .20;
      for (let i = 0; i < motes.length; i += 9) {
        const m = motes[i], p = project(m.v, cx, cy, scale), r = (12 + (i % 23)) * scale / 220;
        ctx.drawImage(cloudSprites[i % 3], p.x - r, p.y - r, r * 2, r * 2);
      }
      ctx.globalAlpha = 1;
      for (const [a, b] of links) {
        const x = project(a, cx, cy, scale), y = project(b, cx, cy, scale);
        const g = ctx.createLinearGradient(x.x, x.y, y.x, y.y);
        g.addColorStop(0, rgba(theme.accent, .045)); g.addColorStop(.5, rgba(theme.second, .12)); g.addColorStop(1, rgba(theme.accent, .025));
        ctx.strokeStyle = g; ctx.lineWidth = .55; ctx.beginPath(); ctx.moveTo(x.x, x.y); ctx.lineTo(y.x, y.y); ctx.stroke();
      }
      for (const m of motes) {
        const p = project(m.v, cx, cy, scale), bright = (.35 + .35 * (p.z + 1.3) / 2.6) * (.85 + .15 * Math.sin(visualTime * .5 + m.phase));
        ctx.fillStyle = rgba(m.tint > .86 ? theme.gold : m.tint > .65 ? theme.second : theme.accent, bright);
        ctx.beginPath(); ctx.arc(p.x, p.y, m.r * (p.z > 0 ? 1 : .7) * Math.sqrt(state.zoom), 0, 6.283); ctx.fill();
      }
      for (let i = 0; i < anchors.length; i += 3) {
        const p = project(anchors[i], cx, cy, scale);
        glow(p.x, p.y, (7 + Math.max(0, p.z) * 9) * Math.sqrt(state.zoom), i % 2 ? theme.accent : theme.gold, .13);
        ctx.fillStyle = rgba(i % 2 ? '#b7f3e9' : '#f4dfbb', .8); ctx.fillRect(p.x - .6, p.y - .6, 1.2, 1.2);
      }
    }
    if (state.layers.past && rp > 0) sphere(rp, cx, cy, scale, theme.gold, .32, true, .25);
    if (state.layers.event && re != null) sphere(re, cx, cy, scale, '#a59ce5', .5, false);
    if (state.layers.hubble && rh != null && rh < 2) sphere(rh, cx, cy, scale, theme.accent, .65, true);
    orbitalRing(cx, cy, scale * 1.37, -.38 - state.pitch * .15, .22, theme.accent);
    orbitalRing(cx, cy, scale * 1.25, .55, .12, theme.second);
    // Observer marker; the orbit lines and volumetric tracers are decorative.
    glow(cx, cy, 28, theme.accent, .5);
    ctx.fillStyle = '#e2fff5'; ctx.beginPath(); ctx.arc(cx, cy, 2.2, 0, 6.283); ctx.fill();
    ctx.strokeStyle = rgba(theme.accent, .55); ctx.lineWidth = .6; ctx.beginPath(); ctx.moveTo(cx - 12, cy); ctx.lineTo(cx + 12, cy); ctx.moveTo(cx, cy - 12); ctx.lineTo(cx, cy + 12); ctx.stroke();
    ctx.globalCompositeOperation = 'source-over'; ctx.fillStyle = '#a9bcbf'; ctx.font = '7px monospace'; ctx.textAlign = 'center'; ctx.fillText('OBSERVER / χ = 0', cx, cy + 24);
    if (photon) {
      const ps = P.photonAt(photon, sample);
      if (ps.status !== 'before') {
        const r = Math.min(radius(ps.proper), 1.7), pos = project([r * .9, -.18 * r, .4 * r], cx, cy, scale);
        ctx.strokeStyle = 'rgba(248,210,141,.38)'; ctx.lineWidth = .8; ctx.setLineDash([3, 5]); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(pos.x, pos.y); ctx.stroke(); ctx.setLineDash([]);
        ctx.globalCompositeOperation = 'screen'; glow(pos.x, pos.y, 17, '#ffce80', .65); ctx.globalCompositeOperation = 'source-over';
        ctx.fillStyle = '#ffe2a6'; ctx.beginPath(); ctx.arc(pos.x, pos.y, 3, 0, 6.283); ctx.fill();
        ctx.font = '8px monospace'; ctx.fillText(ps.status === 'arrived' ? 'RECEIVED' : 'LIGHT SIGNAL', pos.x, pos.y - 15);
      }
    }
    placeLabel($('hubble-label'), cx + (rh || .6) * scale * .4, cy - (rh || .6) * scale * .7, 204);
    placeLabel($('past-label'), cx - rp * scale * .92, cy + rp * scale * .48, 211);
    ctx.textAlign = 'left';
  }
  function placeLabel(el, x, y, fallbackWidth) {
    const width = el.offsetWidth || fallbackWidth;
    el.style.left = P.clamp(x, 14, W - width - 14) + 'px';
    el.style.top = P.clamp(y, 225, H - 92) + 'px';
  }
  function drawRecursion() {
    const theme = themes(), cx = W * .56, cy = H * .58;
    const base = Math.min(W * .43, H * .42) * state.zoom;
    ctx.globalCompositeOperation = 'screen';
    glow(cx, cy, base * 1.65, theme.second, .14);
    const depth = state.depth, drift = Math.sin(visualTime * .08) * .07;
    for (let k = 0; k < depth; k++) {
      const r = base * Math.pow(state.ratio, k), spin = state.yaw + k * .42 + drift;
      const off = (1 - Math.pow(state.ratio, k)) * base * .16;
      const x = cx + Math.sin(spin) * off, y = cy + Math.cos(spin) * off * .25;
      const col = k % 3 === 0 ? theme.accent : k % 3 === 1 ? theme.second : theme.gold;
      glow(x, y, r * 1.2, col, .045 + .012 * k);
      if (state.layers.tracers && k < 5) {
        ctx.save(); ctx.translate(x, y); ctx.rotate(-.35 + k * .48 + state.yaw * .08);
        ctx.scale(1, .32 + .14 * Math.sin(state.pitch + k * .4)); ctx.globalAlpha = .55;
        ctx.drawImage(nebula, -r * 1.2, -r * 1.2, r * 2.4, r * 2.4); ctx.restore();
      }
      sphere(1, x, y, r, col, .48 + k * .018, k < 5, k * .35);
      orbitalRing(x, y, r * 1.14, -.4 + k * .5 + state.pitch, .65, col);
      const t = visualTime * .12 + k * 2.399;
      const satellite = project([Math.cos(t), .1 * Math.sin(t * 2), Math.sin(t)], x, y, r, spin, state.pitch);
      glow(satellite.x, satellite.y, Math.max(6, r * .12), col, .45);
      ctx.fillStyle = rgba(col, .95); ctx.beginPath(); ctx.arc(satellite.x, satellite.y, Math.max(1, 2.2 - k * .15), 0, 6.283); ctx.fill();
      if (state.layers.tracers) {
        for (let j = 0; j < 200; j++) {
          const m = motes[(j * 7 + k * 31) % motes.length];
          const p = project(m.v, x, y, r * .8, spin, state.pitch + .1 * k);
          ctx.fillStyle = rgba(col, .2 + .35 * (p.z + 1.3) / 2.6); ctx.fillRect(p.x, p.y, Math.max(.5, 1.1 - k * .08), Math.max(.5, 1.1 - k * .08));
        }
      }
      if (k > 0 && k < depth - 1) {
        ctx.strokeStyle = rgba(col, .12); ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(cx + Math.sin(spin - .42) * (1 - Math.pow(state.ratio, k - 1)) * base * .16, cy - r / state.ratio); ctx.stroke();
      }
    }
    glow(cx, cy, 24, '#d9eeff', .55);
    ctx.globalCompositeOperation = 'source-over';
  }
  function drawSpacetime() {
    const left = W < 500 ? 52 : 67, right = W - 24, top = Math.min(213, H * .4), bottom = H - 84;
    const width = right - left, height = bottom - top;
    if (height < 40) return;
    const maxEta = model.at(model.max).eta * 1.04, maxChi = maxEta * .62;
    const X = chi => left + width / 2 + chi / maxChi * width / 2;
    const Y = eta => bottom - eta / maxEta * height;
    ctx.font = '8px monospace'; ctx.textAlign = 'center'; ctx.lineWidth = .5;
    for (let i = 0; i <= 4; i++) {
      const eta = maxEta * i / 4, yy = Y(eta);
      ctx.strokeStyle = 'rgba(114,149,172,.16)'; ctx.beginPath(); ctx.moveTo(left, yy); ctx.lineTo(right, yy); ctx.stroke();
      ctx.fillStyle = '#839aac'; ctx.textAlign = 'right'; ctx.fillText(short(eta), left - 9, yy + 3);
      const chi = maxChi * (i / 2 - 1), xx = X(chi);
      ctx.beginPath(); ctx.moveTo(xx, top); ctx.lineTo(xx, bottom); ctx.stroke();
      ctx.textAlign = 'center'; ctx.fillText(short(chi), xx, bottom + 15);
    }
    ctx.save(); ctx.beginPath(); ctx.rect(left, top, width, height); ctx.clip();
    ctx.fillStyle = rgba(themes().accent, .07); ctx.beginPath(); ctx.moveTo(X(0), Y(sample.eta)); ctx.lineTo(X(sample.eta), Y(0)); ctx.lineTo(X(-sample.eta), Y(0)); ctx.closePath(); ctx.fill();
    if (state.layers.past) {
      ctx.strokeStyle = rgba(themes().gold, .7); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(X(-sample.eta), Y(0)); ctx.lineTo(X(0), Y(sample.eta)); ctx.lineTo(X(sample.eta), Y(0)); ctx.stroke();
    }
    function worldCurve(fn, color, dashed = false) {
      ctx.strokeStyle = color; ctx.lineWidth = 1.25; ctx.setLineDash(dashed ? [4, 4] : []);
      for (const sign of [-1, 1]) {
        ctx.beginPath(); let pen = false;
        for (const s of curves) { const chi = fn(s); if (!Number.isFinite(chi) || chi > maxChi * 4) {pen = false; continue;} const x = X(sign * chi), y = Y(s.eta); if (pen) ctx.lineTo(x, y); else {ctx.moveTo(x, y); pen = true;} }
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    if (state.layers.hubble) worldCurve(s => s.rH / s.a, themes().accent);
    if (state.layers.event && state.model === 'lcdm') worldCurve(s => s.event / s.a, '#aa9ee9', true);
    ctx.strokeStyle = 'rgba(183,210,224,.4)'; ctx.lineWidth = .7; ctx.setLineDash([3, 4]); ctx.beginPath(); ctx.moveTo(left, Y(sample.eta)); ctx.lineTo(right, Y(sample.eta)); ctx.stroke(); ctx.setLineDash([]);
    ctx.strokeStyle = '#6a8292'; ctx.beginPath(); ctx.moveTo(X(0), bottom); ctx.lineTo(X(0), top); ctx.stroke();
    if (photon && sample.eta >= photon.eta) {
      const endEta = Math.min(sample.eta, photon.eta + photon.chi), endChi = Math.max(0, photon.chi - (endEta - photon.eta));
      ctx.strokeStyle = '#ffd69a'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(X(photon.chi), Y(photon.eta)); ctx.lineTo(X(endChi), Y(endEta)); ctx.stroke();
      glow(X(endChi), Y(endEta), 12, '#ffcf80', .5); ctx.fillStyle = '#ffe5b2'; ctx.beginPath(); ctx.arc(X(endChi), Y(endEta), 3, 0, 6.283); ctx.fill();
    }
    glow(X(0), Y(sample.eta), 15, themes().accent, .45); ctx.fillStyle = '#c4fff1'; ctx.beginPath(); ctx.arc(X(0), Y(sample.eta), 3, 0, 6.283); ctx.fill();
    ctx.restore(); ctx.fillStyle = '#8ca8b9'; ctx.font = '8px monospace'; ctx.textAlign = 'center'; ctx.fillText('χ · COMOVING Gly', left + width / 2, bottom + 32);
    ctx.save(); ctx.translate(16, top + height / 2); ctx.rotate(-Math.PI / 2); ctx.fillText('η SINCE INITIAL SURFACE · Gly', 0, 0); ctx.restore();
    ctx.fillStyle = '#adc6cf'; ctx.textAlign = 'right'; ctx.fillText('CURRENT EPOCH', right - 4, Math.max(top + 12, Y(sample.eta) - 7));
    ctx.textAlign = 'left'; ctx.fillStyle = themes().accent; ctx.fillText('HUBBLE SCALE', left, top - 15); ctx.fillStyle = themes().gold; ctx.fillText('PAST LIGHT CONE', left + 112, top - 15);
  }
  function render() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    if (backdrop) ctx.drawImage(backdrop, 0, 0, W, H); else {ctx.fillStyle = '#060b13'; ctx.fillRect(0, 0, W, H);}
    if (state.view === 'recursion') drawRecursion(); else if (state.view === 'spacetime') drawSpacetime(); else drawAtlas();
    const vignette = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * .25, W / 2, H / 2, Math.max(W, H) * .72);
    vignette.addColorStop(0, 'rgba(3,7,13,0)'); vignette.addColorStop(1, 'rgba(3,7,13,.45)'); ctx.fillStyle = vignette; ctx.fillRect(0, 0, W, H);
    dirty = false;
  }
  function drawTimeline() {
    const c = chartCtx; c.clearRect(0, 0, chartW, chartH);
    const all = curves.flatMap(s => [s.rH, s.reach, s.event]).filter(v => v > 0 && Number.isFinite(v));
    const hi = Math.log10(Math.max(...all)), lo = Math.max(hi - 18, Math.log10(Math.min(...all)));
    const y = v => chartH - 4 - (Math.log10(v) - lo) / Math.max(hi - lo, 1) * (chartH - 9);
    c.strokeStyle = '#1b2b37'; c.lineWidth = .5;
    for (let i = 0; i < 5; i++) { const x = i * chartW / 4; c.beginPath(); c.moveTo(x, 2); c.lineTo(x, chartH); c.stroke(); }
    for (const [key, color, enabled] of [['rH', themes().accent, state.layers.hubble], ['reach', themes().gold, state.layers.past], ['event', '#a59ce5', state.layers.event && state.model === 'lcdm']]) {
      if (!enabled) continue;
      c.strokeStyle = rgba(color, .75); c.lineWidth = 1; c.beginPath(); let pen = false;
      curves.forEach((s, i) => { if (!(s[key] > 0 && Number.isFinite(s[key]))) {pen = false; return;} const x = i / (curves.length - 1) * chartW, yy = Math.max(1, Math.min(chartH - 2, y(s[key]))); if (pen) c.lineTo(x, yy); else {c.moveTo(x, yy); pen = true;} }); c.stroke();
    }
    const x = state.p * chartW; c.fillStyle = rgba(themes().accent, .035); c.fillRect(0, 0, x, chartH); c.strokeStyle = rgba(themes().accent, .75); c.lineWidth = .8; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, chartH); c.stroke();
    chartDirty = false;
  }
  function frame(t) {
    const dt = Math.min((t - (lastTime || t)) / 1000, .07); lastTime = t;
    if (!document.hidden && !$('about-dialog').open) {
      if (state.playing) {
        state.p = Math.min(1, state.p + dt * state.speed / 45);
        sample = P.position(model, state.p); dirty = chartDirty = true;
        if (state.p >= 1) {setPlaying(false); announce(state.model === 'c1q' ? 'Reached the end of the frozen history at a = 1.' : 'Reached the end of this displayed time window.');}
      }
      if (!state.still && state.view !== 'spacetime') {
        visualTime += dt;
        if (state.orbit && !dragging) state.yaw += dt * .025;
        dirty = true;
      }
      if (state.playing && t - lastUI > 80) {updateUI(); lastUI = t;}
      if (dirty && t - lastPaint >= 32) {render(); lastPaint = t;}
      if (chartDirty) drawTimeline();
    }
    requestAnimationFrame(frame);
  }
  function download(content, filename, type) {
    const blob = content instanceof Blob ? content : new Blob([content], {type});
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  function save() {
    const session = {schema: 'horizon-observatory/session/v1', app_version: '1.0.0', model_source: data.source_commit,
      description: 'Exploratory cosmological visualization; no observational validation.',
      state: {...state, playing: false, layers: {...state.layers}},
      probe: photon ? {p: photon.p, distance: photon.distance} : null};
    download(JSON.stringify(session, null, 2), 'horizon-session.json', 'application/json'); announce('Session exported. Open it here to restore the model, epoch and camera.');
  }
  function validateSession(s) {
    if (!s || s.schema !== 'horizon-observatory/session/v1' || !s.state) throw new Error('This is not a HORIZON v1 session.');
    if (s.model_source !== data.source_commit) throw new Error('This session references a different frozen background version.');
    const v = s.state;
    for (const [key, allowed] of [['model', ['c1q', 'lcdm', 'bounce']], ['view', ['atlas', 'spacetime', 'recursion']], ['palette', Object.keys(palette)]]) if (!allowed.includes(v[key])) throw new Error('Unknown session ' + key + '.');
    const out = {...state, model: v.model, view: v.view, palette: v.palette, playing: false, layers: {...state.layers}};
    const ranges = {p: [0, 1], h0: [50, 90], om: [.1, .5], tau: [1, 10], depth: [2, 10], ratio: [.38, .78], yaw: [-1e6, 1e6], pitch: [-1.4, 1.4], zoom: [.5, 2], speed: [.5, 4]};
    for (const [k, [min, max]] of Object.entries(ranges)) { if (typeof v[k] !== 'number' || !Number.isFinite(v[k]) || v[k] < min || v[k] > max) throw new Error('Invalid ' + k + ' in session.'); out[k] = v[k]; }
    if (!Number.isInteger(out.depth) || ![.5, 1, 2, 4].includes(out.speed)) throw new Error('Invalid discrete control in session.');
    for (const k of ['orbit', 'still']) { if (typeof v[k] !== 'boolean') throw new Error('Invalid motion control.'); out[k] = v[k]; }
    for (const k of Object.keys(out.layers)) { if (typeof v.layers?.[k] !== 'boolean') throw new Error('Invalid layer setting.'); out.layers[k] = v.layers[k]; }
    if (s.probe != null && !(Number.isFinite(s.probe.p) && s.probe.p >= 0 && s.probe.p <= 1 && Number.isFinite(s.probe.distance) && s.probe.distance >= .1 && s.probe.distance <= 30)) throw new Error('Invalid light-signal data.');
    return {state: out, probe: s.probe};
  }
  async function openSession(file) {
    if (!file) return;
    if (file.size > 65536) {announce('Session files must be smaller than 64 KB.'); return;}
    try {
      const parsed = validateSession(JSON.parse(await file.text())); Object.assign(state, parsed.state); buildNebula();
      buildModel(false); if (parsed.probe) {photon = P.emit(model, parsed.probe.p, parsed.probe.distance); $('probe-distance').value = parsed.probe.distance; setText('probe-out', parsed.probe.distance.toFixed(1) + ' Gly'); syncRange($('probe-distance'));}
      updateUI(); dirty = chartDirty = true; announce('Session restored.');
    } catch (e) {announce('Could not open session: ' + e.message);}
  }
  function capture() {
    render();
    const out = document.createElement('canvas'); out.width = cvs.width; out.height = cvs.height;
    const c = out.getContext('2d'); c.drawImage(cvs, 0, 0); c.scale(dpr, dpr);
    const g = c.createLinearGradient(0, 0, 0, 140); g.addColorStop(0, '#07101bed'); g.addColorStop(1, '#07101b00'); c.fillStyle = g; c.fillRect(0, 0, W, 140);
    c.fillStyle = themes().accent; c.font = '18px sans-serif'; c.fillText('H O R I Z O N', 26, 37);
    c.fillStyle = '#c3d6df'; c.font = '10px monospace'; c.fillText(`${model.label}  /  ${state.view.toUpperCase()}  /  a = ${fmt(sample.a, 4)}`, 27, 59);
    c.font = '9px monospace'; c.fillStyle = '#91a8b7'; c.fillText(state.view === 'spacetime' ? 'Computed conformal coordinates; model-dependent, not an observational fit.' : 'Illustrative geometry and synthetic tracers; not observational evidence.', 27, 78);
    c.fillStyle = '#08111be8'; c.fillRect(0, H - 43, W, 43); c.fillStyle = '#aec4ce'; c.font = '9px monospace';
    c.fillText(`Hubble: ${fmt(sample.rH)} Gly  |  Past reach: ${fmt(sample.reach)} Gly`, 27, H - 25);
    c.fillStyle = '#6d899c'; c.font = '8px monospace'; c.fillText('Horizon Observatory 1.0.0 · enuminous/Cosmology · Scientific assumptions in the standalone app', 27, H - 11);
    out.toBlob(blob => { if (blob) {download(blob, 'horizon-' + state.view + '.png'); announce('Viewport captured with model and evidence labels.');} else announce('This browser could not encode a PNG.'); }, 'image/png');
  }
  function exportCSV() {
    const lines = ['# HORIZON 1.0.0; calculated model outputs, not observations', '# model=' + model.id + '; source_commit=' + data.source_commit,
      '# H0_km_s_Mpc=' + (model.h0 ?? 'NA') + '; Omega_m0=' + (model.Om ?? 'NA') + '; tau_Gyr=' + (model.tau ?? 'NA'),
      '# Past reach is measured from the finite initial surface. Empty event field means unspecified or no finite horizon; see app guide.',
      'coordinate,a,z,elapsed_or_bounce_time_Gyr,H_km_s_Mpc,Hubble_Gly,past_reach_Gly,event_horizon_Gly'];
    for (let i = 0; i <= 1000; i++) { const s = P.position(model, i / 1000); lines.push([s.n, s.a, s.z, s.age, s.H, s.rH, s.reach, s.event].map(v => v === null ? '' : v === Infinity ? 'Infinity' : String(v)).join(',')); }
    download(lines.join('\n') + '\n', 'horizon-' + model.id + '-curves.csv', 'text/csv'); announce('1,001 calculated background samples exported.');
  }
  function resetCamera() {state.yaw = -.3; state.pitch = .36; state.zoom = 1; dirty = true;}
  function setFocus(value) {focus = value; $('app').classList.toggle('focus', focus); $('focus-exit').hidden = !focus; $('fullscreen').setAttribute('aria-pressed', focus); requestAnimationFrame(resize);}
  function guide() { $('about-dialog').showModal(); }

  document.querySelectorAll('[data-model]').forEach(b => b.addEventListener('click', () => {state.model = b.dataset.model; buildModel();}));
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
  document.querySelectorAll('[data-palette]').forEach(b => b.addEventListener('click', () => {state.palette = b.dataset.palette; buildNebula(); updateControls(); chartDirty = true;}));
  document.querySelectorAll('[data-epoch]').forEach(b => b.addEventListener('click', () => setP(epochProgress(b.dataset.epoch))));
  for (const k of Object.keys(state.layers)) $('layer-' + k).addEventListener('change', e => {state.layers[k] = e.target.checked; updateUI(); dirty = chartDirty = true;});
  $('epoch').addEventListener('input', e => setP(Number(e.target.value) / 10000));
  for (const [id, key] of [['depth', 'depth'], ['ratio', 'ratio']]) $(id).addEventListener('input', e => {state[key] = Number(e.target.value); updateControls(); dirty = true;});
  for (const [id, key] of [['h0', 'h0'], ['matter', 'om'], ['tau', 'tau']]) $(id).addEventListener('input', e => {state[key] = Number(e.target.value); buildModel(false);});
  $('speed').addEventListener('change', e => state.speed = Number(e.target.value));
  $('play').addEventListener('click', () => {if (!state.playing && state.p >= .9999) setP(state.model === 'bounce' ? 0 : .65); setPlaying(!state.playing);});
  $('restart').addEventListener('click', () => {photon = null; setP(P.progress(model, model.defaultN));});
  $('reset-camera').addEventListener('click', resetCamera);
  $('auto-orbit').addEventListener('click', () => {state.orbit = !state.orbit; if (state.orbit) state.still = false; updateControls();});
  $('motion-toggle').addEventListener('click', () => {state.still = !state.still; if (state.still) {state.orbit = false; setPlaying(false);} updateControls();});
  $('enter-recursion').addEventListener('click', () => setView('recursion'));
  $('probe-distance').addEventListener('input', e => {syncRange(e.target); setText('probe-out', Number(e.target.value).toFixed(1) + ' Gly');});
  $('emit').addEventListener('click', () => emit()); $('probe-example').addEventListener('click', () => emit(true));
  $('clear-probe').addEventListener('click', () => {photon = null; updateProbe(); dirty = true;});
  $('about-button').addEventListener('click', guide); $('science-link').addEventListener('click', guide);
  $('close-dialog').addEventListener('click', () => $('about-dialog').close());
  $('about-dialog').addEventListener('click', e => {if (e.target === $('about-dialog')) {const r = e.target.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close();}});
  $('fullscreen').addEventListener('click', () => setFocus(!focus)); $('focus-exit').addEventListener('click', () => setFocus(false));
  $('save-session').addEventListener('click', save); $('capture').addEventListener('click', capture); $('export-csv').addEventListener('click', exportCSV);
  $('open-session').addEventListener('click', () => $('session-file').click());
  $('session-file').addEventListener('change', e => {openSession(e.target.files[0]); e.target.value = '';});
  cvs.addEventListener('pointerdown', e => {if (state.view === 'spacetime') return; dragging = {x: e.clientX, y: e.clientY}; cvs.setPointerCapture(e.pointerId);});
  cvs.addEventListener('pointermove', e => {if (!dragging) return; state.yaw += (e.clientX - dragging.x) * .006; state.pitch = P.clamp(state.pitch + (e.clientY - dragging.y) * .006, -1.4, 1.4); dragging = {x: e.clientX, y: e.clientY}; dirty = true;});
  cvs.addEventListener('pointerup', () => dragging = null); cvs.addEventListener('pointercancel', () => dragging = null);
  cvs.addEventListener('wheel', e => {if (state.view === 'spacetime') return; e.preventDefault(); state.zoom = P.clamp(state.zoom * Math.exp(-e.deltaY * .001), .5, 2); dirty = true;}, {passive: false});
  document.addEventListener('keydown', e => {
    if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) || e.ctrlKey || e.altKey || e.metaKey || e.repeat) return;
    if ($('about-dialog').open) return;
    if (e.key === ' ') {if (e.target.tagName === 'BUTTON') return; e.preventDefault(); $('play').click();}
    else if (e.key.toLowerCase() === 'r') resetCamera();
    else if (e.key.toLowerCase() === 'f') setFocus(!focus);
    else if (e.key === '?') guide();
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {e.preventDefault(); setP(state.p + (e.key === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? .025 : .0025));}
    else if (e.key === 'Escape' && focus) setFocus(false);
  });
  document.addEventListener('visibilitychange', () => {lastTime = 0; dirty = true;});
  window.addEventListener('resize', resize);
  if ('ResizeObserver' in window) new ResizeObserver(resize).observe($('universe-panel'));
  recalcCurves(); updateControls(); updateUI(); resize(); requestAnimationFrame(frame);
  // Read-only diagnostics make the numerical state inspectable without coupling it to artwork.
  Object.defineProperty(window, 'HorizonObservatory', {value: Object.freeze({version: '1.0.0',
    snapshot: () => ({state: structuredClone(state), sample: {...sample}, source: data.source_commit, probe: photon ? structuredClone(photon) : null}),
    validateSession}), writable: false});
})();
