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
// las flechas; mientras sigue en vista, un ciclo cada ~15 s (vida). Entre ciclos no hay ningún
// cuadro: cero repintado en reposo. Con puntero grueso o pocos núcleos, 30 cuadros por segundo.
const quieto = matchMedia('(prefers-reduced-motion: reduce)');
const lento = matchMedia('(pointer: coarse)').matches || (navigator.hardwareConcurrency || 8) <= 4;
const REPOSO = 2600, MEZCLA = 280, AUTOS = 2, VIDA = 15000;

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
  // lo que ya dice el SVG (scale(0), opacity:0) cuenta como pintado: el primer cuadro solo toca lo
  // que cambia (si no, recalcula el estilo de toda la capa viva de una vez)
  const inicial = el => {
    if (el.__pinta || el.dataset.eje) return undefined;
    const st = el.getAttribute('style') || '';
    return { x: 0, y: 0, k: 0, s: /scale\(0\)/.test(st) ? 0 : 1, o: /opacity:\s*0(?![.\d])/.test(st) ? 0 : 1 };
  };
  const pinta = (el, c) => {
    if (!hechos.has(el)) { const i = inicial(el); if (i) hechos.set(el, i); }
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

// Vida: después de los dos ciclos de entrada, mientras la figura sigue en vista (y es la más visible),
// un ciclo cada ~15 s, contados desde que empezó el anterior. Entre ciclos no se pinta nada.
function vivir(F) {
  clearTimeout(F.espera);
  const dura = F.m.dura(F.turno);
  F.espera = setTimeout(() => {
    if (viva !== F || F.corre || quieto.matches) return;
    if (document.hidden || F.razon < 0.34) { vivir(F); return; }
    jugar(F, paso(F));
  }, Math.max(REPOSO, VIDA - dura));
}
function terminar(F) {
  F.corre = false;
  clearTimeout(F.espera);
  if (F !== viva || quieto.matches) return;
  if (F.autos < AUTOS) {
    F.espera = setTimeout(() => { if (viva === F && !F.corre && F.autos < AUTOS) { F.autos++; jugar(F, paso(F)); } }, REPOSO);
  } else vivir(F);
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
  if (!mejor || quieto.matches) return;
  if (mejor.autos < AUTOS) { mejor.autos++; jugar(mejor, mejor.autos === 1 ? 0 : paso(mejor)); } else vivir(mejor);
}
const umbrales = Array.from({ length: 21 }, (_, i) => i / 20);
const vista = new IntersectionObserver(es => {
  for (const e of es) { const F = FIGS.find(f => f.lienzo === e.target); if (F) F.razon = e.isIntersecting ? e.intersectionRatio : 0; }
  elegirViva();
}, { threshold: umbrales });

// ---------------------------------------------------------------- montar una figura
function montar(fig, nombre, crear, caja) {
  const lienzo = fig.querySelector('.lienzo');
  // la capa viva va en su propio <svg> encima de la imagen fija: un cambio en ella solo vuelve a
  // pintar sus piezas. Sin will-change: promoverla al empezar cada ciclo costaba 50 ms a CPU 4×.
  const vivo = caja.querySelector('svg');
  const fija = vivo;
  const V = JSON.parse(vivo.dataset.vivo);
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
      // el piloto se enciende de golpe, como una luz
      pilotos.forEach((el, j) => pon(el, { s: j === i && t >= LLEGA ? 1 : 0 }));
      // lo que muestra la pantalla del módulo al que llega el dato; las demás quedan como estaban
      const llego = (j, t0, dur, curva = entra) => (j !== i ? 1 : tramo(t, LLEGA + t0, dur, curva));
      barras.forEach((el, q) => pon(el, { k: llego(0, q * 60, 320) }));
      pon(marca, { s: llego(1, 0, 260) });
      pon(chat, { k: Math.floor(llego(2, 0, 680, lineal) * 18) / 18 });
      const m = V.modulos[i];
      if (t < 120) return V.reposo;
      // la lectura en palabras de quien decide; la puerta (REST o MCP) va en la pista, al pasar o enfocar
      return t < LLEGA ? { l: `datos → ${m.n}`, d: '' } : { l: `${m.n} · ${m.q}`, d: `entra por ${m.p}` };
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
      pon(lector, { s: t >= T1 && t < T3 ? 1 : 0 }); // la luz del lector, de golpe
      const alza = ALZA * (tramo(t, T1 + 100, 360, entra) - tramo(t, baja, 380, mueve));
      brazos.forEach(el => pon(el, { k: alza }));
      tapas.forEach((el, i) => pon(el, { o: i === k ? tramo(t, T2, 140, entra) : 0 }));
      // la respuesta: de la columna a la terminal
      const [rx, ry] = sobre(pts, 1 - tramo(t, T2 + 200, VUELTA, mueve));
      pon(resp, { x: rx, y: ry, s: tramo(t, T2 + 80, 180, entra) * (1 - tramo(t, T3, 180, sale)) });
      pon(lineas, { o: tramo(t, T3, 220, entra) });
      const d = V.turnos[k];
      if (t < 120) return { l: [d.p], d: '' };
      // la pregunta y la entidad que responde; el nombre de la herramienta, en la pista
      if (t < T2) return { l: `${d.p} → …`, d: '' };
      return { l: `${d.p} → ${d.e}`, d: t < T3 ? d.h : `${d.h} · ${d.l} · ${d.s}` };
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
  // las columnas altas crecen de verdad: cada cara se alarga en su marco y la tapa sube (sin escala
  // que las aplaste); a altura cero no se dibujan
  const crece = (el, c, antes) => {
    if (antes && antes.k === c.k) return;
    const q = Math.max(0, Math.min(1, c.k));
    if (!el.__partes) el.__partes = [...el.querySelectorAll('[data-m], [data-tapa]')].map(p => ({ p, m: p.dataset.m && p.dataset.m.split(' ').map(Number), h: +(p.dataset.tapa || 0) }));
    for (const { p, m, h } of el.__partes) p.style.transform = m ? `matrix(${m[0]},${m[1]},0,${q.toFixed(3)},${m[2]},${m[3]})` : `translate(0px,${((1 - q) * h).toFixed(2)}px)`;
    el.style.opacity = q <= 0.02 ? '0' : '';
  };
  cols.forEach((el, c) => { if (el && V.celdas[c][4]) el.__pinta = crece; });
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
        // las altas crecen, en escalones de 1/24: así cada cuadro cambia pocas piezas y repinta poco
        const t0 = ESPERA + V.celdas[c][3] * RETRASO;
        // las bajas están quietas desde el principio (casi todas van en la capa fija)
        const k = !entrando || !V.celdas[c][4] ? 1 : Math.round(resorte(t, t0, CRECE) * 24) / 24;
        pon(el, { k, o: k > 0.02 ? 1 : 0 }); // a altura cero no se dibuja
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
    if (t < APARECE) return V.bandeja; // la del ciclo anterior sigue en la bandeja hasta que sale la nueva
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
      // la ficha queda en la bandeja al final (se ve el expediente); al empezar el ciclo siguiente se
      // va con la escala y la nueva sale de la pila
      const z = t < APARECE ? -V.cae : t < fin ? 0 : -V.cae * tramo(t, fin, CAE, sale);
      const s = t < APARECE ? 1 - tramo(t, 0, 180, sale) : t < APARECE + 120 ? 0 : tramo(t, APARECE + 120, 160, entra);
      pon(ficha, { x: ex[0] * x + ez[0] * z, y: ex[1] * x + ez[1] * z, s });
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

// Fig. vigilancia: el carro va al buzón y lo lee; si algo cambió, la banderita se levanta y solo
// entonces el registro corre por la canaleta hasta la impresora, que saca su tique.
FIG.vigilancia = ({ V, pieza }) => {
  const n = V.carriles.length;
  const carro = pieza('carro'), registro = pieza('registro'), tique = pieza('tique'), impreso = pieza('impreso');
  const banderas = V.carriles.map((_, i) => pieza('bandera' + i)), encendidas = V.carriles.map((_, i) => pieza('banderaA' + i));
  const gira = (el, c, antes) => {
    if (antes && antes.k === c.k) return;
    const [u, v] = (el.__p ||= el.dataset.pivote.split(' ').map(Number));
    el.style.transform = c.k ? `translate(${u}px,${v}px) rotate(${c.k.toFixed(2)}deg) translate(${-u}px,${-v}px)` : '';
  };
  banderas.forEach(el => { el.__pinta = gira; });
  const VA = 650, LEE = 900, SUBE = 420, CORRE = 1380, VIAJA = 620, IMPRIME = CORRE + VIAJA, DURA = IMPRIME + 700;
  return {
    n,
    dura: () => DURA,
    cuadros: [[1, 0], [1, 400], [1, LEE], [1, LEE + 260], [1, CORRE + 300], [1, IMPRIME + 300], [1, DURA], [3, DURA]],
    pose(i, t, pon) {
      const prev = (i - 1 + n) % n, c = V.carriles[i];
      const x = V.x[prev] + (V.x[i] - V.x[prev]) * tramo(t, 0, VA, mueve);
      pon(carro, { x: V.ex[0] * x, y: V.ex[1] * x });
      banderas.forEach((el, j) => pon(el, { k: j === i ? -90 * resorte(t, LEE, SUBE) : 0 }));
      encendidas.forEach((el, j) => pon(el, { o: j === i && t >= LEE + SUBE * 0.5 ? 1 : 0 }));
      const f = tramo(t, CORRE, VIAJA, mueve), xr = V.x[i] + (V.imp - V.x[i]) * f;
      pon(registro, { x: V.ex[0] * xr, y: V.ex[1] * xr, s: tramo(t, CORRE - 120, 160, entra) * (1 - tramo(t, IMPRIME - 40, 160, sale)) });
      const sale_ = V.saca * resorte(t, IMPRIME, 520);
      pon(tique, { x: V.ez[0] * sale_, y: V.ez[1] * sale_ });
      pon(impreso, { s: tramo(t, IMPRIME, 160, entra) });
      if (t < VA) return { l: `${c.s} · ${c.e}`, d: '' };
      if (t < LEE + SUBE * 0.6) return { l: `leyendo ${c.s}…`, d: c.e };
      return { l: `${c.s} · ${c.ev}`, d: t < IMPRIME ? c.e : `${c.e} · registrado` };
    },
    desde: x => { let mejor = 0; V.cajas.forEach((cx, q) => { if (Math.abs(cx - x) < Math.abs(V.cajas[mejor] - x)) mejor = q; }); return mejor; },
  };
};

// Fig. asistente: la clavija sale de la boca anterior y entra en la de la entidad que publica el
// dato; su piloto se enciende y la pantalla escribe la respuesta.
FIG.asistente = ({ V, pieza }) => {
  const nb = V.bocas.length;
  const cordones = Array.from({ length: nb }, (_, j) => pieza('cordon' + j));
  const clavijas = Array.from({ length: nb }, (_, j) => pieza('clavija' + j));
  const pilotos = Array.from({ length: nb }, (_, j) => pieza('piloto' + j));
  const respuestas = V.preguntas.map((_, i) => pieza('respuesta' + i));
  const [sx, sy] = V.sale;
  const APARECE = 260, ENTRA = 460, CONECTA = 820, DURA = 1450;
  return {
    n: V.preguntas.length,
    dura: () => DURA,
    cuadros: [[0, 0], [0, 400], [0, 600], [0, CONECTA + 40], [0, DURA], [3, 150], [3, 600], [3, DURA]],
    pose(i, t, pon) {
      const q = V.preguntas[i];
      // la clavija anterior se corre hacia afuera y se va con la escala; la nueva aparece con la
      // escala y entra con resorte. El piloto se enciende de golpe, como una luz.
      clavijas.forEach((el, j) => {
        if (j !== q.j) { pon(el, { x: sx, y: sy, s: 0 }); pon(cordones[j], { o: 0 }); return; }
        const s = tramo(t, APARECE, 200, entra);
        const fuera = 1 - resorte(t, ENTRA, CONECTA - ENTRA);
        pon(el, { x: sx * fuera, y: sy * fuera, s });
        pon(cordones[j], { o: s > 0.5 ? 1 : 0 });
      });
      pilotos.forEach((el, j) => pon(el, { s: j === q.j && t >= CONECTA ? 1 : 0 }));
      respuestas.forEach((el, q) => pon(el, { o: q === i ? tramo(t, CONECTA + 120, 260, entra) : 0 }));
      return t < CONECTA ? { l: `${q.p} …`, d: '' } : { l: `${q.p} → ${q.e}`, d: q.l };
    },
    desde: (x, y) => {
      let mejor = -1, d = 40;
      V.bocas.forEach(([bx, by], j) => { const e = Math.hypot(bx - x, by - y); if (e < d) { d = e; mejor = j; } });
      return mejor < 0 ? -1 : V.preguntas.findIndex(q => q.j === mejor);
    },
  };
};

// ---------------------------------------------------------------- carga perezosa
// La capa fija llega como <img> (sin DOM: no cuesta estilo ni diseño) y la viva, en línea. Para que
// ninguna tarea se alargue al desplazarse, las figuras entran de a una por cuadro, cuando el hilo
// está libre (requestIdleCallback; si no lo hay, el cuadro siguiente).
const ocioso = window.requestIdleCallback ? f => requestIdleCallback(f, { timeout: 400 }) : f => requestAnimationFrame(() => setTimeout(f, 0));
let fila = Promise.resolve();
// un cuadro de por medio (requestAnimationFrame) y luego el hueco libre: entre dos entradas siempre
// hay un cálculo de estilo, así ninguno junta más de una parte
const turno = () => (fila = fila.then(() => new Promise(r => requestAnimationFrame(() => ocioso(r)))));
async function cargar(fig) {
  const lienzo = fig.querySelector('.lienzo');
  // la capa fija viene en trozos (una imagen cada uno: el navegador lee cada una en su tarea)
  const imgs = lienzo.dataset.src.split(',').map((src, i) => {
    const img = new Image();
    img.alt = ''; img.decoding = 'async'; img.className = i ? 'capa-fija encima' : 'capa-fija'; img.src = src;
    return img;
  });
  const [r] = await Promise.all([fetch(lienzo.dataset.viva), ...imgs.map(img => img.decode().catch(() => {}))]);
  if (!r.ok) return;
  // la capa viva se lee fuera del documento y entra por partes, de a unas 250 piezas por cuadro
  // libre: así ningún cálculo de estilo se alarga (la de cobertura tiene unas 2.000)
  const doc = new DOMParser().parseFromString(await r.text(), 'image/svg+xml');
  const fuente = doc.documentElement, grupo = fuente.querySelector('.capa-viva');
  await turno();
  const caja = document.createElement('div');
  caja.className = 'capa-viva';
  const svg = document.importNode(fuente, false);
  const destino = document.importNode(grupo, false);
  svg.append(destino);
  caja.append(svg);
  // las imágenes entran de a una por cuadro (pintar una figura en imagen también cuesta), y la viva
  // encima de todas
  lienzo.append(imgs[0], caja);
  for (const img of imgs.slice(1)) { await turno(); caja.before(img); }
  let lote = [], peso = 0;
  const pasar = async () => { if (!lote.length) return; const l = lote; lote = []; peso = 0; await turno(); destino.append(...l.map(n => document.importNode(n, true))); };
  for (const hijo of [...grupo.childNodes]) {
    lote.push(hijo);
    peso += 1 + (hijo.getElementsByTagName ? hijo.getElementsByTagName('*').length : 0);
    if (peso >= 200) await pasar();
  }
  await pasar();
  const nombre = fig.dataset.figura;
  if (FIG[nombre]) await new Promise(r => ocioso(() => { montar(fig, nombre, FIG[nombre], caja); r(); }));
  // montada: un atributo y no una clase («.lista» es la de las listas del sitio: la figura heredaba su
  // color y se recalculaba entera)
  fig.dataset.lista = '';
}
const cerca = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  cerca.unobserve(e.target);
  cargar(e.target);
}), { rootMargin: '600px 0px' });
document.querySelectorAll('.fig-iso[data-figura]').forEach(f => cerca.observe(f));
