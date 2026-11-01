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
// encima y solo se mueve con transform y opacity (a lo sumo 60 cuadros por segundo). Un planificador único deja viva una sola figura
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
// Cada pieza viva tiene canales numéricos: x, y (traslado en unidades del viewBox), o (opacidad),
// s (escala alrededor de su centro, data-c) y k (un parámetro propio: un ángulo, un avance).
// pinta(el, c) los escribe; por omisión, traslado, escala y opacidad. Solo se toca el DOM si el
// valor cambió. Una pieza de color que aparece o se va lo hace con la escala, no con la opacidad:
// un ámbar a medio fundir sobre gris se ve oliva.
const CERO = { x: 0, y: 0, o: 1, s: 1, k: 0 };
function pintaBase(el, c, antes) {
  if (!antes || antes.x !== c.x || antes.y !== c.y || antes.s !== c.s || antes.k !== c.k) {
    let t = c.x || c.y ? `translate(${c.x.toFixed(2)}px,${c.y.toFixed(2)}px)` : '';
    if (c.s !== 1) {
      const [cx, cy] = (el.__c ||= (el.dataset.c || '0 0').split(' ').map(Number));
      t += ` translate(${cx}px,${cy}px) scale(${Math.max(0.001, c.s).toFixed(3)}) translate(${-cx}px,${-cy}px)`;
    }
    // data-eje="y b": crece en v desde la base b (barras); "x a": en u desde a (un renglón que se escribe)
    if (el.dataset.eje) {
      const [eje, b] = el.dataset.eje.split(' '), q = Math.max(0.001, c.k).toFixed(3);
      t += eje === 'y' ? ` translate(0px,${b}px) scale(1,${q}) translate(0px,${-b}px)` : ` translate(${b}px,0px) scale(${q},1) translate(${-b}px,0px)`;
    }
    el.style.transform = t;
  }
  // a escala cero no se dibuja nada (el filo no escala y dejaría un punto)
  const o = c.s <= 0.002 ? 0 : c.o, oa = antes ? (antes.s <= 0.002 ? 0 : antes.o) : -1;
  if (o !== oa) el.style.opacity = o >= 0.999 ? '' : o <= 0.001 ? '0' : o.toFixed(3);
}

