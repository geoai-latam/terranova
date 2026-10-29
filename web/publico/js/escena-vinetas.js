// Viñetas 3D de los servicios y de la prueba de cada respuesta. Cada elemento [data-vineta] tiene
// su propio lienzo, se crea al acercarse a la vista y solo dibuja mientras se ve. Son esquemas: no
// muestran cifras inventadas, solo cómo se mueve el trabajo.
import { cargarThree, quieto, suave, visible } from './comun3d.js';

const C = {
  crema: '#F3EFE4', hueso: '#E4E9E2', teal: '#6CC3B3', tealOsc: '#236E62', ambar: '#E0A13A',
  bosque: '#0E2A22', linea: '#3E6157',
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
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  el.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  scene.add(new THREE.HemisphereLight('#FFFFFF', oscuro ? '#28463D' : '#AEB9B1', oscuro ? 1.7 : 2.1));
  const sol = new THREE.DirectionalLight('#FFF8EC', oscuro ? 1.3 : 1.4); sol.position.set(-200, 400, 260); scene.add(sol);

  const v = VINETAS[tipo](THREE, scene, el);
  const st = { az: v.az ?? -0.7, pol: v.pol ?? 0.95, px: 0 };
  function tam() {
    const w = el.clientWidth, h = el.clientHeight; renderer.setSize(w, h, false);
    const H = v.alto * (w / h < 1.1 ? 1.25 : 1), W = H * w / h;
    cam.left = -W / 2; cam.right = W / 2; cam.top = H / 2 + (v.sube ?? 0); cam.bottom = -H / 2 + (v.sube ?? 0);
    cam.updateProjectionMatrix();
  }
  new ResizeObserver(tam).observe(el); tam();
  // Un leve paralaje con el puntero: la escena responde, sin pedir que la arrastren.
  el.addEventListener('pointermove', e => { const r = el.getBoundingClientRect(); st.px = ((e.clientX - r.left) / r.width - 0.5); });
  el.addEventListener('pointerleave', () => { st.px = 0; });

  let corre = true, t0 = null, az = st.az;
  visible(el, si => { const antes = corre; corre = si; if (si && !antes) requestAnimationFrame(cuadro); });
  function cuadro(t) {
    if (t0 === null) t0 = t;
    const s = quieto ? (v.quieto ?? 4) : (t - t0) / 1000;
    v.paso(s);
    az += ((st.az + st.px * 0.5 + (quieto || v.fijo ? 0 : Math.sin(s * 0.12) * 0.18)) - az) * 0.05;
    const R = 1500;
    cam.position.set(R * Math.sin(st.pol) * Math.sin(az), R * Math.cos(st.pol), R * Math.sin(st.pol) * Math.cos(az));
    cam.lookAt(0, v.mira ?? 0, 0);
    renderer.render(scene, cam);
    if (v.rotular) v.rotular(cam);
    el.classList.add('viva');
    if (corre && !quieto) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}

const lam = (THREE, color, extra = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
const mezcla = (THREE, a, b, k) => new THREE.Color(a).lerp(new THREE.Color(b), k);
const borde = (THREE, geo, color, op = 0.5) => new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), new THREE.LineBasicMaterial({ color, transparent: true, opacity: op }));
// Un pseudoazar fijo: la misma escena cada vez.
const azar = semilla => () => { semilla = (semilla * 16807) % 2147483647; return (semilla - 1) / 2147483646; };

