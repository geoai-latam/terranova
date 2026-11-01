// Héroe, figura cero: la maqueta de predios reales del SINIC alrededor del punto consultado en
// Santa Marta, en 3D. Es el póster (img/figuras/heroe.svg, dibujado con el kit de Anatomy) hecho
// volumen: la misma geometría (maqueta.js), la misma cámara ortográfica a 45°/30° y el mismo
// sombreado plano de cuatro tonos por orientación de cara, con la luz fija a la cámara. Predios y
// base neutros (estructura), el consultado en teal (el sujeto) y la respuesta como único destello
// ámbar. Solo dibuja cuando algo cambia (la respuesta, el arrastre, el tamaño) y se duerme; el
// giro va por tiempo, no por cuadros. Con movimiento reducido dibuja una vez. heroe.js decide si se
// carga: si no, queda el póster, que es la misma imagen.
import * as M from './maqueta.js';
import { cargarThree } from './comun3d.js';

const esc = document.querySelector('[data-escena="predios"]');
const quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;
const estado = { renders: 0 };
window.__heroe = estado;
if (esc) iniciar(esc).catch((err) => {
  console.warn('escena de predios:', err);
  document.documentElement.dataset.heroe = 'poster';
});

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);

// Cuatro tonos por orientación de cara, como el extrude del kit: el techo aparte y los lados según
// cuánto miran a la luz, que va a la izquierda de la cámara. Sin luces ni sombras de three.js.
const VERT = `
attribute float aMat;
varying vec3 vN;
varying float vMat;
void main() {
  vN = normal; vMat = aMat;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
const FRAG = `
uniform vec3 uRampa[25];
uniform vec2 uLuz;
varying vec3 vN;
varying float vMat;
void main() {
  int m = int(vMat + 0.5);
  vec3 n = normalize(vN);
  int i;
  if (n.y > 0.5) i = 0;
  else {
    float luz = (dot(n.xz, uLuz) + 1.0) * 0.5;
    i = 4 - int(clamp(floor(luz * 4.0), 0.0, 3.0));
  }
  gl_FragColor = vec4(uRampa[m * 5 + i], 1.0);
}`;

// Un prisma desde un anillo del plano (ejes del kit: x este, y sur), de z0 a z1, en coordenadas de
// three (X = x, Y = z, Z = y). Normales planas; los triángulos miran hacia afuera.
function prisma(THREE, anillo, z0, z1, mat, acc) {
  const area = anillo.reduce((s, [ax, ay], i) => {
    const [bx, by] = anillo[(i + 1) % anillo.length];
    return s + ax * by - bx * ay;
  }, 0);
  const ring = area < 0 ? [...anillo].reverse() : anillo;
  const tri = (a, b, c, n) => {
    // orienta el triángulo según la normal
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const cx = u[1] * v[2] - u[2] * v[1], cy = u[2] * v[0] - u[0] * v[2], cz = u[0] * v[1] - u[1] * v[0];
    const ok = cx * n[0] + cy * n[1] + cz * n[2] >= 0;
    for (const p of ok ? [a, b, c] : [a, c, b]) {
      acc.pos.push(p[0], p[1], p[2]); acc.nor.push(n[0], n[1], n[2]); acc.mat.push(mat);
    }
  };
  const V = (x, y, z) => [x, z, y];
  const pts = ring.map(([x, y]) => new THREE.Vector2(x, y));
  for (const t of THREE.ShapeUtils.triangulateShape(pts, [])) {
    tri(...t.map((j) => V(ring[j][0], ring[j][1], z1)), [0, 1, 0]);
  }
  const n = ring.length;
  for (let i = 0; i < n; i++) {
    const [ax, ay] = ring[i], [bx, by] = ring[(i + 1) % n];
    const L = Math.hypot(bx - ax, by - ay) || 1;
    const nn = [(by - ay) / L, 0, -(bx - ax) / L]; // hacia afuera de un anillo antihorario (kit)
    const a0 = V(ax, ay, z0), b0 = V(bx, by, z0), a1 = V(ax, ay, z1), b1 = V(bx, by, z1);
    tri(a0, b0, b1, nn); tri(a0, b1, a1, nn);
  }
}

function malla(THREE, acc, material) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(acc.pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(acc.nor, 3));
  g.setAttribute('aMat', new THREE.Float32BufferAttribute(acc.mat, 1));
  return new THREE.Mesh(g, material);
}
const nuevo = () => ({ pos: [], nor: [], mat: [] });
const circulo = (cx, cy, r, n) => Array.from({ length: n }, (_, i) => [cx + r * Math.cos((i / n) * 2 * Math.PI), cy + r * Math.sin((i / n) * 2 * Math.PI)]);
function redondo({ x, y, w, d, r }, pasos = 6) {
  const out = [];
  for (const [cx, cy, a0] of [[x + w - r, y + r, -90], [x + w - r, y + d - r, 0], [x + r, y + d - r, 90], [x + r, y + r, 180]]) {
    for (let s = 0; s <= pasos; s++) {
      const a = ((a0 + (90 * s) / pasos) * Math.PI) / 180;
      out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
  }
  return out;
}

async function iniciar(esc) {
  document.documentElement.dataset.heroe = 'cargando';
  const [THREE, sm, calles] = await Promise.all([
    cargarThree(),
    fetch('/datos/sm.json').then((r) => r.json()),
    fetch('/datos/calles.json').then((r) => r.json()).catch(() => ({ calles: [] })),
  ]);
  const Q = M.maqueta(sm, calles);
  const lamina = esc.querySelector('.lamina');
  const [qx, qy, VW, VH, KV] = esc.dataset.camara.split(' ').map(Number);
  const css = getComputedStyle(document.documentElement);
  const tok = (n) => hex(css.getPropertyValue('--' + n).trim());
  const rampa = (nombre, desde = 0) => Array.from({ length: 5 }, (_, i) => tok(`${nombre}-${i + desde}`));
  // 0 predios, 1 base, 2 sujeto, 3 acento, 4 patas
  const RAMPAS = [rampa('estructura'), rampa('estructura', 2), rampa('sujeto-teal'), rampa('acento'), rampa('estructura', 2)];

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(1.5, devicePixelRatio || 1));
  const lienzo = renderer.domElement;
  lienzo.setAttribute('aria-hidden', 'true');
  lamina.insertBefore(lienzo, lamina.querySelector('.rotulos'));
  const scene = new THREE.Scene();
  const U = {
    uRampa: { value: RAMPAS.flat().map((c) => new THREE.Vector3(...c)) },
    uLuz: { value: new THREE.Vector2() },
  };
  const material = new THREE.ShaderMaterial({
    uniforms: U, vertexShader: VERT, fragmentShader: FRAG,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  });
  const linea = (n) => new THREE.LineBasicMaterial({ color: css.getPropertyValue('--' + n).trim() });
  const filos = (mesh, mat, umbral = 20) => {
    const l = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, umbral), mat);
    mesh.add(l);
    return l;
  };
  const piso = -M.GRUESO - M.PATA.alto;

  // Base: patas con brida, losa, ranura, costura, tornillos, regla en metros y la flecha del norte.
  const base = nuevo();
  for (const [x, y] of [[M.PLACA.x, M.PLACA.y], [M.PLACA.x + M.PLACA.w, M.PLACA.y], [M.PLACA.x, M.PLACA.y + M.PLACA.d], [M.PLACA.x + M.PLACA.w, M.PLACA.y + M.PLACA.d]]) {
    const cx = x + Math.sign(-x) * M.PATA.dentro, cy = y + Math.sign(-y) * M.PATA.dentro;
    prisma(THREE, circulo(cx, cy, M.PATA.r + 2.5, 28), piso, piso + 1.6, 4, base);
    prisma(THREE, circulo(cx, cy, M.PATA.r, 28), piso + 1.6, -M.GRUESO, 4, base);
  }
  prisma(THREE, redondo(M.PLACA), -M.GRUESO, 0, 1, base);
  const G = M.REGLA;
  prisma(THREE, redondo({ x: G.x0 - 4, y: G.y, w: G.x1 - G.x0 + 8, d: G.ancho, r: 1 }, 2), 0, 0.8, 1, base);
  const mBase = malla(THREE, base, material);
  filos(mBase, linea('linea-media'));
  scene.add(mBase);
  const trazos = (pts, cerrado) => {
    const out = [];
    for (let i = 0; i < pts.length - (cerrado ? 0 : 1); i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      out.push(a[0], a[2], a[1], b[0], b[2], b[1]);
    }
    return out;
  };
  const segmentos = (lista, n) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(lista, 3));
    scene.add(new THREE.LineSegments(g, linea(n)));
  };
  const ranura = redondo({ x: M.PLACA.x + 6, y: M.PLACA.y + 6, w: M.PLACA.w - 12, d: M.PLACA.d - 12, r: 0 }, 1);
  segmentos([
    ...trazos(ranura.map(([x, y]) => [x, y, 0.02]), true),
    ...trazos(redondo(M.PLACA).map(([x, y]) => [x, y, -M.GRUESO / 2]), true),
  ], 'linea-tenue');
  const torn = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) torn.push(...trazos(circulo(sx * (M.LADO - 11), sy * (M.LADO - 11), 2.6, 16).map(([x, y]) => [x, y, 0.02]), true));
  const menores = [], mayores = [];
  for (let at = Math.ceil(G.x0 / G.paso) * G.paso, i = Math.round(at / G.paso); at <= G.x1 + 1e-9; at += G.paso, i++) {
    const largo = i % G.cada === 0 ? 5.5 : 3;
    (i % G.cada === 0 ? mayores : menores).push(at, 0.82, G.y + 0.4, at, 0.82, G.y + 0.4 + largo);
  }
  segmentos([...torn, ...menores], 'linea-baja');
  segmentos(mayores, 'linea-media');
  const N = M.NORTE;
  const flecha = [[N.x, N.y - N.largo], [N.x + N.ancho / 2, N.y], [N.x, N.y - N.largo * 0.3], [N.x - N.ancho / 2, N.y]];
  const fl = nuevo();
  prisma(THREE, flecha, 0, 0.05, 1, fl);
  const mFl = malla(THREE, fl, material);
  scene.add(mFl);
  segmentos(trazos(flecha.map(([x, y]) => [x, y, 0.06]), true), 'linea-baja');

  // Sombra de contacto: las mismas tres capas del póster, planas sobre el piso, sin desenfoque.
  const matSombra = new THREE.MeshBasicMaterial({ color: css.getPropertyValue('--halo').trim(), transparent: true, opacity: M.SOMBRA.opacidad, depthWrite: false, side: THREE.DoubleSide });
  M.SOMBRA.pasos.forEach((by, i) => {
    const pl = { x: M.PLACA.x - by, y: M.PLACA.y - by, w: M.PLACA.w + 2 * by, d: M.PLACA.d + 2 * by, r: M.PLACA.r + by };
    const g = new THREE.ShapeGeometry(new THREE.Shape(redondo(pl).map(([x, y]) => new THREE.Vector2(x, y))));
    const m = new THREE.Mesh(g, matSombra);
    m.rotation.x = Math.PI / 2; // (x, y) del plano → (X, Z) de three
    m.position.y = piso - 0.05 + i * 0.01; m.renderOrder = -1;
    scene.add(m);
  });

  // Predios neutros.
  const pr = nuevo();
  Q.predios.forEach((q) => prisma(THREE, q.anillo, 0, M.H, 0, pr));
  const mPredios = malla(THREE, pr, material);
  filos(mPredios, linea('linea-media'), 30);
  scene.add(mPredios);

  // El consultado: un prisma de altura 1 que se estira, en teal, con su filo; y el punto ámbar.
  const ob = nuevo();
  prisma(THREE, Q.consultado.anillo, 0, 1, 2, ob);
  const mObj = malla(THREE, ob, material);
  filos(mObj, linea('sujeto-teal-filo'), 30);
  scene.add(mObj);
  const [cx, cy] = Q.consultado.centro;
  const pu = nuevo();
  prisma(THREE, circulo(cx, cy, 2.4, 20), 0, 1.2, 3, pu);
  const mPunto = malla(THREE, pu, material);
  filos(mPunto, linea('acento-filo'), 30);
  scene.add(mPunto);
  // El destello: un anillo ámbar que sale una vez del pie del consultado, sobre los techos.
  const mOnda = new THREE.Mesh(new THREE.RingGeometry(0.94, 1, 72), new THREE.MeshBasicMaterial({ color: css.getPropertyValue('--acento-1').trim(), transparent: true, opacity: 0, depthWrite: false }));
  mOnda.rotation.x = -Math.PI / 2; mOnda.position.set(cx, M.H + 0.3, cy); mOnda.visible = false;
  scene.add(mOnda);

  // Cámara: el encuadre exacto del póster (data-camara: dónde cae el centro de la base en el
  // viewBox, su tamaño y las unidades por metro), girando alrededor del centro de la base.
  const cam = new THREE.OrthographicCamera(-qx / KV, (VW - qx) / KV, qy / KV, -(VH - qy) / KV, 1, 4000);
  const E = (M.ELEVACION * Math.PI) / 180;
  const st = { az: M.AZIMUT, azMeta: M.AZIMUT, alto: M.ALTO, v: 0, altoMeta: M.ALTO, punto: 1, puntoMeta: 1, onda: null, enVista: true, pedido: 0, ultimo: 0, sucio: true, w: 0, h: 0 };
  const colocar = () => {
    const A = (st.az * Math.PI) / 180;
    cam.position.set(1500 * Math.cos(A) * Math.cos(E), 1500 * Math.sin(E), 1500 * Math.sin(A) * Math.cos(E));
    cam.up.set(0, 1, 0);
    cam.lookAt(0, 0, 0);
    U.uLuz.value.set(-Math.sin(A), Math.cos(A));
  };
  function tam() {
    const r = lamina.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (w === st.w && h === st.h) return;
    st.w = w; st.h = h;
    renderer.setSize(w, h, false);
    pedir();
  }

  // Rótulos: siguen a la cámara solo si alguien la giró; si no, quedan donde los puso el póster.
  const capa = esc.querySelector('.rotulos');
  const spans = [...capa.querySelectorAll('.calle')];
  const v3 = new THREE.Vector3();
  const pct = (x, y, z) => { v3.set(x, z, y).project(cam); return [(v3.x + 1) * 50, (1 - v3.y) * 50]; };
  function rotulos() {
    Q.rotulos.forEach((r, i) => {
      const e = spans[i];
      if (!e) return;
      const a = pct(r.x, r.y, M.H), b = pct(r.x + r.dx, r.y + r.dy, M.H);
      let ang = (Math.atan2((b[1] - a[1]) * lamina.clientHeight, (b[0] - a[0]) * lamina.clientWidth) * 180) / Math.PI;
      if (ang > 90) ang -= 180; else if (ang < -90) ang += 180;
      e.style.left = a[0].toFixed(2) + '%'; e.style.top = a[1].toFixed(2) + '%';
      e.style.setProperty('--a', ang.toFixed(1) + 'deg');
    });
  }

  // Bucle bajo demanda: corre mientras algo se mueve y se duerme.
  // Pedir un cuadro marca la escena como sucia; fuera de la vista se queda sucia y se dibuja al
  // volver. Un cuadro sin nada que mover no pide el siguiente: la escena se duerme.
  function pedir() {
    st.sucio = true;
    if (!st.pedido && st.enVista) st.pedido = requestAnimationFrame(cuadro);
  }
  const resorte = (x, v, meta, dt, tau) => {
    // críticamente amortiguado (sin rebote), en cuatro subpasos
    const w = 1 / tau;
    for (let i = 0; i < 4; i++) { const h = dt / 4; v += (w * w * (meta - x) - 2 * w * v) * h; x += v * h; }
    if (Math.abs(meta - x) < 1e-3 && Math.abs(v) < 1e-3) return [meta, 0];
    return [x, v];
  };
  let vP = 0;
  function cuadro(t) {
    st.pedido = 0;
    st.sucio = false;
    const dt = st.ultimo ? Math.min((t - st.ultimo) / 1000, 1 / 30) : 1 / 60;
    st.ultimo = t;
    let sigue = false;
    if (quieto) { st.az = st.azMeta; st.alto = st.altoMeta; st.punto = st.puntoMeta; st.onda = null; }
    else {
      const az0 = st.az;
      st.az += (st.azMeta - st.az) * (1 - Math.exp(-dt / 0.12));
      if (Math.abs(st.azMeta - st.az) < 0.01) st.az = st.azMeta;
      if (st.az !== az0) sigue = true;
      [st.alto, st.v] = resorte(st.alto, st.v, st.altoMeta, dt, 0.11);
      [st.punto, vP] = resorte(st.punto, vP, st.puntoMeta, dt, 0.06);
      if (st.alto !== st.altoMeta || st.punto !== st.puntoMeta) sigue = true;
    }
    colocar();
    mObj.scale.y = Math.max(0.01, st.alto);
    mPunto.position.y = st.alto;
    mPunto.scale.set(Math.max(0.001, st.punto), Math.max(0.001, st.punto), Math.max(0.001, st.punto));
    mPunto.visible = st.punto > 0.01;
    if (st.onda !== null) {
      const k = Math.min(1, (t - st.onda) / M.ONDA.ms);
      const e = 1 - Math.pow(1 - k, 3); // salida suave
      mOnda.visible = k < 1;
      mOnda.scale.setScalar(M.ONDA.r0 + (M.ONDA.r1 - M.ONDA.r0) * e);
      mOnda.material.opacity = 0.9 * (1 - k);
      if (k < 1) sigue = true; else st.onda = null;
    }
    if (st.az !== M.AZIMUT || esc.dataset.girada) { esc.dataset.girada = '1'; rotulos(); }
    renderer.render(scene, cam);
    estado.renders++;
    if (!esc.classList.contains('viva')) {
      esc.classList.add('viva');
      document.documentElement.dataset.heroe = '3d';
      document.dispatchEvent(new Event('terranova:escena'));
    }
    if (sigue) pedir(); else st.ultimo = 0;
  }

  // La respuesta manda: mientras se escribe la pregunta, el consultado baja con los demás; cuando
  // llega su respuesta, sube y sale el destello.
  const turno = (k) => {
    if (k === 'predio') {
      st.altoMeta = M.ALTO; st.puntoMeta = 1;
      if (!quieto) st.onda = performance.now();
    } else { st.altoMeta = M.H; st.puntoMeta = 0; }
    pedir();
  };
  document.addEventListener('terranova:turno', (e) => turno(e.detail));
  const previo = document.documentElement.dataset.turno;
  if (previo) {
    // la consola ya empezó: va a su estado (sin repetir el destello si la respuesta ya llegó)
    turno(previo);
    st.onda = null;
  }

  // Arrastre: gira en azimut (sigue al dedo con un poco de inercia); sin zoom.
  let x0 = null;
  esc.addEventListener('pointerdown', (e) => {
    if (e.pointerType !== 'mouse' || e.button !== 0) return;
    x0 = e.clientX; esc.setPointerCapture(e.pointerId); esc.classList.add('arrastra');
  });
  esc.addEventListener('pointermove', (e) => {
    if (x0 === null) return;
    st.azMeta -= (e.clientX - x0) * 0.35; x0 = e.clientX; pedir();
  });
  const suelta = () => { x0 = null; esc.classList.remove('arrastra'); };
  esc.addEventListener('pointerup', suelta);
  esc.addEventListener('pointercancel', suelta);

  new IntersectionObserver((es) => {
    st.enVista = es[es.length - 1].isIntersecting;
    if (st.enVista && st.sucio) pedir();
  }, { rootMargin: '120px 0px' }).observe(esc);
  new ResizeObserver(tam).observe(lamina);
  tam();
}
