// Las figuras isométricas del sitio (dibujadas con el kit de Anatomy en web/figuras). figuras.js las
// trae cuando se acercan a la vista y les da movimiento con significado:
//
//   reposo → disparo → tránsito (400–700 ms) → resultado → reposo (≥ 2,6 s, todo quieto)
//
// Cada figura es una función pura del tiempo: pose(turno, t) pone las piezas vivas y devuelve la
// lectura de ese instante, así la lectura cambia en el cuadro en que llega el dato, una captura
// puede pedir cualquier instante y con movimiento reducido basta pose(turno, dura) (el resultado).
//
// Rendimiento: el SVG llega en dos capas (capa-fija y capa-viva); la viva va en su propio <svg>
// encima y solo se mueve con transform y opacity. Un planificador único deja viva una sola figura
// (la más visible); corre dos ciclos al entrar en vista y vuelve con el puntero, el toque, el foco o
// las flechas. Fuera de eso no hay ningún cuadro: cero repintado en reposo. Con puntero grueso o
// pocos núcleos, 30 cuadros por segundo.
const quieto = matchMedia('(prefers-reduced-motion: reduce)');
const lento = matchMedia('(pointer: coarse)').matches || (navigator.hardwareConcurrency || 8) <= 4;
const REPOSO = 2600, MEZCLA = 280, AUTOS = 2;

// ---------------------------------------------------------------- curvas y tiempos
function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const X = t => ((ax * t + bx) * t + cx) * t, dX = t => (3 * ax * t + 2 * bx) * t + cx;
  return x => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 6; i++) { const e = X(t) - x, d = dX(t); if (Math.abs(e) < 1e-5 || !d) break; t -= e / d; }
    return ((ay * t + by) * t + cy) * t;
  };
}
const entra = bezier(0, 0, 0.3, 1);       // llegar: rápido al principio, se posa
const sale = bezier(0.4, 0.14, 1, 1);     // irse: arranca suave, termina rápido
const mueve = bezier(0.45, 0, 0.3, 1);    // de un punto a otro
// avance 0..1 de un tramo [t0, t0 + dur]
const tramo = (t, t0, dur, curva = mueve) => curva(Math.min(1, Math.max(0, (t - t0) / dur)));
// resorte críticamente amortiguado de 0 a 1 en ~dur (sin pasarse)
const resorte = (t, t0, dur) => { const u = Math.max(0, t - t0) * 7.4 / dur; return u >= 7.4 ? 1 : 1 - (1 + u) * Math.exp(-u); };
// resorte subamortiguado (una aguja que se asienta): oscila solo mientras llega
const asienta = (t, t0, dur, zeta = 0.42) => {
  const u = Math.max(0, t - t0) / dur;
  if (u >= 1) return 1;
  const w = 9.5, wd = w * Math.sqrt(1 - zeta * zeta);
  return 1 - Math.exp(-zeta * w * u) * (Math.cos(wd * u) + (zeta * w / wd) * Math.sin(wd * u));
};
// posición sobre una polilínea en pantalla (puntos precalculados), por fracción de su largo
function sobre(pts, f) {
  let total = 0;
  const l = [];
  for (let i = 1; i < pts.length; i++) { l.push(Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])); total += l[i - 1]; }
  let d = Math.max(0, Math.min(1, f)) * total;
  for (let i = 0; i < l.length; i++) {
    if (d <= l[i] || i === l.length - 1) { const u = l[i] ? Math.min(1, d / l[i]) : 0; return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u]; }
    d -= l[i];
  }
  return pts[pts.length - 1];
}

// ---------------------------------------------------------------- canales y pintura
// Cada pieza viva tiene canales numéricos: x, y (traslado en unidades del viewBox), o (opacidad) y
// k (un parámetro propio: un ángulo, una escala). pinta(el, c) los escribe; por omisión, traslado y
// opacidad. Solo se toca el DOM si el valor cambió.
const CERO = { x: 0, y: 0, o: 1, k: 0 };
function pintaBase(el, c, antes) {
  if (!antes || antes.x !== c.x || antes.y !== c.y) el.style.transform = c.x || c.y ? `translate(${c.x.toFixed(2)}px,${c.y.toFixed(2)}px)` : '';
  if (!antes || antes.o !== c.o) el.style.opacity = c.o >= 0.999 ? '' : c.o <= 0.001 ? '0' : c.o.toFixed(3);
}

function motorDe(F) {
  const hechos = new Map(); // el -> canales pintados
  let desde = null, t0Mezcla = 0;
  const pinta = (el, c) => {
    const antes = hechos.get(el);
    if (antes && antes.x === c.x && antes.y === c.y && antes.o === c.o && antes.k === c.k) return;
    (el.__pinta || pintaBase)(el, c, antes);
    hechos.set(el, c);
  };
  // dibuja la pose del turno i en t; si hay mezcla en curso, parte de lo que se veía
  function poner(i, t, ahora) {
    const nuevos = new Map();
    const pon = (el, c) => { if (el) nuevos.set(el, { ...CERO, ...c }); };
    const lectura = F.m.pose(i, t, pon);
    const m = desde ? Math.min(1, (ahora - t0Mezcla) / MEZCLA) : 1;
    const e = entra(m);
    for (const [el, c] of nuevos) {
      const a = desde && desde.get(el);
      pinta(el, a && m < 1 ? { x: a.x + (c.x - a.x) * e, y: a.y + (c.y - a.y) * e, o: a.o + (c.o - a.o) * e, k: a.k + (c.k - a.k) * e } : c);
    }
    if (m >= 1) desde = null;
    if (lectura !== undefined && lectura !== null) F.decir(lectura);
    return m < 1;
  }
  return {
    poner,
    mezclar(ahora) { desde = new Map(hechos); t0Mezcla = ahora; },
  };
}

