// Movimiento de las dos figuras isométricas de la portada (dibujadas con el kit de Anatomy en
// web/figuras). Sin este archivo, o con movimiento reducido, cada figura queda armada y quieta.
// Movimiento con tiempo y seguimiento exponencial; un recorrido en reposo cuando nadie toca; el
// puntero y las flechas eligen; fuera de la vista no corre nada.
const quieto = matchMedia('(prefers-reduced-motion: reduce)');
const sigue = (actual, meta, dt, s) => actual + (meta - actual) * (1 - Math.exp(-dt / s));

function enVista(el, cambio) {
  new IntersectionObserver(es => cambio(es[es.length - 1].isIntersecting), { rootMargin: '80px 0px' }).observe(el);
}

// ---------------------------------------------------------------- Fig. 1: el bastidor
function capas(fig) {
  const placa = fig.querySelector('.placa');
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
}

// ---------------------------------------------------------------- Fig. 2: la ruta de una pregunta
function ruta(fig) {
  const placa = fig.querySelector('.placa');
  const svg = fig.querySelector('svg');
  const vivo = JSON.parse(svg.dataset.vivo);
  const P = vivo.P;
  const lectura = fig.querySelector('[data-lectura]');
  const pregunta = fig.querySelector('[data-pregunta]');
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
    lectura.append(c, ` → ${d.e}`);
    pregunta.textContent = d.p;
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

document.querySelectorAll('[data-figura="capas"]').forEach(capas);
document.querySelectorAll('[data-figura="ruta"]').forEach(ruta);
