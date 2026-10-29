// Viñetas 3D de los servicios y de la prueba de cada respuesta. Cada elemento [data-vineta] tiene
// su propio lienzo, se crea al acercarse a la vista y solo dibuja mientras se ve. Lo que nombran
// (entidades, sistemas, preguntas, licencias) llega del catálogo en data-datos; los resultados que
// se ven pasar son un esquema del trabajo, no cifras.
import { cargarThree, quieto, suave, visible } from './comun3d.js';

const C = {
  crema: '#F3EFE4', hueso: '#E4E9E2', teal: '#6CC3B3', tealOsc: '#236E62', ambar: '#E0A13A',
  bosque: '#0E2A22', suelo: '#163830', apagado: '#3F6158', linea: '#2F5248',
};

const els = [...document.querySelectorAll('[data-vineta]')];
if (els.length) {
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    io.unobserve(e.target);
    iniciar(e.target).catch(err => console.warn('viñeta', e.target.dataset.vineta, err));
  }), { rootMargin: '300px' });
  els.forEach(el => io.observe(el));
}

async function iniciar(el) {
  const THREE = await cargarThree();
  const tipo = el.dataset.vineta;
  const oscuro = el.dataset.fondo !== 'claro';
  const datos = el.dataset.datos ? JSON.parse(el.dataset.datos) : null;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  el.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  scene.add(new THREE.HemisphereLight('#FFFFFF', oscuro ? '#28463D' : '#AEB9B1', oscuro ? 1.6 : 2.1));
  const sol = new THREE.DirectionalLight('#FFF6E6', oscuro ? 1.5 : 1.4);
  sol.position.set(-220, 420, 260); scene.add(sol);

  // Rótulos en HTML, anclados a puntos de la escena: el texto se lee nítido a cualquier tamaño.
  const capa = el.querySelector('.rotulos-v');
  const rotulo = (html, cls = '') => {
    const s = document.createElement('span'); s.className = 'rv ' + cls; s.innerHTML = html; capa.append(s); return s;
  };
  const v = VINETAS[tipo](THREE, scene, { el, datos, rotulo });
  if (v.sombras && el.clientWidth >= 420) {
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    sol.castShadow = true; const l = v.sombras;
    Object.assign(sol.shadow.camera, { left: -l, right: l, top: l, bottom: -l, near: 1, far: 2000 });
    sol.shadow.mapSize.set(1024, 1024); sol.shadow.bias = -0.0006; sol.shadow.normalBias = 0.4;
  }
  const st = { az: v.az ?? -0.5, pol: v.pol ?? 0.95, px: 0 };
  const v3 = new THREE.Vector3();
  const pantalla = (x, y, z) => { v3.set(x, y, z).project(cam); return [(v3.x + 1) / 2 * el.clientWidth, (1 - v3.y) / 2 * el.clientHeight]; };
  const poner = (s, x, y, z) => { const [a, b] = pantalla(x, y, z); s.style.transform = `translate(${a.toFixed(1)}px, ${b.toFixed(1)}px)`; };
  function tam() {
    const w = el.clientWidth, h = el.clientHeight; renderer.setSize(w, h, false);
    el.classList.toggle('angosta', w < 520);  // en pantallas chicas, solo los rótulos principales
    const H = (w < 520 && v.altoAngosto || v.alto) * (w / h < 1.15 ? 1.22 : 1), W = H * w / h;
    cam.left = -W / 2; cam.right = W / 2; cam.top = H / 2 + (v.sube ?? 0); cam.bottom = -H / 2 + (v.sube ?? 0);
    cam.updateProjectionMatrix();
  }
  new ResizeObserver(tam).observe(el); tam();
  // Un leve paralaje con el puntero: la escena responde sin pedir que la arrastren.
  el.addEventListener('pointermove', e => { const r = el.getBoundingClientRect(); st.px = (e.clientX - r.left) / r.width - 0.5; });
  el.addEventListener('pointerleave', () => { st.px = 0; });

  let corre = true, t0 = null, az = st.az;
  visible(el, si => { const antes = corre; corre = si; if (si && !antes) requestAnimationFrame(cuadro); });
  function cuadro(t) {
    if (t0 === null) t0 = t;
    const s = quieto ? (v.quieto ?? 4) : (t - t0) / 1000;
    v.paso(s);
    az += ((st.az + st.px * 0.35 + (quieto ? 0 : Math.sin(s * 0.11) * (v.vaiven ?? 0.08))) - az) * 0.05;
    const R = 1500, m = (el.clientWidth < 520 && v.miraAngosta) || v.mira || [0, 0, 0];
    cam.position.set(m[0] + R * Math.sin(st.pol) * Math.sin(az), m[1] + R * Math.cos(st.pol), m[2] + R * Math.sin(st.pol) * Math.cos(az));
    cam.lookAt(m[0], m[1], m[2]);
    renderer.render(scene, cam);
    if (v.rotular) v.rotular(poner);
    el.classList.add('viva');
    if (corre && !quieto) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}

const lam = (THREE, color, extra = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
const borde = (THREE, geo, color, op = 0.5) => new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), new THREE.LineBasicMaterial({ color, transparent: true, opacity: op }));
const tramo = (k, a, b) => suave((k - a) / (b - a));
// Un punto en un arco entre dos posiciones: lo que viaja de un lado a otro, salta.
const arco = (out, a, b, k, alto) => out.set(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k + Math.sin(k * Math.PI) * alto, a[2] + (b[2] - a[2]) * k);
const suelo = THREE => { const m = new THREE.Mesh(new THREE.PlaneGeometry(2400, 2400), new THREE.ShadowMaterial({ color: '#000000', opacity: 0.32 })); m.rotation.x = -Math.PI / 2; m.position.y = -0.05; m.receiveShadow = true; return m; };