// ---------------------------------------------------------------- el planificador
const FIGS = [];
let viva = null, cuadro = 0, ultimo = 0;

function bucle(ahora) {
  cuadro = 0;
  const F = viva;
  if (!F || !F.corre) return;
  if (lento && ultimo && ahora - ultimo < 30) { cuadro = requestAnimationFrame(bucle); return; }
  ultimo = ahora;
  const t = ahora - F.inicio;
  const dura = F.m.dura(F.turno);
  const mezcla = F.motor.poner(F.turno, Math.min(t, dura), ahora);
  if (t >= dura && !mezcla) terminar(F);
  else cuadro = requestAnimationFrame(bucle);
}
function despertar() { if (!cuadro) { ultimo = 0; cuadro = requestAnimationFrame(bucle); } }

function terminar(F) {
  F.corre = false;
  F.vivo.classList.remove('animando');
  clearTimeout(F.espera);
  if (F === viva && F.autos < AUTOS && !quieto.matches) {
    F.espera = setTimeout(() => { if (viva === F && !F.corre && F.autos < AUTOS) { F.autos++; jugar(F, (F.turno + 1) % F.m.n); } }, REPOSO);
  }
}
// cierra el ciclo en curso de una figura que deja de estar viva: salta a su resultado
function cerrar(F) {
  clearTimeout(F.espera);
  if (!F.corre) return;
  F.motor.poner(F.turno, F.m.dura(F.turno), Infinity);
  F.corre = false;
  F.vivo.classList.remove('animando');
}
function jugar(F, i) {
  if (quieto.matches) { fijo(F, i); return; }
  if (viva && viva !== F) cerrar(viva);
  viva = F;
  clearTimeout(F.espera);
  const ahora = performance.now();
  F.motor.mezclar(ahora);
  F.turno = i; F.inicio = ahora; F.corre = true;
  F.vivo.classList.add('animando');
  despertar();
}
function fijo(F, i) {
  F.turno = i;
  F.motor.mezclar(-Infinity);
  F.motor.poner(i, F.m.dura(i), Infinity);
}
// la figura más visible (al menos un tercio en pantalla) es la única que puede correr sola
function elegirViva() {
  let mejor = null;
  for (const F of FIGS) if (F.razon >= 0.34 && (!mejor || F.razon > mejor.razon)) mejor = F;
  if (mejor === viva) return;
  if (viva) cerrar(viva);
  viva = mejor;
  if (mejor && mejor.autos < AUTOS && !quieto.matches) { mejor.autos++; jugar(mejor, mejor.autos === 1 ? 0 : (mejor.turno + 1) % mejor.m.n); }
}
const umbrales = Array.from({ length: 21 }, (_, i) => i / 20);
const vista = new IntersectionObserver(es => {
  for (const e of es) { const F = FIGS.find(f => f.lienzo === e.target); if (F) F.razon = e.isIntersecting ? e.intersectionRatio : 0; }
  elegirViva();
}, { threshold: umbrales });

// ---------------------------------------------------------------- montar una figura
function montar(fig, nombre, crear) {
  const lienzo = fig.querySelector('.lienzo');
  const fija = lienzo.querySelector('svg');
  const vivo = fija.cloneNode(false);
  vivo.removeAttribute('role'); vivo.removeAttribute('aria-label'); vivo.removeAttribute('data-vivo');
  vivo.setAttribute('aria-hidden', 'true');
  vivo.classList.add('capa-viva-svg');
  const capa = fija.querySelector(':scope > .capa-viva');
  if (capa) vivo.append(capa);
  lienzo.append(vivo);
  const V = JSON.parse(fija.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const pieza = n => vivo.querySelector(`[data-v="${n}"]`);
  const F = { fig, nombre, lienzo, vivo, V, razon: 0, autos: 0, turno: 0, corre: false, inicio: 0, espera: 0 };
  let dicho = '';
  F.decir = txt => {
    const clave = Array.isArray(txt) ? txt.map(p => typeof p === 'string' ? p : '`' + p.c).join('') : txt;
    if (clave === dicho) return;
    dicho = clave;
    if (!Array.isArray(txt)) { lectura.textContent = txt; return; }
    lectura.replaceChildren(...txt.map(p => { if (typeof p === 'string') return p; const c = document.createElement('code'); c.textContent = p.c; return c; }));
  };
  F.m = crear({ V, pieza, vivo, fija });
  F.motor = motorDe(F);
  // el puntero (ratón) elige; el toque y el clic juegan; el foco y las flechas también
  const enCaja = e => {
    const caja = lienzo.getBoundingClientRect(), vb = fija.viewBox.baseVal;
    return [vb.x + (e.clientX - caja.left) / caja.width * vb.width, vb.y + (e.clientY - caja.top) / caja.height * vb.height];
  };
  const tomar = i => { F.autos = AUTOS; if (i === F.turno && (F.corre || quieto.matches)) return; jugar(F, i); };
  lienzo.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse' || !F.m.desde) return;
    const i = F.m.desde(...enCaja(e));
    if (i >= 0 && (i !== F.turno || viva !== F)) tomar(i);
  });
  lienzo.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse' && !F.m.desde && !F.corre) tomar((F.turno + 1) % F.m.n); });
  lienzo.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') return;
    const i = F.m.desde ? F.m.desde(...enCaja(e)) : -1;
    tomar(i >= 0 ? i : (F.turno + 1) % F.m.n);
  });
  lienzo.addEventListener('focus', () => { if (!F.corre) tomar(F.turno); });
  lienzo.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    tomar((F.turno + d + F.m.n) % F.m.n);
  });
  // estado inicial: el reposo antes del primer ciclo; con movimiento reducido, el resultado
  if (quieto.matches) fijo(F, 0); else F.motor.poner(0, 0, Infinity);
  FIGS.push(F);
  vista.observe(lienzo);
  return F;
}

