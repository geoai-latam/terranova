// «Cada respuesta trae su prueba»: tres capas reales del mismo lote del SINIC en Santa Marta,
// apiladas. Abajo la Fuente (los linderos como los publica el IGAC), en medio la Copia de consulta
// del 28-10-2026 (los mismos linderos, ya cargados) y arriba el Resultado: solo el predio
// 47001…0308. La sonda baja por el punto consultado, el lindero se enciende en la copia (el
// Indicio), la copia se ata a su fuente y el predio sube. La consola se llena campo por campo y
// cada campo tiene su guía a la capa que lo prueba. La separación entre capas y las alturas son
// simbólicas; los linderos, el punto y la respuesta son reales.
import {
  getT, C, ambiente, papelDe, anillo, centro, encoger, area, recortar, mats, pintarMats, prisma, bloques,
  lineas, contorno, filete, caja, encuadrar, orientar, aPantalla, tramo, registrar, solo, quieto,
  matsAO, sueloAO, mapaContacto, losa, ajustarSombra, mapaSombra, SOL, marco, plano, resorte, impulso, golpe,
} from './motor3d.js?v=0cb2e43b98';
import { ambarLibre } from './ambar.js?v=420978c8f1';

const RM = 30, S = 32, HB = 2.4, HR = 13, Y_SONDA = 2 * S + 46;
// cuándo llega cada cosa (ms)
const TT = { sonda: 250, toca: 1350, ata: 1450, servido: 1500, entidad: 1950, licencia: 2250, sube: 2450, estado: 3150, predial: 3400, destino: 3650, huella: 4150, fin: 4700 };

