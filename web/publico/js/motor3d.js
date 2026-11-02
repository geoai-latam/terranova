// Motor de las figuras 3D de la portada. Un solo WebGLRenderer, fuera de pantalla, pinta cada
// figura en su trozo del búfer y la copia a su lienzo 2D (drawImage): un contexto WebGL para todas.
// Solo se pinta lo que está en vista y en ciclo; entre ciclos, cero cuadros. Con movimiento
// reducido, un cuadro del resultado. Misma luz, materiales y cámara que el héroe (comun3d.js).
import { cargarThree, luces, quieto, suave } from './comun3d.js?v=4f51e3ba7b';
export { quieto, suave };

export const medidor = { cuadros: 0, porFigura: {}, figs: {} };
// Validación (visual-validation): congelar una figura en un instante dado para capturas deterministas.
medidor.estado = () => ({ vivas: vivas.size, bucle: !!raf });
medidor.fijar = (nombre, t, turno) => {
  const f = medidor.figs[nombre]; if (!f) return false;
  vivas.delete(f); if (turno !== undefined) f.turno = turno; f.t = Math.max(0, Math.min(t, f.dur)); f.w = 0; pintar(f); return true;
};
window.__fig3d = medidor;

let T = null, R = null, BW = 0, BH = 0, promesa = null;
export function three() {
  if (!promesa) promesa = cargarThree().then(m => {
    T = m;
    R = new T.WebGLRenderer({ antialias: true, alpha: true });
    R.setPixelRatio(1); R.setClearColor(0x000000, 0);
    R.shadowMap.enabled = true; R.shadowMap.type = T.PCFSoftShadowMap;
    R.setScissorTest(true);
    return T;
  });
  return promesa;
}
const dpr = () => Math.min(2, window.devicePixelRatio || 1);

// Colores del héroe: techos blancos, muros un poco más oscuros, filos en tinta al 22 %, el predio en
// ámbar, lo verificado en teal.
export const C = {
  techo: '#FFFFFF', lado: '#E4E9E2', placa: '#E2E6DF', placaLado: '#D7DBD4', tinta: '#12261F',
  ambar: '#EBAE45', ambarLado: '#D99A2E', teal: '#236E62', tinte: '#8FD3C4', tinteLado: '#7CC2B2',
  revisado: '#CDE6DF', revisadoLado: '#B9D6CD', suave: '#4E5E57', suaveLado: '#3E4C46', medio: '#6F7C75',
};

// ---------- pintar ----------
export function pintar(f) {
  if (!f.listo) return;
  const t0p = performance.now();
  const w = f.lienzo.clientWidth, h = f.lienzo.clientHeight;
  if (!w || !h) return;
  const r = dpr(), pw = Math.round(w * r), ph = Math.round(h * r);
  if (pw > BW || ph > BH) { BW = Math.max(BW, pw); BH = Math.max(BH, ph); R.setSize(BW, BH, false); }
  if (f.lienzo.width !== pw || f.lienzo.height !== ph) { f.lienzo.width = pw; f.lienzo.height = ph; }
  if (f.w !== w || f.h !== h) { f.w = w; f.h = h; f.tam(w, h); }
  f.pose(f.t, f.turno);
  R.setViewport(0, 0, pw, ph); R.setScissor(0, 0, pw, ph);
  R.render(f.escena, f.cam);
  f.ctx.clearRect(0, 0, pw, ph);
  f.ctx.drawImage(R.domElement, 0, BH - ph, pw, ph, 0, 0, pw, ph);
  if (f.despues) f.despues(w, h);
  medidor.cuadros++; medidor.porFigura[f.nombre] = (medidor.porFigura[f.nombre] || 0) + 1;
  if (!vivas.has(f)) medidor.sueltos = (medidor.sueltos || 0) + 1;
  medidor.ms = (medidor.ms || 0) + (performance.now() - t0p);
  { const d = performance.now() - t0p, mx = medidor.max || (medidor.max = {}); (mx[f.nombre] = mx[f.nombre] || []).push(Math.round(d)); if (mx[f.nombre].length > 6) mx[f.nombre].splice(3, 1); }
}