// Para capturas y pruebas: un instante cualquiera de un turno, sin correr el reloj.
window.__figuras = {
  info: n => { const F = FIGS.find(f => f.nombre === n); return F && { turnos: F.m.n, dura: Array.from({ length: F.m.n }, (_, i) => F.m.dura(i)), cuadros: F.m.cuadros || [] }; },
  ver: (n, i, ms) => {
    const F = FIGS.find(f => f.nombre === n);
    if (!F) return;
    if (viva) cerrar(viva);
    viva = null; F.autos = AUTOS; F.turno = i;
    F.motor.mezclar(-Infinity);
    F.motor.poner(i, ms, Infinity);
  },
};

// ================================================================ las figuras
const FIG = {};

// Fig. capas: el dato sube por el cable del módulo que pregunta; al llegar, su piloto se enciende.
FIG.capas = ({ V, pieza }) => {
  const datos = V.viajes.map((_, j) => pieza('dato' + j));
  const pilotos = V.viajes.map((_, j) => pieza('piloto' + j));
  const APARECE = 220, VIAJA = 640, LLEGA = APARECE + VIAJA, DURA = LLEGA + 380;
  return {
    n: V.modulos.length,
    dura: () => DURA,
    cuadros: [[0, 0], [0, 180], [0, 420], [0, 640], [0, LLEGA + 40], [0, DURA], [1, DURA], [2, DURA]],
    pose(i, t, pon) {
      datos.forEach((el, j) => {
        const [vx, vy] = V.viajes[j];
        if (j !== i) { pon(el, { x: vx, y: vy, o: 0 }); return; }
        const f = tramo(t, APARECE, VIAJA, mueve);
        pon(el, { x: vx * f, y: vy * f, o: tramo(t, 0, APARECE, entra) });
      });
      pilotos.forEach((el, j) => pon(el, { o: j === i ? tramo(t, LLEGA, 140, entra) : 0 }));
      const m = V.modulos[i];
      if (t < 120) return V.reposo;
      return t < LLEGA ? `datos → ${m.n} · por ${m.p}` : `${m.n} · ${m.q} · entra por ${m.p}`;
    },
    desde: (x, y) => V.franjas.findIndex(([a, b]) => y >= a - 3 && y <= b + 3),
  };
};

// Fig. ruta: la pregunta corre por la regla, el lector valida la llave, la barrera se levanta, la
// tapa de la columna de su entidad se enciende y la respuesta vuelve a la terminal.
FIG.ruta = ({ V, pieza }) => {
  const preg = pieza('pregunta'), resp = pieza('respuesta-ficha'), lineas = pieza('respuesta');
  const lector = pieza('lector'), brazo = pieza('brazo');
  const tapas = V.turnos.map((_, i) => pieza('tapa' + i));
  const [u0, v0] = V.eje;
  brazo.__pinta = (el, c, antes) => { if (!antes || antes.k !== c.k) el.style.transform = c.k ? `translate(${u0}px,${v0}px) rotate(${c.k.toFixed(2)}deg) translate(${-u0}px,${-v0}px)` : ''; };
  const ALZA = 84;
  const tiempos = k => {
    const [l1, l2, l3] = V.largos[k], total = l1 + l2 + l3;
    const T1 = 200 + 460;                              // la pregunta llega al lector
    const T2 = T1 + 320 + 440 + (l2 + l3) / 150 * 320; // llega a la columna
    const VUELTA = 760, T3 = T2 + 200 + VUELTA;        // la respuesta llega a la terminal
    return { s1: l1 / total, T1, T2, T3, VUELTA, baja: T2 + 200 + (l3 / total) * VUELTA + 60, dura: T3 + 420 };
  };
  const T = V.turnos.map((_, k) => tiempos(k));
  return {
    n: V.turnos.length,
    dura: k => T[k].dura,
    cuadros: [[0, 0], [0, 520], [0, T[0].T1 + 200], [0, T[0].T1 + 600], [0, T[0].T2 + 80], [0, T[0].T2 + 560], [0, T[0].dura], [2, T[2].dura]],
    pose(k, t, pon) {
      const { s1, T1, T2, T3, VUELTA, baja } = T[k];
      const pts = V.recorridos[k];
      // la pregunta: aparece en la terminal, va al lector, espera la barrera, sigue a la columna
      const f = t < T1 ? s1 * tramo(t, 200, T1 - 200, mueve) : s1 + (1 - s1) * tramo(t, T1 + 320, T2 - T1 - 320, mueve);
      const [px, py] = sobre(pts, f);
      pon(preg, { x: px, y: py, o: tramo(t, 0, 200, entra) * (1 - tramo(t, T2, 160, sale)) });
      pon(lector, { o: tramo(t, T1, 120, entra) * (1 - tramo(t, T3, 200, sale)) });
      pon(brazo, { k: ALZA * (tramo(t, T1 + 100, 360, entra) - tramo(t, baja, 380, mueve)) });
      tapas.forEach((el, i) => pon(el, { o: i === k ? tramo(t, T2, 140, entra) : 0 }));
      // la respuesta: de la columna a la terminal
      const [rx, ry] = sobre(pts, 1 - tramo(t, T2 + 200, VUELTA, mueve));
      pon(resp, { x: rx, y: ry, o: tramo(t, T2 + 80, 160, entra) * (1 - tramo(t, T3, 160, sale)) });
      pon(lineas, { o: tramo(t, T3, 220, entra) });
      const d = V.turnos[k];
      if (t < 120) return [d.p];
      if (t < T2) return [`${d.p} → `, { c: d.h }];
      if (t < T3) return [`${d.p} → `, { c: d.h }, ` → ${d.e}`];
      return [`${d.p} → `, { c: d.h }, ` → ${d.e} · ${d.l} · ${d.s}`];
    },
    desde: x => { let mejor = 0; V.franjas.forEach((fx, i) => { if (Math.abs(fx - x) < Math.abs(V.franjas[mejor] - x)) mejor = i; }); return mejor; },
  };
};

