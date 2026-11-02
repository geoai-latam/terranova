// «Dónde hay predio SINIC hoy» (vuelve, en el renderer compartido). Columnas hexagonales con la
// muestra del 3 % de predios del SINIC sobre las celdas de tierra de Colombia (datos/co.json). Altura
// y color siguen la raíz del conteo; las celdas planas son tierra sin predios en la muestra. Al entrar,
// las columnas suben desde Bogotá hacia afuera y la cámara baja de un plano cerrado y alto sobre los
// Andes al plano del país. Al pasar el puntero, la columna se pinta de ámbar y da su conteo. Después
// de la entrada gira sola, despacio (una vuelta en unos 80 s), solo mientras se ve, sin movimiento
// reducido y sin nadie arrastrando ni señalando una columna; tras un gesto espera unos segundos.
import {
  getT, C, ambiente, papelDe, encuadrar, aPantalla, registrar, solo, quieto,
  contactoMat, mapaContacto, calco, ajustarSombra, mapaSombra, marco, plano, resorte, pedir, corriendo,
  anillo, bloques, lineas, contorno, prisma, mats, tramo,
} from './motor3d.js?v=0cb2e43b98';
import { ambarLibre } from './ambar.js?v=420978c8f1';

const LUGARES = [
  ['Bogotá', -74.08, 4.61], ['Medellín', -75.57, 6.25], ['Cali', -76.53, 3.45],
  ['Barranquilla', -74.80, 10.96], ['Cartagena', -75.51, 10.39], ['Santa Marta', -74.20, 11.24],
  ['Bucaramanga', -73.12, 7.12], ['Cúcuta', -72.50, 7.89], ['Pereira', -75.69, 4.81],
  ['Villavicencio', -73.63, 4.14], ['Montería', -75.88, 8.75],
  ['Mar Caribe', -76.9, 12.0, 'm'], ['Océano Pacífico', -79.0, 4.6, 'm'],
];