// ---------- planificador: un solo bucle para todas ----------
const vivas = new Set();
let raf = 0, ultimo = 0;
// a lo sumo 60 cuadros por segundo, y 30 con puntero grueso o pocos núcleos (DISENO.md)
const PASO = matchMedia('(pointer: coarse)').matches || (navigator.hardwareConcurrency || 8) <= 4 ? 32 : 15.5;
function bucle(now) {
  raf = 0;
  if (now - ultimo < PASO) { raf = requestAnimationFrame(bucle); return; }
  ultimo = now;
  for (const f of vivas) {
    const t = now - f.t0;
    f.t = Math.max(0, Math.min(t, f.dur));
    if (f.vista) pintar(f);
    if (t >= f.dur) { vivas.delete(f); if (f.fin) f.fin(); }
  }
  if (vivas.size) raf = requestAnimationFrame(bucle);
}
export function correr(f, turno) {
  if (turno !== undefined) { f.antes = f.turno; f.turno = turno; }
  if (quieto) { f.t = f.dur; pintar(f); return; }
  f.t0 = performance.now(); f.t = 0; vivas.add(f);
  if (!raf) raf = requestAnimationFrame(bucle);
}
function despertar() { if (!raf && vivas.size) raf = requestAnimationFrame(bucle); }

// Vista: con cualquier trozo visible se puede pintar; con un 35 % arranca el primer ciclo.
const io = new IntersectionObserver(es => es.forEach(e => {
  const f = e.target.__f3; if (!f) return;
  const antes = f.vista;
  f.vista = e.isIntersecting;
  if (f.vista && !antes) { if (vivas.has(f)) despertar(); else pintar(f); }
  f.arranca = e.intersectionRatio >= 0.35 || (e.isIntersecting && e.intersectionRect.height > innerHeight * 0.5);
  if (f.alVer) f.alVer(f.arranca);
}), { threshold: [0, 0.35, 0.6] });

// Registra una figura ya construida: lienzo 2D, escena, cámara y pose(t, turno).
export function registrar(f) {
  f.ctx = f.lienzo.getContext('2d');
  f.turno = f.turno || 0; f.t = f.tInicial === 0 && !quieto ? 0 : f.dur; f.listo = true; f.vista = false;
  f.caja.__f3 = f; medidor.figs[f.nombre] = f;
  // compila los programas al montar (antes de que la figura entre en vista), no en su primer cuadro
  try { R.compile(f.escena, f.cam); } catch (e) { /* sin compilar antes: compila en el primer cuadro */ }
  new ResizeObserver(() => { f.w = 0; if (f.vista || !f.pintada) { pintar(f); f.pintada = true; } }).observe(f.lienzo);
  io.observe(f.caja);
  // tocar, Enter, espacio: otro ciclo; flechas: otro turno
  const el = f.control || f.caja;
  el.addEventListener('click', () => f.tocar && f.tocar(1));
  el.addEventListener('keydown', e => {
    if (!f.tocar) return;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); f.tocar(1); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); f.tocar(1); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); f.tocar(-1); }
  });
  return f;
}

// Una figura sola: dos ciclos al entrar (si tiene turnos) y uno cada `cada` ms mientras se ve.
export function solo(f, { entrada = 1, cada = 15000 } = {}) {
  let timer = 0, restan = 0, visto = false, debe = false;
  const lanzar = d => { clearTimeout(timer); correr(f, (f.turno + d + f.n) % f.n); };
  f.fin = () => {
    clearTimeout(timer);
    const ms = restan > 0 ? 2600 : cada;
    if (restan > 0) restan--;
    timer = setTimeout(() => { if (f.vista) lanzar(1); else debe = true; }, ms);
  };
  f.alVer = arranca => {
    if (arranca && !visto) { visto = true; restan = entrada - 1; clearTimeout(timer); correr(f, f.turno); }
    else if (arranca && debe) { debe = false; lanzar(1); }
  };
  f.tocar = d => { restan = 0; lanzar(d); };
  if (f.arranca) f.alVer(true);
}

