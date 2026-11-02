// «El expediente de un ítem» (debida diligencia): el acercamiento al dudoso de la criba, 47001…0345,
// con sus vecinos reales en 60 × 60 m. Salen sus cuatro preguntas (una guía a cada entidad) y cada una
// vuelve con su estado y la marca de DISENO: no encontrado (anillo vacío), fuera de cobertura y, en el
// catastro, «por revisar», que es lo único en ámbar. Se cierra con la huella del expediente.
import {
  getT, C, ambiente, papelDe, anillo, centro, encoger, area, recortar, prisma, bloques, lineas, contorno,
  encuadrar, aPantalla, registrar, correr, quieto, ajustarSombra, SOL, mats, matsAO, mapaContacto, losa, resorte, tramo, pedir, corriendo,
} from './motor3d.js?v=0cb2e43b98';
import { ambarLibre } from './ambar.js?v=420978c8f1';

const RM = 26, HB = 2.4, HD = 7;
const TT = { sale: 250, vuelve: 1350, prueba: 2700, fin: 3500 };

export async function montar(fig) {
  const T = getT();
  const [D, P] = await Promise.all([fetch('/datos/sm.json').then(r => r.json()), fetch('/datos/portada.json').then(r => r.json())]);
  const K = P.criba;
  const lienzo = fig.querySelector('canvas'), escenaEl = fig.querySelector('.ex3-escena');
  const escena = new T.Scene(), cam = new T.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  const luz = ambiente(escena, { lado: 70, papel: papelDe(fig), reticula: false, sol: SOL });
  luz.userData.suelo.visible = false;

  const crudos = D.polys.map(anillo), oc = centro(crudos[K.dudoso].slice());
  const polys = crudos.map(p => p.map(q => q.clone().sub(oc)));
  const obj = encoger(polys[K.dudoso], 0.5), vec = [];
  polys.forEach((p, i) => {
    if (i === K.dudoso) return;
    const c = recortar(p, -RM, RM, -RM, RM);
    if (c.length >= 3 && Math.abs(area(c)) > 5) vec.push(encoger(c, 0.5));
  });
  const rect = [-RM - 2, RM + 2, -RM - 2, RM + 2];
  const ao = mapaContacto([...vec, obj], rect, { res: 256, rad: 1.3, fuerza: 0.65 });
  escena.add(losa(rect, 1.0, { ao }));
  escena.add(bloques(vec, HB, { ao: { suelo: 0, rad: 1.5, min: 0.45 } }));
  const mO = matsAO(C.techo, C.lado, { suelo: 0, rad: 2, min: 0.5 }), pred = prisma(obj, mO); escena.add(pred);
  const filo = lineas(contorno(obj, 1), C.tinta, 0.95); escena.add(filo);

  const caja3 = [];
  for (const y of [-1, HD]) for (const sx of [-1, 1]) for (const sz of [-1, 1]) caja3.push(new T.Vector3(sx * (RM + 2), y, sz * (RM + 2)));
  ajustarSombra(luz, caja3, { mapa: 1024 });
  const AZ = -0.62, POL = 0.98, mira = new T.Vector3(0, 0, 0);

  const filas = [...fig.querySelectorAll('[data-fila]')];
  const svg = fig.querySelector('.ex3-guias'), NS = 'http://www.w3.org/2000/svg';
  const guias = filas.map(() => { const p = document.createElementNS(NS, 'path'); svg.append(p); return p; });
  const lectura = fig.querySelector('[data-lectura]');
  const huella = 'sha256:' + K.huella.slice(0, 8) + '…';
  let geo = null;
  function tam(w, h) {
    encuadrar(cam, { az: AZ, pol: POL, mira, puntos: caja3, w, h, margen: [6, 6, 6, 6] });
    const fr = fig.getBoundingClientRect(), er = escenaEl.getBoundingClientRect();
    geo = { ex: er.left - fr.left, ey: er.top - fr.top, filas: filas.map(f => { const r = f.getBoundingClientRect(); return [r.left - fr.left, r.top - fr.top + r.height / 2]; }) };
    svg.setAttribute('viewBox', `0 0 ${fr.width} ${fr.height}`);
  }
  let amb = true, decidido = false;
  function pose(t) {
    pred.scale.y = HB + (HD - HB) * resorte(t, 0, 700, 0.6);
    filo.position.y = pred.scale.y - 1 + 0.03;
    filas.forEach((f, i) => {
      f.classList.toggle('sale', t >= TT.sale + i * 160);
      f.classList.toggle('vuelve', t >= TT.vuelve + i * 300);
    });
    if (t >= TT.prueba && !decidido) { decidido = true; amb = quieto ? ambarLibre() : ambarLibre(); }
    if (t < TT.prueba) decidido = false;
    fig.classList.toggle('probando', t >= TT.prueba);
    fig.classList.toggle('sin-ambar', !(fig.__actual && amb));
    const txt = t < TT.vuelve ? `${K.dudoso_corto}: cuatro preguntas, una por entidad`
      : t < TT.prueba ? 'cada una vuelve con su estado' : `expediente · ${K.dudoso_corto} · huella ${huella}`;
    if (lectura.textContent !== txt) lectura.textContent = txt;
  }
  function despues(w, h) {
    if (!geo || getComputedStyle(svg).display === 'none') return;
    // del techo del predio a cada fila: sale una guía por pregunta
    const [ax, ay] = aPantalla(cam, 0, pred.scale.y, 0, w, h);
    const x = ax + geo.ex, y = ay + geo.ey;
    filas.forEach((fl, i) => {
      const g = guias[i];
      if (!fl.classList.contains('sale')) { g.setAttribute('d', ''); return; }
      const [fx, fy] = geo.filas[i], xm = fx - 18;
      g.setAttribute('d', `M${x.toFixed(1)} ${y.toFixed(1)}L${xm.toFixed(1)} ${fy.toFixed(1)}H${(fx - 2).toFixed(1)}`);
      g.setAttribute('class', fl.classList.contains('dudosa') && fig.classList.contains('probando') && !fig.classList.contains('sin-ambar') ? 'amb' : '');
    });
  }
  const f = registrar({ nombre: 'expediente', caja: fig, lienzo, control: fig, escena, cam, dur: TT.fin, n: 1, tInicial: 0, pose, tam, despues });
  f.tocar = null;
  // la interfaz del grupo de servicios (tipo.js): correr(cb), reposo(conAmbar), corre
  return {
    el: fig, nombre: 'expediente',
    correr(cb) { fig.__actual = true; f.fin = () => { f.fin = null; if (cb) cb(); }; correr(f, 0); },
    reposo(conAmbar) { fig.__actual = !!conAmbar; f.t = f.dur; pedir(f); },
    get corre() { return corriendo(f); },
  };
}