function motorDe(F) {
  const hechos = new Map(); // el -> canales pintados
  let desde = null, t0Mezcla = 0;
  const pinta = (el, c) => {
    const antes = hechos.get(el);
    if (antes && antes.x === c.x && antes.y === c.y && antes.o === c.o && antes.s === c.s && antes.k === c.k) return;
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
      pinta(el, a && m < 1 ? { x: a.x + (c.x - a.x) * e, y: a.y + (c.y - a.y) * e, o: a.o + (c.o - a.o) * e, s: a.s + (c.s - a.s) * e, k: a.k + (c.k - a.k) * e } : c);
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
// el turno que sigue (o el anterior): una figura puede tener un turno de entrada que no se repite
const paso = (F, d = 1) => (F.m.paso ? F.m.paso(F.turno, d) : (F.turno + d + F.m.n) % F.m.n);
let viva = null, cuadro = 0, ultimo = 0;

function bucle(ahora) {
  cuadro = 0;
  const F = viva;
  if (!F || !F.corre) return;
  // a lo sumo 60 cuadros por segundo (en pantallas de 120 o 165 Hz no hace falta más), 30 en equipos lentos
  if (ultimo && ahora - ultimo < (lento ? 30 : 15.5)) { cuadro = requestAnimationFrame(bucle); return; }
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
  clearTimeout(F.espera);
  if (F === viva && F.autos < AUTOS && !quieto.matches) {
    F.espera = setTimeout(() => { if (viva === F && !F.corre && F.autos < AUTOS) { F.autos++; jugar(F, paso(F)); } }, REPOSO);
  }
}
// cierra el ciclo en curso de una figura que deja de estar viva: salta a su resultado
function cerrar(F) {
  clearTimeout(F.espera);
  if (!F.corre) return;
  F.motor.poner(F.turno, F.m.dura(F.turno), Infinity);
  F.corre = false;
}
function jugar(F, i) {
  if (quieto.matches) { fijo(F, i); return; }
  if (viva && viva !== F) cerrar(viva);
  viva = F;
  clearTimeout(F.espera);
  const ahora = performance.now();
  F.motor.mezclar(ahora);
  F.turno = i; F.inicio = ahora; F.corre = true;
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
  if (mejor && mejor.autos < AUTOS && !quieto.matches) { mejor.autos++; jugar(mejor, mejor.autos === 1 ? 0 : paso(mejor)); }
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
  // la capa viva va en su propio <svg> encima: un cambio en ella solo vuelve a pintar sus piezas.
  // Sin will-change: promoverla a una capa al empezar cada ciclo costaba 50 ms a CPU 4× (medido).
  const caja = document.createElement('div');
  caja.className = 'capa-viva';
  caja.append(vivo);
  lienzo.append(caja);
  const V = JSON.parse(fija.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const pieza = n => vivo.querySelector(`[data-v="${n}"]`);
  const F = { fig, nombre, lienzo, vivo: caja, V, razon: 0, autos: 0, turno: 0, corre: false, inicio: 0, espera: 0 };
  let dicho = '', dichoD = null;
  const pista = fig.querySelector('.pista'), pistaBase = pista ? pista.textContent : '';
  F.decir = txt => {
    // {l, d}: la lectura en una línea y el detalle, que va en la pista (al pasar o enfocar)
    if (txt && !Array.isArray(txt) && typeof txt === 'object') {
      if (pista && txt.d !== dichoD) { dichoD = txt.d; pista.textContent = txt.d ? `${txt.d} · ${pistaBase}` : pistaBase; }
      txt = txt.l;
    }
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
  lienzo.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse' && !F.m.desde && !F.corre) tomar(paso(F)); });
  lienzo.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') return;
    const i = F.m.desde ? F.m.desde(...enCaja(e)) : -1;
    tomar(i >= 0 ? i : paso(F));
  });
  lienzo.addEventListener('focus', () => { if (!F.corre) tomar(F.turno); });
  lienzo.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    tomar(paso(F, d));
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
  const barras = [0, 1, 2, 3, 4, 5].map(q => pieza('barra' + q)), marca = pieza('marca'), chat = pieza('chat');
  const APARECE = 220, VIAJA = 640, LLEGA = APARECE + VIAJA, DURA = LLEGA + 760;
  const lineal = x => x;
  return {
    n: V.modulos.length,
    dura: () => DURA,
    cuadros: [[0, 0], [0, 240], [0, 520], [0, LLEGA + 40], [0, LLEGA + 260], [0, DURA], [1, LLEGA + 120], [2, LLEGA + 380]],
    pose(i, t, pon) {
      datos.forEach((el, j) => {
        const [vx, vy] = V.viajes[j];
        if (j !== i) { pon(el, { x: vx, y: vy, s: 0 }); return; }
        const f = tramo(t, APARECE, VIAJA, mueve);
        pon(el, { x: vx * f, y: vy * f, s: tramo(t, 0, APARECE, entra) });
      });
      pilotos.forEach((el, j) => pon(el, { o: j === i ? tramo(t, LLEGA, 140, entra) : 0 }));
      // lo que muestra la pantalla del módulo al que llega el dato; las demás quedan como estaban
      const llego = (j, t0, dur, curva = entra) => (j !== i ? 1 : tramo(t, LLEGA + t0, dur, curva));
      barras.forEach((el, q) => pon(el, { k: llego(0, q * 60, 320) }));
      pon(marca, { s: llego(1, 0, 260) });
      pon(chat, { k: Math.floor(llego(2, 0, 680, lineal) * 18) / 18 });
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
  const lector = pieza('lector'), brazos = ['brazo', 'brazo1', 'brazo2', 'brazo3', 'brazo4'].map(pieza);
  const tapas = V.turnos.map((_, i) => pieza('tapa' + i));
  const [u0, v0] = V.eje;
  const gira = (el, c, antes) => { if (!antes || antes.k !== c.k) el.style.transform = c.k ? `translate(${u0}px,${v0}px) rotate(${c.k.toFixed(2)}deg) translate(${-u0}px,${-v0}px)` : ''; };
  brazos.forEach(el => { el.__pinta = gira; });
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
    cuadros: [[0, 0], [0, 520], [0, T[0].T1 + 260], [0, T[0].T1 + 640], [0, T[0].T2 + 80], [0, T[0].T2 + 560], [2, T[2].T1 + 900], [2, T[2].dura]],
    pose(k, t, pon) {
      const { s1, T1, T2, T3, VUELTA, baja } = T[k];
      const pts = V.recorridos[k];
      // la pregunta: aparece en la terminal, va al lector, espera la barrera, sigue a la columna
      const f = t < T1 ? s1 * tramo(t, 200, T1 - 200, mueve) : s1 + (1 - s1) * tramo(t, T1 + 320, T2 - T1 - 320, mueve);
      const [px, py] = sobre(pts, f);
      pon(preg, { x: px, y: py, s: tramo(t, 0, 200, entra) * (1 - tramo(t, T2, 180, sale)) });
      pon(lector, { o: tramo(t, T1, 120, entra) * (1 - tramo(t, T3, 200, sale)) });
      const alza = ALZA * (tramo(t, T1 + 100, 360, entra) - tramo(t, baja, 380, mueve));
      brazos.forEach(el => pon(el, { k: alza }));
      tapas.forEach((el, i) => pon(el, { o: i === k ? tramo(t, T2, 140, entra) : 0 }));
      // la respuesta: de la columna a la terminal
      const [rx, ry] = sobre(pts, 1 - tramo(t, T2 + 200, VUELTA, mueve));
      pon(resp, { x: rx, y: ry, s: tramo(t, T2 + 80, 180, entra) * (1 - tramo(t, T3, 180, sale)) });
      pon(lineas, { o: tramo(t, T3, 220, entra) });
      const d = V.turnos[k];
      if (t < 120) return { l: [d.p], d: '' };
      if (t < T2) return { l: [`${d.p} → `, { c: d.h }], d: '' };
      return { l: [`${d.p} → `, { c: d.h }, ` → ${d.e}`], d: t < T3 ? '' : `${d.l} · ${d.s}` };
    },
    desde: x => { let mejor = 0; V.franjas.forEach((fx, i) => { if (Math.abs(fx - x) < Math.abs(V.franjas[mejor] - x)) mejor = i; }); return mejor; },
  };
};

// Fig. prueba: la ficha que se lee sube y su pestaña se enciende; con la huella, el sello se
// entinta en el tampón y la ficha queda sellada.
FIG.prueba = ({ V, pieza }) => {
  const n = V.lecturas.length;
  const fichas = Array.from({ length: n }, (_, i) => pieza('ficha' + i));
  const tabs = Array.from({ length: n }, (_, i) => pieza('pestana' + i));
  const sello = pieza('sello'), sellador = pieza('sellador');
  const SUBE0 = 120, SUBE = 560, LEE = 400, ALZA = 760, BAJA = 1020, SELLA = 1220;
  const huella = n - 1;
  // la lista de al lado marca la misma capa que la ficha que se lee
  const notas = [...document.querySelectorAll('.notas-p [data-capa]')];
  let marcada = -2;
  const marcar = i => { if (i !== marcada) { marcada = i; notas.forEach(nt => nt.classList.toggle('vivo', +nt.dataset.capa === i)); } };
  return {
    n,
    dura: i => (i === huella ? SELLA + 420 : SUBE0 + SUBE + 260),
    cuadros: [[0, 0], [0, 260], [0, 520], [0, 940], [2, 940], [huella, 600], [huella, 1100], [huella, SELLA + 420]],
    pose(i, t, pon) {
      fichas.forEach((el, j) => {
        const f = j === i ? resorte(t, SUBE0, SUBE) : 0;
        pon(el, { x: V.sube[0] * f, y: V.sube[1] * f });
      });
      tabs.forEach((el, j) => pon(el, { o: j === i && t >= LEE ? 1 : 0 }));
      // el sello: sube, baja al tampón (se entinta) y la huella queda sellada
      const z = i === huella ? tramo(t, ALZA, 260, entra) - tramo(t, BAJA, 200, sale) : 0;
      pon(sellador, { x: V.alza[0] * z, y: V.alza[1] * z });
      pon(sello, { s: i === huella ? tramo(t, SELLA, 200, entra) : 0 });
      marcar(t < LEE ? -1 : i);
      if (t < LEE) return i === 0 && t < 120 ? V.lecturas[0] : `${V.lecturas[i].split(' · ')[0]} · …`;
      return i === huella && t >= SELLA ? `${V.lecturas[i]} · sellada` : V.lecturas[i];
    },
    desde: (x, y) => {
      let mejor = -1, d = 70;
      V.pestanas.forEach(([px, py], i) => { const q = Math.hypot(px - x, (py - y) * 0.6); if (q < d) { d = q; mejor = i; } });
      return mejor;
    },
  };
};

// Fig. cobertura: al entrar, las columnas crecen desde el piso (de Bogotá hacia afuera) y caen los
// alfileres; después, la columna que se mira se enciende y la lectura da su conteo y su lugar.
FIG.cobertura = ({ V, pieza }) => {
  const cols = V.celdas.map((_, i) => pieza('c' + i));
  const luces = V.candidatas.map(i => pieza('luz' + i));
  const pines = V.ciudades.map((_, j) => pieza('pin' + j));
  const n = 1 + V.candidatas.length;
  const ESPERA = 160, RETRASO = 130, CRECE = 420;
  const fin = ESPERA + Math.max(...V.celdas.map(c => c[3])) * RETRASO + CRECE * 0.8;
  const PINES = fin, LUZ0 = PINES + V.ciudades.length * 60 + 300;
  const f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }), fn = new Intl.NumberFormat('es-CO');
  const coord = (v, p, q) => f2.format(Math.abs(v)) + ' ' + (v >= 0 ? p : q);
  const lugar = i => {
    const [lon, lat, c] = V.celdas[i];
    let ciudad = null, d = 0.6;
    V.ciudades.forEach(([nom, x, y]) => { const q = Math.hypot(x - lon, y - lat); if (q < d) { d = q; ciudad = nom; } });
    return `${fn.format(c)} predios de la muestra · ${coord(lat, 'N', 'S')}, ${coord(lon, 'E', 'W')}${ciudad ? ' · ' + ciudad : ''}`;
  };
  const base = `${fn.format(V.total)} predios de la muestra (3 %) en ${fn.format(V.celdas.length)} celdas`;
  return {
    n,
    dura: i => (i === 0 ? LUZ0 + 400 : 520),
    paso: (i, d) => { const j = i + d; return j < 1 ? n - 1 : j > n - 1 ? 1 : j; },
    cuadros: [[0, 0], [0, 300], [0, 600], [0, 900], [0, PINES + 200], [0, LUZ0 + 400], [2, 520], [4, 520]],
    pose(i, t, pon) {
      const entrando = i === 0;
      cols.forEach((el, c) => {
        // las columnas bajas (la mayoría) aparecen de una vez con su anillo; las altas crecen, en
        // escalones de 1/24: así cada cuadro cambia pocas piezas y repinta poco
        const t0 = ESPERA + V.celdas[c][3] * RETRASO;
        const k = !entrando ? 1 : V.celdas[c][4] ? Math.round(resorte(t, t0, CRECE) * 24) / 24 : t >= t0 + CRECE * 0.3 ? 1 : 0;
        pon(el, { k, o: k > 0.02 ? 1 : 0 }); // aplastada no se dibuja (el filo no escala)
      });
      pines.forEach((el, j) => {
        const u = entrando ? tramo(t, PINES + j * 60, 280, entra) : 1;
        pon(el, { y: V.sube * (1 - u), o: u });
      });
      const cual = V.candidatas[entrando ? 0 : i - 1], desde = entrando ? LUZ0 : 120;
      luces.forEach((el, q) => pon(el, { o: V.candidatas[q] === cual && t >= desde ? 1 : 0 }));
      return t >= desde ? lugar(cual) : base;
    },
    desde: (x, y) => {
      let mejor = -1, d = 30;
      V.puntas.forEach(([px, py], q) => { const e = Math.hypot(px - x, py - y); if (e < d) { d = e; mejor = q; } });
      return mejor < 0 ? -1 : mejor + 1;
    },
  };
};

// Fig. revision: la ficha sale de la pila, para bajo cada estación (la cinta avanza solo con ella),
// cada palpador baja y su piloto marca teal o ámbar (con su banderita); al final cae al expediente.
FIG.revision = ({ V, pieza }) => {
  const ficha = pieza('ficha'), cinta = pieza('cinta');
  const palp = V.est.map((_, j) => pieza('palpador' + j));
  const ok = V.est.map((_, j) => pieza('ok' + j)), rev = V.est.map((_, j) => pieza('rev' + j)), ban = V.est.map((_, j) => pieza('bandera' + j));
  const [ex, ez] = [V.ex, V.ez];
  const APARECE = 300, PRIMERO = 520, ENTRE = 420, PARA = 340, BAJA = 130, ALFINAL = 420, CAE = 360;
  // tiempos de llegada a cada estación y del final
  const llega = V.est.map((_, k) => APARECE + PRIMERO + k * (PARA + ENTRE));
  const sale3 = llega[3] + PARA, fin = sale3 + ALFINAL, cayo = fin + CAE, DURA = cayo + 380;
  const xEn = t => {
    if (t < APARECE) return 0;
    if (t < llega[0]) return V.est[0] * tramo(t, APARECE, PRIMERO, mueve);
    for (let k = 0; k < 4; k++) {
      if (t < llega[k] + PARA) return V.est[k];
      if (k < 3 && t < llega[k + 1]) return V.est[k] + (V.est[k + 1] - V.est[k]) * tramo(t, llega[k] + PARA, ENTRE, mueve);
    }
    if (t < fin) return V.est[3] + (V.fin - V.est[3]) * tramo(t, sale3, ALFINAL, mueve);
    return V.fin + (V.bandeja - V.fin) * tramo(t, fin, CAE, entra);
  };
  return {
    n: V.tipos.length,
    dura: () => DURA,
    cuadros: [[0, 0], [0, 700], [0, llega[0] + 140], [0, llega[1] + 160], [0, llega[2] + 300], [0, fin + 200], [0, DURA], [2, DURA]],
    pose(i, t, pon) {
      const tipo = V.tipos[i];
      const x = xEn(t);
      const z = t < fin ? 0 : -V.cae * tramo(t, fin, CAE, sale) ** 1;
      pon(ficha, { x: ex[0] * x + ez[0] * z, y: ex[1] * x + ez[1] * z, s: t < APARECE ? 0 : 1 - tramo(t, cayo + 120, 200, sale) });
      // la cinta lleva a la ficha: sus travesaños avanzan lo mismo (y se quedan quietos en las paradas)
      const xc = Math.min(x, V.fin) % V.paso;
      pon(cinta, { x: ex[0] * xc, y: ex[1] * xc });
      let lectura = { l: `${tipo.t} · ${tipo.c} · ${tipo.f.length} fuentes`, d: '' };
      V.est.forEach((_, k) => {
        const u = t - llega[k];
        const b = u < 0 || u > PARA ? 0 : u < BAJA ? tramo(u, 0, BAJA, entra) : 1 - tramo(u, PARA - BAJA, BAJA, sale);
        pon(palp[k], { x: -ez[0] * V.baja * b, y: -ez[1] * V.baja * b });
        const visto = u >= BAJA, malo = tipo.h === k;
        pon(ok[k], { s: visto && !malo ? 1 : 0 });
        pon(rev[k], { s: visto && malo ? 1 : 0 });
        pon(ban[k], { s: malo ? tramo(u, BAJA, 240, entra) : 0 });
        if (visto) lectura = { l: `${tipo.t} · ${tipo.f[k][0]}: ${malo ? 'revisar' : 'sin hallazgos'}`, d: tipo.f[k][1] };
      });
      if (t >= cayo) lectura = { l: `${tipo.t} · expediente: ${tipo.h == null ? 'sin hallazgos' : '1 caso para revisar'}`, d: `${tipo.c} · ${tipo.f.length} fuentes` };
      return lectura;
    },
  };
};

// Fig. tablero: el pórtico vuelve al principio con seguimiento, la aguja del reloj elegido barre
// hasta su lectura y oscila solo al asentarse, y la pluma dibuja la serie de ese indicador.
FIG.tablero = ({ V, pieza }) => {
  const n = V.ind.length;
  const agujas = V.ind.map((_, i) => pieza('aguja' + i)), ambar = V.ind.map((_, i) => pieza('ambar' + i));
  const tramos = V.ind.map((_, i) => Array.from({ length: V.tramos }, (_, j) => pieza(`s${i}_${j}`)));
  const portico = pieza('portico'), carro = pieza('carro');
  const gira = (el, c, antes) => {
    if (antes && antes.k === c.k && antes.o === c.o) return;
    const [cx, cy] = (el.__cc ||= el.dataset.centro.split(' ').map(Number));
    el.style.transform = `translate(${cx}px,${cy}px) rotate(${c.k.toFixed(2)}deg) translate(${-cx}px,${-cy}px)`;
    el.style.opacity = c.o >= 0.999 ? '' : '0';
  };
  [...agujas, ...ambar].forEach(el => { el.__pinta = gira; });
  const angulo = v => V.desde + V.arco * v;
  const VUELVE = 650, DIBUJA0 = 720, DIBUJA = 1600, LEE = 950, DURA = DIBUJA0 + DIBUJA + 250;
  const plotter = bezier(0.3, 0, 0.7, 1);
  const enSerie = (i, f) => { const s = V.series[i], u = Math.max(0, Math.min(1, f)) * (s.length - 1), j = Math.min(s.length - 2, Math.floor(u)); return s[j] + (s[j + 1] - s[j]) * (u - j); };
  return {
    n,
    dura: () => DURA,
    cuadros: [[0, 0], [0, 300], [0, 650], [0, 900], [0, 1300], [0, 1900], [0, DURA], [3, DURA]],
    pose(i, t, pon) {
      const f = tramo(t, DIBUJA0, DIBUJA, plotter);
      const dx = t < DIBUJA0 ? V.largo * (1 - resorte(t, 0, VUELVE)) : V.largo * f;
      pon(portico, { x: V.ex[0] * dx, y: V.ex[1] * dx });
      const dy = enSerie(i, t < DIBUJA0 ? 0 : f);
      pon(carro, { x: V.ey[0] * dy, y: V.ey[1] * dy });
      tramos.forEach((ts, q) => ts.forEach((el, j) => pon(el, { o: q === i && t >= DIBUJA0 && f >= (j + 1) / V.tramos - 1e-6 ? 1 : 0 })));
      agujas.forEach((el, q) => {
        const k = q === i ? angulo(V.valores[q] * asienta(t, 150, 1100)) : angulo(V.valores[q]);
        pon(el, { k, o: q === i ? 0 : 1 });
        pon(ambar[q], { k, o: q === i ? 1 : 0 });
      });
      const d = V.ind[i];
      return t < LEE ? { l: `${d.t} · ${d.e}`, d: d.m } : { l: `${d.t} · ${d.e} · tu municipio frente a sus comparables`, d: d.m };
    },
    desde: (x, y) => {
      let mejor = -1, d = 60;
      V.centros.forEach(([px, py], q) => { const e = Math.hypot(px - x, (py - y) * 0.7); if (e < d) { d = e; mejor = q; } });
      return mejor;
    },
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

// La cámara del kit (iso-kit.mjs, iso), para lo que se rehace en cada cuadro.
const camara = P => {
  const R = Math.PI / 180, K = P.scale * Math.sqrt(1.6);
  const sA = Math.sin(P.azimuth * R), cA = Math.cos(P.azimuth * R), sE = Math.sin(P.elevation * R), cE = Math.cos(P.elevation * R);
  return ([x, y, z]) => [P.origin[0] + (x * sA - y * cA) * K, P.origin[1] + ((x * cA + y * sA) * sE - z * cE) * K];
};

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

// ---------------------------------------------------------------- carga perezosa
const LEGADO = { vigilancia, asistente };
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