// Un grupo (los cuatro servicios): corre una figura a la vez y solo esa lleva el ámbar.
export function grupo(figs, { cada = 15000, hueco = 500 } = {}) {
  let i = -1, timer = 0, ronda = 0, visto = false, debe = false;
  const enVista = () => figs.some(f => f.vista);
  const lanzar = (k, d) => {
    clearTimeout(timer);
    figs.forEach((f, j) => { if (j !== k && f.actual) { f.actual = false; pintar(f); } });
    i = k; const f = figs[k]; f.actual = true;
    correr(f, (f.turno + d + f.n) % f.n);
  };
  if (quieto) figs.forEach((f, j) => { f.actual = j === 0; });
  const proxima = () => { for (let s = 1; s <= figs.length; s++) { const j = (i + s) % figs.length; if (figs[j].vista) return j; } return -1; };
  figs.forEach((f, k) => {
    f.fin = () => {
      clearTimeout(timer);
      const primera = ronda < figs.length;
      timer = setTimeout(() => {
        const j = proxima();
        if (j < 0) { debe = true; return; }
        ronda++;
        lanzar(j, ronda <= figs.length ? 0 : 1);
      }, primera ? hueco : cada);
    };
    f.alVer = arranca => {
      if (arranca && !visto) { visto = true; ronda = 1; lanzar(k, 0); }
      else if (arranca && debe) { debe = false; ronda++; lanzar(k, 1); }
    };
    f.tocar = d => { ronda = Math.max(ronda, figs.length); lanzar(k, d); };
  });
  const ya = figs.find(f => f.arranca); if (ya) ya.alVer(true);
}

// ---------- escena: luz, suelo, retícula y niebla del héroe ----------
export function papelDe(el) {
  let n = el;
  while (n && n !== document.documentElement) {
    const c = getComputedStyle(n).backgroundColor;
    if (c && c !== 'transparent' && !/rgba\(.*,\s*0\)$/.test(c)) return c;
    n = n.parentElement;
  }
  return '#F6F7F4';
}
export function ambiente(escena, { lado, papel, reticula = true, sol }) {
  const luz = luces(T, R, escena, { sombras: true, lado, sol });
  luz.shadow.mapSize.set(1024, 1024);
  const suelo = new T.Mesh(new T.PlaneGeometry(lado * 8, lado * 8), new T.ShadowMaterial({ opacity: 0.09 }));
  suelo.rotation.x = -Math.PI / 2; suelo.position.y = -0.05; suelo.receiveShadow = true; escena.add(suelo);
  if (reticula) {
    const g = new T.GridHelper(lado * 5, 20, '#D3D9D1', '#D3D9D1');
    g.material.transparent = true; g.material.opacity = 0.5; g.position.y = -0.1; escena.add(g);
  }
  escena.fog = new T.Fog(new T.Color(papel), 1000 + lado * 0.9, 1000 + lado * 2.1);
  luz.userData.suelo = suelo;
  return luz;
}

// ---------- geometría ----------
export function anillo(flat) {
  let pts = [];
  for (let k = 0; k < flat.length; k += 2) pts.push(new T.Vector2(flat[k], flat[k + 1]));
  if (T.ShapeUtils.isClockWise(pts)) pts.reverse();
  return pts;
}
export const centro = pts => pts.reduce((a, p) => a.add(p), new T.Vector2()).divideScalar(pts.length);
export function encoger(pts, d = 0.55) {
  const c = centro(pts);
  return pts.map(p => { const v = p.clone().sub(c), L = v.length(); return L > d * 2.2 ? c.clone().add(v.multiplyScalar((L - d) / L)) : p.clone(); });
}
export const area = pts => pts.reduce((a, p, i) => { const q = pts[(i + 1) % pts.length]; return a + p.x * q.y - q.x * p.y; }, 0) / 2;
// Sutherland–Hodgman contra el cuadrado [x0,x1]×[y0,y1]
export function recortar(pts, x0, x1, y0, y1) {
  const bordes = [[p => p.x >= x0, (a, b) => cruce(a, b, 'x', x0)], [p => p.x <= x1, (a, b) => cruce(a, b, 'x', x1)],
    [p => p.y >= y0, (a, b) => cruce(a, b, 'y', y0)], [p => p.y <= y1, (a, b) => cruce(a, b, 'y', y1)]];
  let out = pts;
  for (const [dentro, corta] of bordes) {
    const ent = out; out = [];
    if (!ent.length) break;
    for (let i = 0; i < ent.length; i++) {
      const a = ent[(i + ent.length - 1) % ent.length], b = ent[i];
      if (dentro(b)) { if (!dentro(a)) out.push(corta(a, b)); out.push(b); }
      else if (dentro(a)) out.push(corta(a, b));
    }
  }
  return out;
}
function cruce(a, b, eje, v) {
  const k = (v - a[eje]) / (b[eje] - a[eje]);
  return new T.Vector2(a.x + (b.x - a.x) * k, a.y + (b.y - a.y) * k);
}