const VINETAS = {
  // Revisión de una lista: predios, empresas y contratos pasan por la compuerta de las fuentes
  // oficiales; salen en teal si no hay hallazgos y en ámbar, más altos, si hay algo que revisar.
  revision(THREE, scene) {
    const N = 14, PASO = 46, VEL = 26;
    const formas = [
      () => { const s = new THREE.Shape([[-15, -12], [14, -14], [17, 9], [-4, 15], [-16, 6]].map(p => new THREE.Vector2(...p))); return new THREE.ExtrudeGeometry(s, { depth: 4, bevelEnabled: false }).rotateX(-Math.PI / 2); },
      () => new THREE.BoxGeometry(24, 4, 30).translate(0, 2, 0),
      () => new THREE.CylinderGeometry(14, 14, 4, 6).translate(0, 2, 0),
    ];
    const items = [];
    for (let i = 0; i < N; i++) {
      const g = formas[i % 3](), m = lam(THREE, C.hueso);
      const mesh = new THREE.Mesh(g, m); mesh.add(borde(THREE, g, C.bosque, 0.25));
      const revisar = [2, 6, 9, 13].includes(i);
      // Lo que hay que revisar sale con una banderita ámbar.
      let bandera = null;
      if (revisar) {
        bandera = new THREE.Group();
        const asta = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 22, 6).translate(0, 11, 0), lam(THREE, C.crema));
        const tela = new THREE.Mesh(new THREE.PlaneGeometry(11, 7).translate(5.5, 18, 0), new THREE.MeshLambertMaterial({ color: C.ambar, side: THREE.DoubleSide }));
        bandera.add(asta, tela); bandera.position.set(6, 4, 4); mesh.add(bandera);
      }
      scene.add(mesh); items.push({ mesh, m, revisar, bandera, fase: i * PASO });
    }
    // La compuerta: un marco con una cortina translúcida que barre.
    const marco = new THREE.Group();
    const barra = (w, h, d, x, y) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), lam(THREE, C.tealOsc)); b.position.set(x, y, 0); marco.add(b); };
    barra(4, 70, 4, 0, 35 - 2); marco.children[0].position.z = -34; barra(4, 70, 4, 0, 33); marco.children[1].position.z = 34;
    const dintel = new THREE.Mesh(new THREE.BoxGeometry(4, 4, 72), lam(THREE, C.tealOsc)); dintel.position.y = 68; marco.add(dintel);
    const cortina = new THREE.Mesh(new THREE.PlaneGeometry(68, 64), new THREE.MeshBasicMaterial({ color: C.teal, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false }));
    cortina.rotation.y = Math.PI / 2; cortina.position.y = 34; marco.add(cortina);
    const haz = new THREE.Mesh(new THREE.PlaneGeometry(68, 1.6), new THREE.MeshBasicMaterial({ color: C.teal, transparent: true, opacity: 0.9, side: THREE.DoubleSide }));
    haz.rotation.y = Math.PI / 2; marco.add(haz);
    scene.add(marco);
    // La banda por donde corren.
    const banda = new THREE.Mesh(new THREE.BoxGeometry(N * PASO, 2, 56), lam(THREE, '#1B3B32')); banda.position.y = -1.2; scene.add(banda);
    const rayas = new THREE.Group();
    for (let i = 0; i < N * 2; i++) { const l = new THREE.Mesh(new THREE.PlaneGeometry(1, 56), new THREE.MeshBasicMaterial({ color: C.linea })); l.rotation.x = -Math.PI / 2; l.position.y = 0.05; rayas.add(l); }
    scene.add(rayas);
    const largo = N * PASO, OK = new THREE.Color(C.teal), MAL = new THREE.Color(C.ambar), BASE = new THREE.Color(C.hueso);
    return {
      alto: 215, az: -0.62, pol: 1.0, mira: 22, sube: 14,
      paso(s) {
        haz.position.y = 34 + Math.sin(s * 2.4) * 30;
        rayas.children.forEach((l, i) => { l.position.x = ((i * PASO / 2 + s * VEL) % largo) - largo / 2; });
        for (const it of items) {
          const x = ((it.fase + s * VEL) % largo) - largo / 2;
          const k = suave((x + 4) / 30);  // 0 antes de la compuerta, 1 después
          it.mesh.position.set(x, k * (it.revisar ? 18 : 6), 0);
          it.m.color.copy(BASE).lerp(it.revisar ? MAL : OK, k);
          it.mesh.rotation.y = it.revisar ? k * 0.25 : 0;
          if (it.bandera) { it.bandera.scale.setScalar(Math.max(0.001, suave((x - 14) / 16))); it.bandera.children[1].rotation.y = Math.sin(s * 5 + it.fase) * 0.3; }
        }
      },
    };
  },

  // Tableros: los municipios como prismas hexagonales; cada pocos segundos cambia el indicador y
  // las alturas se reacomodan.
  tablero(THREE, scene) {
    const r = azar(11), R = 11, cols = 11, filas = 8;
    const geo = new THREE.CylinderGeometry(R * 0.9, R * 0.9, 1, 6); geo.translate(0, 0.5, 0);
    const n = cols * filas, mesh = new THREE.InstancedMesh(geo, lam(THREE, '#FFFFFF', { flatShading: true }), n);
    const pos = [], capas = [[], [], []];
    for (let f = 0; f < filas; f++) for (let c = 0; c < cols; c++) {
      const x = (c - cols / 2 + (f % 2) * 0.5) * R * 1.75, z = (f - filas / 2) * R * 1.52;
      pos.push([x, z]);
      const d = Math.hypot(x / 90, z / 60);
      capas[0].push(Math.max(0, 1 - d) * 0.8 + r() * 0.3);
      capas[1].push(r() ** 2);
      capas[2].push(Math.max(0, Math.sin(x / 30) * 0.5 + 0.5) * (0.4 + r() * 0.6));
    }
    scene.add(mesh);
    const o = new THREE.Object3D(), A = new THREE.Color('#2D5248'), B = new THREE.Color(C.teal), X = new THREE.Color(C.ambar);
    const piso = new THREE.Mesh(new THREE.PlaneGeometry(240, 170), lam(THREE, '#173A31')); piso.rotation.x = -Math.PI / 2; piso.position.y = -0.2; scene.add(piso);
    const ciclo = 3.2;
    return {
      alto: 245, az: -0.5, pol: 0.92, mira: 10, sube: 4,
      paso(s) {
        const i = Math.floor(s / ciclo) % 3, j = (i + 1) % 3, k = suave(((s % ciclo) - 2.2) / 1);
        const top = Math.floor(s / ciclo) % n;
        for (let q = 0; q < n; q++) {
          const v = capas[i][q] + (capas[j][q] - capas[i][q]) * k;
          o.position.set(pos[q][0], 0, pos[q][1]); o.scale.set(1, 2 + v * 70, 1); o.updateMatrix(); mesh.setMatrixAt(q, o.matrix);
          mesh.setColorAt(q, (q * 37 + top * 13) % n === 0 ? X : A.clone().lerp(B, Math.min(1, v * 1.1)));
        }
        mesh.instanceMatrix.needsUpdate = true; mesh.instanceColor.needsUpdate = true;
      },
    };
  },

  // Vigilancia: un barrido pasa sobre lo que vigilas; cuando algo cambia, sube una señal ámbar.
  vigilancia(THREE, scene) {
    const r = azar(3), N = 46, RAD = 100;
    const disco = new THREE.Mesh(new THREE.CircleGeometry(RAD + 8, 64), lam(THREE, '#173A31')); disco.rotation.x = -Math.PI / 2; scene.add(disco);
    for (const rr of [35, 70, RAD + 8]) {
      const a = new THREE.Mesh(new THREE.RingGeometry(rr - 0.4, rr + 0.4, 96), new THREE.MeshBasicMaterial({ color: C.linea })); a.rotation.x = -Math.PI / 2; a.position.y = 0.1; scene.add(a);
    }
    const puntos = [];
    const g = new THREE.CylinderGeometry(2.6, 2.6, 5, 12); g.translate(0, 2.5, 0);
    for (let i = 0; i < N; i++) {
      const a = r() * Math.PI * 2, d = 14 + Math.sqrt(r()) * (RAD - 14);
      const m = lam(THREE, '#5E8077'), p = new THREE.Mesh(g, m); p.position.set(Math.cos(a) * d, 0, Math.sin(a) * d);
      scene.add(p); puntos.push({ p, m, a: (a + Math.PI * 2) % (Math.PI * 2) });
    }
    // El barrido: un abanico translúcido.
    const abanico = new THREE.Mesh(new THREE.CircleGeometry(RAD + 6, 48, 0, 0.7), new THREE.MeshBasicMaterial({ color: C.teal, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false }));
    abanico.rotation.x = -Math.PI / 2; abanico.position.y = 0.4; scene.add(abanico);
    const filo = new THREE.Mesh(new THREE.PlaneGeometry(RAD + 6, 1.4), new THREE.MeshBasicMaterial({ color: C.teal, side: THREE.DoubleSide }));
    filo.geometry.translate((RAD + 6) / 2, 0, 0); filo.rotation.x = -Math.PI / 2; filo.position.y = 0.5; scene.add(filo);
    // La señal: un poste y una onda en el punto que cambió.
    const poste = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 1, 8).translate(0, 0.5, 0), lam(THREE, C.ambar));
    const cabeza = new THREE.Mesh(new THREE.OctahedronGeometry(5), lam(THREE, C.ambar, { flatShading: true }));
    const onda = new THREE.Mesh(new THREE.RingGeometry(0.85, 1, 48), new THREE.MeshBasicMaterial({ color: C.ambar, transparent: true, side: THREE.DoubleSide }));
    onda.rotation.x = -Math.PI / 2; scene.add(poste, cabeza, onda);
    const VEL = 1.1, VUELTA = Math.PI * 2 / VEL, elegidos = [7, 22, 31, 12, 40];
    const gris = new THREE.Color('#5E8077'), luz = new THREE.Color(C.teal), amb = new THREE.Color(C.ambar);
    return {
      alto: 190, az: -0.4, pol: 0.88, sube: 12, quieto: VUELTA * 0.6,
      paso(s) {
        const ang = (s * VEL) % (Math.PI * 2);
        abanico.rotation.z = ang - 0.7; filo.rotation.z = ang;
        const vuelta = Math.floor(s / VUELTA), sel = puntos[elegidos[vuelta % elegidos.length]];
        for (const pt of puntos) {
          const atras = ((ang - (Math.PI * 2 - pt.a)) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
          const brillo = Math.exp(-atras * 2.2);
          pt.m.color.copy(gris).lerp(luz, brillo);
          pt.p.scale.y = 1 + brillo * 0.8;
        }
        // La señal aparece cuando el barrido pasa por el punto elegido de esta vuelta.
        const paso = ((ang - (Math.PI * 2 - sel.a)) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
        const k = suave(paso / 1.2), alto = 10 + k * 34;
        sel.m.color.copy(amb); sel.p.scale.y = 1.6;
        poste.position.copy(sel.p.position); poste.scale.y = alto;
        cabeza.position.set(sel.p.position.x, alto + 5, sel.p.position.z); cabeza.rotation.y = s * 1.5; cabeza.scale.setScalar(0.3 + k * 0.7);
        const ro = suave(paso / 2.4) * 34;
        onda.position.set(sel.p.position.x, 0.6, sel.p.position.z); onda.scale.setScalar(4 + ro); onda.material.opacity = Math.max(0, 1 - ro / 34);
      },
    };
  },

  // Asistente: la pregunta sale del centro hacia las fuentes que hacen falta y vuelve con la
  // respuesta; las fuentes que responden se encienden.
  asistente(THREE, scene) {
    const N = 12, RAD = 92;
    const nucleo = new THREE.Mesh(new THREE.IcosahedronGeometry(17, 1), lam(THREE, C.crema, { flatShading: true }));
    nucleo.position.y = 20; scene.add(nucleo);
    const anillo = new THREE.Mesh(new THREE.TorusGeometry(26, 0.8, 8, 80), lam(THREE, C.ambar)); anillo.position.y = 20; anillo.rotation.x = Math.PI / 2.3; scene.add(anillo);
    const base = new THREE.Mesh(new THREE.CircleGeometry(RAD + 18, 64), lam(THREE, '#173A31')); base.rotation.x = -Math.PI / 2; scene.add(base);
    const nodos = [], lineas = [];
    const gn = new THREE.BoxGeometry(14, 14, 14); gn.translate(0, 7, 0);
    for (let i = 0; i < N; i++) {
      const a = (i / N) * Math.PI * 2, x = Math.cos(a) * RAD, z = Math.sin(a) * RAD;
      const m = lam(THREE, '#4E7268'), n = new THREE.Mesh(gn, m); n.position.set(x, 0, z); n.add(borde(THREE, gn, C.teal, 0.35)); scene.add(n);
      const lg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 20, 0), new THREE.Vector3(x, 7, z)]);
      const lm = new THREE.LineBasicMaterial({ color: C.teal, transparent: true, opacity: 0.18 }), l = new THREE.Line(lg, lm); scene.add(l);
      nodos.push({ n, m, x, z }); lineas.push(lm);
    }
    const pulsos = [0, 1, 2].map(() => { const p = new THREE.Mesh(new THREE.SphereGeometry(3.2, 16, 12), new THREE.MeshBasicMaterial({ color: C.ambar })); scene.add(p); return p; });
    const rondas = [[1, 5, 8], [3, 9, 11], [0, 4, 6], [2, 7, 10]];
    const apagado = new THREE.Color('#4E7268'), prendido = new THREE.Color(C.teal), CICLO = 3.4;
    return {
      alto: 200, az: -0.5, pol: 0.95, mira: 8, sube: 8,
      paso(s) {
        nucleo.rotation.y = s * 0.4; anillo.rotation.z = s * 0.8;
        const ronda = rondas[Math.floor(s / CICLO) % rondas.length], f = (s % CICLO) / CICLO;
        // Ida (0–0.4), espera (0.4–0.55), vuelta (0.55–0.95).
        const ida = suave(f / 0.4), vuelta = suave((f - 0.55) / 0.4), q = f < 0.55 ? ida : 1 - vuelta;
        nodos.forEach((nd, i) => {
          const en = ronda.includes(i), luz = en ? Math.max(0, Math.min(1, (f - 0.35) * 6)) * (f < 0.97 ? 1 : 0) : 0;
          nd.m.color.copy(apagado).lerp(prendido, luz); nd.n.position.y = luz * 6; lineas[i].opacity = en ? 0.18 + 0.6 * Math.min(1, f * 3) * (1 - vuelta * 0.7) : 0.12;
        });
        ronda.forEach((i, j) => { const nd = nodos[i]; pulsos[j].position.set(nd.x * q, 20 + (7 - 20) * q + Math.sin(q * Math.PI) * 14, nd.z * q); pulsos[j].visible = f < 0.96; });
        nucleo.scale.setScalar(1 + Math.max(0, Math.sin((f - 0.9) * Math.PI * 10)) * 0.08 * (f > 0.9 ? 1 : 0));
      },
    };
  },

  // La prueba de una respuesta: el dato y sus capas (procedencia, licencia, de dónde se sirvió y
  // la huella) se separan para leerse y se vuelven a juntar. Valores de una respuesta real.
  prueba(THREE, scene, el) {
    const capas = JSON.parse(el.dataset.capas);
    const W = 220, D = 130, G = 7, n = capas.length;
    const forma = new THREE.Shape(); const rr = 10, w = W / 2, d = D / 2;
    forma.moveTo(-w + rr, -d); forma.lineTo(w - rr, -d); forma.quadraticCurveTo(w, -d, w, -d + rr); forma.lineTo(w, d - rr);
    forma.quadraticCurveTo(w, d, w - rr, d); forma.lineTo(-w + rr, d); forma.quadraticCurveTo(-w, d, -w, d - rr); forma.lineTo(-w, -d + rr); forma.quadraticCurveTo(-w, -d, -w + rr, -d);
    const geo = new THREE.ExtrudeGeometry(forma, { depth: G, bevelEnabled: true, bevelThickness: 0.8, bevelSize: 0.8, bevelSegments: 2 });
    geo.rotateX(-Math.PI / 2);
    // La cara superior lleva el texto como textura (plano encima de la losa).
    const tapa = new THREE.PlaneGeometry(W - 6, D - 6); tapa.rotateX(-Math.PI / 2);
    const fuente = getComputedStyle(document.body).fontFamily;
    const losas = capas.map((c, i) => {
      const lienzo = document.createElement('canvas'); lienzo.width = 1024; lienzo.height = 600;
      const x = lienzo.getContext('2d');
      x.fillStyle = i === 0 ? '#FFFFFF' : '#F6F7F4'; x.fillRect(0, 0, 1024, 600);
      // Con las capas abiertas, de cada losa de abajo solo se ve su borde cercano: ahí va el texto.
      const y0 = i === 0 ? 120 : 330;
      x.fillStyle = i === 0 ? '#8F570B' : '#236E62'; x.font = `500 44px "Geist Mono", ui-monospace, monospace`; x.fillText(c.campo, 64, y0);
      x.fillStyle = '#12261F'; x.font = `600 ${i === 0 ? 84 : 68}px ${fuente}`;
      const palabras = c.valor.split(' '); let linea = '', y = i === 0 ? 270 : y0 + 96;
      for (const p of palabras) { const t = linea ? linea + ' ' + p : p; if (x.measureText(t).width > 890 && linea) { x.fillText(linea, 64, y); linea = p; y += i === 0 ? 96 : 78; } else linea = t; }
      x.fillText(linea, 64, y);
      if (c.nota) { x.fillStyle = '#4E5E57'; x.font = `400 38px ${fuente}`; x.fillText(c.nota, 64, i === 0 ? 530 : 545); }
      const tex = new THREE.CanvasTexture(lienzo); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
      const g = new THREE.Group();
      const cuerpo = new THREE.Mesh(geo, lam(THREE, i === 0 ? C.ambar : '#DCE3DA'));
      const cara = new THREE.Mesh(tapa, new THREE.MeshBasicMaterial({ map: tex })); cara.position.y = G + 0.9;
      g.add(cuerpo, cara); scene.add(g);
      return g;
    });
    const sombra = new THREE.Mesh(new THREE.PlaneGeometry(W * 1.3, D * 1.5), new THREE.MeshBasicMaterial({ color: '#0E2A22', transparent: true, opacity: 0.08, depthWrite: false }));
    sombra.rotation.x = -Math.PI / 2; sombra.position.y = -2; scene.add(sombra);
    const notas = [...document.querySelectorAll('[data-capa]')];
    const CICLO = 10, SEP = 64;
    let activa = -1;
    return {
      alto: 420, az: -0.55, pol: 0.9, mira: 120, fijo: false, quieto: 4,
      paso(s) {
        const f = (s % CICLO) / CICLO;
        // Juntas (0–0.12), se abren (0.12–0.3), abiertas (0.3–0.82), se cierran (0.82–1).
        const k = f < 0.12 ? 0 : f < 0.3 ? suave((f - 0.12) / 0.18) : f < 0.82 ? 1 : 1 - suave((f - 0.82) / 0.18);
        losas.forEach((g, i) => {
          const desde = n - 1 - i;  // la de arriba es el dato
          g.position.y = desde * (G + 1.2) + k * desde * SEP;
          g.position.x = k * desde * -6;
        });
        // Con las capas abiertas, cada nota se ilumina por turnos.
        const turno = k === 1 ? Math.min(n - 1, Math.floor((f - 0.3) / 0.52 * n)) : -1;
        if (turno !== activa) { activa = turno; notas.forEach(nt => nt.classList.toggle('activa', +nt.dataset.capa === turno)); }
        sombra.material.opacity = 0.08 + 0.04 * (1 - k);
      },
    };
  },
};
