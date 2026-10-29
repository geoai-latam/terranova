// Cobertura: columnas hexagonales con la muestra del 3 % de predios del SINIC sobre Colombia.
// Altura y color siguen la raíz del conteo; las celdas planas son tierra sin predios en la muestra.
import { cargarThree, orbita, quieto, visible } from './comun3d.js';

const esc = document.querySelector('[data-escena="cobertura"]');
if (esc) {
  // Se carga solo cuando se acerca a la vista: el héroe va primero.
  const io = new IntersectionObserver(es => {
    if (es.some(e => e.isIntersecting)) { io.disconnect(); iniciar(esc).catch(err => console.warn('escena de cobertura:', err)); }
  }, { rootMargin: '400px' });
  io.observe(esc);
}

async function iniciar(esc) {
  const [THREE, D] = await Promise.all([cargarThree(), fetch('/datos/co.json').then(r => r.json())]);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  esc.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 6000);
  const st = { az: 0.2, pol: 0.82, polMin: 0.25, polMax: 1.15, toque: -1e9 };
  orbita(esc, st);

  const K = 40, CX = -73.6, CY = 4.3, r = D.R * K * 0.9;
  const X = lon => (lon - CX) * K, Z = lat => -(lat - CY) * K;
  const max = Math.max(...D.bins.map(b => b[2]));
  const hex = new THREE.CylinderGeometry(r, r, 1, 6); hex.translate(0, 0.5, 0);
  const hg = hex.toNonIndexed(); hg.computeVertexNormals();
  const sh = new Float32Array(hg.attributes.position.count * 3), sol = new THREE.Vector3(-0.5, 0, -0.85).normalize();
  for (let v = 0; v < hg.attributes.position.count; v++) {
    const n = hg.attributes.normal, ny = n.getY(v);
    const k = ny > 0.5 ? 1 : ny < -0.5 ? 0.6 : 0.74 + 0.2 * Math.max(0, n.getX(v) * sol.x + n.getZ(v) * sol.z);
    sh[v * 3] = sh[v * 3 + 1] = sh[v * 3 + 2] = k;
  }
  hg.setAttribute('color', new THREE.BufferAttribute(sh, 3));
  const mt = new THREE.MeshBasicMaterial({ vertexColors: true });
  const tierra = new THREE.InstancedMesh(hg, mt, D.land.length), cols = new THREE.InstancedMesh(hg, mt.clone(), D.bins.length);
  const o = new THREE.Object3D();
  D.land.forEach((p, i) => { o.position.set(X(p[0]), 0, Z(p[1])); o.scale.set(1, 0.6, 1); o.updateMatrix(); tierra.setMatrixAt(i, o.matrix); });
  D.bins.forEach((b, i) => { o.position.set(X(b[0]), 0, Z(b[1])); o.scale.set(1, 0.6 + Math.sqrt(b[2] / max) * 90, 1); o.updateMatrix(); cols.setMatrixAt(i, o.matrix); });
  scene.add(tierra, cols);
  const T = new THREE.Color('#D6DCD3'), L0 = new THREE.Color('#9CCFC3'), L1 = new THREE.Color('#1A5A4E'), H = new THREE.Color('#E0A13A');
  const tono = i => L0.clone().lerp(L1, Math.sqrt(D.bins[i][2] / max));
  for (let i = 0; i < D.land.length; i++) tierra.setColorAt(i, T);
  D.bins.forEach((_, i) => cols.setColorAt(i, tono(i)));

  const angosto = () => esc.clientWidth < 700;
  function tam() {
    const w = esc.clientWidth, h = esc.clientHeight; renderer.setSize(w, h, false);
    const Hm = angosto() ? 560 : 430, Wm = Hm * w / h;
    cam.left = -Wm / 2; cam.right = Wm / 2; cam.top = Hm * 0.66; cam.bottom = -Hm * 0.34; cam.updateProjectionMatrix();
  }
  new ResizeObserver(tam).observe(esc); tam();

  const ray = new THREE.Raycaster(), m = new THREE.Vector2(), lectura = esc.querySelector('.lectura'), base = lectura.innerHTML;
  const fmt = new Intl.NumberFormat('es-CO'), f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const coord = (val, p, n) => f2.format(Math.abs(val)) + ' ' + (val >= 0 ? p : n);
  let sel = -1;
  esc.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    const rc = esc.getBoundingClientRect();
    m.set((e.clientX - rc.left) / rc.width * 2 - 1, -(e.clientY - rc.top) / rc.height * 2 + 1);
    ray.setFromCamera(m, cam);
    const h = ray.intersectObject(cols)[0], i = h ? h.instanceId : -1;
    if (i !== sel) {
      if (sel >= 0) cols.setColorAt(sel, tono(sel));
      if (i >= 0) cols.setColorAt(i, H);
      cols.instanceColor.needsUpdate = true; sel = i;
    }
    lectura.innerHTML = i >= 0 ? '<b>' + fmt.format(D.bins[i][2]) + ' predios</b> en la muestra<br>' + coord(D.bins[i][1], 'N', 'S') + ' · ' + coord(D.bins[i][0], 'E', 'W') : base;
  });

  let corre = true;
  visible(esc, si => { const antes = corre; corre = si; if (si && !antes) requestAnimationFrame(cuadro); });
  function cuadro(t) {
    if (!quieto && t - st.toque > 3500) st.az += 0.0009;
    const R = 2000;
    cam.position.set(R * Math.sin(st.pol) * Math.sin(st.az), R * Math.cos(st.pol), R * Math.sin(st.pol) * Math.cos(st.az));
    cam.lookAt(0, 0, 0); renderer.render(scene, cam); esc.classList.add('viva');
    if (corre) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}