// Materiales de maqueta: [techo, muros] en Lambert, como el héroe.
export const mats = (techo, lado) => [new T.MeshLambertMaterial({ color: techo }), new T.MeshLambertMaterial({ color: lado })];
export function pintarMats(m, techo, lado) { m[0].color.set(techo); m[1].color.set(lado); }

// Un prisma de un lindero (x este, y norte) a la altura 1; se escala en y.
export function prisma(pts, m) {
  const g = new T.ExtrudeGeometry(new T.Shape(pts), { depth: 1, bevelEnabled: false });
  g.rotateX(-Math.PI / 2);
  const o = new T.Mesh(g, m); o.castShadow = true; o.receiveShadow = true;
  return o;
}
// Muchos prismas en una sola malla, techos blancos y muros más oscuros, con sus filos.
export function bloques(lista, h, { techo = C.techo, lado = C.lado, filo = 0.22, ao = null } = {}) {
  const pos = [], seg = [];
  const P = (x, y, z) => pos.push(x, z, -y);
  for (const pts of lista) {
    T.ShapeUtils.triangulateShape(pts, []).forEach(t => t.forEach(j => P(pts[j].x, pts[j].y, h)));
    for (let k = 0; k < pts.length; k++) {
      const a = pts[k], b = pts[(k + 1) % pts.length];
      P(a.x, a.y, 0); P(b.x, b.y, 0); P(b.x, b.y, h); P(a.x, a.y, 0); P(b.x, b.y, h); P(a.x, a.y, h);
      seg.push(a.x, h + 0.04, -a.y, b.x, h + 0.04, -b.y);
    }
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  const col = new Float32Array(pos.length), ct = new T.Color(techo), cl = new T.Color(lado), n = g.attributes.normal;
  for (let v = 0; v < n.count; v++) { const c = n.getY(v) > 0.5 ? ct : cl; col.set([c.r, c.g, c.b], v * 3); }
  g.setAttribute('color', new T.Float32BufferAttribute(col, 3));
  const mb = new T.MeshLambertMaterial({ vertexColors: true });
  if (ao) contactoMat(mb, ao);
  const malla = new T.Mesh(g, mb);
  malla.castShadow = malla.receiveShadow = true;
  const grupo = new T.Group(); grupo.add(malla); grupo.userData.mat = mb;
  if (filo > 0) grupo.add(lineas(seg, C.tinta, filo));
  return grupo;
}
export function lineas(seg, color, opacidad = 1) {
  const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(seg, 3));
  return new T.LineSegments(g, new T.LineBasicMaterial({ color, transparent: opacidad < 1, opacity: opacidad }));
}
export function contorno(pts, y) {
  const seg = [];
  for (let k = 0; k < pts.length; k++) { const a = pts[k], b = pts[(k + 1) % pts.length]; seg.push(a.x, y, -a.y, b.x, y, -b.y); }
  return seg;
}
// Un filete plano de ancho `a` alrededor de un lindero (se ve nítido, a diferencia de una línea de 1 px).
export function filete(pts, a, color) {
  const sh = new T.Shape(pts), adentro = encoger(pts, a);
  sh.holes.push(new T.Path(adentro.slice().reverse()));
  const g = new T.ShapeGeometry(sh); g.rotateX(-Math.PI / 2);
  return new T.Mesh(g, new T.MeshBasicMaterial({ color, side: T.DoubleSide }));
}
export function caja(w, h, d, m) {
  const o = new T.Mesh(new T.BoxGeometry(w, h, d), Array.isArray(m) ? [m[1], m[1], m[0], m[1], m[1], m[1]] : m);
  o.castShadow = o.receiveShadow = true; return o;
}