// ================================================================ legado (se migra por tandas)
const sigue = (actual, meta, dt, s) => actual + (meta - actual) * (1 - Math.exp(-dt / s));

function enVista(el, cambio) {
  new IntersectionObserver(es => cambio(es[es.length - 1].isIntersecting), { rootMargin: '80px 0px' }).observe(el);
}

// ---------------------------------------------------------------- vida ambiente
// Un bucle por figura que corre mientras está en vista (y nunca con movimiento reducido): mueve
// paquetes por cables y rieles, balancea agujas, hace latir lo que late. tick(t) recibe segundos.
function ambiente(fig, tick) {
  if (quieto.matches) return;
  const lienzo = fig.querySelector('.lienzo');
  let raf = 0, vis = false;
  const bucle = ahora => { tick(ahora / 1000); raf = vis ? requestAnimationFrame(bucle) : 0; };
  enVista(lienzo, v => { vis = v; if (v && !raf) raf = requestAnimationFrame(bucle); });
}
// Paquetes de datos: bloques de color que recorren un trazo (un <path>) a su ritmo.
function paquetes(svg, trazo, { n = 2, color = 'var(--teal-400)', r = 1.6, periodo = 2.4, desde = 0, al = 1, desfase = 0 } = {}) {
  const ns = 'http://www.w3.org/2000/svg', largo = trazo.getTotalLength();
  const ps = Array.from({ length: n }, () => {
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('class', 'paquete'); c.setAttribute('r', r); c.style.fill = color;
    trazo.parentNode.insertBefore(c, trazo.nextSibling);
    return c;
  });
  return t => ps.forEach((c, i) => {
    const u = ((t / periodo + i / n + desfase) % 1 + 1) % 1;
    const f = desde + (al - desde) * u;
    const p = trazo.getPointAtLength(largo * f);
    c.setAttribute('cx', p.x.toFixed(1)); c.setAttribute('cy', p.y.toFixed(1));
    c.style.opacity = String(Math.min(1, Math.min(u, 1 - u) * 8));
  });
}
const escribir = svg => svg.querySelectorAll('.escribe path').forEach(p => p.setAttribute('pathLength', '1'));

// ---------------------------------------------------------------- herramientas comunes
// Elegir uno de n: recorrido en reposo, el puntero y las flechas eligen, y vuelve el recorrido
// 3,6 s después del último toque. pintar(dt) mueve las piezas y devuelve true mientras algo se mueva.
function selector(fig, { n, cada = 2.8, elegir, pintar, desde }) {
  const lienzo = fig.querySelector('.lienzo');
  let actual = 0, tour = !quieto.matches, reloj = 0, ultimo = 0, cuadro = 0, visible = false, espera = 0;
  const poner = i => { actual = i; elegir(i); };
  function paso(ahora) {
    const dt = ultimo ? Math.min((ahora - ultimo) / 1000, 1 / 20) : 1 / 60;
    ultimo = ahora;
    if (tour) { reloj += dt; const i = Math.floor(reloj / cada) % n; if (i !== actual) poner(i); }
    const mueve = pintar(quieto.matches ? 1e3 : dt);
    cuadro = visible && (tour || mueve) ? requestAnimationFrame(paso) : 0;
  }
  const correr = () => { if (!cuadro && visible) { ultimo = 0; cuadro = requestAnimationFrame(paso); } };
  const tomar = i => {
    tour = false; if (i !== actual) poner(i); correr();
    clearTimeout(espera);
    espera = setTimeout(() => { tour = !quieto.matches; reloj = actual * cada; correr(); }, 3600);
  };
  if (desde) lienzo.addEventListener('pointermove', e => {
    const caja = lienzo.getBoundingClientRect(), vb = lienzo.querySelector('svg').viewBox.baseVal;
    const i = desde(vb.x + (e.clientX - caja.left) / caja.width * vb.width, vb.y + (e.clientY - caja.top) / caja.height * vb.height);
    if (i >= 0) tomar(i);
  });
  lienzo.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    tomar((actual + d + n) % n);
  });
  poner(0);
  pintar(1e3);
  enVista(lienzo, v => { visible = v; if (v) correr(); });
  return { tomar };
}
const cerca2 = (pts, x, y) => {
  let mejor = -1, d = Infinity;
  pts.forEach(([px, py], i) => { const q = Math.hypot(px - x, (py - y) * 0.6); if (q < d) { d = q; mejor = i; } });
  return d < 70 ? mejor : -1;
};

