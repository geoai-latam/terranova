// Héroe: los predios reales del SINIC alrededor del punto consultado en Santa Marta, en 3D.
// El grosor de los predios (4 m) y la subida del consultado (44 m) son simbólicos: no son dato.
import { cargarThree, orbita, quieto, visible } from './comun3d.js';

const esc = document.querySelector('[data-escena="predios"]');
const con = document.querySelector('[data-consola]');
if (esc) iniciar(esc).catch(err => console.warn('escena de predios:', err));

async function iniciar(esc) {
  const [THREE, D, C] = await Promise.all([
    cargarThree(), fetch('/datos/sm.json').then(r => r.json()),
    fetch('/datos/calles.json').then(r => r.json()).catch(() => ({ calles: [] })),
  ]);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  esc.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  const st = { az: -0.55, pol: 0.98, polMin: 0.35, polMax: 1.22, toque: -1e9, mpp: 1 };
  orbita(esc, st);

  // Geometría: cada lindero recortado medio metro, así los huecos dibujan la trama de calles.
  const BASE_H = 4, ALTO = 44;
  const pos = [], tri = [], seg = [], rango = [];
  let objPoly = null;
  D.polys.forEach((flat, i) => {
    let pts = [];
    for (let k = 0; k < flat.length; k += 2) pts.push(new THREE.Vector2(flat[k], flat[k + 1]));
    if (THREE.ShapeUtils.isClockWise(pts)) pts.reverse();
    const c = pts.reduce((a, p) => a.add(p), new THREE.Vector2()).divideScalar(pts.length);
    pts = pts.map(p => { const d = p.clone().sub(c), L = d.length(); return L > 1.2 ? c.clone().add(d.multiplyScalar((L - 0.55) / L)) : p; });
    if (i === D.obj) { objPoly = pts; return; }
    const v0 = pos.length / 3;
    const P = (x, y, h) => pos.push(x, h, -y);
    THREE.ShapeUtils.triangulateShape(pts, []).forEach(t => { t.forEach(j => P(pts[j].x, pts[j].y, BASE_H)); tri.push(i); });
    const nTop = pos.length / 3 - v0;
    for (let k = 0; k < pts.length; k++) {
      const a = pts[k], b = pts[(k + 1) % pts.length];
      P(a.x, a.y, 0); P(b.x, b.y, 0); P(b.x, b.y, BASE_H); P(a.x, a.y, 0); P(b.x, b.y, BASE_H); P(a.x, a.y, BASE_H);
      tri.push(i, i);
      seg.push(a.x, BASE_H + 0.05, -a.y, b.x, BASE_H + 0.05, -b.y);
    }
    rango[i] = [v0, nTop];
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(pos.length), 3));
  g.computeVertexNormals();
  const malla = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true }));
  scene.add(malla);
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(seg, 3));
  const lmat = new THREE.LineBasicMaterial({ transparent: true, color: '#12261F', opacity: 0.26 });
  scene.add(new THREE.LineSegments(lg, lmat));

  const og = new THREE.ExtrudeGeometry(new THREE.Shape(objPoly), { depth: 1, bevelEnabled: false });
  og.rotateX(-Math.PI / 2);
  const obj = new THREE.Mesh(og, [new THREE.MeshBasicMaterial({ color: '#E0A13A' }), new THREE.MeshBasicMaterial({ color: '#C68A26' })]);
  obj.scale.y = BASE_H; scene.add(obj);
  const oc = objPoly.reduce((a, p) => a.add(p), new THREE.Vector2()).divideScalar(objPoly.length);
  const anillo = new THREE.Mesh(new THREE.RingGeometry(27, 29.5, 64), new THREE.MeshBasicMaterial({ color: '#236E62', side: THREE.DoubleSide }));
  anillo.rotation.x = -Math.PI / 2; anillo.position.y = 0.3; scene.add(anillo);
  const grid = new THREE.GridHelper(900, 18, '#D9DED6', '#D9DED6');
  grid.material.transparent = true; grid.material.opacity = 0.6; scene.add(grid);
  scene.fog = new THREE.Fog('#F6F7F4', 1040, 1420);

  // Colores exactos de los tokens con sombreado plano calculado.
  const TOP = new THREE.Color('#FFFFFF'), LADO = new THREE.Color('#D3D9D1'), HOVER = '#CDE6DF';
  const sol = new THREE.Vector3(-0.55, 0, -0.83).normalize();
  { const n = g.attributes.normal, c = g.attributes.color, t = new THREE.Color();
    for (let v = 0; v < c.count; v++) {
      if (n.getY(v) > 0.5) t.copy(TOP);
      else t.copy(LADO).multiplyScalar(0.82 + 0.18 * Math.max(0, n.getX(v) * sol.x + n.getZ(v) * sol.z));
      c.setXYZ(v, t.r, t.g, t.b);
    } }
  const pintar = (i, hex) => {
    if (i < 0 || !rango[i]) return;
    const [v0, n] = rango[i], c = g.attributes.color, t = new THREE.Color(hex);
    for (let v = v0; v < v0 + n; v++) c.setXYZ(v, t.r, t.g, t.b);
    c.needsUpdate = true;
  };

  // Cámara ortográfica con encuadre asimétrico: a todo lo ancho, el predio queda a la derecha del texto y sobre la consola.
  const apilado = () => getComputedStyle(esc).position !== 'absolute';
  function tam() {
    const w = esc.clientWidth, h = esc.clientHeight; renderer.setSize(w, h, false);
    const ap = apilado(), Hm = ap ? 330 : 400, Wm = Hm * w / h, fx = ap ? 0.5 : 0.67, fy = ap ? 0.4 : 0.3;
    cam.left = -fx * Wm; cam.right = (1 - fx) * Wm; cam.top = fy * Hm; cam.bottom = -(1 - fy) * Hm; cam.updateProjectionMatrix();
    st.mpp = Hm / h;
  }
  new ResizeObserver(tam).observe(esc); tam();

  const ray = new THREE.Raycaster(), m = new THREE.Vector2();
  const lectura = esc.querySelector('.lectura'), base = lectura.innerHTML;
  let hover = -1;
  esc.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    const r = esc.getBoundingClientRect();
    m.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
    ray.setFromCamera(m, cam);
    const h = ray.intersectObject(malla)[0], enObj = ray.intersectObject(obj)[0];
    const i = h ? tri[h.faceIndex] : -1;
    if (i !== hover) { pintar(hover, '#FFFFFF'); hover = i; pintar(i, HOVER); }
    lectura.innerHTML = enObj ? '<b>predio consultado</b> · ' + D.codes[D.obj] : i >= 0 ? '<b>predio</b> · ' + D.codes[i] : base;
  });
  esc.addEventListener('pointerleave', () => { pintar(hover, '#FFFFFF'); hover = -1; lectura.innerHTML = base; });

  // Rótulos: nombres de calle (OpenStreetMap) alineados con la calle y siempre derechos; el barrio va fijo arriba.
  // Se esconden los que caerían debajo del texto del héroe o de la consola.
  const capa = esc.querySelector('.rotulos');
  const rotulos = C.calles.map(c => {
    const e = document.createElement('span'); e.className = 'calle'; e.textContent = c.n; capa.append(e);
    return { e, c };
  });
  if (C.barrio) {
    const e = document.createElement('span'); e.className = 'barrio'; e.textContent = 'Barrio ' + C.barrio + ' · Santa Marta'; capa.append(e);
  }

  // Escala, norte y línea guía siguen a la cámara.
  const esb = esc.querySelector('.escala i'), est = esc.querySelector('.escala span'), nor = esc.querySelector('.norte svg');
  const gl = esc.querySelector('.guia line'), gc = esc.querySelector('.guia circle'), guia = esc.querySelector('.guia');
  const v = new THREE.Vector3();
  const pantalla = (x, y, z) => { v.set(x, y, z).project(cam); return [(v.x + 1) / 2 * esc.clientWidth, (1 - v.y) / 2 * esc.clientHeight]; };
  function muebles() {
    const pxm = 1 / st.mpp, L = [25, 50, 100, 200].find(o => o * pxm >= 60) || 200;
    esb.style.width = (L * pxm).toFixed(1) + 'px'; est.textContent = L + ' m';
    const a = pantalla(0, 0, 0), b = pantalla(0, 0, -100);
    nor.style.transform = 'rotate(' + (Math.atan2(b[0] - a[0], -(b[1] - a[1])) * 180 / Math.PI).toFixed(1) + 'deg)';
    const er = esc.getBoundingClientRect();
    const tapas = [document.querySelector('.h-texto .izq'), con, capa.querySelector('.barrio'), lectura].filter(x => x && x.offsetParent).map(x => {
      const r = x.getBoundingClientRect(); return [r.left - er.left - 24, r.top - er.top - 16, r.right - er.left + 24, r.bottom - er.top + 16];
    });
    for (const { e, c } of rotulos) {
      const p = pantalla(c.x, 0.5, -c.y);
      e.style.opacity = tapas.some(([a, b, c2, d]) => p[0] > a && p[0] < c2 && p[1] > b && p[1] < d) ? 0 : 1;
      let ang = 0;
      if (c.dx || c.dy) {
        const q = pantalla(c.x + c.dx, 0.5, -(c.y + c.dy));
        ang = Math.atan2(q[1] - p[1], q[0] - p[0]) * 180 / Math.PI;
        if (ang > 90) ang -= 180; else if (ang < -90) ang += 180;
      }
      e.style.transform = `translate(${p[0].toFixed(1)}px, ${p[1].toFixed(1)}px) translate(-50%, -50%) rotate(${ang.toFixed(1)}deg)`;
    }
    if (con && conGuia && obj.scale.y > ALTO * 0.6) {
      const top = pantalla(oc.x, obj.scale.y, -oc.y), tr = con.getBoundingClientRect();
      const x2 = Math.min(tr.right - er.left - 32, Math.max(tr.left - er.left + 32, top[0]));
      gl.setAttribute('x1', top[0]); gl.setAttribute('y1', top[1]);
      gl.setAttribute('x2', x2); gl.setAttribute('y2', tr.top - er.top);
      gc.setAttribute('cx', top[0]); gc.setAttribute('cy', top[1]); guia.style.display = '';
    } else guia.style.display = 'none';
  }

  const turno = document.documentElement.dataset.turno;
  let objetivo = !turno || turno === 'predio' ? ALTO : BASE_H, conGuia = objetivo === ALTO;
  document.addEventListener('terranova:turno', e => {
    objetivo = e.detail === 'predio' ? ALTO : BASE_H; conGuia = e.detail === 'predio';
  });
  let corre = true;
  visible(esc, si => { const antes = corre; corre = si; if (si && !antes) requestAnimationFrame(cuadro); });
  function cuadro(t) {
    if (!quieto && t - st.toque > 3500) st.az += 0.0012;
    obj.scale.y = quieto ? objetivo : obj.scale.y + (objetivo - obj.scale.y) * 0.07;
    const R = 1000;
    cam.position.set(R * Math.sin(st.pol) * Math.sin(st.az), R * Math.cos(st.pol), R * Math.sin(st.pol) * Math.cos(st.az));
    cam.lookAt(0, 0, 0);
    renderer.render(scene, cam); muebles(); esc.classList.add('viva');
    if (corre) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}