// ---------- cámara ----------
// Ortográfica, como el héroe: acimut y polar, y un encuadre que ajusta los puntos dados al lienzo,
// con márgenes en píxeles (izq, der, arriba, abajo).
const v3 = () => new T.Vector3();
export function encuadrar(cam, { az, pol, mira, puntos, w, h, margen = [12, 12, 12, 12] }) {
  const D = 1000, c = mira;
  cam.position.set(c.x + D * Math.sin(pol) * Math.sin(az), c.y + D * Math.cos(pol), c.z + D * Math.sin(pol) * Math.cos(az));
  cam.up.set(0, 1, 0); cam.lookAt(c); cam.updateMatrixWorld();
  const inv = cam.matrixWorldInverse, v = v3();
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of puntos) { v.copy(p).applyMatrix4(inv); x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y); }
  const [ml, mr, mt, mb] = margen, aw = Math.max(20, w - ml - mr), ah = Math.max(20, h - mt - mb);
  const k = Math.max((x1 - x0) / aw, (y1 - y0) / ah); // metros por píxel
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const l = cx - (aw / 2 + ml) * k, r = cx + (aw / 2 + mr) * k, t = cy + (ah / 2 + mt) * k, b = cy - (ah / 2 + mb) * k;
  Object.assign(cam, { left: l, right: r, top: t, bottom: b, near: 1, far: 4000 });
  cam.updateProjectionMatrix();
  return k;
}
// Mueve la cámara sin cambiar el encuadre (para una deriva leve durante el ciclo).
export function orientar(cam, { az, pol, mira }) {
  const D = 1000, c = mira;
  cam.position.set(c.x + D * Math.sin(pol) * Math.sin(az), c.y + D * Math.cos(pol), c.z + D * Math.sin(pol) * Math.cos(az));
  cam.lookAt(c); cam.updateMatrixWorld();
}
const _p = { v: null };
export function aPantalla(cam, x, y, z, w, h) {
  const v = _p.v || (_p.v = v3());
  v.set(x, y, z).project(cam);
  return [(v.x + 1) / 2 * w, (1 - v.y) / 2 * h];
}

// tramos de tiempo: 0 antes de a, 1 después de a+d, con la curva de salida del héroe
export const tramo = (t, a, d) => suave((t - a) / d);
export const lineal = (t, a, d) => Math.min(1, Math.max(0, (t - a) / d));

export { T as THREE_ };
export const getT = () => T;

// ======================================================================================
// Contacto (AO), sombras ajustadas, resortes y planos con autor.
// ======================================================================================

// ---------- movimiento (procedural-animation): curvas analíticas con bloqueo terminal ----------
// Respuesta al escalón de un oscilador amortiguado: de 0 a 1 en d ms, con un rebote (z < 1) que se
// asienta antes del final; el último 20 % se funde con 1 para que el reposo sea exacto.
export function resorte(t, a, d, z = 0.5) {
  const u = (t - a) / d;
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  const D = d / 1000, w = 4.6 / (z * D), wd = w * Math.sqrt(1 - z * z), s = u * D;
  const x = 1 - Math.exp(-z * w * s) * (Math.cos(wd * s) + (z * w / wd) * Math.sin(wd * s));
  const k = Math.min(1, Math.max(0, (u - 0.8) / 0.2)), b = k * k * (3 - 2 * k);
  return x + (1 - x) * b;
}
// Anticipación: recoge un poco (−k) durante la fracción p del tramo, con velocidad cero al final del
// recogido, y sale con resorte hasta 1.
export function impulso(t, a, d, { k = 0.12, p = 0.25, z = 0.5 } = {}) {
  const u = (t - a) / d;
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  if (u < p) return -k * (1 - Math.cos(Math.PI * u / p)) / 2;
  return -k + (1 + k) * resorte(t, a + p * d, (1 - p) * d, z);
}
// Una campana 0 → 1 → 0 (para un golpe de contacto o un hundimiento).
export const golpe = (t, a, d) => { const u = (t - a) / d; return u <= 0 || u >= 1 ? 0 : Math.sin(Math.PI * u) ** 2; };

