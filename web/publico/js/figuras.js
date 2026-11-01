// Las figuras isométricas del sitio (dibujadas con el kit de Anatomy en web/figuras): las trae
// cuando se acercan a la vista y les da movimiento. Con movimiento reducido quedan armadas y quietas.
// Movimiento con tiempo y seguimiento exponencial; un recorrido en reposo cuando nadie toca; el
// puntero y las flechas eligen; fuera de la vista no corre nada.
const quieto = matchMedia('(prefers-reduced-motion: reduce)');
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

// ---------------------------------------------------------------- Fig. 1: el bastidor
function capas(fig) {
  const placa = fig.querySelector('.lienzo');
  const svg = fig.querySelector('svg');
  const vivo = JSON.parse(svg.dataset.vivo);
  const lectura = fig.querySelector('[data-lectura]');
  const modulos = [...svg.querySelectorAll('[data-modulo]')];
  const cables = [...svg.querySelectorAll('[data-cable]')];
  const grupoCables = svg.querySelector('.cables');
  let actual = -1, tour = !quieto.matches, reloj = 0, ultimo = 0, cuadro = 0, visible = false, armado = false, espera = 0;

  function elegir(i) {
    if (i === actual) return;
    actual = i;
    modulos.forEach((m, j) => {
      const s = m.querySelector('[data-frente] > .iso-solid');
      if (j === i) s.setAttribute('data-lit', ''); else s.removeAttribute('data-lit');
    });
    cables.forEach(c => { if (+c.dataset.cable === i) c.setAttribute('data-on', ''); else c.removeAttribute('data-on'); });
    lectura.textContent = vivo.lecturas[i];
  }

  // Entrada: los módulos asoman por el frente y entran uno tras otro; luego se enchufan los cables.
  function armar() {
    if (armado) return;
    armado = true;
    if (quieto.matches) { elegir(0); return; }
    const [dx, dy] = vivo.entra;
    modulos.forEach(m => { m.style.transition = 'none'; m.style.transform = `translate(${dx}px, ${dy}px)`; });
    grupoCables.style.opacity = '0';
    svg.getBoundingClientRect();
    modulos.forEach((m, j) => {
      m.style.transition = '';
      m.style.transitionDelay = `${j * 0.22}s`;
      m.style.transform = '';
    });
    setTimeout(() => { grupoCables.style.opacity = ''; elegir(0); correr(); }, modulos.length * 220 + 700);
  }

  function paso(ahora) {
    const dt = ultimo ? Math.min((ahora - ultimo) / 1000, 1 / 20) : 1 / 60;
    ultimo = ahora;
    if (tour) {
      reloj += dt;
      elegir(Math.floor(reloj / 2.8) % modulos.length);
    }
    cuadro = visible && tour ? requestAnimationFrame(paso) : 0;
  }
  const correr = () => { if (!cuadro && visible && tour && armado) { ultimo = 0; cuadro = requestAnimationFrame(paso); } };
  const tomar = i => {
    tour = false; elegir(i);
    clearTimeout(espera);
    espera = setTimeout(() => { tour = !quieto.matches; reloj = actual * 2.8; correr(); }, 3600);
  };

  placa.addEventListener('pointermove', e => {
    const caja = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    const y = vb.y + (e.clientY - caja.top) / caja.height * vb.height;
    const i = vivo.franjas.findIndex(([a, b]) => y >= a - 4 && y <= b + 4);
    if (i >= 0 && armado) tomar(i);
  });
  placa.addEventListener('keydown', e => {
    const d = e.key === 'ArrowUp' || e.key === 'ArrowRight' ? 1 : e.key === 'ArrowDown' || e.key === 'ArrowLeft' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    tomar((Math.max(actual, 0) + d + modulos.length) % modulos.length);
  });
  enVista(placa, v => { visible = v; if (v) { armar(); correr(); } });
  // vida: el dato sube por los tres cables en el color de su módulo; la pantalla de agentes escribe
  escribir(svg);
  const COLORES = ['var(--teal-400)', 'var(--fondo)', 'var(--ambar-500)'];
  const vidas = cables.map((c, j) => paquetes(svg, c.querySelector('.cable-alma'), { n: 2, color: COLORES[j], r: 2, periodo: 2.2 + j * 0.5, desde: 1, al: 0, desfase: j * 0.3 }));
  ambiente(fig, t => vidas.forEach(v => v(t)));
}

