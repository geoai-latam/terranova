// «La criba» (el motor): los linderos reales del SINIC alrededor del punto del héroe, como
// una lista. Una pasada los revisa contra cuatro fuentes (RUNAP, ANT, SINCHI, IGAC): lo despejado se
// asienta, lo dudoso se levanta (altura y filo en tinta, sin ámbar) y lo que no tiene polígono queda
// vacío. La cámara se acerca al dudoso más cercano al predio del héroe, que se pone ámbar, y se abre
// su expediente. Los estados salen de un cruce local (criba/preparar.py) con las copias de RUNAP y ANT
// del 22-10-2026 y los linderos del SINIC del 28-10-2026: nada se inventa.
import {
  getT, C, ambiente, papelDe, anillo, centro, encoger, area, prisma, lineas, contorno,
  encuadrar, aPantalla, registrar, solo, quieto, ajustarSombra, mapaSombra, SOL, marco, plano, resorte, tramo, mats, pintarMats,
} from './motor3d.js?v=0cb2e43b98';
import { ambarLibre } from './ambar.js?v=420978c8f1';

const H0 = 3.2, HD = 0.9, HR = 9;
const TT = { barra: 300, pasa: 2600, acerca: 2900, ambar: 3700, filas: 3950, fin: 5200 };

export async function montar(fig) {
  const T = getT();
  const [D, P] = await Promise.all([fetch('/datos/sm.json').then(r => r.json()), fetch('/datos/portada.json').then(r => r.json())]);
  const K = P.criba, rev = new Set(K.revision);
  const lienzo = fig.querySelector('canvas'), escenaEl = fig.querySelector('.cr-escena');
  const escena = new T.Scene(), cam = new T.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  const luz = ambiente(escena, { lado: 700, papel: papelDe(fig), reticula: false, sol: SOL });

  const crudos = D.polys.map(anillo), oc = centro(crudos[D.obj].slice());
  const polys = crudos.map(p => encoger(p.map(q => q.clone().sub(oc)), 0.45));
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  polys.forEach(p => p.forEach(q => { x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y); }));

  // Una sola malla para todos (menos el dudoso): cada vértice sabe dónde está su predio en la pasada
  // (aOrd) y qué salió de la revisión (aEst: 0 despejado, 1 a revisión). El sombreador pone la altura
  // y el tinte; la pasada es un uniforme: sin tocar la geometría en cada cuadro.
  const pos = [], ord = [], est = [], col = [], seg = [], sOrd = [], sEst = [], sCol = [];
  const ct = new T.Color(C.techo), cl = new T.Color(C.lado);
  polys.forEach((pts, i) => {
    if (i === K.dudoso || pts.length < 3 || Math.abs(area(pts)) < 1) return;
    const c = centro(pts), o = c.x + c.y * 0.35, e = rev.has(i) ? 1 : 0;
    const V = (x, y, z, techo) => { pos.push(x, z, -y); ord.push(o); est.push(e); const k = techo ? ct : cl; col.push(k.r, k.g, k.b); };
    T.ShapeUtils.triangulateShape(pts, []).forEach(t => t.forEach(j => V(pts[j].x, pts[j].y, 1, true)));
    for (let k = 0; k < pts.length; k++) {
      const a = pts[k], b = pts[(k + 1) % pts.length];
      V(a.x, a.y, 0); V(b.x, b.y, 0); V(b.x, b.y, 1); V(a.x, a.y, 0); V(b.x, b.y, 1); V(a.x, a.y, 1);
      seg.push(a.x, 1, -a.y, b.x, 1, -b.y); sOrd.push(o, o); sEst.push(e, e); sCol.push(0, 0, 0, 0, 0, 0);
    }
  });
  const U = { uBarra: { value: -1e4 }, uAncho: { value: 40 }, uH0: { value: H0 }, uHD: { value: HD }, uHR: { value: HR } };
  const papel = new T.Color(papelDe(fig)), tinta = new T.Color(C.tinta);
  const inyectar = (mat, linea) => {
    mat.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, U, { uPapel: { value: papel }, uTinta: { value: tinta }, uTinte: { value: new T.Color('#DCEBE4') } });
      sh.vertexShader = 'attribute float aOrd;\nattribute float aEst;\nuniform float uBarra, uAncho, uH0, uHD, uHR;\nuniform vec3 uPapel, uTinta, uTinte;\n' +
        sh.vertexShader.replace('#include <color_vertex>', `#include <color_vertex>
          float crP = clamp((uBarra - aOrd) / uAncho, 0.0, 1.0); crP = crP * crP * (3.0 - 2.0 * crP);
          ${linea
            ? 'vColor = mix(uPapel, uTinta, mix(0.30, aEst > 0.5 ? 0.95 : 0.16, crP));'
            : 'vColor = mix(vColor, vColor * uTinte, crP * (1.0 - aEst));'}`)
          .replace('#include <begin_vertex>', `#include <begin_vertex>
          transformed.y *= mix(uH0, aEst > 0.5 ? uHR : uHD, crP);`);
    };
    mat.customProgramCacheKey = () => 'criba-' + (linea ? 'l' : 'm');
    return mat;
  };
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('aOrd', new T.Float32BufferAttribute(ord, 1)); g.setAttribute('aEst', new T.Float32BufferAttribute(est, 1));
  g.setAttribute('color', new T.Float32BufferAttribute(col, 3)); g.computeVertexNormals();
  const malla = new T.Mesh(g, inyectar(new T.MeshLambertMaterial({ vertexColors: true }), false));
  malla.castShadow = malla.receiveShadow = true; malla.frustumCulled = false; escena.add(malla);
  const gl = new T.BufferGeometry();
  gl.setAttribute('position', new T.Float32BufferAttribute(seg, 3));
  gl.setAttribute('aOrd', new T.Float32BufferAttribute(sOrd, 1)); gl.setAttribute('aEst', new T.Float32BufferAttribute(sEst, 1));
  gl.setAttribute('color', new T.Float32BufferAttribute(sCol, 3));
  const filos = new T.LineSegments(gl, inyectar(new T.LineBasicMaterial({ vertexColors: true }), true));
  filos.frustumCulled = false; filos.position.y = 0.03; escena.add(filos);

  // el dudoso, aparte: sube con los suyos y se pone ámbar cuando la cámara llega
  const pd = polys[K.dudoso], cd = centro(pd), ordD = cd.x + cd.y * 0.35;
  const mD = mats(C.techo, C.lado), dud = prisma(pd, mD); escena.add(dud);
  const filoD = lineas(contorno(pd, 1.0), C.tinta, 0.95); escena.add(filoD);
  // el predio del héroe: solo un rótulo (está despejado)
  const ch = centro(polys[D.obj]);

  // la pasada: una regla en tinta que barre la lista en diagonal
  const largo = Math.hypot(x1 - x0, y1 - y0);
  const regla = new T.Mesh(new T.BoxGeometry(1.0, 12, largo * 0.8), new T.MeshLambertMaterial({ color: C.tinta }));
  regla.castShadow = true; escena.add(regla);
  regla.rotation.y = Math.atan2(-0.35, -1); // perpendicular a la dirección de la pasada (x + 0.35 y)
  const oMin = x0 + y0 * 0.35 - 10, oMax = x1 + y1 * 0.35 + 50;
  const enO = o => { const d = new T.Vector2(1, 0.35).normalize(); const k = o / Math.hypot(1, 0.35); return [d.x * k, d.y * k]; };

  // rótulos
  const capa = fig.querySelector('.f3-rot');
  const rot = (cls, txt) => { const e = document.createElement('span'); e.className = cls; e.innerHTML = txt; capa.append(e); return e; };
  const rRegla = rot('cr-regla', 'RUNAP · ANT · SINCHI · IGAC');
  const rHeroe = rot('cr-heroe', `${K.heroe_corto} <i>el de arriba · despejado</i>`);
  const rDud = rot('cr-dud', `${K.dudoso_corto} <i>a revisión</i>`);
  const exp = fig.querySelector('.cr-exp'), filasExp = [...exp.querySelectorAll('[data-fila]')];
  const lectura = fig.querySelector('[data-lectura]');

  // encuadre: la lista entera; el acercamiento se cierra sobre el dudoso
  const caja3 = [];
  for (const x of [x0, x1]) for (const y of [y0, y1]) caja3.push(new T.Vector3(x, 0, -y), new T.Vector3(x, HR, -y));
  ajustarSombra(luz, caja3, { mapa: mapaSombra(true) });
  const AZ = -0.62, POL = 0.86, mira = new T.Vector3(0, 0, 0), foco = new T.Vector3(cd.x, HR * 0.6, -cd.y);
  let base = null, W = 0, Hh = 0;
  const angosto = () => escenaEl.clientWidth < 560;
  function tam(w, h) {
    W = w; Hh = h;
    encuadrar(cam, { az: AZ, pol: POL, mira, puntos: caja3, w, h, margen: [10, 10, 10, 10] });
    base = marco(cam);
  }
  const ACERCA = () => (angosto() ? 2.0 : 2.3);
  let conAmbar = true, ultimoAmbar = null;

  function pose(t) {
    const barraO = oMin + (oMax - oMin) * tramo(t, TT.barra, TT.pasa - TT.barra);
    U.uBarra.value = t >= TT.pasa ? 1e4 : barraO;
    const [bx, by] = enO(barraO);
    regla.position.set(bx, 8, -by); regla.visible = t > TT.barra && t < TT.pasa;
    // el dudoso: misma regla que los suyos
    const p = Math.min(1, Math.max(0, (U.uBarra.value - ordD) / 40)), ps = p * p * (3 - 2 * p);
    const hd = H0 + (HR - H0) * ps; dud.scale.y = hd; filoD.position.y = hd - 1.0 + 0.03;
    // acercamiento al dudoso (empuje de lente, el foco no se mueve en pantalla), y vuelve a abrir al final
    const s = 1 + (ACERCA() - 1) * resorte(t, TT.acerca, 1300, 0.85);
    if (base) plano(cam, base, s, foco);
    // ámbar: solo si no hay un botón principal en vista (se decide al llegar)
    if (t >= TT.ambar && ultimoAmbar === null) ultimoAmbar = conAmbar = ambarLibre();
    if (t < TT.ambar) ultimoAmbar = null;
    const amb = t >= TT.ambar && (quieto ? ambarLibre() : conAmbar);
    pintarMats(mD, amb ? C.ambar : C.techo, amb ? C.ambarLado : C.lado);
    fig.classList.toggle('sin-ambar', !amb && t >= TT.ambar);
    // expediente: una fila por fuente
    filasExp.forEach((f, i) => f.classList.toggle('llega', t >= TT.filas + i * 230));
    exp.classList.toggle('abierto', t >= TT.ambar);
    const txt = t < TT.barra ? `la lista: ${K.n.toLocaleString('es-CO')} predios del SINIC, cada uno con su lindero`
      : t < TT.pasa ? 'una pasada contra cuatro fuentes, predio por predio'
        : t < TT.ambar ? `${K.n - K.revision.length} despejados · ${K.revision.length} a revisión · ${K.con_hallazgo} con hallazgo` : `expediente de ${K.dudoso_corto}`;
    if (lectura.textContent !== txt) lectura.textContent = txt;
  }
  function despues(w, h) {
    const [bx, by] = enO(Math.min(oMax, oMin + (oMax - oMin) * tramo(f.t, TT.barra, TT.pasa - TT.barra)));
    const [rx, ry] = aPantalla(cam, bx, 17, -by, w, h);
    rRegla.style.transform = `translate(${rx.toFixed(1)}px, ${ry.toFixed(1)}px) translate(-50%, -130%)`;
    rRegla.style.opacity = f.t > TT.barra && f.t < TT.pasa ? 1 : 0;
    const [hx, hy] = aPantalla(cam, ch.x, HD, -ch.y, w, h);
    rHeroe.style.transform = `translate(${hx.toFixed(1)}px, ${hy.toFixed(1)}px) translate(10px, 2px)`;
    rHeroe.style.opacity = f.t >= TT.pasa ? 1 : 0;
    const [dx, dy] = aPantalla(cam, cd.x, dud.scale.y + 1, -cd.y, w, h);
    rDud.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) translate(-50%, -140%)`;
    rDud.style.opacity = f.t >= TT.pasa ? 1 : 0;
  }
  const f = registrar({ nombre: 'criba', caja: fig, lienzo, control: escenaEl, escena, cam, dur: TT.fin, n: 1, tInicial: 0, pose, tam, despues });
  solo(f, { entrada: 1, cada: 1e9 });
  return f;
}
