// «Del barrio al país»: la cobertura del SINIC con el lenguaje de su primera versión (29-10-2026),
// que era la buena. Columnas hexagonales con la muestra del 3 % de predios del SINIC sobre las celdas
// de tierra de Colombia (datos/co.json): altura y color siguen la raíz del conteo; las celdas planas
// son tierra sin predios en la muestra. Plano cerrado y fijo sobre los Andes (el país se sale del
// cuadro), sombreado plano horneado en los vértices, sin sombras; con los rótulos de las ciudades grandes y los mares. Al entrar, las columnas
// suben desde la celda de Santa Marta (el punto del héroe) hacia afuera, después de verla de cerca con
// sus terrenos reales del SINIC (datos/ciudad-sm.bin, un punto cada uno; lo prepara web/ciudad_datos.py); después gira sola en vaivén, con el norte arriba,
// solo mientras se ve, sin movimiento reducido y en pausa mientras alguien arrastra o señala una
// columna. Al pasar el puntero, la columna se pinta de ámbar y da su conteo.
import { getT, aPantalla, registrar, solo, quieto, pedir, corriendo } from './motor3d.js?v=0cb2e43b98';

// los rótulos: las ciudades grandes y los dos mares (las menores se callan en móvil)
const LUGARES = [
  ['Bogotá', -74.08, 4.61], ['Medellín', -75.57, 6.25], ['Cali', -76.53, 3.45],
  ['Barranquilla', -74.80, 10.96], ['Cartagena', -75.51, 10.39], ['Santa Marta', -74.20, 11.24],
  ['Bucaramanga', -73.12, 7.12], ['Cúcuta', -72.50, 7.89], ['Pereira', -75.69, 4.81],
  ['Villavicencio', -73.63, 4.14], ['Montería', -75.88, 8.75],
  ['Mar Caribe', -76.9, 12.0, 'm'], ['Océano Pacífico', -79.0, 4.6, 'm'],
];
const MENORES = ['Cartagena', 'Pereira', 'Villavicencio', 'Montería', 'Cúcuta', 'Santa Marta'];