export async function montar(fig) {
  const T = getT();
  const [D, SM] = await Promise.all([fetch('/datos/co.json').then(r => r.json()), fetch('/datos/sm.json').then(r => r.json())]);
  const escena = new T.Scene(), cam = new T.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  const luz = ambiente(escena, { lado: 300, papel: papelDe(fig), reticula: false, sol: [-0.55, 0.85, 0.35] });

  const K = 40, CX = -74.6, CY = 6.4, r = D.R * K * 0.8; // hueco del 20 %: cada celda se lee como hexágono
  const X = lon => (lon - CX) * K, Z = lat => -(lat - CY) * K;
  const max = Math.max(...D.bins.map(b => b[2]));
  const hex = new T.CylinderGeometry(r, r, 1, 6); hex.translate(0, 0.5, 0);
  const mTierra = new T.MeshLambertMaterial({ flatShading: true });
  // contacto en el pie de las columnas, sobre la tierra (radio en metros de la maqueta, solo luz del cielo)
  const mCols = contactoMat(new T.MeshLambertMaterial({ flatShading: true }), { suelo: 0.6, rad: 3.2, min: 0.55 });
  const tierra = new T.InstancedMesh(hex, mTierra, D.land.length), cols = new T.InstancedMesh(hex, mCols, D.bins.length);
  tierra.receiveShadow = true; cols.castShadow = cols.receiveShadow = true;
  const o = new T.Object3D();
  D.land.forEach((p, i) => { o.position.set(X(p[0]), 0, Z(p[1])); o.scale.set(1, 0.6, 1); o.updateMatrix(); tierra.setMatrixAt(i, o.matrix); });
  const alto = D.bins.map(b => 0.6 + Math.sqrt(b[2] / max) * 60);
  // La entrada empieza donde termina el héroe: el punto de Santa Marta y sus linderos reales, a su
  // escala verdadera sobre la columna de su celda. La cámara sube (el barrio cabe en una celda de
  // ~8 km de radio) y se abre al país; la onda de columnas sale de esa celda.
  const LON0 = -74.1572, LAT0 = 11.2211;
  const ex = K / (111320 * Math.cos(LAT0 * Math.PI / 180)), ey = K / 110574;
  const X0 = X(LON0), Z0 = Z(LAT0);
  const iSM = D.bins.reduce((a, b, i) => ((b[0] - LON0) ** 2 + (b[1] - LAT0) ** 2 < (D.bins[a][0] - LON0) ** 2 + (D.bins[a][1] - LAT0) ** 2 ? i : a), 0);
  const barrio = new T.Group(); escena.add(barrio);
  const plano2 = SM.polys.map(f => anillo(f).map(q => new T.Vector2(X0 + q.x * ex, -Z0 + q.y * ey)));
  const hB = 7 * ey;
  const bq = bloques(plano2.filter((_, i) => i !== SM.obj), hB, { filo: 0 }); bq.children[0].castShadow = false; barrio.add(bq);
  const segB = []; plano2.forEach(p => segB.push(...contorno(p, hB * 1.02))); barrio.add(lineas(segB, C.tinta, 0.3));
  const mP = mats(C.ambar, C.ambarLado), predSM = prisma(plano2[SM.obj], mP); predSM.scale.y = hB * 2.2; predSM.castShadow = false; barrio.add(predSM);
  // el contorno de la celda de Santa Marta, en tinta, mientras la cámara sube
  const bSM = D.bins[iSM], celda = [];
  for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3, b = (k + 1) * Math.PI / 3; celda.push(X(bSM[0]) + r * Math.sin(a), 0, Z(bSM[1]) + r * Math.cos(a), X(bSM[0]) + r * Math.sin(b), 0, Z(bSM[1]) + r * Math.cos(b)); }
  const lCelda = lineas(celda, C.tinta, 0.9); escena.add(lCelda);
  const ori = new T.Vector2(X(bSM[0]), Z(bSM[1]));
  const espera0 = 2500;
  const espera = D.bins.map(b => espera0 + new T.Vector2(X(b[0]), Z(b[1])).distanceTo(ori) * 3.2);
  const SUBE = 900, ENTRA = Math.max(...espera) + SUBE;
  const sube = k => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);
  let ultimoT = -1, colSM = null;
  function colocar(ms) {
    if (ms === ultimoT) return; ultimoT = ms;
    D.bins.forEach((b, i) => {
      o.position.set(X(b[0]), 0, Z(b[1]));
      o.scale.set(1, 0.6 + (alto[i] - 0.6) * sube((ms - espera[i]) / SUBE), 1);
      o.updateMatrix(); cols.setMatrixAt(i, o.matrix);
    });
    cols.instanceMatrix.needsUpdate = true;
    // la celda de Santa Marta es papel mientras el barrio está encima; toma su tono cuando sube
    const llego = ms >= espera[iSM];
    if (llego !== colSM) { colSM = llego; cols.setColorAt(iSM, llego ? tono(iSM) : cT); if (cols.instanceColor) cols.instanceColor.needsUpdate = true; }
  }
  escena.add(tierra, cols);
  const cT = new T.Color('#E4E9E2'), L0 = new T.Color('#A6D8CC'), L1 = new T.Color('#14564A'), cA = new T.Color(C.ambar);
  const tono = i => L0.clone().lerp(L1, Math.sqrt(D.bins[i][2] / max));
  for (let i = 0; i < D.land.length; i++) tierra.setColorAt(i, cT);
  D.bins.forEach((_, i) => cols.setColorAt(i, tono(i)));
  // el país se apoya en el papel: un calco de contacto con la silueta de la tierra
  const xs = D.land.map(p => X(p[0])), zs = D.land.map(p => Z(p[1]));
  const rect = [Math.min(...xs) - 12, Math.max(...xs) + 12, -Math.max(...zs) - 12, -Math.min(...zs) + 12];
  const hexPts = (x, y) => Array.from({ length: 6 }, (_, k) => new T.Vector2(x + r * 1.25 * Math.sin(k * Math.PI / 3), y + r * 1.25 * Math.cos(k * Math.PI / 3)));
  escena.add(calco(mapaContacto(D.land.map(p => hexPts(X(p[0]), -Z(p[1]))), rect, { res: 1024, rad: 5, fuerza: 1, invertir: true }), rect, -0.02, 0.18));

  // encuadre: la tierra y las columnas más altas
  const caja3 = [];
  for (const x of [Math.min(...xs), Math.max(...xs)]) for (const z of [Math.min(...zs), Math.max(...zs)]) caja3.push(new T.Vector3(x, 0, z));
  D.land.forEach((p, i) => { if (i % 40 === 0) caja3.push(new T.Vector3(X(p[0]), 0, Z(p[1]))); });
  D.bins.forEach((b, i) => { if (alto[i] > 24) caja3.push(new T.Vector3(X(b[0]), alto[i], Z(b[1]))); });
  ajustarSombra(luz, caja3.concat([new T.Vector3(0, 62, 0)]), { mapa: mapaSombra(true) });
  // el encuadre gira con el mapa: un cilindro alrededor del centro del país, así la escala no cambia
  // con el azimut (el giro solo no acerca ni aleja)
  const cx0 = (Math.min(...xs) + Math.max(...xs)) / 2, cz0 = (Math.min(...zs) + Math.max(...zs)) / 2;
  const radio = Math.max(...D.land.map(p => Math.hypot(X(p[0]) - cx0, Z(p[1]) - cz0))) * 0.9;
  const envol = [];
  for (let k = 0; k < 32; k++) {
    const a = k * Math.PI / 16;
    envol.push(new T.Vector3(cx0 + radio * Math.cos(a), 0, cz0 + radio * Math.sin(a)), new T.Vector3(cx0 + radio * 0.45 * Math.cos(a), 50, cz0 + radio * 0.45 * Math.sin(a)));
  }
  const mira0 = new T.Vector3(cx0, 10, cz0);
  const st = { az: 0.2, pol: 0.82 };
  const TE = { quieto: 700, celda: 2400 };
  const lienzo = fig.querySelector('canvas'), control = fig.querySelector('.lienzo');
  const foco = new T.Vector3(X0, 0.6, Z0);
  let W = 0, Hh = 0, ultimaToma = '';
  function tam(w, h) { W = w; Hh = h; ultimaToma = ''; }
  // plano con autor: entra alto y cerrado sobre Bogotá (de donde sale la onda) y baja al plano oblicuo
  // del país a medida que la onda llega a las costas; después, el plano es del lector (arrastrar).
  // la escala de la cámara, en logaritmo: del barrio (~0,9 km de ancho) a la celda y de la celda al país
  let sBarrio = 1, sCelda = 1, pxBarrio = 1e9;
  function toma(t) {
    const k = quieto ? 1 : resorte(t, TE.celda - 400, ENTRA - TE.celda + 400, 0.9);
    const az = st.az + 0.35 * (1 - k), pol = 0.5 + (st.pol - 0.5) * k;
    const clave = `${az.toFixed(4)}|${pol.toFixed(4)}|${t.toFixed(0)}|${W}|${Hh}`;
    if (clave === ultimaToma) return; ultimaToma = clave;
    encuadrar(cam, { az, pol, mira: mira0, puntos: envol, w: W, h: Hh, margen: [4, 4, 8, 4] });
    const ancho = cam.right - cam.left;
    sBarrio = ancho / (950 * ex); sCelda = ancho / (r * 5.2);
    const a = Math.log(sBarrio), b = Math.log(sCelda);
    const u = quieto ? 1 : tramo(t, TE.quieto, TE.celda - TE.quieto);
    const ls = t < TE.celda || quieto ? a + (b - a) * u : b * (1 - k);
    const s = Math.exp(quieto ? 0 : ls);
    // el barrio empieza en el centro del cuadro y viaja a su sitio en el país mientras la cámara sube
    const base = marco(cam), w = quieto ? 0 : 1 - k;
    if (w > 0) {
      const v = foco.clone().applyMatrix4(cam.matrixWorldInverse);
      const dx = (v.x - (base.left + base.right) / 2) * w, dy = (v.y - (base.top + base.bottom) / 2) * w;
      base.left += dx; base.right += dx; base.top += dy; base.bottom += dy;
    }
    plano(cam, base, s, foco);
    pxBarrio = 950 * ex * s / ancho * W; // ancho del barrio en pantalla: por debajo de ~28 px se va
  }

  // rótulos: ciudades y mares (sin versalitas), anclados a su coordenada; y el dato de la columna
  const capa = fig.querySelector('.f3-rot');
  const rot = LUGARES.map(([n, lon, lat, k]) => {
    const e = document.createElement('span'); e.className = k === 'm' ? 'f3-mar' : 'f3-ciudad'; e.textContent = n; capa.append(e);
    return { e, x: X(lon), z: Z(lat), menor: k === 'm' || ['Pereira', 'Villavicencio', 'Montería', 'Cúcuta', 'Santa Marta'].includes(n) };
  });
  const dato = document.createElement('span'); dato.className = 'f3-dato-col'; dato.hidden = true; capa.append(dato);
  const lectura = fig.querySelector('[data-lectura]'), base = lectura.textContent;
  const fmt = new Intl.NumberFormat('es-CO'), f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const coord = (val, p, n) => f2.format(Math.abs(val)) + ' ' + (val >= 0 ? p : n);
  let sel = -1;
  const rB = document.createElement('span'); rB.className = 'f3-dato cob-b'; rB.innerHTML = '<b>el punto del héroe</b> Santa Marta, 11,2211 N, 74,1572 W'; capa.append(rB);
  const rC = document.createElement('span'); rC.className = 'f3-dato cob-b'; rC.innerHTML = `<b>la celda de Santa Marta</b> ~8 km de radio · ${fmt.format(D.bins[iSM][2])} predios en la muestra`; capa.append(rC);
  function despues(w, h) {
    const tt = quieto ? 1e9 : f.t;
    const [bx, by] = aPantalla(cam, X0, barrio.position.y, Z0, w, h);
    rB.style.transform = `translate(${bx.toFixed(1)}px, ${(by + 30).toFixed(1)}px) translate(-50%, 0)`; rB.style.opacity = tt < TE.quieto + 500 ? 1 : 0;
    const [cx, cy] = aPantalla(cam, X(bSM[0]), barrio.position.y, Z(bSM[1]) + r, w, h);
    rC.style.transform = `translate(${cx.toFixed(1)}px, ${(cy + 14).toFixed(1)}px) translate(-50%, 0)`; rC.style.opacity = tt > TE.celda - 600 && tt < espera0 + 600 ? 1 : 0;
    const op = quieto ? 1 : Math.min(1, Math.max(0, (f.t - ENTRA * 0.55) / 500));
    for (const q of rot) {
      const [x, y] = aPantalla(cam, q.x, 2, q.z, w, h);
      const fuera = x < 30 || x > w - 30 || y < 14 || y > h - 14 || (w < 520 && q.menor);
      q.e.style.display = fuera ? 'none' : '';
      q.e.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      q.e.style.opacity = op;
    }
    if (sel >= 0) {
      const b = D.bins[sel], [x, y] = aPantalla(cam, X(b[0]), alto[sel] + 2, Z(b[1]), w, h);
      dato.style.transform = `translate(${x.toFixed(1)}px, ${(y - 6).toFixed(1)}px) translate(-50%, -100%)`;
    }
  }
  let ambSM = null;
  function pose(t) {
    colocar(quieto ? 1e9 : t); toma(t);
    // el barrio viaja sobre su columna; el predio del héroe va en ámbar al entrar
    o.position.set(0, 0, 0);
    const hc = 0.6 + (alto[iSM] - 0.6) * sube(((quieto ? 1e9 : t) - espera[iSM]) / SUBE);
    barrio.position.y = hc; barrio.visible = !quieto && t < ENTRA * 0.8 && pxBarrio > 28;
    if (t < 50) ambSM = null; else if (ambSM === null) ambSM = ambarLibre();
    mP[0].color.set(ambSM === false ? C.techo : C.ambar); mP[1].color.set(ambSM === false ? C.lado : C.ambarLado);
    lCelda.visible = !quieto && t > TE.quieto && t < espera0 + 400; lCelda.position.y = hc + 0.05;
    lCelda.material.opacity = 0.9; lCelda.material.transparent = true;
  }

  const f = registrar({ nombre: 'cobertura', caja: fig, lienzo, control, escena, cam, dur: ENTRA, n: 1, tInicial: 0, pose, tam, despues });
  f.tocar = null; // tocar no repite: el gesto de esta figura es girar y señalar
  solo(f, { entrada: 1, cada: 1e9 });
  f.tocar = null;

  // señalar una columna
  const ray = new T.Raycaster(), m = new T.Vector2();
  const elegir = i => {
    if (i === sel) return;
    if (sel >= 0) cols.setColorAt(sel, tono(sel));
    if (i >= 0) cols.setColorAt(i, cA);
    cols.instanceColor.needsUpdate = true; sel = i;
    if (i < 0) { dato.hidden = true; lectura.textContent = base; }
    else {
      const b = D.bins[i];
      dato.hidden = false; dato.innerHTML = '<b>' + fmt.format(b[2]) + '</b> predios';
      lectura.textContent = `${fmt.format(b[2])} predios en la celda de ${coord(b[1], 'N', 'S')}, ${coord(b[0], 'E', 'W')}`;
    }
    pedir(f);
  };
  // girar: arrastre (en táctil solo horizontal, para no robar el scroll) y flechas
  let x0 = 0, y0 = 0, activo = false, movio = false;
  control.addEventListener('pointerdown', e => { activo = true; movio = false; x0 = e.clientX; y0 = e.clientY; if (e.pointerType === 'mouse') control.setPointerCapture(e.pointerId); });
  control.addEventListener('pointermove', e => {
    if (activo && !corriendo(f)) {
      const dx = e.clientX - x0, dy = e.clientY - y0;
      if (Math.abs(dx) + Math.abs(dy) > 2) movio = true;
      st.az -= dx * 0.006;
      if (e.pointerType === 'mouse') st.pol = Math.min(1.15, Math.max(0.3, st.pol - dy * 0.004));
      x0 = e.clientX; y0 = e.clientY; pedir(f); return;
    }
    if (e.pointerType !== 'mouse' || corriendo(f)) return;
    const rc = lienzo.getBoundingClientRect();
    m.set((e.clientX - rc.left) / rc.width * 2 - 1, -(e.clientY - rc.top) / rc.height * 2 + 1);
    ray.setFromCamera(m, cam);
    const hit = ray.intersectObject(cols)[0];
    elegir(hit ? hit.instanceId : -1);
  });
  const fin = () => { activo = false; };
  control.addEventListener('pointerup', fin); control.addEventListener('pointercancel', fin);
  control.addEventListener('pointerleave', () => { fin(); elegir(-1); });
  control.addEventListener('keydown', e => {
    const d = { ArrowLeft: 0.12, ArrowRight: -0.12 }[e.key], p = { ArrowUp: -0.08, ArrowDown: 0.08 }[e.key];
    if (d === undefined && p === undefined) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (d) st.az += d; if (p) st.pol = Math.min(1.15, Math.max(0.3, st.pol + p));
    pedir(f);
  }, true);
  void movio;

  // giro solo: un cuadro cada ~33 ms con pedir(), nunca mientras corre la entrada
  const VEL = 0.000078; let girando = false, ultimoG = 0, pausa = 0;
  const parar = () => { pausa = performance.now() + 4000; };
  control.addEventListener('pointerdown', parar); control.addEventListener('keydown', parar);
  function giro(now) {
    girando = false;
    if (quieto || !f.vista || document.hidden) { ultimoG = 0; return; }
    if (!corriendo(f) && !activo && sel < 0 && now > pausa) {
      if (now - ultimoG >= 32) { st.az -= (ultimoG ? Math.min(80, now - ultimoG) : 0) * VEL; ultimoG = now; pedir(f); }
    } else ultimoG = 0;
    girando = true; requestAnimationFrame(giro);
  }
  const arrancarGiro = () => { if (!girando && !quieto) { girando = true; requestAnimationFrame(giro); } };
  const alVer0 = f.alVer;
  f.alVer = a => { alVer0(a); if (f.vista) arrancarGiro(); };
  document.addEventListener('visibilitychange', () => { if (!document.hidden && f.vista) arrancarGiro(); });
  if (f.vista) arrancarGiro();
  return f;
}