// ---------------------------------------------------------------- Fig. 2: la ruta de una pregunta
function ruta(fig) {
  const placa = fig.querySelector('.lienzo');
  const svg = fig.querySelector('svg');
  const vivo = JSON.parse(svg.dataset.vivo);
  const P = vivo.P;
  const lectura = fig.querySelector('[data-lectura]');
  const punto = svg.querySelector('[data-pregunta-punto]');
  const trazas = [...svg.querySelectorAll('[data-traza]')];
  const columnas = [...svg.querySelectorAll('[data-columna]')];
  const respuestas = [...svg.querySelectorAll('[data-respuesta]')];
  const piloto = svg.querySelector('[data-piloto]');
  const brazo = svg.querySelector('[data-brazo]');
  const n = vivo.turnos.length;

  // La cámara del kit (iso-kit.mjs, iso) y el brazo como en construir.mjs (brazoSvg).
  const R = Math.PI / 180, K = P.scale * Math.sqrt(1.6);
  const sA = Math.sin(P.azimuth * R), cA = Math.cos(P.azimuth * R), sE = Math.sin(P.elevation * R), cE = Math.cos(P.elevation * R);
  const iso = ([x, y, z]) => [P.origin[0] + (x * sA - y * cA) * K, P.origin[1] + ((x * cA + y * sA) * sE - z * cE) * K];
  const casco = pts => {
    const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cruz = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const bajo = [], alto = [];
    for (const q of p) { while (bajo.length >= 2 && cruz(bajo[bajo.length - 2], bajo[bajo.length - 1], q) <= 0) bajo.pop(); bajo.push(q); }
    for (const q of p.reverse()) { while (alto.length >= 2 && cruz(alto[alto.length - 2], alto[alto.length - 1], q) <= 0) alto.pop(); alto.push(q); }
    return bajo.slice(0, -1).concat(alto.slice(0, -1));
  };
  const camino = (pts, cerrado) => 'M' + pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join('L') + (cerrado ? 'Z' : '');
  const [prisma, banda1, banda2, banda3, arista] = brazo.querySelectorAll('path');
  const bandas = [banda1, banda2, banda3];
  function brazoA(grados) {
    const { eje, largo, ancho, grueso } = vivo.brazo;
    const t = grados * R, dir = [0, Math.cos(t), Math.sin(t)], nor = [0, -Math.sin(t), Math.cos(t)];
    const pt = (s, a, g) => [eje[0] + a, eje[1] + dir[1] * s + nor[1] * g, eje[2] + dir[2] * s + nor[2] * g];
    const caja = (s0, s1) => {
      const e = [];
      for (const s of [s0, s1]) for (const a of [-ancho / 2, ancho / 2]) for (const g of [-grueso / 2, grueso / 2]) e.push(iso(pt(s, a, g)));
      return camino(casco(e), true);
    };
    prisma.setAttribute('d', caja(0, largo));
    vivo.brazo.bandas.forEach(([a, b], j) => bandas[j].setAttribute('d', caja(a, b)));
    arista.setAttribute('d', camino([pt(0, -ancho / 2, grueso / 2), pt(largo, -ancho / 2, grueso / 2), pt(largo, ancho / 2, grueso / 2)].map(iso)));
  }

  // Posición a lo largo de un recorrido (en pantalla), de 0 a 1.
  const largos = vivo.recorridos.map(pts => {
    const tramos = [];
    let total = 0;
    for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); tramos.push(l); total += l; }
    return { tramos, total };
  });
  function sobre(k, f) {
    const pts = vivo.recorridos[k], { tramos, total } = largos[k];
    let d = Math.max(0, Math.min(1, f)) * total;
    for (let i = 0; i < tramos.length; i++) {
      if (d <= tramos[i] || i === tramos.length - 1) {
        const u = tramos[i] ? Math.min(1, d / tramos[i]) : 0;
        return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u];
      }
      d -= tramos[i];
    }
    return pts[pts.length - 1];
  }
  // Fracción del recorrido donde está la barrera (el brazo cruza la regla en x = 89).
  const enBarrera = vivo.recorridos.map((pts, k) => {
    const [bx] = iso([vivo.brazo.eje[0], 1, 0.6]);
    let mejor = 0, dist = Infinity;
    for (let f = 0; f <= 1; f += 0.005) { const d = Math.abs(sobre(k, f)[0] - bx); if (d < dist) { dist = d; mejor = f; } }
    return mejor;
  });

  // Guion de un turno (segundos): ida hasta la barrera, se levanta, sigue a la columna, la
  // columna se enciende, vuelve, la respuesta aparece en la pantalla, baja el brazo.
  const T = { ida: 0.5, barrera: 1.5, alza: 2.1, llega: 3.2, vuelta: 3.6, regreso: 5.0, baja: 5.6, fin: 7.0 };
  const suave = x => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
  let turno = 0, t = 0, angulo = 0, ultimo = 0, cuadro = 0, visible = false, tour = !quieto.matches, espera = 0;

  function marcar(k) {
    const d = vivo.turnos[k];
    lectura.innerHTML = '';
    const c = document.createElement('code'); c.textContent = d.h;
    lectura.append(`${d.p} → `, c, ` → ${d.e}`);
    columnas.forEach(col => col.querySelector('.iso-solid').toggleAttribute('data-lit', +col.dataset.columna === k && t >= T.llega));
  }
  function pintar() {
    const k = turno;
    let f = 0, va = false;
    if (t < T.ida) f = 0;
    else if (t < T.barrera) { f = enBarrera[k] * 0.92 * suave((t - T.ida) / (T.barrera - T.ida)); va = true; }
    else if (t < T.alza) { f = enBarrera[k] * 0.92; va = true; }
    else if (t < T.llega) { f = enBarrera[k] * 0.92 + (1 - enBarrera[k] * 0.92) * suave((t - T.alza) / (T.llega - T.alza)); va = true; }
    else if (t < T.vuelta) f = 1;
    else if (t < T.regreso) { f = 1 - suave((t - T.vuelta) / (T.regreso - T.vuelta)); va = true; }
    const [x, y] = sobre(k, f);
    punto.setAttribute('cx', x.toFixed(1)); punto.setAttribute('cy', y.toFixed(1));
    punto.toggleAttribute('data-on', va || (t >= T.llega && t < T.vuelta));
    trazas.forEach((tr, j) => {
      tr.toggleAttribute('data-on', false);
      tr.style.strokeDashoffset = j === k ? String(100 - 100 * (t < T.llega ? f : t < T.baja ? 1 : 1 - suave((t - T.baja) / (T.fin - T.baja)))) : '100';
    });
    respuestas.forEach((r, j) => r.toggleAttribute('data-on', j === k && t >= T.regreso));
    piloto.toggleAttribute('data-on', t >= T.ida + 0.5 && t < T.baja);
    columnas.forEach(col => col.querySelector('.iso-solid').toggleAttribute('data-lit', +col.dataset.columna === k && t >= T.llega - 0.1));
  }
  function paso(ahora) {
    const dt = ultimo ? Math.min((ahora - ultimo) / 1000, 1 / 20) : 1 / 60;
    ultimo = ahora;
    t += dt;
    if (t >= T.fin) {
      if (tour) { turno = (turno + 1) % n; t = 0; marcar(turno); }
      else t = T.fin;
    }
    const meta = t >= T.barrera && t < T.baja ? 84 : 0;
    angulo = sigue(angulo, meta, dt, 0.22);
    if (Math.abs(meta - angulo) < 0.05) angulo = meta;
    brazoA(angulo);
    pintar();
    const quieta = !tour && t >= T.fin && angulo === 0;
    cuadro = visible && !quieta ? requestAnimationFrame(paso) : 0;
  }
  const correr = () => { if (!cuadro && visible) { ultimo = 0; cuadro = requestAnimationFrame(paso); } };

  // Con movimiento reducido: el primer turno, completo y quieto (la respuesta ya llegó).
  function fijo(k) {
    turno = k; t = T.vuelta; angulo = 84;
    marcar(k); brazoA(84); pintar();
    trazas.forEach((tr, j) => { tr.style.strokeDashoffset = j === k ? '0' : '100'; });
    respuestas.forEach((r, j) => r.toggleAttribute('data-on', j === k));
    punto.removeAttribute('data-on');
  }
  const tomar = k => {
    if (quieto.matches) { fijo(k); return; }
    tour = false; turno = k; t = 0; marcar(k); correr();
    clearTimeout(espera);
    espera = setTimeout(() => { tour = true; correr(); }, 9000);
  };
  placa.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    tomar((turno + d + n) % n);
  });
  placa.addEventListener('pointermove', e => {
    if (quieto.matches) return;
    const caja = placa.getBoundingClientRect();
    const k = Math.min(n - 1, Math.floor((e.clientX - caja.left) / caja.width * n));
    if (k !== turno) tomar(k);
  });
  if (quieto.matches) fijo(0); else marcar(0);
  enVista(placa, v => { visible = v; if (v && !quieto.matches) correr(); });
}

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
const VIDAS = { capas, ruta, prueba, revision, tablero, vigilancia, asistente, cobertura };
const cargar = async fig => {
  const lienzo = fig.querySelector('.lienzo');
  const r = await fetch(lienzo.dataset.src);
  if (!r.ok) return;
  lienzo.innerHTML = await r.text();
  const svg = lienzo.querySelector('svg');
  svg.setAttribute('aria-hidden', 'true');
  svg.removeAttribute('role');
  fig.classList.add('lista');
  enVista(lienzo, v => fig.classList.toggle('en-vista', v));
  const vida = VIDAS[fig.dataset.figura];
  if (vida) vida(fig);
};
const cerca = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  cerca.unobserve(e.target);
  cargar(e.target);
}), { rootMargin: '600px 0px' });
document.querySelectorAll('[data-figura]').forEach(f => cerca.observe(f));
