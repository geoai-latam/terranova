// Héroe: los predios reales del SINIC alrededor del punto consultado en Santa Marta, en 3D.
// El grosor de los predios (5 m) y la subida del consultado (44 m) son simbólicos: no son dato.
// Al entrar, la cámara baja desde arriba y los predios crecen desde el punto consultado hacia
// afuera. Cuando la consola muestra la respuesta del predio, sale una onda del punto y el predio sube.
import { cargarThree, luces, orbita, parchar, quieto, suave, visible } from './comun3d.js';

const esc = document.querySelector('[data-escena="predios"]');
const con = document.querySelector('[data-consola], [data-sobre]');
if (esc) iniciar(esc).catch(err => console.warn('escena de predios:', err));

async function iniciar(esc) {
  const [THREE, D, C] = await Promise.all([
    cargarThree(), fetch('/datos/sm.json').then(r => r.json()),
    fetch('/datos/calles.json').then(r => r.json()).catch(() => ({ calles: [] })),
  ]);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  esc.prepend(renderer.domElement);
  // La imagen accesible es el lienzo (y la de respaldo mientras carga): la lectura, con el enlace
  // de OpenStreetMap, queda fuera de role=img.
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', esc.dataset.etiqueta || '');
  const scene = new THREE.Scene();
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  const st = { az: -0.55, pol: 0.98, polMin: 0.35, polMax: 1.22, toque: -1e9, mpp: 1 };
  orbita(esc, st);
  // Con movimiento reducido no hay bucle: un solo render, y otro solo si el lector arrastra,
  // pasa el puntero o cambia el tamaño.
  const pedir = () => { if (quieto && !pendiente) { pendiente = true; requestAnimationFrame(cuadro); } };
  let pendiente = false;
  if (quieto) for (const ev of ['pointermove', 'pointerdown']) esc.addEventListener(ev, pedir);
  luces(THREE, renderer, scene, { sombras: esc.clientWidth >= 700, lado: 560 });

  // Geometría: cada lindero recortado medio metro, así los huecos dibujan la trama de calles.
  const BASE_H = 5, ALTO = 44;
  const anillos = D.polys.map(flat => {
    let pts = [];
    for (let k = 0; k < flat.length; k += 2) pts.push(new THREE.Vector2(flat[k], flat[k + 1]));
    if (THREE.ShapeUtils.isClockWise(pts)) pts.reverse();
    const c = pts.reduce((a, p) => a.add(p), new THREE.Vector2()).divideScalar(pts.length);
    pts = pts.map(p => { const d = p.clone().sub(c), L = d.length(); return L > 1.2 ? c.clone().add(d.multiplyScalar((L - 0.55) / L)) : p; });
    return { pts, c };
  });
  const objPoly = anillos[D.obj].pts, oc = anillos[D.obj].c;
  const pos = [], dist = [], tri = [], seg = [], segd = [], rango = [];
  anillos.forEach(({ pts, c }, i) => {
    if (i === D.obj) return;
    const d = c.distanceTo(oc), v0 = pos.length / 3;
    const P = (x, y, h) => { pos.push(x, h, -y); dist.push(d); };
    THREE.ShapeUtils.triangulateShape(pts, []).forEach(t => { t.forEach(j => P(pts[j].x, pts[j].y, BASE_H)); tri.push(i); });
    const nTop = pos.length / 3 - v0;
    for (let k = 0; k < pts.length; k++) {
      const a = pts[k], b = pts[(k + 1) % pts.length];
      P(a.x, a.y, 0); P(b.x, b.y, 0); P(b.x, b.y, BASE_H); P(a.x, a.y, 0); P(b.x, b.y, BASE_H); P(a.x, a.y, BASE_H);
      tri.push(i, i);
      seg.push(a.x, BASE_H + 0.05, -a.y, b.x, BASE_H + 0.05, -b.y); segd.push(d, d);
    }
    rango[i] = [v0, nTop];
  });
  const U = { uCrece: { value: quieto ? 99 : 0 }, uOnda: { value: -1 }, uTinte: { value: new THREE.Color('#8FD3C4') } };
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('aDist', new THREE.Float32BufferAttribute(dist, 1));
  g.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(pos.length), 3));
  g.computeVertexNormals();
  const malla = new THREE.Mesh(g, parchar(new THREE.MeshLambertMaterial({ vertexColors: true }), U, true));
  malla.customDepthMaterial = parchar(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking }), U, false);
  malla.castShadow = malla.receiveShadow = true;
  scene.add(malla);
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(seg, 3));
  lg.setAttribute('aDist', new THREE.Float32BufferAttribute(segd, 1));
  scene.add(new THREE.LineSegments(lg, parchar(new THREE.LineBasicMaterial({ transparent: true, color: '#12261F', opacity: 0.22 }), U, false)));

  // El predio consultado, el anillo que lo marca y la onda que sale de él.
  const og = new THREE.ExtrudeGeometry(new THREE.Shape(objPoly), { depth: 1, bevelEnabled: false });
  og.rotateX(-Math.PI / 2);
  const obj = new THREE.Mesh(og, [new THREE.MeshLambertMaterial({ color: '#EBAE45' }), new THREE.MeshLambertMaterial({ color: '#D99A2E' })]);
  obj.castShadow = true; obj.scale.y = 0.01; scene.add(obj);
  const plano = (r0, r1, color, op) => {
    const m = new THREE.Mesh(new THREE.RingGeometry(r0, r1, 128), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: op, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.position.set(oc.x, 0.3, -oc.y); scene.add(m); return m;
  };
  const anillo = plano(27, 29.5, '#236E62', 1);
  const onda = plano(0.985, 1, '#236E62', 0); onda.visible = false;

  // Suelo: recibe las sombras, con una retícula tenue y niebla del color del fondo en los bordes.
  const suelo = new THREE.Mesh(new THREE.PlaneGeometry(2600, 2600), new THREE.ShadowMaterial({ opacity: 0.09 }));
  suelo.rotation.x = -Math.PI / 2; suelo.position.y = -0.05; suelo.receiveShadow = true; scene.add(suelo);
  const grid = new THREE.GridHelper(1000, 20, '#D9DED6', '#D9DED6');
  grid.material.transparent = true; grid.material.opacity = 0.55; grid.position.y = -0.1; scene.add(grid);
  scene.fog = new THREE.Fog('#F6F7F4', 1040, 1420);

  // Techos blancos y muros un poco más oscuros; la luz hace el resto.
  const TOP = new THREE.Color('#FFFFFF'), LADO = new THREE.Color('#E4E9E2'), HOVER = '#CDE6DF';
  { const n = g.attributes.normal, c = g.attributes.color;
    for (let v = 0; v < c.count; v++) { const t = n.getY(v) > 0.5 ? TOP : LADO; c.setXYZ(v, t.r, t.g, t.b); } }
  const pintar = (i, hex) => {
    if (i < 0 || !rango[i]) return;
    const [v0, n] = rango[i], c = g.attributes.color, t = new THREE.Color(hex);
    for (let v = v0; v < v0 + n; v++) c.setXYZ(v, t.r, t.g, t.b);
    c.needsUpdate = true;
  };

  // Cámara ortográfica con encuadre asimétrico: a todo lo ancho, el predio queda a la derecha del
  // texto y sobre la consola; apilado, al centro.
  const apilado = () => getComputedStyle(esc).position !== 'absolute';
  function tam() {
    const w = esc.clientWidth, h = esc.clientHeight; renderer.setSize(w, h, false);
    const ap = apilado(), Hm = ap ? 330 : 400, Wm = Hm * w / h, fx = ap ? 0.5 : 0.67, fy = ap ? 0.4 : 0.3;
    cam.left = -fx * Wm; cam.right = (1 - fx) * Wm; cam.top = fy * Hm; cam.bottom = -(1 - fy) * Hm; cam.updateProjectionMatrix();
    st.mpp = Hm / h;
  }
  new ResizeObserver(() => { tam(); pedir(); }).observe(esc); tam();

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
    lectura.innerHTML = enObj ? '<b>predio consultado</b> ' + D.codes[D.obj] : i >= 0 ? '<b>predio</b> ' + D.codes[i] : base;
  });
  esc.addEventListener('pointerleave', () => { pintar(hover, '#FFFFFF'); hover = -1; lectura.innerHTML = base; });

  // Rótulos: nombres de calle (OpenStreetMap) alineados con la calle y siempre derechos; el barrio va
  // fijo arriba. Se esconden los que caerían debajo del texto del héroe o de la consola.
  const capa = esc.querySelector('.rotulos');
  const rotulos = C.calles.map(c => {
    const e = document.createElement('span'); e.className = 'calle'; e.textContent = c.n; capa.append(e);
    return { e, c };
  });
  if (C.barrio) {
    const e = document.createElement('span'); e.className = 'barrio'; e.textContent = 'Barrio ' + C.barrio + ', Santa Marta'; capa.append(e);
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
    const tr = con && con.getBoundingClientRect();
    // la guía solo baja hasta la respuesta cuando esta queda dentro de la escena
    if (con && conGuia && obj.scale.y > ALTO * 0.6 && tr.top - er.top < esc.clientHeight) {
      const top = pantalla(oc.x, obj.scale.y, -oc.y);
      const x2 = Math.min(tr.right - er.left - 32, Math.max(tr.left - er.left + 32, top[0]));
      gl.setAttribute('x1', top[0]); gl.setAttribute('y1', top[1]);
      gl.setAttribute('x2', x2); gl.setAttribute('y2', tr.top - er.top);
      gc.setAttribute('cx', top[0]); gc.setAttribute('cy', top[1]); guia.style.display = '';
    } else guia.style.display = 'none';
  }

  // La consola manda el turno: el predio sube con su respuesta y la onda sale del punto consultado.
  const turno = document.documentElement.dataset.turno;
  let objetivo = !turno || turno === 'predio' ? ALTO : BASE_H, conGuia = objetivo === ALTO, ondaT = null;
  document.addEventListener('terranova:turno', e => {
    objetivo = e.detail === 'predio' ? ALTO : BASE_H; conGuia = e.detail === 'predio';
    if (e.detail === 'predio' && !quieto) ondaT = performance.now();
    pedir();
  });

  // Entrada: la cámara baja desde casi cenital mientras los predios crecen desde el punto.
  const ENTRA = 2800, POL0 = 0.4, AZ0 = -1.3;
  // El giro y la subida van por tiempo (dt), no por cuadros: la misma velocidad a 60 o a 144 Hz.
  let corre = true, t0 = null, tAnt = null;
  visible(esc, si => { const antes = corre; corre = si; if (si && !antes && !quieto) { tAnt = null; requestAnimationFrame(cuadro); } });
  function cuadro(t) {
    pendiente = false;
    if (t0 === null) t0 = t;
    const dt = tAnt === null ? 1 / 60 : Math.min(0.1, (t - tAnt) / 1000);
    tAnt = t;
    const k = quieto ? 1 : suave((t - t0) / ENTRA);
    if (k < 1 && st.toque < t0) { st.pol = POL0 + (0.98 - POL0) * k; st.az = AZ0 + (-0.55 - AZ0) * k; }
    else if (!quieto && t - st.toque > 3500) st.az += 0.066 * dt;
    if (!quieto) U.uCrece.value = (t - t0) / 1000;
    capa.style.opacity = k;
    obj.scale.y = quieto ? objetivo : Math.max(0.01, obj.scale.y + (objetivo - obj.scale.y) * (1 - Math.exp(-dt / 0.23)));
    if (ondaT !== null) {
      const r = Math.max(0, t - ondaT) / 1000 * 320;
      if (r > 900) { ondaT = null; U.uOnda.value = -1; onda.visible = false; }
      else { U.uOnda.value = r; onda.visible = true; onda.scale.setScalar(Math.max(1, r)); onda.material.opacity = 0.7 * (1 - r / 900); }
    }
    anillo.material.opacity = k;
    const R = 1000;
    cam.position.set(R * Math.sin(st.pol) * Math.sin(st.az), R * Math.cos(st.pol), R * Math.sin(st.pol) * Math.cos(st.az));
    cam.lookAt(0, 0, 0);
    renderer.render(scene, cam); muebles();
    if (!esc.classList.contains('viva')) {
      esc.classList.add('viva');
      document.documentElement.dataset.escena = 'lista';
      document.dispatchEvent(new Event('terranova:escena'));
    }
    if (corre && !quieto) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}