export async function montar(fig) {
  const T = getT();
  const D = await fetch('/datos/sm.json').then(r => r.json());
  const lienzo = fig.querySelector('canvas'), escenaEl = fig.querySelector('.p3-escena');
  const escena = new T.Scene();
  const cam = new T.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  // sin suelo de sombras: la pila flota sobre la retícula y las sombras quedan dentro de cada capa
  const luz = ambiente(escena, { lado: 90, papel: papelDe(fig), reticula: true, sol: SOL });
  luz.userData.suelo.visible = false;

  // Linderos reales, centrados en el predio consultado y recortados a 60 × 60 m.
  const crudos = D.polys.map(anillo), oc = centro(crudos[D.obj].slice());
  const polys = crudos.map(p => p.map(q => q.clone().sub(oc)));
  const obj = encoger(polys[D.obj]);
  const vecinos = [];
  polys.forEach((p, i) => {
    if (i === D.obj) return;
    const c = recortar(p, -RM, RM, -RM, RM);
    if (c.length >= 3 && Math.abs(area(c)) > 6) vecinos.push(encoger(c));
  });

  const rect = [-RM - 2, RM + 2, -RM - 2, RM + 2];
  // Fuente: la placa blanca con los linderos en tinta, como un plano.
  // La fuente va en trazo, «como se publica»: sin placa ni volumen, solo los linderos.
  const segF = []; for (const p of [...vecinos, obj]) segF.push(...contorno(p, 0.06));
  escena.add(lineas(segF, C.tinta, 0.62));
  const marcoF = lineas(contorno([[-RM - 2, -RM - 2], [RM + 2, -RM - 2], [RM + 2, RM + 2], [-RM - 2, RM + 2]].map(([x, y]) => new T.Vector2(x, y)), 0.07), C.medio, 0.6);
  escena.add(marcoF);
  const objF = filete(obj, 0.7, C.teal); objF.position.y = 0.08; objF.visible = false; escena.add(objF);

  // Copia de consulta: placa gris con los predios cargados, blancos como en el héroe. Todo en un
  // grupo, que acusa el toque de la sonda. El techo de la placa lleva el mapa de contacto de sus
  // predios (la calle angosta entre dos muros se oscurece) y los muros, su AO al pie.
  const gC = new T.Group(); gC.position.y = S; escena.add(gC);
  const aoC = mapaContacto([...vecinos, obj], rect, { res: 512, rad: 1.3, fuerza: 0.7 });
  const pC = losa(rect, 1.2, { ao: aoC, aoFuerza: 1 }); gC.add(pC);
  const AO = { suelo: S, rad: 1.5, min: 0.42 };
  const cop = bloques(vecinos, HB, { ao: AO }); gC.add(cop);
  const mObjC = matsAO(C.techo, C.lado, AO), objC = prisma(obj, mObjC); objC.scale.y = HB; gC.add(objC);
  const objCfilo = lineas(contorno(obj, HB + 0.05), C.tinta, 0.22); gC.add(objCfilo);
  const anilloC = new T.Mesh(new T.RingGeometry(11.6, 12.5, 96), new T.MeshBasicMaterial({ color: C.teal }));
  anilloC.rotation.x = -Math.PI / 2; anilloC.position.y = 0.06; gC.add(anilloC);

  // El vínculo: la copia viene de la fuente (líneas punteadas que bajan de una a otra).
  const ata = new T.Group(); ata.position.y = 0; gC.add(ata);
  { const seg = []; for (const p of obj) seg.push(p.x, 0, -p.y, p.x, -S, -p.y);
    const l = lineas(seg, C.teal, 1); l.material = new T.LineDashedMaterial({ color: C.teal, dashSize: 1.4, gapSize: 1.1 }); l.computeLineDistances(); ata.add(l); }

  // Resultado: no es una placa (no tapa la copia): solo su marco, y el predio solo.
  const yR = 2 * S;
  const marcoR = lineas(contorno([[-RM - 2, -RM - 2], [RM + 2, -RM - 2], [RM + 2, RM + 2], [-RM - 2, RM + 2]].map(([x, y]) => new T.Vector2(x, y)), yR), C.medio, 0.85);
  escena.add(marcoR);
  const esquinas = new T.Group();
  { const L = 6, seg = [];
    for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      const x = sx * (RM + 2), y = sy * (RM + 2);
      seg.push(x, yR, -y, x - sx * L, yR, -y, x, yR, -y, x, yR, -(y - sy * L));
    }
    esquinas.add(lineas(seg, C.tinta, 0.9)); }
  escena.add(esquinas);
  const huellaR = filete(obj, 0.6, C.teal); huellaR.position.y = yR + 0.05; escena.add(huellaR);
  const mObj = matsAO('#8EDAC9', '#5FB9A6', { suelo: yR, rad: 2.4, min: 0.55 }), pred = prisma(obj, mObj); pred.position.y = yR; pred.scale.y = 0.01; pred.castShadow = false; escena.add(pred);

  // La sonda: un hilo en tinta con la punta en ámbar mientras baja.
  const sonda = new T.Group();
  const hilo = new T.Mesh(new T.CylinderGeometry(0.22, 0.22, 1, 8), new T.MeshLambertMaterial({ color: C.tinta }));
  hilo.position.y = 0.5; sonda.add(hilo);
  const mPunta = new T.MeshLambertMaterial({ color: C.tinta });
  const punta = new T.Mesh(new T.ConeGeometry(1.5, 3.6, 24), mPunta); punta.rotation.x = Math.PI; punta.position.y = 1.8;
  punta.castShadow = true; sonda.add(punta); escena.add(sonda);

  // El hilo ámbar: la cadena de prueba. Baja del predio del resultado a su lindero en la copia y de
  // ahí a la fuente; es lo único en ámbar (si un botón principal está en vista, va en tinta).
  const pc = centro(obj.slice());
  const mHilo = new T.MeshBasicMaterial({ color: C.ambar });
  const hilo1 = new T.Mesh(new T.CylinderGeometry(0.38, 0.38, 1, 10), mHilo), hilo2 = new T.Mesh(new T.CylinderGeometry(0.38, 0.38, 1, 10), mHilo);
  const nudos = [0, 1, 2].map(() => { const n = new T.Mesh(new T.SphereGeometry(0.95, 16, 10), mHilo); escena.add(n); return n; });
  escena.add(hilo1, hilo2);
  const TH = { a: TT.estado - 200, b: TT.huella };
  let hiloAmb = null;

  // ---------- la consola, las notas y las guías ----------
  const con = fig.querySelector('.p3-con');
  const filas = [...con.querySelectorAll('dt')].map(dt => ({ dt, dd: dt.nextElementSibling, g: dt.dataset.g, k: dt.dataset.k }));
  const pie = con.querySelector('.pie');
  const notas = [...(fig.closest('section') || document).querySelectorAll('.p3-notas [data-p]')];
  const capas = Object.fromEntries([...fig.querySelectorAll('.p3-capa')].map(e => [e.dataset.capa, e]));
  const lectura = fig.querySelector('[data-lectura]');
  // lo que dice la lectura sale de la página (construir.py): el predio, la copia y la lectura final
  const PRED = fig.dataset.predio, COPIA = fig.dataset.copia, FINAL = lectura.textContent;
  const svg = fig.querySelector('.p3-guias');
  const NS = 'http://www.w3.org/2000/svg';
  const guias = filas.map(() => { const p = document.createElementNS(NS, 'path'); svg.append(p); return p; });
  const puntos = filas.map(() => { const c = document.createElementNS(NS, 'circle'); c.setAttribute('r', '2.5'); svg.append(c); return c; });
  const llega = { estado: TT.estado, predial: TT.predial, destinacion: TT.destino, servido: TT.servido, entidad: TT.entidad, licencia: TT.licencia };
  const notaDe = { estado: 0, predial: 0, destinacion: 0, entidad: 1, licencia: 2, servido: 3 };
  const estado = filas.map(() => null);
  let pieV = null, notaV = -2, capaV = '', lecturaV = '';

  function consola(t) {
    let ultima = -1, ultimaT = -1, ultimaG = '';
    filas.forEach((f, i) => {
      const si = t >= llega[f.k];
      if (si !== estado[i]) {
        estado[i] = si;
        f.dt.classList.toggle('espera', !si); f.dd.classList.toggle('espera', !si);
        f.dd.classList.toggle('aparece', si && !quieto && t < TT.fin);
      }
      if (si && llega[f.k] > ultimaT) { ultimaT = llega[f.k]; ultima = notaDe[f.k]; ultimaG = f.g; }
    });
    const ph = t >= TT.huella;
    if (ph !== pieV) { pieV = ph; pie.classList.toggle('espera', !ph); pie.classList.toggle('aparece', ph && !quieto && t < TT.fin); }
    if (ph) { ultima = 4; ultimaG = ''; }
    if (ultima !== notaV) { notaV = ultima; notas.forEach(n => n.classList.toggle('vivo', +n.dataset.p === ultima)); }
    if (ultimaG !== capaV) { capaV = ultimaG; for (const k in capas) capas[k].classList.toggle('vivo', k === ultimaG); }
    const txt = t < TT.toca ? `consulta en ${fig.dataset.punto}`
      : t < TT.sube ? `indicio: el lindero del predio en la ${COPIA}`
        : t < TT.huella ? `predio ${PRED}, ${fig.dataset.destino}` : FINAL;
    if (txt !== lecturaV) { lecturaV = txt; lectura.textContent = txt; }
  }

  // ---------- encuadre ----------
  const angosto = () => escenaEl.clientWidth < 560;
  const mira = new T.Vector3(0, S, 0);
  const caja3 = [];
  for (const y of [-1.2, yR]) for (const sx of [-1, 1]) for (const sz of [-1, 1]) caja3.push(new T.Vector3(sx * (RM + 2), y, sz * (RM + 2)));
  caja3.push(new T.Vector3(0, yR + HR, 0));
  const AZ = -0.62, POL = 1.05;
  ajustarSombra(luz, caja3, { mapa: mapaSombra(true) });
  let geo = null, base = null;
  const foco = new T.Vector3(0, S + HB, 0);
  function tam(w, h) {
    const a = angosto();
    orientar(cam, { az: AZ, pol: POL, mira });
    encuadrar(cam, { az: AZ, pol: POL, mira, puntos: caja3, w, h, margen: a ? [92, 4, 22, 8] : [140, 16, 30, 10] });
    base = marco(cam);
    // posiciones de las filas de la consola, relativas a la figura
    const fr = fig.getBoundingClientRect(), cr = con.getBoundingClientRect(), er = escenaEl.getBoundingClientRect();
    geo = { x0: cr.left - fr.left, ex: er.left - fr.left, ey: er.top - fr.top, filas: filas.map(f => { const r = f.dt.getBoundingClientRect(); return r.top - fr.top + r.height / 2; }) };
    svg.setAttribute('viewBox', `0 0 ${fr.width} ${fr.height}`);
    for (const k in capas) capas[k].classList.toggle('corta', a);
  }

  const P = (x, y, z, w, h) => aPantalla(cam, x, y, z, w, h);
  const esquinaDer = (y, w, h) => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sz]) => P(sx * (RM + 2), y, sz * (RM + 2), w, h)).reduce((a, b) => (b[0] > a[0] ? b : a));
  const esquinaIzq = (y, w, h) => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sz]) => P(sx * (RM + 2), y, sz * (RM + 2), w, h)).reduce((a, b) => (b[0] < a[0] ? b : a));
  let abierto = 1;
  function despues(w, h) {
    // rótulos de las capas, a la izquierda de cada placa; entran cuando el plano se abre
    for (const [k, y] of [['r', yR], ['c', S], ['f', 0]]) {
      const [x, yy] = esquinaIzq(y, w, h);
      capas[k].style.transform = `translate(${(x - 14).toFixed(1)}px, ${yy.toFixed(1)}px) translate(-100%, -50%)`;
      capas[k].style.opacity = abierto.toFixed(2);
    }
    if (!geo || getComputedStyle(svg).display === 'none') return;
    // anclas: el predio (resultado), la esquina derecha de la copia y la de la fuente
    const top = pred.scale.y * 1 + yR;
    void top;
    const ancla = {
      r: obj.map(p => P(p.x, top, -p.y, w, h)).reduce((a, b) => (b[0] > a[0] ? b : a)),
      c: esquinaDer(S, w, h), f: esquinaDer(0, w, h),
    };
    const tronco = { r: -18, c: -32, f: -46 };
    filas.forEach((f, i) => {
      const g = guias[i], c = puntos[i];
      if (!estado[i]) { g.setAttribute('d', ''); c.setAttribute('r', '0'); return; }
      const [ax, ay] = ancla[f.g], x = ax + geo.ex, y = ay + geo.ey, y0 = geo.filas[i], xt = geo.x0 + tronco[f.g];
      g.setAttribute('d', `M${geo.x0 - 2} ${y0.toFixed(1)}H${xt.toFixed(1)}V${y.toFixed(1)}H${x.toFixed(1)}`);
      g.setAttribute('class', f.g === capaV ? 'viva' : '');
      c.setAttribute('cx', (x).toFixed(1)); c.setAttribute('cy', y.toFixed(1)); c.setAttribute('r', '2.5');
    });
  }

  // la sonda baja con aceleración y frena antes de tocar (entrada y salida suaves, sin rebote)
  const enOut = (t, a, d) => { const u = Math.min(1, Math.max(0, (t - a) / d)); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; };
  function pose(t) {
    // Plano con autor: entra cerrado sobre el punto de la copia mientras baja la sonda (el foco no se
    // mueve en pantalla) y se abre con un resorte leve cuando el predio sube al resultado. En reposo,
    // el plano compuesto. Sin órbita: el ángulo no cambia.
    const s = 1 + 0.2 * (1 - resorte(t, TT.sube - 250, 1500, 0.72));
    if (base) plano(cam, base, s, foco);
    abierto = Math.min(1, Math.max(0, (1.07 - s) / 0.07));
    // la copia acusa el toque: se hunde un poco y vuelve
    gC.position.y = S - 0.9 * golpe(t, TT.toca, 520);
    sueloAO(mObjC[0], gC.position.y); sueloAO(mObjC[1], gC.position.y); sueloAO(cop.userData.mat, gC.position.y);
    // sonda: baja hasta el techo del predio en la copia, se vuelve tinta al tocar y sube
    const baja = enOut(t, TT.sonda, TT.toca - TT.sonda), sube = tramo(t, TT.sube, 700);
    const yTop = Y_SONDA, yToca = gC.position.y + HB;
    const punta0 = yTop - (yTop - yToca) * baja + (yTop - yToca) * sube;
    const ver = t >= TT.sonda && t < TT.sube + 700;
    sonda.visible = ver;
    if (ver) {
      sonda.position.set(0, punta0, 0);
      hilo.scale.y = Math.max(0.01, yTop + 30 - punta0); hilo.position.y = hilo.scale.y / 2 + 3.4;
      mPunta.color.set(C.tinta);
    }
    // indicio en la copia
    const ind = t >= TT.toca;
    pintarMats(mObjC, ind ? C.tinte : C.techo, ind ? C.tinteLado : C.lado);
    anilloC.scale.setScalar(Math.max(0.001, tramo(t, TT.toca, 380)));
    // la copia se ata a su fuente
    ata.scale.y = Math.max(0.001, tramo(t, TT.ata, 600)); ata.visible = t >= TT.ata;
    objF.visible = t >= TT.ata + 520;
    // el predio sube en la capa del resultado
    pred.scale.y = Math.max(0.01, HR * impulso(t, TT.sube, 950, { k: 0, p: 0.01, z: 0.45 }));
    pred.visible = t >= TT.sube;
    huellaR.visible = t >= TT.sube;
    // el hilo: del techo del predio (resultado) a la copia y de la copia a la fuente
    if (t < TH.a) hiloAmb = null; else if (hiloAmb === null) hiloAmb = ambarLibre();
    mHilo.color.set(hiloAmb === false || (quieto && !ambarLibre()) ? C.tinta : C.ambar);
    const yArr = yR + pred.scale.y, yC = gC.position.y + HB, k1 = tramo(t, TH.a, 520), k2 = tramo(t, TH.a + 520, 520);
    const y1 = yArr - (yArr - yC) * k1, y2 = gC.position.y - gC.position.y * k2;
    hilo1.visible = k1 > 0; hilo1.scale.y = Math.max(0.01, yArr - y1); hilo1.position.set(pc.x, (yArr + y1) / 2, -pc.y);
    hilo2.visible = k2 > 0; hilo2.scale.y = Math.max(0.01, gC.position.y - y2); hilo2.position.set(pc.x, (gC.position.y + y2) / 2, -pc.y);
    nudos[0].visible = k1 > 0; nudos[0].position.set(pc.x, yArr, -pc.y);
    nudos[1].visible = k1 >= 1; nudos[1].position.set(pc.x, yC, -pc.y);
    nudos[2].visible = k2 >= 1; nudos[2].position.set(pc.x, 0.1, -pc.y);
    consola(t);
  }

  const f = registrar({ nombre: 'prueba', caja: fig, lienzo, control: escenaEl, escena, cam, dur: TT.fin, n: 1, tInicial: 0, pose, tam, despues });
  solo(f, { entrada: 1, cada: 20000 });
  return f;
}