function textura(THREE, ancho, alto, dibujar) {
  const lienzo = document.createElement('canvas'); lienzo.width = ancho; lienzo.height = alto;
  dibujar(lienzo.getContext('2d'), getComputedStyle(document.body).fontFamily);
  const tex = new THREE.CanvasTexture(lienzo); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return tex;
}

const VINETAS = {
  // Revisión de una lista. Cada ítem (un predio, una empresa, un contratista) sale de la lista, se
  // cruza con las cuatro fuentes que le tocan y entra al expediente con su resultado.
  revision(THREE, scene, { datos, rotulo }) {
    const grupos = datos, T = 3.8;
    const orden = [0, 1, 2, 0, 1, 2];
    const revisar = [[0, 1, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 1], [0, 0, 0, 0]];
    scene.add(suelo(THREE));
    // Las fichas: una textura por tipo.
    const texs = grupos.map(g => textura(THREE, 512, 360, (x, f) => {
      x.fillStyle = '#FFFFFF'; x.fillRect(0, 0, 512, 360);
      x.fillStyle = '#12261F'; x.font = `600 74px ${f}`; x.fillText(g.tipo, 40, 120);
      x.fillStyle = '#56645E'; x.font = `400 38px ${f}`; x.fillText(g.como, 40, 178);
      x.fillStyle = '#D9DED6'; [236, 276, 316].forEach((y, i) => x.fillRect(40, y, [380, 300, 340][i], 14));
    }));
    const FW = 64, FD = 44, FH = 3;
    const cuerpoG = new THREE.BoxGeometry(FW, FH, FD); cuerpoG.translate(0, FH / 2, 0);
    const tapaG = new THREE.PlaneGeometry(FW - 2, FD - 2); tapaG.rotateX(-Math.PI / 2);
    const ficha = g => {
      const grupo = new THREE.Group();
      const m = lam(THREE, '#CFD8D1'), b = new THREE.Mesh(cuerpoG, m); b.castShadow = true;
      const t = new THREE.Mesh(tapaG, new THREE.MeshBasicMaterial({ map: texs[g] })); t.position.y = FH + 0.05;
      grupo.add(b, t); scene.add(grupo); return { grupo, m };
    };
    const LISTA = [-150, 0, -18], MESA = [-52, 0, 0], EXP = [-52, 0, 86];
    // La lista: una pila que no se acaba.
    for (let i = 0; i < 6; i++) { const f = ficha(i % 3); f.grupo.position.set(LISTA[0] + (i % 2) * 1.5, i * (FH + 0.6), LISTA[2] - (i % 3)); }
    const fichas = Array.from({ length: 7 }, (_, i) => ficha(orden[i % 6]));
    // Las fuentes: cuatro losas con su rótulo; cambian según el tipo de ítem.
    const ZS = [-72, -24, 24, 72], FX = 62;
    const losas = ZS.map(z => {
      const g = new THREE.BoxGeometry(40, 4, 30); g.translate(0, 2, 0);
      const m = lam(THREE, C.apagado), mesh = new THREE.Mesh(g, m); mesh.position.set(FX, 0, z); mesh.castShadow = true;
      mesh.add(borde(THREE, g, C.teal, 0.3)); scene.add(mesh);
      const haz = new THREE.Mesh(new THREE.SphereGeometry(2.4, 14, 10), new THREE.MeshBasicMaterial({ color: C.ambar })); scene.add(haz);
      return { mesh, m, haz, rl: rotulo('', 'fuente'), z };
    });
    const rLista = rotulo('Tu lista', 'lugar'), rExp = rotulo('Expediente', 'lugar lado');
    const OK = new THREE.Color(C.teal), MAL = new THREE.Color(C.ambar), APAG = new THREE.Color(C.apagado), FICHA = new THREE.Color('#CFD8D1');
    const p = new THREE.Vector3();
    let item = -1;
    return {
      alto: 286, altoAngosto: 330, miraAngosta: [34, 0, 2], az: -0.2, pol: 0.8, mira: [6, 0, 2], sombras: 230, vaiven: 0.06, quieto: 2.6,
      paso(s) {
        const n = Math.floor(s / T), k = s - n * T, tipo = orden[n % 6], res = revisar[n % 6];
        if (n !== item) {
          item = n;
          losas.forEach((l, j) => { const f = grupos[tipo].fuentes[j]; l.rl.innerHTML = `<b>${f.t}</b><small>${f.e}</small><i></i>`; });
        }
        // La ficha en curso: de la lista a la mesa, el cruce, y al expediente.
        const actual = fichas[n % 7], hechas = n % 6;
        arco(p, [LISTA[0], 6 * (FH + 0.6), LISTA[2]], MESA, tramo(k, 0, 0.6), 26);
        if (k > 3.0) arco(p, MESA, [EXP[0], hechas * (FH + 0.8), EXP[2]], tramo(k, 3.0, 3.6), 22);
        actual.grupo.position.copy(p); actual.grupo.visible = true;
        actual.m.color.copy(FICHA).lerp(res.some(Boolean) ? MAL : OK, tramo(k, 2.7, 3.0));
        // Las fichas ya revisadas forman el expediente; al llenarse, empieza uno nuevo.
        fichas.forEach((f, i) => {
          const edad = (n % 7 - i + 7) % 7;
          if (edad === 0) return;
          f.grupo.visible = edad <= hechas;
          if (f.grupo.visible) f.grupo.position.set(EXP[0], (hechas - edad) * (FH + 0.8), EXP[2]);
        });
        losas.forEach((l, j) => {
          const t0 = 0.75 + j * 0.5, viaje = tramo(k, t0, t0 + 0.3), on = tramo(k, t0 + 0.28, t0 + 0.45);
          arco(l.haz.position, [MESA[0] + 20, 6, MESA[2]], [FX - 16, 6, l.z], viaje, 12);
          l.haz.visible = viaje > 0 && viaje < 1;
          const fuera = k > 3.3 ? 1 - tramo(k, 3.3, 3.7) : 1;
          l.m.color.copy(APAG).lerp(res[j] ? MAL : OK, on * fuera);
          l.mesh.position.y = on * fuera * (res[j] ? 9 : 4);
          l.rl.classList.toggle('ok', on > 0.5 && k < 3.3 && !res[j]);
          l.rl.classList.toggle('mal', on > 0.5 && k < 3.3 && !!res[j]);
        });
      },
      rotular(poner) {
        losas.forEach(l => poner(l.rl, FX + 24, l.mesh.position.y + 4, l.z));
        poner(rLista, LISTA[0], 34, LISTA[2] - 22); poner(rExp, EXP[0] + 38, 2, EXP[2] + 4);
      },
    };
  },

  // Tablero: un tablero de verdad, despiezado en capas como una vista explotada. Abajo, la
  // ventana; encima flotan el mapa de Colombia en columnas, el ranking de tu municipio frente a los
  // comparables y las tarjetas de cada indicador, unidos por hilos finos. Con cada indicador (y la
  // entidad que lo publica) cambian las tres capas a la vez. Alturas de esquema, sin cifras.
  tablero(THREE, scene, { datos, rotulo }) {
    const T = 4.2, ARMA = 1.9, N = 11, TU = 3, HB = 34;
    scene.add(suelo(THREE));
    const ruido = (a, b) => { const x = Math.sin(a * 12.9898 + b * 78.233) * 43758.5453; return x - Math.floor(x); };
    // Una losa de esquinas apenas redondeadas, con su filo claro: la pieza de cada capa.
    const losa = (w, d, color, alto = 2) => {
      const r = 3, s = new THREE.Shape(), x = w / 2, z = d / 2;
      s.moveTo(-x + r, -z); s.lineTo(x - r, -z); s.quadraticCurveTo(x, -z, x, -z + r); s.lineTo(x, z - r);
      s.quadraticCurveTo(x, z, x - r, z); s.lineTo(-x + r, z); s.quadraticCurveTo(-x, z, -x, z - r);
      s.lineTo(-x, -z + r); s.quadraticCurveTo(-x, -z, -x + r, -z);
      const g = new THREE.ExtrudeGeometry(s, { depth: alto, bevelEnabled: false, curveSegments: 4 }); g.rotateX(-Math.PI / 2);
      const grupo = new THREE.Group(), m = new THREE.Mesh(g, lam(THREE, color));
      m.castShadow = true; m.receiveShadow = true;
      const filo = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(s.getPoints(4).map(p => new THREE.Vector3(p.x, alto + 0.05, -p.y))),
        new THREE.LineBasicMaterial({ color: C.teal, transparent: true, opacity: 0.5 }));
      grupo.add(m, filo); scene.add(grupo); grupo.userData = { w, d };
      return grupo;
    };
    // La ventana: barra con sus tres puntos, menú lateral y la huella de cada capa que flota encima.
    const ventana = losa(330, 224, '#12322B', 3);
    ventana.add(new THREE.Mesh(new THREE.BoxGeometry(326, 0.8, 14).translate(0, 3.4, -104), lam(THREE, '#1A4238')));
    [0, 1, 2].forEach(i => { const p = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 1.8, 0.8, 14), lam(THREE, i ? '#3F6158' : C.ambar)); p.position.set(-152 + i * 7, 4, -104); ventana.add(p); });
    ventana.add(new THREE.Mesh(new THREE.BoxGeometry(30, 0.8, 196).translate(-146, 3.4, 10), lam(THREE, '#173B33')));
    for (let i = 0; i < 7; i++) ventana.add(new THREE.Mesh(new THREE.BoxGeometry(i === 1 ? 20 : 16, 0.5, 2.6).translate(-148 + (i === 1 ? 2 : 0), 4, -80 + i * 13), lam(THREE, i === 1 ? C.teal : '#33574D')));
    const huella = (x, z, w, d) => {
      const pts = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => new THREE.Vector3(x + a * w / 2, 3.1, z + b * d / 2));
      ventana.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: C.teal, transparent: true, opacity: 0.22 })));
    };
    // Las capas que flotan: [losa, x, altura, z].
    const mapa = losa(148, 196, '#1B4339'), rank = losa(132, 74, '#1B4339');
    const tarjetas = datos.map(() => losa(60, 32, '#1F4A3F'));
    const capas = [[mapa, -66, 34, 6], [rank, 82, 58, 54], ...tarjetas.map((t, j) => [t, 50 + (j % 2) * 68, 78, -86 + Math.floor(j / 2) * 46])];
    capas.forEach(([g, x, , z]) => huella(x, z, g.userData.w, g.userData.d));

    // El mapa: los puntos de Colombia agregados en hexágonos grandes, para que cada columna se lea.
    const S = 0.56, K = 10.2, R = S * K / Math.sqrt(3) * 0.9;
    const o = new THREE.Object3D(), col = new THREE.Color();
    let malla = null, celdas = [], elegidas = [];
    fetch('/datos/co.json').then(r => r.json()).then(D => {
      const cuenta = new Map();
      for (const [lon, lat] of D.land) {
        const f = Math.round((lat + 4.3) / (S * 0.866)), c = Math.round((lon + 79.2) / S - (f % 2) * 0.5);
        cuenta.set(f * 1000 + c, (cuenta.get(f * 1000 + c) || 0) + 1);
      }
      for (const [k, n] of cuenta) {
        if (n < 4) continue;
        const f = Math.floor(k / 1000), c = k % 1000;
        const lon = -79.2 + (c + (f % 2) * 0.5) * S, lat = -4.3 + f * S * 0.866;
        if (lon < -79.6) continue;  // las islas quedan fuera del recuadro
        celdas.push({ x: (lon + 73.1) * K, z: -(lat - 4.1) * K, lon, lat, h: 0.1, hObj: 0.1 });
      }
      const g = new THREE.CylinderGeometry(R, R, 1, 6); g.translate(0, 0.5, 0);
      malla = new THREE.InstancedMesh(g, lam(THREE, '#FFFFFF', { flatShading: true }), celdas.length);
      malla.castShadow = true; malla.receiveShadow = true; malla.position.y = 2; mapa.add(malla);
      // El municipio elegido cambia con cada indicador: cerca de varias ciudades, para que la escena varíe.
      const cerca = (lo, la) => celdas.reduce((b, c, i) => Math.hypot(c.lon - lo, c.lat - la) < Math.hypot(celdas[b].lon - lo, celdas[b].lat - la) ? i : b, 0);
      elegidas = [[-74.1, 4.6], [-75.6, 6.2], [-76.5, 3.4], [-74.8, 10.9], [-73.1, 7.1]].map(p => cerca(...p));
      ind = -1;
    });
    const anillo = new THREE.Mesh(new THREE.RingGeometry(0.86, 1, 48), new THREE.MeshBasicMaterial({ color: C.ambar, transparent: true, side: THREE.DoubleSide, depthWrite: false }));
    anillo.rotation.x = -Math.PI / 2; mapa.add(anillo);

    // El ranking: once columnas; la de tu municipio, en ámbar, y la línea del promedio.
    const gb = new THREE.BoxGeometry(6.6, 1, 6.6); gb.translate(0, 0.5, 0);
    const barras = Array.from({ length: N }, (_, j) => {
      const m = new THREE.Mesh(gb, lam(THREE, j === TU ? C.ambar : '#86C6B8')); m.castShadow = true; m.position.set(0, 2, 6); rank.add(m);
      return { m, x: (j - 5) * 9.6, h: 0.2, xObj: 0, hObj: 0.2 };
    });
    for (let i = 1; i <= 3; i++) { const l = new THREE.Mesh(new THREE.BoxGeometry(110, 0.3, 0.3), new THREE.MeshBasicMaterial({ color: C.linea })); l.position.set(0, 2 + i * HB / 3, -4); rank.add(l); }
    const prom = new THREE.Mesh(new THREE.BoxGeometry(112, 0.7, 0.7), new THREE.MeshBasicMaterial({ color: C.crema })); rank.add(prom);
    let promH = 0.5, promObj = 0.5;

    // Las tarjetas: la tendencia de cada indicador, una cinta que se dibuja tramo a tramo.
    const P = 9, gs = new THREE.BoxGeometry(1, 1.1, 1.1);
    const cintas = tarjetas.map(t => Array.from({ length: P - 1 }, () => { const m = new THREE.Mesh(gs, new THREE.MeshBasicMaterial({ color: C.teal })); t.add(m); return m; }));
    const punto = new THREE.Mesh(new THREE.SphereGeometry(1.6, 12, 8), new THREE.MeshBasicMaterial({ color: C.ambar })); scene.add(punto);

    // Los hilos de la vista explotada: de las esquinas de cada capa a su huella en la ventana.
    const hilos = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: C.teal, transparent: true, opacity: 0.3 }));
    hilos.geometry.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(capas.length * 4 * 6), 3)); scene.add(hilos);
    // El pulso que va del municipio en el mapa a su columna en el ranking.
    const pulso = new THREE.Mesh(new THREE.SphereGeometry(2.2, 14, 10), new THREE.MeshBasicMaterial({ color: C.ambar })); scene.add(pulso);
    const estela = new THREE.Line(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 24 }, () => new THREE.Vector3())),
      new THREE.LineBasicMaterial({ color: C.ambar, transparent: true, opacity: 0.55 })); scene.add(estela);

    const rTit = rotulo('', 'titulo-t'), rTu = rotulo('Tu municipio', 'tu');
    const rTarj = datos.map(d => rotulo(`<b>${d.t}</b><small>${d.e}</small>`, 'tarj'));
    const rRank = rotulo('Frente a 10 comparables', 'capa'), rMapa = rotulo('Por zona', 'capa');
    const BASE = new THREE.Color('#24493F'), ALTA = new THREE.Color('#B4EBDD'), AMB = new THREE.Color(C.ambar);
    const a3 = new THREE.Vector3(), b3 = new THREE.Vector3();
    let ind = -1, sel = -1;
    return {
      alto: 298, altoAngosto: 350, az: -0.58, pol: 0.84, mira: [4, 60, 10], miraAngosta: [6, 84, 10], sombras: 230, vaiven: 0.06, quieto: ARMA + 1.6,
      paso(s) {
        // Se arma: de una pila plana sobre la ventana a la vista explotada; luego flota apenas.
        const k = tramo(s, 0.15, ARMA);
        capas.forEach(([g, x, y, z], j) => g.position.set(x, 3 + (y - 3) * k + j * 1.4 * (1 - k) + Math.sin(s * 0.9 + j * 1.3) * 1.2 * k, z));
        const t = Math.max(0, s - ARMA * 0.8), n = Math.floor(t / T), f = t - n * T, i = n % datos.length;
        if (n !== ind) {
          ind = n;
          rTit.innerHTML = `<b>${datos[i].t}</b><small>Publica: ${datos[i].e} · tu municipio frente a los comparables</small>`;
          rTarj.forEach((r, j) => r.classList.toggle('activa', j === i));
          // Un patrón que cambia con el territorio, no ruido: así se lee como un mapa de verdad.
          celdas.forEach(c => {
            const v = 0.5 + 0.42 * Math.sin(c.lon * 0.62 + i * 1.9) * Math.cos(c.lat * 0.38 + i * 2.6) + 0.22 * (ruido(c.lon + i, c.lat) - 0.5);
            c.hObj = Math.min(1, Math.max(0.05, v));
          });
          sel = elegidas.length ? elegidas[n % elegidas.length] : -1;
          const vs = barras.map((_, j) => 0.2 + 0.8 * ruido(i + 3, j)), orden = vs.map((v, j) => [v, j]).sort((a, b) => b[0] - a[0]);
          orden.forEach(([v, j], r) => { barras[j].xObj = (r - (N - 1) / 2) * 9.6; barras[j].hObj = v; });
          promObj = vs.reduce((a, b) => a + b, 0) / N;
        }
        rTit.classList.toggle('ver', k > 0.7 && f > 0.15);
        const ent = tramo(f, 0.1, 0.8);
        if (malla) {
          celdas.forEach((c, q) => {
            c.h += (c.hObj - c.h) * 0.06;
            const alto = (0.8 + c.h * 13 + (q === sel ? 18 * ent : 0)) * (0.15 + 0.85 * k);
            o.position.set(c.x, 0, c.z); o.scale.set(1, alto, 1); o.updateMatrix(); malla.setMatrixAt(q, o.matrix);
            malla.setColorAt(q, q === sel ? col.copy(ALTA).lerp(AMB, ent) : col.copy(BASE).lerp(ALTA, Math.pow(c.h, 1.4)));
          });
          malla.instanceMatrix.needsUpdate = true; malla.instanceColor.needsUpdate = true;
        }
        barras.forEach((b, j) => {
          const g = Math.min(1, Math.max(0, (f - 0.3 - j * 0.03) / 0.9));
          b.x += (b.xObj - b.x) * (0.05 + 0.1 * g); b.h += (b.hObj - b.h) * (0.05 + 0.1 * g);
          b.m.position.x = b.x; b.m.scale.y = Math.max(0.4, b.h * HB * k);
        });
        promH += (promObj - promH) * 0.07; prom.position.set(0, 2 + promH * HB * k, 11);
        // La cinta de la tarjeta activa se dibuja; las demás quedan quietas y apagadas.
        cintas.forEach((cinta, j) => {
          const activa = j === i, dib = activa ? tramo(f, 0.5, 1.8) * (P - 1) : P - 1;
          const y = p => 3 + 2 + ruido(j * 7 + (activa ? i : 0), p) * 10;
          cinta.forEach((m, p) => {
            const x0 = -22 + p * 44 / (P - 1), x1 = x0 + 44 / (P - 1), y0 = y(p), y1 = y(p + 1), dx = x1 - x0, dy = y1 - y0;
            const vis = Math.min(1, Math.max(0, dib - p));
            m.visible = vis > 0;
            m.scale.x = Math.max(0.001, Math.hypot(dx, dy) * vis); m.position.set(x0 + dx * vis / 2, y0 + dy * vis / 2, 6); m.rotation.z = Math.atan2(dy, dx);
            m.material.color.set(activa ? C.ambar : '#4E7D71');
          });
          if (activa) {
            const pi = Math.min(P - 1, Math.floor(dib)), r = dib - pi;
            punto.position.set(-22 + dib * 44 / (P - 1), y(pi) + (y(Math.min(P - 1, pi + 1)) - y(pi)) * r, 6);
            tarjetas[j].localToWorld(punto.position);
          }
        });
        punto.visible = k > 0.9;
        // Del municipio elegido a su columna en el ranking, en arco, con estela.
        if (malla && sel >= 0) {
          const c = celdas[sel];
          mapa.localToWorld(a3.set(c.x, 2 + (0.8 + c.h * 13 + 18 * ent) * (0.15 + 0.85 * k), c.z));
          rank.localToWorld(b3.set(barras[TU].x, 2 + barras[TU].h * HB * k, 6));
          const u = tramo(f, 0.55, 1.5), A = [a3.x, a3.y, a3.z], B = [b3.x, b3.y, b3.z];
          arco(pulso.position, A, B, u, 34); pulso.visible = u > 0.01 && u < 0.99 && k > 0.9;
          const pos = estela.geometry.attributes.position;
          for (let p = 0; p < 24; p++) { arco(a3, A, B, Math.max(0, u - p * 0.012), 34); pos.setXYZ(p, a3.x, a3.y, a3.z); }
          pos.needsUpdate = true; estela.visible = pulso.visible;
          anillo.position.set(c.x, 2.3, c.z); const e = tramo(f, 0.1, 1.3); anillo.scale.setScalar(3 + e * 18); anillo.material.opacity = (1 - e) * 0.9 * k;
        }
        const pos = hilos.geometry.attributes.position;
        let q = 0;
        capas.forEach(([g]) => {
          const { w, d } = g.userData, p = g.position;
          [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([a, b]) => {
            pos.setXYZ(q++, p.x + a * w / 2, p.y, p.z + b * d / 2); pos.setXYZ(q++, p.x + a * w / 2, 3.1, p.z + b * d / 2);
          });
        });
        pos.needsUpdate = true; hilos.material.opacity = 0.16 * k;
      },
      rotular(poner) {
        tarjetas.forEach((t, j) => { const p = t.position; poner(rTarj[j], p.x - 28, p.y + 2, p.z - 13); });
        const r = rank.position, m = mapa.position;
        poner(rRank, r.x - 64, r.y + 2, r.z + 35); poner(rMapa, m.x - 72, m.y + 2, m.z + 96);
        if (malla && sel >= 0) { const c = celdas[sel]; poner(rTu, m.x + c.x, m.y + 2 + 0.8 + c.h * 13 + 16, m.z + c.z); }
      },
    };
  },

  // Vigilancia: lo que publica cada fuente pasa por su carril; cuando algo que vigilas cruza la
  // línea de hoy, se levanta y llega a tus alertas.
  vigilancia(THREE, scene, { datos, rotulo }) {
    const carriles = datos, ZS = [-54, -18, 18, 54], X0 = -110, X1 = 96, HOY = 56, VEL = 24, LARGO = X1 - X0;
    scene.add(suelo(THREE));
    ZS.forEach(z => {
      const c = new THREE.Mesh(new THREE.PlaneGeometry(LARGO, 20), lam(THREE, '#1D4238')); c.rotation.x = -Math.PI / 2; c.position.set((X0 + X1) / 2, 0.1, z); c.receiveShadow = true; scene.add(c);
      for (let x = X0 + 10; x < X1; x += 26) { const t = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 20), new THREE.MeshBasicMaterial({ color: C.linea })); t.rotation.x = -Math.PI / 2; t.position.set(x, 0.15, z); scene.add(t); }
    });
    // La línea de hoy.
    const linea = new THREE.Mesh(new THREE.PlaneGeometry(132, 34), new THREE.MeshBasicMaterial({ color: C.teal, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }));
    linea.rotation.y = Math.PI / 2; linea.position.set(HOY, 17, 0); scene.add(linea);
    const filo = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 132), new THREE.MeshBasicMaterial({ color: C.teal })); filo.position.set(HOY, 34, 0); scene.add(filo);
    const piso = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.4, 132), new THREE.MeshBasicMaterial({ color: C.teal })); piso.position.set(HOY, 0.3, 0); scene.add(piso);
    // La bandeja de alertas.
    const BAN = [132, 0, 0];
    const bandeja = new THREE.Mesh(new THREE.BoxGeometry(40, 3, 30).translate(0, 1.5, 0), lam(THREE, '#EEF1EC')); bandeja.position.set(...BAN); bandeja.castShadow = bandeja.receiveShadow = true; scene.add(bandeja);
    const avisos = Array.from({ length: 6 }, () => { const m = new THREE.Mesh(new THREE.BoxGeometry(30, 1.6, 20).translate(0, 0.8, 0), lam(THREE, C.ambar)); m.castShadow = true; m.visible = false; scene.add(m); return m; });
    // Los eventos: cada carril con su ritmo; algunos son de lo que vigilas.
    const ev = [], g = new THREE.BoxGeometry(13, 6, 11); g.translate(0, 3, 0);
    carriles.forEach((_, i) => {
      for (let j = 0; j < 7; j++) {
        const m = lam(THREE, '#55786E'), mesh = new THREE.Mesh(g, m); mesh.castShadow = true; scene.add(mesh);
        ev.push({ mesh, m, carril: i, fase: j * (LARGO / 7) + ((i * 37 + j * 23) % 19), vigila: (i + j * 3) % 7 === 0 });
      }
    });
    const rCar = carriles.map(c => rotulo(`<b>${c.s}</b><small>${c.e}</small>`, 'carril'));
    const rHoy = rotulo('hoy', 'lugar'), rBan = rotulo('Tus alertas', 'lugar'), rAviso = rotulo('', 'aviso');
    const GRIS = new THREE.Color('#55786E'), AMB = new THREE.Color(C.ambar), CREMA = new THREE.Color('#BFD3CB');
    const p = new THREE.Vector3();
    let ultimo = null, visto = -10;
    return {
      alto: 262, az: -0.14, pol: 0.9, mira: [-34, 0, 6], sombras: 240, vaiven: 0.05, quieto: 6,
      paso(s) {
        let llegadas = 0, reciente = null;
        for (const e of ev) {
          const recorrido = e.fase + s * VEL, vuelta = Math.floor(recorrido / LARGO), x = X0 + (recorrido % LARGO);
          const z = ZS[e.carril], orilla = Math.min(1, (x - X0) / 14, (X1 - x) / 14);
          const pasado = e.vigila ? suave((x - HOY) / 10) : 0;
          e.mesh.position.set(x, pasado * 7, z); e.mesh.scale.setScalar(Math.max(0.01, orilla));
          e.m.color.copy(e.vigila ? CREMA : GRIS).lerp(AMB, pasado);
          if (e.vigila) {
            // Una alerta por cada vez que algo vigilado cruza la línea de hoy.
            llegadas += vuelta + (x > HOY ? 1 : 0);
            const t = (x - HOY) / VEL;  // segundos desde que cruzó
            if (x > HOY && t < 1.2 && (!reciente || t < reciente.t)) reciente = { e, t, x, z };
          }
        }
        const total = llegadas % 6;
        avisos.forEach((a, i) => { a.visible = i < total; a.position.set(BAN[0], 3 + i * 1.9, BAN[2]); });
        if (reciente) {
          const a = avisos[Math.max(0, total - 1)];
          arco(p, [reciente.x, 8, reciente.z], [BAN[0], 3 + Math.max(0, total - 1) * 1.9, BAN[2]], suave(reciente.t / 1.0), 30);
          a.position.copy(p); a.visible = true; visto = s;
          if (ultimo !== reciente.e) {
            ultimo = reciente.e; const c = carriles[reciente.e.carril];
            rAviso.innerHTML = `<i></i><span><small>${c.s}</small>${c.ev}</span>`;
          }
        }
        rAviso.classList.toggle('ver', !!ultimo && s - visto < 2.4);
      },
      rotular(poner) {
        rCar.forEach((r, i) => poner(r, X0 - 4, 1, ZS[i]));
        poner(rHoy, HOY, 2, 74); poner(rBan, BAN[0], 4, BAN[2] + 22);
      },
    };
  },

  // Asistente: la pregunta, de una herramienta real, viaja a la entidad que la responde y vuelve
  // con su fuente y su licencia.
  asistente(THREE, scene, { datos, rotulo }) {
    const { preguntas, nodos } = datos, N = nodos.length, RAD = 112, T = 4.4;
    scene.add(suelo(THREE));
    const disco = new THREE.Mesh(new THREE.CylinderGeometry(RAD + 26, RAD + 26, 1.2, 96), lam(THREE, '#1A3F35')); disco.position.y = 0.4; disco.receiveShadow = true; scene.add(disco);
    // El centro: tu asistente, una pieza de tres placas.
    const centro = new THREE.Group(); scene.add(centro);
    [[34, 4, C.hueso], [28, 3, C.teal], [22, 3, C.crema]].forEach(([r, h, c], i) => {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 6).translate(0, h / 2, 0), lam(THREE, c, { flatShading: true }));
      m.position.y = 1.2 + i * 4.2; m.castShadow = true; centro.add(m);
    });
    const onda = new THREE.Mesh(new THREE.RingGeometry(0.92, 1, 64), new THREE.MeshBasicMaterial({ color: C.ambar, transparent: true, side: THREE.DoubleSide }));
    onda.rotation.x = -Math.PI / 2; onda.position.y = 1.4; scene.add(onda);
    const gn = new THREE.CylinderGeometry(9, 9, 6, 6); gn.translate(0, 3, 0);
    const ns = nodos.map((e, i) => {
      const a = (i / N) * Math.PI * 2 - Math.PI / 2, x = Math.cos(a) * RAD, z = Math.sin(a) * RAD;
      const m = lam(THREE, C.apagado, { flatShading: true }), mesh = new THREE.Mesh(gn, m); mesh.position.set(x, 1.2, z); mesh.castShadow = true; scene.add(mesh);
      const lm = new THREE.LineBasicMaterial({ color: C.teal, transparent: true, opacity: 0.16 });
      scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 8, 0), new THREE.Vector3(x, 5, z)]), lm));
      return { e, x, z, mesh, m, lm, r: rotulo(e, 'nodo') };
    });
    const ida = new THREE.Mesh(new THREE.SphereGeometry(3, 16, 12), new THREE.MeshBasicMaterial({ color: C.ambar })); scene.add(ida);
    const rPreg = rotulo('', 'burbuja'), rResp = rotulo('', 'respuesta');
    const APAG = new THREE.Color(C.apagado), LUZ = new THREE.Color(C.teal);
    let ronda = -1;
    return {
      alto: 330, az: 0, pol: 0.93, mira: [0, 0, 10], sombras: 200, vaiven: 0.1, quieto: 2.2,
      paso(s) {
        const n = Math.floor(s / T), k = s - n * T, q = preguntas[n % preguntas.length];
        const nd = ns.find(x => x.e === q.e);
        if (n !== ronda) {
          ronda = n;
          rPreg.textContent = q.p;
          rResp.innerHTML = `<span>Responde</span> <b>${q.e}</b><small>con su fuente y su licencia: ${q.l}</small>`;
        }
        rPreg.classList.toggle('ver', k > 0.1 && k < T - 0.3);
        rResp.classList.toggle('ver', k > 2.6 && k < T - 0.3);
        const v1 = tramo(k, 0.7, 1.4), v2 = tramo(k, 1.9, 2.6);
        arco(ida.position, [0, 12, 0], [nd.x, 8, nd.z], k < 1.65 ? v1 : 1 - v2, 26); ida.visible = k > 0.7 && k < 2.6;
        const luz = tramo(k, 1.3, 1.5) * (1 - tramo(k, T - 0.5, T));
        ns.forEach(x => {
          const es = x === nd;
          x.m.color.copy(APAG).lerp(LUZ, es ? luz : 0); x.mesh.position.y = 1.2 + (es ? luz * 6 : 0);
          x.lm.opacity = es ? 0.16 + 0.7 * luz : 0.12; x.r.classList.toggle('activo', es && luz > 0.5);
        });
        const e = tramo(k, 2.6, 3.6);
        onda.scale.setScalar(20 + e * 60); onda.material.opacity = k > 2.6 ? 1 - e : 0;
        centro.rotation.y = s * 0.25;
      },
      rotular(poner) {
        ns.forEach(x => poner(x.r, x.x * 1.18, 4, x.z * 1.18));
      },
    };
  },

  // La prueba de una respuesta: el dato y sus capas (procedencia, licencia, de dónde se sirvió y
  // la huella) se separan para leerse y se vuelven a juntar. Valores de una respuesta real.
  prueba(THREE, scene, { el }) {
    const capas = JSON.parse(el.dataset.capas);
    const W = 220, D = 130, G = 7, n = capas.length;
    const forma = new THREE.Shape(); const rr = 10, w = W / 2, d = D / 2;
    forma.moveTo(-w + rr, -d); forma.lineTo(w - rr, -d); forma.quadraticCurveTo(w, -d, w, -d + rr); forma.lineTo(w, d - rr);
    forma.quadraticCurveTo(w, d, w - rr, d); forma.lineTo(-w + rr, d); forma.quadraticCurveTo(-w, d, -w, d - rr); forma.lineTo(-w, -d + rr); forma.quadraticCurveTo(-w, -d, -w + rr, -d);
    const geo = new THREE.ExtrudeGeometry(forma, { depth: G, bevelEnabled: true, bevelThickness: 0.8, bevelSize: 0.8, bevelSegments: 2 });
    geo.rotateX(-Math.PI / 2);
    // La cara superior lleva el texto como textura (plano encima de la losa).
    const tapa = new THREE.PlaneGeometry(W - 6, D - 6); tapa.rotateX(-Math.PI / 2);
    const losas = capas.map((c, i) => {
      const tex = textura(THREE, 1024, 600, (x, fuente) => {
        x.fillStyle = i === 0 ? '#FFFFFF' : '#F6F7F4'; x.fillRect(0, 0, 1024, 600);
        // Con las capas abiertas, de cada losa de abajo solo se ve su borde cercano: ahí va el texto.
        const y0 = i === 0 ? 120 : 330;
        x.fillStyle = i === 0 ? '#8F570B' : '#236E62'; x.font = '500 44px "Geist Mono", ui-monospace, monospace'; x.fillText(c.campo, 64, y0);
        x.fillStyle = '#12261F'; x.font = `600 ${i === 0 ? 84 : 68}px ${fuente}`;
        const palabras = c.valor.split(' '); let linea = '', y = i === 0 ? 270 : y0 + 96;
        for (const p of palabras) { const t = linea ? linea + ' ' + p : p; if (x.measureText(t).width > 890 && linea) { x.fillText(linea, 64, y); linea = p; y += i === 0 ? 96 : 78; } else linea = t; }
        x.fillText(linea, 64, y);
        if (c.nota) { x.fillStyle = '#4E5E57'; x.font = `400 38px ${fuente}`; x.fillText(c.nota, 64, i === 0 ? 530 : 545); }
      });
      const g = new THREE.Group();
      const m = lam(THREE, i === 0 ? C.ambar : '#DCE3DA');
      const cara = new THREE.Mesh(tapa, new THREE.MeshBasicMaterial({ map: tex })); cara.position.y = G + 0.9;
      g.add(new THREE.Mesh(geo, m), cara); scene.add(g);
      return { g, m, base: new THREE.Color(i === 0 ? C.ambar : '#DCE3DA') };
    });
    const sombra = new THREE.Mesh(new THREE.PlaneGeometry(W * 1.3, D * 1.5), new THREE.MeshBasicMaterial({ color: '#0E2A22', transparent: true, opacity: 0.08, depthWrite: false }));
    sombra.rotation.x = -Math.PI / 2; sombra.position.y = -2; scene.add(sombra);
    const notas = [...document.querySelectorAll('[data-capa]')];
    const CICLO = 11, SEP = 64, VIVO = new THREE.Color(C.teal);
    const brillo = new Float32Array(n);
    let activa = -1;
    return {
      alto: 420, az: -0.55, pol: 0.9, mira: [0, 120, 0], vaiven: 0.12, quieto: 4,
      paso(s) {
        const f = (s % CICLO) / CICLO;
        // Juntas (0–0.1), se abren (0.1–0.26), abiertas (0.26–0.84), se cierran (0.84–1).
        const k = f < 0.1 ? 0 : f < 0.26 ? suave((f - 0.1) / 0.16) : f < 0.84 ? 1 : 1 - suave((f - 0.84) / 0.16);
        const turno = k === 1 ? Math.min(n - 1, Math.floor((f - 0.26) / 0.58 * n)) : -1;
        losas.forEach((l, i) => {
          const desde = n - 1 - i;  // la de arriba es el dato
          brillo[i] += ((i === turno ? 1 : 0) - brillo[i]) * 0.12;
          l.g.position.y = desde * (G + 1.2) + k * desde * SEP;
          l.g.position.x = k * desde * -6 + brillo[i] * 16;
          l.m.color.copy(l.base).lerp(VIVO, i === 0 ? 0 : brillo[i] * 0.8);
        });
        // Con las capas abiertas, cada nota se ilumina por turnos, junto con su capa.
        if (turno !== activa) { activa = turno; notas.forEach(nt => nt.classList.toggle('activa', +nt.dataset.capa === turno)); }
        sombra.material.opacity = 0.08 + 0.04 * (1 - k);
      },
    };
  },
};