// ---------------------------------------------------------------- la prueba: el fichero
function prueba(fig) {
  const svg = fig.querySelector('svg');
  const vivo = JSON.parse(svg.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const fichas = [];
  svg.querySelectorAll('[data-ficha]').forEach(g => { fichas[+g.dataset.ficha] = g; });
  const notas = [...document.querySelectorAll('.notas-p [data-capa]')];
  const sello = svg.querySelector('[data-sello]');
  escribir(svg);
  // resortes: cada ficha entra cayendo desde arriba, escalonada, y rebota en el piso del fichero
  const alto = fichas.map((_, j) => ({ x: 2.4 + j * 0.35, v: 0 }));
  const st = { x: 0, v: 0 };
  let meta = 0, llega = -1, ultimo = 0;
  const [dx, dy] = vivo.sube;
  const { cruza, arriba, fieltro, salto } = vivo.sello;
  function aplicar(t) {
    fichas.forEach((g, j) => {
      // la ficha que se lee se mece un poco, como sostenida en la mano
      const a = alto[j].x + (j === meta && !quieto.matches ? Math.sin(t * 1.7) * 0.025 * Math.min(1, alto[j].x) : 0);
      if (Math.abs(a) > 0.001) g.setAttribute('transform', `translate(${(dx * a).toFixed(2)} ${(dy * a).toFixed(2)})`); else g.removeAttribute('transform');
      g.querySelector('[data-pestana] > .iso-solid').toggleAttribute('data-lit', j === meta && alto[j].x > 0.5);
      g.classList.toggle('activa', j === meta);
    });
    // el sello cruza, sube y cae al tampón con un rebote; en la huella marca cada tanto
    const s = Math.max(0, Math.min(1, st.x));
    let z = fieltro * s + salto * Math.sin(Math.PI * s);
    if (llega >= 0) {
      const u = t - llega;
      z += Math.exp(-4 * u) * Math.abs(Math.sin(10 * u)) * 2.2;
      if (u > 1.4) z += Math.max(0, Math.sin(((u - 1.4) / 2.2) * Math.PI * 2)) ** 6 * 3.5;
    }
    if (s > 0.001) sello.setAttribute('transform', `translate(${(cruza[0] * s + arriba[0] * z).toFixed(2)} ${(cruza[1] * s + arriba[1] * z).toFixed(2)})`);
    else sello.removeAttribute('transform');
  }
  function paso(dt, t) {
    const K = 70, C = 2 * Math.sqrt(K) * 0.5;
    alto.forEach((a, j) => {
      const m = j === meta ? 1 : 0;
      a.v += (K * (m - a.x) - C * a.v) * dt; a.x += a.v * dt;
      if (a.x < 0) { a.x = 0; a.v = -a.v * 0.3; }
    });
    const ms = meta === fichas.length - 1 ? 1 : 0;
    st.v += (40 * (ms - st.x) - 2 * Math.sqrt(40) * st.v) * dt; st.x += st.v * dt;
    if (ms && st.x > 0.995 && llega < 0) llega = t;
    if (!ms) llega = -1;
    aplicar(t);
  }
  selector(fig, {
    n: fichas.length,
    elegir: i => {
      meta = i;
      lectura.textContent = vivo.lecturas[i];
      notas.forEach(nt => nt.classList.toggle('vivo', +nt.dataset.capa === i));
    },
    pintar: () => {
      if (!quieto.matches) return false;
      alto.forEach((a, j) => { a.x = j === meta ? 1 : 0; a.v = 0; });
      st.x = meta === fichas.length - 1 ? 1 : 0;
      aplicar(0);
      return false;
    },
    desde: (x, y) => cerca2(vivo.pestanas, x, y),
  });
  ambiente(fig, t => { const dt = ultimo ? Math.min(t - ultimo, 1 / 20) : 1 / 60; ultimo = t; paso(dt, t); });
}

// ---------------------------------------------------------------- un guion que se repite
// Corre guion(t, i) con t en segundos dentro del turno i; dura(i) es lo que dura el turno. Las
// flechas pasan de turno; fuera de la vista no corre; con movimiento reducido, quieto(i) deja el
// turno completo.
function guionado(fig, { n, dura, guion, quieto: fijo }) {
  const lienzo = fig.querySelector('.lienzo');
  let i = 0, t = 0, ultimo = 0, cuadro = 0, visible = false;
  function paso(ahora) {
    const dt = ultimo ? Math.min((ahora - ultimo) / 1000, 1 / 20) : 1 / 60;
    ultimo = ahora; t += dt;
    if (t >= dura(i)) { t = 0; i = (i + 1) % n; }
    guion(t, i);
    cuadro = visible ? requestAnimationFrame(paso) : 0;
  }
  const correr = () => { if (!cuadro && visible && !quieto.matches) { ultimo = 0; cuadro = requestAnimationFrame(paso); } };
  lienzo.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    i = (i + d + n) % n; t = 0;
    if (quieto.matches) fijo(i); else guion(0, i);
  });
  if (quieto.matches) fijo(0); else guion(0, 0);
  enVista(lienzo, v => { visible = v; if (v) correr(); });
}
const suave = x => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
const mover = (g, v, a, b) => {
  const dx = v[0][0] * a + v[1][0] * b, dy = v[0][1] * a + v[1][1] * b;
  if (Math.abs(dx) + Math.abs(dy) < 0.01) g.removeAttribute('transform');
  else g.setAttribute('transform', `translate(${dx.toFixed(2)} ${dy.toFixed(2)})`);
};