export async function montar(fig) {
  const T = getT();
  const [D, bin] = await Promise.all([fetch('/datos/co.json').then(r => r.json()), fetch('/datos/ciudad-sm.bin').then(r => r.arrayBuffer())]);
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
  const SUBE = 900, ONDA = Math.max(...espera) + SUBE;
  const sube = k => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);
  const suave = k => { k = Math.min(1, Math.max(0, k)); return k * k * (3 - 2 * k); };

  // la ciudad real: un punto por terreno del SINIC dentro del hexágono de Santa Marta (datos/ciudad-sm.bin)
  const cab = new Float32Array(bin, 0, 4), q = new Uint16Array(bin, 16, cab[3] * 2), rC = cab[2];
  const pos = new Float32Array(cab[3] * 3);
  for (let k = 0; k < cab[3]; k++) {
    pos[k * 3] = X(cab[0] + (q[k * 2] / 65535 * 2 - 1) * rC); pos[k * 3 + 1] = 0.62; pos[k * 3 + 2] = Z(cab[1] + (q[k * 2 + 1] / 65535 * 2 - 1) * rC);
  }
  const gp = new T.BufferGeometry(); gp.setAttribute('position', new T.BufferAttribute(pos, 3));
  const mp = new T.PointsMaterial({ color: '#1A5A4E', size: 1.6 * Math.min(2, window.devicePixelRatio || 1), sizeAttenuation: false, transparent: true, depthWrite: false });
  const ciudad = new T.Points(gp, mp); escena.add(ciudad);

  // la entrada: la ciudad llena su celda (CERCA), la cámara se aleja (LEJOS) mientras la ciudad se vuelve
  // su columna, y la onda sale de ahí hacia el país
  const CERCA = 1500, LEJOS = 2800, TW = CERCA + 700, ENTRA = TW + ONDA;
  const iSMc = new T.Color();
  let ultimoT = -1;
  function colocar(ms, hm) {
    if (ms === ultimoT) return; ultimoT = ms;
    const tw = ms - TW;
    D.bins.forEach((b, i) => {
      o.position.set(X(b[0]), 0, Z(b[1]));
      // la de Santa Marta sube con el alejamiento: nunca más de un quinto del cuadro
      const h = i === iSM ? Math.min(0.6 + (alto[i] - 0.6) * sube(tw / (SUBE * 2)), Math.max(0.6, hm * 0.22)) : 0.6 + (alto[i] - 0.6) * sube((tw - espera[i]) / SUBE);
      o.scale.set(1, h, 1);
      o.updateMatrix(); cols.setMatrixAt(i, o.matrix);
    });
    cols.instanceMatrix.needsUpdate = true;
    // mientras se ve la ciudad, su celda es tierra; después toma su tono
    const e = suave((ms - CERCA) / (LEJOS * 0.5));
    if (sel !== iSM) { cols.setColorAt(iSM, iSMc.copy(cT).lerp(tono(iSM), e)); cols.instanceColor.needsUpdate = true; }
    mp.opacity = Math.min(1, ms / 350) * (1 - suave((ms - CERCA - 200) / 900));
    ciudad.visible = mp.opacity > 0.01;
  }

  // el plano: cerrado y fijo, como el de la primera versión (330 de alto; 440 en móvil: el país se sale del cuadro)
  // de cerca, la celda de Santa Marta llena el cuadro; el alejamiento es exponencial y lleva a Santa Marta
  // de su centro a su sitio en el plano final, sin derivas
  const st = { az: 0.2, pol: 0.82 };
  const SMx = X(D.bins[iSM][0]), SMz = Z(D.bins[iSM][1]), HC = r * 1.9, POLC = 0.5;
  let W = 0, Hh = 0;
  function tam(w, h) { W = w; Hh = h; }
  const lejos = t => (quieto ? 1 : suave((t - CERCA) / LEJOS));
  const altoCuadro = t => { const HF = W < 520 ? 440 : 330; return HC * Math.pow(HF / HC, lejos(t)); };
  function toma(t) {
    const HF = W < 520 ? 440 : 330, e = lejos(t), Hm = altoCuadro(t), Wm = Hm * W / Math.max(1, Hh);
    const arriba = 0.5 + 0.16 * e;
    cam.left = -Wm / 2; cam.right = Wm / 2; cam.top = Hm * arriba; cam.bottom = -Hm * (1 - arriba); cam.updateProjectionMatrix();
    const k = Math.pow(e, 3) * Hm / HF, tx = SMx - SMx * k, tz = SMz - SMz * k, pol = POLC + (st.pol - POLC) * e;
    const R = 2000;
    cam.position.set(tx + R * Math.sin(pol) * Math.sin(st.az), R * Math.cos(pol), tz + R * Math.sin(pol) * Math.cos(st.az));
    cam.lookAt(tx, 0, tz); cam.updateMatrixWorld();
  }
  function pose(t) { const tt = quieto ? 1e9 : t; colocar(tt, altoCuadro(tt)); toma(tt); }

  let sel = -1;
  { const l = fig.querySelector('[data-lectura]'); l.dataset.base = l.textContent; }
  const lienzo = fig.querySelector('canvas'), control = fig.querySelector('.lienzo');
  const capa = fig.querySelector('.f3-rot');
  const rot = LUGARES.map(([nm, lon, lat, k]) => {
    const e = document.createElement('span'); e.className = k === 'm' ? 'f3-mar' : 'f3-ciudad'; e.textContent = nm; capa.append(e);
    return { e, x: X(lon), z: Z(lat), menor: k === 'm' || MENORES.includes(nm) };
  });
  const lecturaC = fig.querySelector('[data-lectura]'), fmtC = new Intl.NumberFormat('es-CO');
  let enCiudad = null;
  function despues(w, h) {
    const c = !quieto && f.t < CERCA + 600;
    if (c !== enCiudad && sel < 0) { enCiudad = c; lecturaC.textContent = c ? `Santa Marta: ${fmtC.format(cab[3])} terrenos del SINIC en su celda, un punto cada uno` : lecturaC.dataset.base; }
    // aparecen cuando la onda ya pasó por más de la mitad del país
    const op = quieto ? 1 : Math.min(1, Math.max(0, (f.t - TW - ONDA * 0.55) / 500));
    for (const q of rot) {
      const [x, y] = aPantalla(cam, q.x, 2, q.z, w, h);
      const fuera = x < 30 || x > w - 30 || y < 14 || y > h - 14 || (w < 520 && q.menor);
      q.e.style.display = fuera ? 'none' : '';
      q.e.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      q.e.style.opacity = op;
    }
  }
  const f = registrar({ nombre: 'cobertura', caja: fig, lienzo, control, escena, cam, dur: ENTRA, n: 1, tInicial: 0, pose, tam, despues });
  f.tocar = null; // tocar no repite: el gesto de esta figura es girar y señalar
  solo(f, { entrada: 1, cada: 1e9 });
  f.tocar = null;

  // señalar una columna
  const lectura = fig.querySelector('[data-lectura]'), base = lectura.dataset.base;
  const fmt = new Intl.NumberFormat('es-CO'), f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const coord = (val, p, q) => f2.format(Math.abs(val)) + ' ' + (val >= 0 ? p : q);
  const ray = new T.Raycaster(), m = new T.Vector2();
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

  // giro solo, en vaivén: el norte siempre arriba (±0,45 rad alrededor del plano de partida, una vuelta
  // de ida y regreso cada ~40 s); tras un arrastre vuelve suave al vaivén. Un cuadro cada ~33 ms con
  // pedir(), nunca mientras corre la entrada.
  const AZ0 = st.az, AMP = 0.45, W_OSC = (2 * Math.PI) / 40000; let fase = 0, girando = false, ultimoG = 0;
  function giro(now) {
    girando = false;
    if (quieto || !f.vista || document.hidden) { ultimoG = 0; return; }
    if (!corriendo(f) && !activo && sel < 0 && now > pausa) {
      if (now - ultimoG >= 32) {
        const dt = ultimoG ? Math.min(80, now - ultimoG) : 0;
        fase += dt * W_OSC;
        const meta = AZ0 + AMP * Math.sin(fase);
        st.az += (meta - st.az) * Math.min(1, dt / 900);
        ultimoG = now; pedir(f);
      }
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
