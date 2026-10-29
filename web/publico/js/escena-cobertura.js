// Cobertura: columnas hexagonales con la muestra del 3 % de predios del SINIC sobre Colombia.
// Altura y color siguen la raíz del conteo; las celdas planas son tierra sin predios en la muestra.
// Al entrar en la vista, las columnas suben desde Bogotá hacia afuera; al pasar sobre una, una
// etiqueta junto a la columna da su conteo.
import { cargarThree, luces, orbita, quieto, suave, visible } from './comun3d.js';

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
  luces(THREE, renderer, scene, { sombras: esc.clientWidth >= 600, lado: 260, sol: [-0.55, 0.85, 0.35] });

  const K = 40, CX = -74.6, CY = 6.4, r = D.R * K * 0.8;  // hueco del 20 %: cada celda se lee como hexágono
  const X = lon => (lon - CX) * K, Z = lat => -(lat - CY) * K;
  const max = Math.max(...D.bins.map(b => b[2]));
  const hex = new THREE.CylinderGeometry(r, r, 1, 6); hex.translate(0, 0.5, 0);
  const mt = new THREE.MeshLambertMaterial({ flatShading: true });
  const tierra = new THREE.InstancedMesh(hex, mt, D.land.length), cols = new THREE.InstancedMesh(hex, mt.clone(), D.bins.length);
  tierra.receiveShadow = true; cols.castShadow = cols.receiveShadow = true;
  const o = new THREE.Object3D();
  D.land.forEach((p, i) => { o.position.set(X(p[0]), 0, Z(p[1])); o.scale.set(1, 0.6, 1); o.updateMatrix(); tierra.setMatrixAt(i, o.matrix); });
  const alto = D.bins.map(b => 0.6 + Math.sqrt(b[2] / max) * 60);
  const bog = new THREE.Vector2(X(-74.08), Z(4.61));
  const espera = D.bins.map(b => new THREE.Vector2(X(b[0]), Z(b[1])).distanceTo(bog) * 4.5);
  function colocar(ms) {
    D.bins.forEach((b, i) => {
      o.position.set(X(b[0]), 0, Z(b[1]));
      o.scale.set(1, 0.6 + (alto[i] - 0.6) * suave((ms - espera[i]) / 900), 1);
      o.updateMatrix(); cols.setMatrixAt(i, o.matrix);
    });
    cols.instanceMatrix.needsUpdate = true;
  }
  colocar(quieto ? 1e9 : 0);
  scene.add(tierra, cols);
  const T = new THREE.Color('#E4E9E2'), L0 = new THREE.Color('#A6D8CC'), L1 = new THREE.Color('#14564A'), H = new THREE.Color('#E0A13A');
  const tono = i => L0.clone().lerp(L1, Math.sqrt(D.bins[i][2] / max));
  for (let i = 0; i < D.land.length; i++) tierra.setColorAt(i, T);
  D.bins.forEach((_, i) => cols.setColorAt(i, tono(i)));

  const angosto = () => esc.clientWidth < 700;
  function tam() {
    const w = esc.clientWidth, h = esc.clientHeight; renderer.setSize(w, h, false);
    const Hm = angosto() ? 300 : 230, Wm = Hm * w / h;
    cam.left = -Wm / 2; cam.right = Wm / 2; cam.top = Hm * 0.55; cam.bottom = -Hm * 0.45; cam.updateProjectionMatrix();
  }
  new ResizeObserver(tam).observe(esc); tam();

  // Rótulos: ciudades y mares, anclados a su coordenada y siempre derechos; y la etiqueta de la
  // columna bajo el puntero.
  const LUGARES = [
    ['Bogotá', -74.08, 4.61, 'c'], ['Medellín', -75.57, 6.25, 'c'], ['Cali', -76.53, 3.45, 'c'],
    ['Barranquilla', -74.80, 10.96, 'c'], ['Cartagena', -75.51, 10.39, 'c'], ['Santa Marta', -74.20, 11.24, 'c'],
    ['Bucaramanga', -73.12, 7.12, 'c'], ['Cúcuta', -72.50, 7.89, 'c'], ['Pereira', -75.69, 4.81, 'c'],
    ['Ibagué', -75.23, 4.44, 'c'], ['Villavicencio', -73.63, 4.14, 'c'], ['Montería', -75.88, 8.75, 'c'],
    ['Mar Caribe', -76.6, 11.6, 'm'], ['Océano Pacífico', -78.4, 5.0, 'm'],
  ];
  const capa = esc.querySelector('.rotulos'), v3 = new THREE.Vector3();
  const rot = LUGARES.map(([n, lon, lat, k]) => {
    const e = document.createElement('span'); e.className = k === 'm' ? 'mar' : 'ciudad'; e.textContent = n; capa.append(e);
    return { e, x: X(lon), z: Z(lat) };
  });
  const dato = document.createElement('span'); dato.className = 'dato'; dato.hidden = true; capa.append(dato);
  const pantalla = (x, y, z) => { v3.set(x, y, z).project(cam); return [(v3.x + 1) / 2 * esc.clientWidth, (1 - v3.y) / 2 * esc.clientHeight]; };
  function rotular() {
    const w = esc.clientWidth, h = esc.clientHeight;
    for (const r of rot) {
      const [x, y] = pantalla(r.x, 2, r.z);
      r.e.style.display = x < 40 || x > w - 40 || y < 20 || y > h - 20 ? 'none' : '';
      r.e.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
    }
    if (sel >= 0) {
      const b = D.bins[sel], [x, y] = pantalla(X(b[0]), alto[sel] + 2, Z(b[1]));
      dato.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -100%)`;
    }
  }

  const ray = new THREE.Raycaster(), m = new THREE.Vector2(), lectura = esc.querySelector('.lectura'), base = lectura.innerHTML;
  const fmt = new Intl.NumberFormat('es-CO'), f2 = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const coord = (val, p, n) => f2.format(Math.abs(val)) + ' ' + (val >= 0 ? p : n);
  let sel = -1;
  const elegir = i => {
    if (i === sel) return;
    if (sel >= 0) cols.setColorAt(sel, tono(sel));
    if (i >= 0) cols.setColorAt(i, H);
    cols.instanceColor.needsUpdate = true; sel = i;
    if (i < 0) { dato.hidden = true; lectura.innerHTML = base; return; }
    const b = D.bins[i];
    dato.hidden = false; dato.innerHTML = '<b>' + fmt.format(b[2]) + '</b> predios';
    lectura.innerHTML = coord(b[1], 'N', 'S') + ', ' + coord(b[0], 'E', 'W');
  };
  esc.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    const rc = esc.getBoundingClientRect();
    m.set((e.clientX - rc.left) / rc.width * 2 - 1, -(e.clientY - rc.top) / rc.height * 2 + 1);
    ray.setFromCamera(m, cam);
    const h = ray.intersectObject(cols)[0];
    elegir(h ? h.instanceId : -1);
  });
  esc.addEventListener('pointerleave', () => elegir(-1));

  const ENTRA = Math.max(...espera) + 900;
  let corre = true, t0 = null, listo = quieto;
  visible(esc, si => { const antes = corre; corre = si; if (si && !antes) requestAnimationFrame(cuadro); });
  function cuadro(t) {
    if (t0 === null) t0 = t;
    if (!listo) { colocar(t - t0); listo = t - t0 > ENTRA; }
    if (!quieto && t - st.toque > 3500) st.az += 0.0009;
    const R = 2000;
    cam.position.set(R * Math.sin(st.pol) * Math.sin(st.az), R * Math.cos(st.pol), R * Math.sin(st.pol) * Math.cos(st.az));
    cam.lookAt(0, 0, 0); renderer.render(scene, cam); rotular(); esc.classList.add('viva');
    if (corre) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}