// ---------------------------------------------------------------- debida diligencia: la banda
function revision(fig) {
  const svg = fig.querySelector('svg');
  const V = JSON.parse(svg.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const ficha = svg.querySelector('[data-ficha]');
  const bandera = svg.querySelector('[data-bandera]');
  const palp = [...svg.querySelectorAll('[data-palpador]')];
  const pilotos = [...svg.querySelectorAll('[data-piloto]')];
  svg.querySelector('[data-motor]').classList.add('encendido');
  const ejes = [V.ex, V.ez];
  // tiempos del turno: sale, cuatro paradas (baja, sube, sigue), llega al final, cae, reposa
  const SALE = 1.1, PARA = 1.25, VIAJA = 0.6, FIN = 0.8, CAE = 0.7, REPOSA = 1.4;
  const llega = k => SALE + k * (PARA + VIAJA);
  const tFin = llega(V.est.length - 1) + PARA;
  const dura = () => tFin + FIN + CAE + REPOSA;
  let dicho = '';
  function decir(txt) { if (txt !== dicho) { dicho = txt; lectura.textContent = txt; } }
  function guion(t, i) {
    const tipo = V.tipos[i];
    let x = V.x0, z = 0;
    if (t < SALE) x = V.x0 + (V.est[0] - V.x0) * suave(t / SALE);
    else if (t < tFin) {
      const k = Math.min(V.est.length - 1, Math.floor((t - SALE) / (PARA + VIAJA)));
      const u = t - llega(k);
      x = u < PARA ? V.est[k] : V.est[k] + (V.est[k + 1] - V.est[k]) * suave((u - PARA) / VIAJA);
    } else if (t < tFin + FIN) x = V.est[3] + (V.fin - V.est[3]) * suave((t - tFin) / FIN);
    else { const u = suave((t - tFin - FIN) / CAE); x = V.fin + (V.bandeja - V.fin) * u; z = -V.cae * u * u; }
    mover(ficha, ejes, x - V.x0, z);
    ficha.style.opacity = t > dura() - 0.45 ? String(Math.max(0, (dura() - t) / 0.45)) : '';
    let texto = `${tipo.t} · ${tipo.c} · ${tipo.f.length} fuentes`;
    palp.forEach((g, k) => {
      const u = t - llega(k);
      const b = u < 0 || u > PARA ? 0 : u < 0.4 ? suave(u / 0.4) : u < 0.75 ? 1 : 1 - suave((u - 0.75) / 0.4);
      mover(g, ejes, 0, -V.baja * b);
      const visto = u >= 0.4;
      const estado = !visto ? '' : tipo.h === k ? 'rev' : 'ok';
      if (pilotos[k].dataset.estado !== estado) { if (estado) pilotos[k].dataset.estado = estado; else delete pilotos[k].dataset.estado; }
      if (u >= 0 && u < PARA + VIAJA) texto = `${tipo.t} · ${tipo.f[k]} · ${!visto ? 'consultando' : tipo.h === k ? 'revisar' : 'sin hallazgos'}`;
    });
    if (t >= tFin) texto = `${tipo.t} · expediente: ${tipo.h == null ? 'sin hallazgos' : '1 caso para revisar'}`;
    bandera.style.opacity = tipo.h != null && t - llega(tipo.h) >= 0.45 ? '1' : '0';
    decir(texto);
  }
  // quieto: la ficha en la última estación con los cuatro pilotos dichos
  const fijo = i => guion(tFin, i);
  guionado(fig, { n: V.tipos.length, dura, guion, quieto: fijo });
  // vida: la cinta avanza sin parar y el motor late
  const cinta = svg.querySelector('[data-cinta]');
  svg.querySelector('[data-motor]').classList.add('late');
  ambiente(fig, t => { const u = (t * 7) % V.paso; mover(cinta, [V.ex, V.ez], u, 0); });
}

// La cámara del kit (iso-kit.mjs, iso), para lo que se rehace en cada cuadro.
const camara = P => {
  const R = Math.PI / 180, K = P.scale * Math.sqrt(1.6);
  const sA = Math.sin(P.azimuth * R), cA = Math.cos(P.azimuth * R), sE = Math.sin(P.elevation * R), cE = Math.cos(P.elevation * R);
  return ([x, y, z]) => [P.origin[0] + (x * sA - y * cA) * K, P.origin[1] + ((x * cA + y * sA) * sE - z * cE) * K];
};

// ---------------------------------------------------------------- tableros: relojes y trazador
function tablero(fig) {
  const svg = fig.querySelector('svg');
  const V = JSON.parse(svg.dataset.vivo);
  const iso = camara(V.P);
  const lectura = fig.querySelector('[data-lectura]');
  const agujas = [...svg.querySelectorAll('[data-aguja]')];
  const series = [...svg.querySelectorAll('[data-serie]')];
  const portico = svg.querySelector('[data-portico]');
  const carro = svg.querySelector('[data-carro]');
  const ang = V.valores.slice();
  let meta = 0, p = 1;
  const DIBUJA = 2.8;
  const aguja = (i, v) => {
    const [cx, cy] = V.centros[i], t = V.desde + V.arco * v;
    const a = iso([cx - Math.sin(t) * 2.2, cy + Math.cos(t) * 2.2, V.zd + 0.2]), b = iso([cx + Math.sin(t) * V.R, cy - Math.cos(t) * V.R, V.zd + 0.2]);
    agujas[i].setAttribute('d', `M${a[0].toFixed(1)} ${a[1].toFixed(1)}L${b[0].toFixed(1)} ${b[1].toFixed(1)}`);
  };
  // la pluma sobre la serie, a la fracción f de su largo
  const sobre = (pts, f) => {
    const u = Math.max(0, Math.min(1, f)) * (pts.length - 1), j = Math.min(pts.length - 2, Math.floor(u)), r = u - j;
    return [pts[j][0] + (pts[j + 1][0] - pts[j][0]) * r, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * r];
  };
  const centros = V.centros.map(([x, y]) => iso([x, y, V.zd]));
  selector(fig, {
    n: agujas.length,
    cada: 4.2,
    elegir: i => {
      meta = i; p = quieto.matches ? 1 : 0; ang[i] = quieto.matches ? V.valores[i] : 0;
      lectura.textContent = V.lecturas[i];
      agujas.forEach((a, j) => a.toggleAttribute('data-on', j === i));
      series.forEach((sv, j) => { sv.style.opacity = j === i ? '1' : '0'; });
    },
    pintar: dt => {
      let mueve = false;
      ang.forEach((v, i) => {
        const m = V.valores[i];
        ang[i] = sigue(v, m, dt, 0.5);
        if (Math.abs(ang[i] - m) < 0.001) ang[i] = m; else mueve = true;
        aguja(i, ang[i]);
      });
      if (p < 1) { p = Math.min(1, p + dt / DIBUJA); mueve = true; }
      const sp = suave(p);
      series[meta].style.strokeDashoffset = String(100 - 100 * sp);
      const [dx, dy] = sobre(V.series[meta], sp);
      portico.setAttribute('transform', `translate(${(V.ex[0] * dx).toFixed(2)} ${(V.ex[1] * dx).toFixed(2)})`);
      carro.setAttribute('transform', `translate(${(V.ey[0] * dy).toFixed(2)} ${(V.ey[1] * dy).toFixed(2)})`);
      return mueve;
    },
    desde: (x, y) => cerca2(centros, x, y),
  });
  // vida: las agujas tiemblan alrededor de su lectura, cada una a su ritmo
  ambiente(fig, t => ang.forEach((v, i) => aguja(i, v + Math.sin(t * (1.1 + i * 0.37) + i) * 0.012 + Math.sin(t * 3.3 + i * 2) * 0.004)));
}

// ---------------------------------------------------------------- vigilancia: el puesto de guardia
function vigilancia(fig) {
  const svg = fig.querySelector('svg');
  const V = JSON.parse(svg.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const carro = svg.querySelector('[data-carro]');
  const lector = svg.querySelector('[data-lector]');
  const ticket = svg.querySelector('[data-ticket]');
  const banderas = [...svg.querySelectorAll('[data-bandera]')];
  const pilotos = [...svg.querySelectorAll('[data-buzon] [data-piloto]')];
  const pImp = svg.querySelector('[data-piloto="imp"]');
  const ejes = [V.ex, V.ez];
  const n = V.carriles.length;
  const VA = 1.6, LEE = 0.5, SUBE = 0.5, SACA = 1.2, DURA = 6.4;
  let dicho = '';
  const estado = (el, e) => { if ((el.dataset.estado || '') !== e) { if (e) el.dataset.estado = e; else delete el.dataset.estado; } };
  function guion(t, i) {
    const prev = (i - 1 + n) % n, c = V.carriles[i];
    const x = V.x[prev] + (V.x[i] - V.x[prev]) * suave(t / VA);
    mover(carro, ejes, x, 0);
    const t1 = VA + LEE, t2 = t1 + SUBE, t3 = t2 + SACA;
    estado(lector, t >= VA && t < t1 + 0.3 ? 'ok' : '');
    banderas.forEach((b, j) => {
      const u = j === i ? suave((t - t1) / SUBE) : j === prev ? 1 - suave(t / 0.5) : 0;
      mover(b, ejes, 0, V.sube * u);
      b.querySelector('.iso-solid:last-child').toggleAttribute('data-lit', j === i && t >= t1);
    });
    pilotos.forEach((p, j) => estado(p, j === i && t >= t1 ? 'rev' : ''));
    const sale = t < 0.4 ? 1 - t / 0.4 : t < t2 ? 0 : suave((t - t2) / SACA);
    ticket.style.opacity = t < 0.4 ? String(1 - t / 0.4) : '';
    mover(ticket, ejes, 0, V.saca * (t < 0.4 ? 1 : sale));
    estado(pImp, t >= t2 && t < t3 ? 'ok' : '');
    const txt = t < t1 ? `leyendo ${c.s}…` : `${c.s} · ${c.e} · ${c.ev}`;
    if (txt !== dicho) { dicho = txt; lectura.textContent = txt; }
  }
  const fijo = i => guion(DURA - 0.01, i);
  guionado(fig, { n, dura: () => DURA, guion, quieto: fijo });
  // vida: los registros viajan por el canto de la viga hasta la impresora
  const viaje = paquetes(svg, svg.querySelector('.ruta-dato'), { n: 4, color: 'var(--ambar-500)', r: 2, periodo: 4.8 });
  ambiente(fig, viaje);
}

// ---------------------------------------------------------------- asistentes: el tablero de conmutación
function asistente(fig) {
  const svg = fig.querySelector('svg');
  const V = JSON.parse(svg.dataset.vivo);
  const iso = camara(V.P);
  const lectura = fig.querySelector('[data-lectura]');
  const [forro, alma] = svg.querySelectorAll('.cordon path');
  const clavija = svg.querySelector('.clavija');
  const renglones = svg.querySelector('[data-renglones]');
  const pilotos = [...svg.querySelectorAll('[data-piloto]')];
  const qs = V.preguntas;
  let desde = V.tomas[qs[0].j], hacia = desde, f = 1, meta = 0;
  // la clavija sale 9 hacia adelante, viaja y entra; el cordón cuelga entre el puerto y ella
  // la clavija sale, viaja con inercia (se pasa un poco y vuelve) y entra
  const conInercia = u => { const c = 1.7; return u >= 1 ? 1 : 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };
  const enCamino = u => {
    const s = conInercia(Math.min(1, u)), salir = Math.sin(Math.PI * Math.min(1, u)) * 9;
    return [desde[0] + (hacia[0] - desde[0]) * s, desde[1] + (hacia[1] - desde[1]) * s + 0.8 + salir, desde[2] + (hacia[2] - desde[2]) * s];
  };
  let vaiven = 0;
  function cordon(q) {
    const a = V.puerto, m = [(a[0] + q[0]) / 2 + vaiven * 3, (a[1] + q[1]) / 2 + 16 + vaiven * 2, Math.max(a[2] + 6, (a[2] + q[2]) / 2 - 12)];
    const pts = [];
    for (let i = 0; i <= 20; i++) {
      const t = i / 20, u = 1 - t;
      pts.push(iso([0, 1, 2].map(c => u * u * a[c] + 2 * u * t * m[c] + t * t * q[c])));
    }
    const d = 'M' + pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join('L');
    forro.setAttribute('d', d); alma.setAttribute('d', d);
    const [cx, cy] = iso(q);
    clavija.setAttribute('cx', cx.toFixed(1)); clavija.setAttribute('cy', cy.toFixed(1));
  }
  const ojos = V.tomas.map(t => iso(t));
  selector(fig, {
    n: qs.length,
    cada: 3.6,
    elegir: i => {
      const q = qs[i];
      desde = f >= 1 ? hacia : enCamino(f); hacia = V.tomas[q.j]; f = quieto.matches ? 1 : 0; meta = i;
      lectura.textContent = `${q.p} → ${q.e} · ${q.l}`;
      renglones.style.opacity = '0';
    },
    pintar: dt => {
      f = Math.min(1, f + dt / 1.3);
      cordon(f >= 1 ? hacia : enCamino(f));
      pilotos.forEach((p, j) => {
        const e = f >= 1 && j === qs[meta].j ? 'ok' : '';
        if ((p.dataset.estado || '') !== e) { if (e) p.dataset.estado = e; else delete p.dataset.estado; }
      });
      if (f >= 1) renglones.style.opacity = '';
      return f < 1;
    },
    desde: (x, y) => {
      const j = cerca2(ojos, x, y);
      return j < 0 ? -1 : qs.findIndex(q => q.j === j);
    },
  });
  // vida: el cordón se mece y la pantalla escribe
  escribir(svg);
  ambiente(fig, t => { vaiven = Math.sin(t * 1.3) * 0.8 + Math.sin(t * 0.47) * 0.5; cordon(f >= 1 ? hacia : enCamino(f)); });
}

// ---------------------------------------------------------------- cobertura: la maqueta de Colombia
function cobertura(fig) {
  const svg = fig.querySelector('svg');
  const V = JSON.parse(svg.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const base = lectura.textContent;
  const celdas = [];
  svg.querySelectorAll('[data-celda]').forEach(g => { celdas[+g.dataset.celda] = g; });
  const f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }), fn = new Intl.NumberFormat('es-CO');
  const coord = (v, p, q) => f2.format(Math.abs(v)) + ' ' + (v >= 0 ? p : q);
  const cerca = (lon, lat) => {
    let mejor = null, d = 0.6;
    V.ciudades.forEach(([n, x, y]) => { const q = Math.hypot(x - lon, y - lat); if (q < d) { d = q; mejor = n; } });
    return mejor;
  };
  // entrada: las columnas aparecen desde Bogotá hacia afuera (una vez), quietas con movimiento reducido
  const [bx, by] = [-74.08, 4.61];
  if (!quieto.matches) celdas.forEach((g, i) => { g.style.transitionDelay = `${(Math.hypot(V.celdas[i][0] - bx, V.celdas[i][1] - by) * 0.09).toFixed(2)}s`; });
  let sel = -1;
  const elegir = i => {
    if (i === sel) return;
    if (sel >= 0) celdas[sel].querySelector('.iso-solid').removeAttribute('data-lit');
    sel = i;
    if (i < 0) { lectura.textContent = base; return; }
    celdas[i].querySelector('.iso-solid').setAttribute('data-lit', '');
    const [lon, lat, n] = V.celdas[i], c = cerca(lon, lat);
    lectura.textContent = `${fn.format(n)} predios de la muestra · ${coord(lat, 'N', 'S')}, ${coord(lon, 'E', 'W')}${c ? ' · ' + c : ''}`;
  };
  const lienzo = fig.querySelector('.lienzo');
  let tour = !quieto.matches, k = 0, reloj = 0, espera = 0;
  const pasar = () => { if (tour) { elegir(V.orden[k % V.orden.length]); k++; } };
  enVista(lienzo, v => {
    if (!v) { clearInterval(reloj); reloj = 0; return; }
    svg.classList.add('armada');
    if (!reloj && tour) reloj = setInterval(pasar, 2600);
  });
  lienzo.addEventListener('pointermove', e => {
    const caja = lienzo.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    const x = vb.x + (e.clientX - caja.left) / caja.width * vb.width, y = vb.y + (e.clientY - caja.top) / caja.height * vb.height;
    let mejor = -1, d = 14;
    V.puntas.forEach(([px, py], i) => { const q = Math.hypot(px - x, py - y); if (q < d) { d = q; mejor = i; } });
    tour = false; clearInterval(reloj); reloj = 0; clearTimeout(espera);
    elegir(mejor);
    espera = setTimeout(() => { tour = !quieto.matches; if (!reloj && tour) reloj = setInterval(pasar, 2600); }, 3600);
  });
  lienzo.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault(); tour = false; clearInterval(reloj); reloj = 0;
    k = (k + d + V.orden.length) % V.orden.length; elegir(V.orden[k]);
  });
}


// ---------------------------------------------------------------- carga perezosa
const LEGADO = { prueba, revision, tablero, vigilancia, asistente, cobertura };
async function cargar(fig) {
  const lienzo = fig.querySelector('.lienzo');
  const r = await fetch(lienzo.dataset.src);
  if (!r.ok) return;
  lienzo.innerHTML = await r.text();
  const svg = lienzo.querySelector('svg');
  svg.setAttribute('aria-hidden', 'true');
  svg.removeAttribute('role');
  fig.classList.add('lista');
  const nombre = fig.dataset.figura;
  if (FIG[nombre]) { montar(fig, nombre, FIG[nombre]); return; }
  enVista(lienzo, v => fig.classList.toggle('en-vista', v));
  if (LEGADO[nombre]) LEGADO[nombre](fig);
}
const cerca = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  cerca.unobserve(e.target);
  cargar(e.target);
}), { rootMargin: '600px 0px' });
document.querySelectorAll('.fig-iso[data-figura]').forEach(f => cerca.observe(f));