// ---------- contacto (screen-space-ambient-occlusion, horneado) ----------
// La AO solo atenúa la luz indirecta (la del cielo), nunca la del sol, y su radio está en metros del
// mundo, no en píxeles: el pie de un muro se oscurece igual en la miniatura y en la grande, y un techo
// al sol no se ensucia. Sin pasada de pantalla: en esta maqueta el contacto es siempre muro–piso, así
// que se resuelve en el material (muros) y en un mapa de contacto (pisos).
export function contactoMat(mat, { suelo = 0, rad = 2.2, min = 0.5 } = {}) {
  const U = { uSuelo: { value: suelo }, uAoRad: { value: rad }, uAoMin: { value: min } };
  mat.userData.ao = U;
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = 'varying float vAoY;\nvarying float vAoN;\n' + sh.vertexShader.replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
      { vec4 aoP = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
        aoP = instanceMatrix * aoP;
        #endif
        aoP = modelMatrix * aoP; vAoY = aoP.y;
        vAoN = abs(normalize(mat3(modelMatrix) * objectNormal).y); }`);
    sh.fragmentShader = 'uniform float uSuelo;\nuniform float uAoRad;\nuniform float uAoMin;\nvarying float vAoY;\nvarying float vAoN;\n' +
      sh.fragmentShader.replace('#include <aomap_fragment>', `#include <aomap_fragment>
      { float aoH = max(vAoY - uSuelo, 0.0);
        float aoW = mix(uAoMin, 1.0, smoothstep(0.0, uAoRad, aoH));
        reflectedLight.indirectDiffuse *= mix(aoW, 1.0, step(0.6, vAoN)); }`);
  };
  mat.customProgramCacheKey = () => 'terrnova-ao';
  return mat;
}
export const sueloAO = (mat, y) => { if (mat.userData.ao) mat.userData.ao.uSuelo.value = y; };
// Materiales de maqueta con contacto: [techo, muros].
export const matsAO = (techo, lado, op = {}) => mats(techo, lado).map(m => contactoMat(m, op));

// Mapa de contacto de un piso: las huellas de lo que se apoya en él, difuminadas a un radio en metros.
// Sirve como aoMap (atenúa solo la luz del cielo) o, invertido, como calco de contacto sobre el papel.
// rect = [x0, x1, y0, y1] en coordenadas del plano (x este, y norte).
export function mapaContacto(huellas, rect, { res = 512, rad = 1.6, fuerza = 0.75, invertir = false } = {}) {
  const [x0, x1, y0, y1] = rect, W = x1 - x0, H = y1 - y0;
  const s = res / Math.max(W, H), cw = Math.max(8, Math.round(W * s)), ch = Math.max(8, Math.round(H * s));
  // las huellas se dibujan nítidas en un lienzo y se difuminan de una sola vez al pasarlas al final
  // (un filtro por huella sobre el lienzo entero costaba segundos en el primer cuadro)
  const nit = document.createElement('canvas'); nit.width = cw; nit.height = ch;
  const g0 = nit.getContext('2d');
  const v = Math.round(255 * (invertir ? fuerza : 1 - fuerza));
  g0.fillStyle = g0.strokeStyle = `rgb(${v},${v},${v})`;
  g0.lineWidth = rad * s * 0.5; g0.lineJoin = 'round';
  g0.beginPath();
  for (const pts of huellas) {
    pts.forEach((p, i) => { const X = (p.x - x0) * s, Y = (y1 - p.y) * s; i ? g0.lineTo(X, Y) : g0.moveTo(X, Y); });
    g0.closePath();
  }
  g0.fill('nonzero'); g0.stroke();
  const cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
  const g = cv.getContext('2d');
  g.fillStyle = invertir ? '#000' : '#fff'; g.fillRect(0, 0, cw, ch);
  g.filter = `blur(${Math.max(0.5, rad * s * 0.6).toFixed(1)}px)`;
  g.drawImage(nit, 0, 0);
  const tex = new T.CanvasTexture(cv);
  tex.colorSpace = T.NoColorSpace; tex.needsUpdate = true;
  return tex;
}
// Un calco de contacto sobre el papel (donde no hay piso que reciba un aoMap).
export function calco(tex, rect, y, opacidad = 0.2) {
  const [x0, x1, y0, y1] = rect;
  const g = new T.PlaneGeometry(x1 - x0, y1 - y0); g.rotateX(-Math.PI / 2);
  const m = new T.MeshBasicMaterial({ color: C.tinta, alphaMap: tex, transparent: true, opacity: opacidad, depthWrite: false });
  const o = new T.Mesh(g, m); o.position.set((x0 + x1) / 2, y, -(y0 + y1) / 2); o.renderOrder = -1;
  return o;
}
// Una losa (placa) cuyo techo recibe el mapa de contacto. rect en coordenadas del plano; el techo en y = 0.
export function losa(rect, alto, { techo = C.placa, lado = C.placaLado, ao = null, aoFuerza = 1 } = {}) {
  const [x0, x1, y0, y1] = rect;
  const m = mats(techo, lado);
  if (ao) { m[0].aoMap = ao; m[0].aoMapIntensity = aoFuerza; }
  const o = caja(x1 - x0, alto, y1 - y0, m);
  o.position.set((x0 + x1) / 2, -alto / 2, -(y0 + y1) / 2);
  o.userData.mats = m;
  return o;
}

// ---------- sombras (shadow-systems): la cámara de sombra ajustada a lo que se ve ----------
// Encaja el volumen de la sombra a los puntos de la escena vistos desde el sol y escala el sesgo
// normal con el tamaño del texel: sin acné en los techos y sin despegue en el pie de los muros.
export function ajustarSombra(luz, puntos, { mapa = 1024, margen = 1.5 } = {}) {
  const c = new T.Vector3(); puntos.forEach(p => c.add(p)); c.divideScalar(puntos.length);
  const dir = luz.position.clone().sub(luz.target.position).normalize();
  let r = 0; puntos.forEach(p => { r = Math.max(r, p.distanceTo(c)); });
  luz.target.position.copy(c);
  if (!luz.target.parent && luz.parent) luz.parent.add(luz.target);
  luz.position.copy(c).addScaledVector(dir, r * 2 + 20);
  luz.updateMatrixWorld(); luz.target.updateMatrixWorld();
  const sc = luz.shadow.camera;
  sc.position.copy(luz.position); sc.lookAt(c); sc.updateMatrixWorld();
  const inv = sc.matrixWorldInverse, v = new T.Vector3();
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const p of puntos) { v.copy(p).applyMatrix4(inv); x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y); z0 = Math.min(z0, v.z); z1 = Math.max(z1, v.z); }
  Object.assign(sc, { left: x0 - margen, right: x1 + margen, bottom: y0 - margen, top: y1 + margen, near: Math.max(0.1, -z1 - margen * 4), far: -z0 + margen * 4 });
  sc.updateProjectionMatrix();
  const texel = (Math.max(x1 - x0, y1 - y0) + 2 * margen) / mapa;
  luz.shadow.mapSize.set(mapa, mapa);
  if (luz.shadow.map) { luz.shadow.map.dispose(); luz.shadow.map = null; }
  luz.shadow.normalBias = texel * 1.2; luz.shadow.bias = -0.0002;
  return texel;
}
// Sol bajo y de lado: los dos muros que ve la cámara quedan en dos tonos (uno al sol, otro solo con
// el cielo) y la sombra cae hacia delante, sobre el piso que se ve.
export const SOL = [-0.78, 0.92, -0.12];
export const mapaSombra = grande => (matchMedia('(pointer: coarse)').matches ? 1024 : grande ? 2048 : 1024);

// ---------- cámara (camera-direction): un plano con autor ----------
// encuadrar() da el plano final compuesto; plano() lo cierra alrededor de un foco del mundo sin mover
// el foco en pantalla (un empuje de lente). s = 1 es el plano final.
export const marco = cam => ({ left: cam.left, right: cam.right, top: cam.top, bottom: cam.bottom });
export function plano(cam, base, s, foco) {
  const v = new T.Vector3().copy(foco).applyMatrix4(cam.matrixWorldInverse);
  cam.left = v.x + (base.left - v.x) / s; cam.right = v.x + (base.right - v.x) / s;
  cam.top = v.y + (base.top - v.y) / s; cam.bottom = v.y + (base.bottom - v.y) / s;
  cam.updateProjectionMatrix();
}

// ---------- pintar a pedido (puntero, arrastre): un cuadro por evento, nunca un bucle ----------
const pedidos = new Set(); let rafP = 0;
export function pedir(f) {
  pedidos.add(f);
  if (!rafP) rafP = requestAnimationFrame(() => { rafP = 0; for (const g of pedidos) if (!vivas.has(g) && g.vista) pintar(g); pedidos.clear(); });
}
export const corriendo = f => vivas.has(f);
export const rendererDe = () => R;
