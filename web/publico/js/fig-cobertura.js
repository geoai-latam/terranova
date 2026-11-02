// «Del barrio al país»: la cobertura del SINIC con el lenguaje de su primera versión (29-10-2026),
// que era la buena. Columnas hexagonales con la muestra del 3 % de predios del SINIC sobre las celdas
// de tierra de Colombia (datos/co.json): altura y color siguen la raíz del conteo; las celdas planas
// son tierra sin predios en la muestra. Plano cerrado y fijo sobre los Andes (el país se sale del
// cuadro), sombreado plano horneado en los vértices, sin sombras ni rótulos. Al entrar, las columnas
// suben desde la celda de Santa Marta (el punto del héroe) hacia afuera; después gira sola, despacio,
// solo mientras se ve, sin movimiento reducido y en pausa mientras alguien arrastra o señala una
// columna. Al pasar el puntero, la columna se pinta de ámbar y da su conteo.
import { getT, registrar, solo, quieto, pedir, corriendo } from './motor3d.js?v=0cb2e43b98';

export async function montar(fig) {
  const T = getT();
  const D = await fetch('/datos/co.json').then(r => r.json());
  const escena = new T.Scene(), cam = new T.OrthographicCamera(-1, 1, 1, -1, 1, 6000);

  const K = 40, CX = -73.6, CY = 4.3, r = D.R * K * 0.9;
  const X = lon => (lon - CX) * K, Z = lat => -(lat - CY) * K;
  const max = Math.max(...D.bins.map(b => b[2]));
  // un hexágono con su luz horneada: techo claro, caras según el sol, base oscura
  const hex = new T.CylinderGeometry(r, r, 1, 6); hex.translate(0, 0.5, 0);
  const hg = hex.toNonIndexed(); hg.computeVertexNormals();
  const n = hg.attributes.normal, sh = new Float32Array(n.count * 3), sol = new T.Vector3(-0.5, 0, -0.85).normalize();
  for (let v = 0; v < n.count; v++) {
    const ny = n.getY(v);
    const k = ny > 0.5 ? 1 : ny < -0.5 ? 0.6 : 0.74 + 0.2 * Math.max(0, n.getX(v) * sol.x + n.getZ(v) * sol.z);
    sh[v * 3] = sh[v * 3 + 1] = sh[v * 3 + 2] = k;
  }
  hg.setAttribute('color', new T.BufferAttribute(sh, 3));
  const mt = new T.MeshBasicMaterial({ vertexColors: true });
  const tierra = new T.InstancedMesh(hg, mt, D.land.length), cols = new T.InstancedMesh(hg, mt.clone(), D.bins.length);
  const o = new T.Object3D();
  D.land.forEach((p, i) => { o.position.set(X(p[0]), 0, Z(p[1])); o.scale.set(1, 0.6, 1); o.updateMatrix(); tierra.setMatrixAt(i, o.matrix); });
  escena.add(tierra, cols);
  const cT = new T.Color('#D6DCD3'), L0 = new T.Color('#9CCFC3'), L1 = new T.Color('#1A5A4E'), cA = new T.Color('#E0A13A');
  const tono = i => L0.clone().lerp(L1, Math.sqrt(D.bins[i][2] / max));
  for (let i = 0; i < D.land.length; i++) tierra.setColorAt(i, cT);
  D.bins.forEach((_, i) => cols.setColorAt(i, tono(i)));
  const alto = D.bins.map(b => 0.6 + Math.sqrt(b[2] / max) * 90);

  // la onda de entrada sale de la celda de Santa Marta (el punto del héroe)
  const LON0 = -74.1572, LAT0 = 11.2211;
  const iSM = D.bins.reduce((a, b, i) => ((b[0] - LON0) ** 2 + (b[1] - LAT0) ** 2 < (D.bins[a][0] - LON0) ** 2 + (D.bins[a][1] - LAT0) ** 2 ? i : a), 0);
  const ori = new T.Vector2(X(D.bins[iSM][0]), Z(D.bins[iSM][1]));
  const espera = D.bins.map(b => new T.Vector2(X(b[0]), Z(b[1])).distanceTo(ori) * 2.4);
  const SUBE = 900, ENTRA = Math.max(...espera) + SUBE;
  const sube = k => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);
  let ultimoT = -1;
  function colocar(ms) {
    if (ms === ultimoT) return; ultimoT = ms;
    D.bins.forEach((b, i) => {
      o.position.set(X(b[0]), 0, Z(b[1]));
      o.scale.set(1, 0.6 + (alto[i] - 0.6) * sube((ms - espera[i]) / SUBE), 1);
      o.updateMatrix(); cols.setMatrixAt(i, o.matrix);
    });
    cols.instanceMatrix.needsUpdate = true;
  }

  // el plano: cerrado y fijo, como el de la primera versión (330 de alto; 440 en móvil: el país se sale del cuadro)
  const st = { az: 0.2, pol: 0.82 };
  let W = 0, Hh = 0;
  function tam(w, h) { W = w; Hh = h; }
  function toma() {
    const Hm = W < 520 ? 440 : 330, Wm = Hm * W / Math.max(1, Hh);
    cam.left = -Wm / 2; cam.right = Wm / 2; cam.top = Hm * 0.66; cam.bottom = -Hm * 0.34; cam.updateProjectionMatrix();
    const R = 2000;
    cam.position.set(R * Math.sin(st.pol) * Math.sin(st.az), R * Math.cos(st.pol), R * Math.sin(st.pol) * Math.cos(st.az));
    cam.lookAt(0, 0, 0); cam.updateMatrixWorld();
  }
  function pose(t) { colocar(quieto ? 1e9 : t); toma(); }

  const lienzo = fig.querySelector('canvas'), control = fig.querySelector('.lienzo');
  const f = registrar({ nombre: 'cobertura', caja: fig, lienzo, control, escena, cam, dur: ENTRA, n: 1, tInicial: 0, pose, tam });
  f.tocar = null; // tocar no repite: el gesto de esta figura es girar y señalar
  solo(f, { entrada: 1, cada: 1e9 });
  f.tocar = null;

  // señalar una columna
  const lectura = fig.querySelector('[data-lectura]'), base = lectura.textContent;
  const fmt = new Intl.NumberFormat('es-CO'), f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const coord = (val, p, q) => f2.format(Math.abs(val)) + ' ' + (val >= 0 ? p : q);
  const ray = new T.Raycaster(), m = new T.Vector2();
  let sel = -1;
  const elegir = i => {
    if (i === sel) return;
    if (sel >= 0) cols.setColorAt(sel, tono(sel));
    if (i >= 0) cols.setColorAt(i, cA);
    cols.instanceColor.needsUpdate = true; sel = i;
    lectura.textContent = i < 0 ? base : `${fmt.format(D.bins[i][2])} predios de la muestra en la celda de ${coord(D.bins[i][1], 'N', 'S')}, ${coord(D.bins[i][0], 'E', 'W')}`;
    pedir(f);
  };
  // girar: arrastre (en táctil solo horizontal, para no robar el scroll) y flechas
  let x0 = 0, y0 = 0, activo = false, pausa = 0;
  const parar = () => { pausa = performance.now() + 3500; };
  control.addEventListener('pointerdown', e => { activo = true; parar(); x0 = e.clientX; y0 = e.clientY; if (e.pointerType === 'mouse') control.setPointerCapture(e.pointerId); });
  control.addEventListener('pointermove', e => {
    if (activo && !corriendo(f)) {
      st.az -= (e.clientX - x0) * 0.006;
      if (e.pointerType === 'mouse') st.pol = Math.min(1.15, Math.max(0.25, st.pol - (e.clientY - y0) * 0.004));
      x0 = e.clientX; y0 = e.clientY; parar(); pedir(f); return;
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
    e.preventDefault(); e.stopImmediatePropagation(); parar();
    if (d) st.az += d; if (p) st.pol = Math.min(1.15, Math.max(0.25, st.pol + p));
    pedir(f);
  }, true);

  // giro solo: un cuadro cada ~33 ms con pedir(), nunca mientras corre la entrada
  const VEL = 0.00006; let girando = false, ultimoG = 0;
  function giro(now) {
    girando = false;
    if (quieto || !f.vista || document.hidden) { ultimoG = 0; return; }
    if (!corriendo(f) && !activo && sel < 0 && now > pausa) {
      if (now - ultimoG >= 32) { st.az += (ultimoG ? Math.min(80, now - ultimoG) : 0) * VEL; ultimoG = now; pedir(f); }
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
