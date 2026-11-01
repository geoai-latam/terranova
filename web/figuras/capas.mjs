// Fig. capas: el bastidor de equipos. Abajo, el módulo de datos (el producto, en teal): una placa
// grabada, un medidor por familia de herramientas y tres tomas. Encima, Analítica, Automatización y
// Agentes, en neutro, cada uno con un cable a su toma. Lo que se mueve: el dato (la única pieza
// ámbar) sube por el cable del módulo que pregunta y, cuando llega, el piloto del módulo se
// enciende. Nada más se mueve.
import { D, L, S, encuadre, esc, k, r1, sombra, svgDe } from "./comun.mjs";

const tramo = (a, b, P) => k.segment(a, b, P);

export function capas(DATOS, huella) {
  const { fuentes, herramientas, familias, modulos } = DATOS.capas;
  const W = 120, FD = 60; // hueco del bastidor: x 0..W, y 0..FD (el frente mira a +y)
  const yF = FD + 1.5; // cara de los frentes
  const UNID = [
    { z: 9, h: 33 },
    { z: 43, h: 22 },
    { z: 66, h: 22 },
    { z: 89, h: 22 },
  ];
  const TECHO = 112;
  const ZOCALO = { x: -9, y: -7, w: W + 18, d: FD + 15, r: 3 };
  const TOMAS = [88, 95, 102]; // x de la toma de cada módulo en el de datos (Analítica, Automatización, Agentes)

  const { P, ancho, alto } = encuadre(
    [...k.boxCorners(ZOCALO, -14, 0), ...k.boxCorners({ x: -4, y: -1, w: W + 8, d: FD + 3 }, TECHO, TECHO + 6)],
    { azimuth: 58 },
  );
  const at = (p) => k.iso(p, P);
  const fija = [];

  // zócalo sobre patas, con ranura, tornillos y regla en el borde delantero
  fija.push(sombra(ZOCALO, -7, P, { pad: 6 }));
  const porProf = (pts) => [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  for (const [x, y] of porProf(k.corners(ZOCALO, 9))) {
    fija.push(S(k.cylinder(x, y, 5.6, -7, 1.4, P, 24), { tone: "lo", m: "acero" }));
    fija.push(S(k.cylinder(x, y, 4.2, -5.6, 5.6, P, 24), { tone: "mid", m: "metal" }));
  }
  fija.push(S(k.slabOf(ZOCALO, 0, 8, P, 6, 1.2), { tone: "mid", m: "trabajo" }));
  fija.push(L(k.planOutline(k.insetPlan(ZOCALO, 3.5), 8, P, 4), { tone: "faint" }));
  const tornZ = k.corners(ZOCALO, 6);
  fija.push(L(tornZ.map(([x, y]) => k.ring(x, y, 1.6, 8, P, 14)).join(""), { tone: "lo" }));
  fija.push(D(tornZ.map(([x, y]) => at([x, y, 8])), { size: 0.45 }));
  const regla = { x: 8, y: ZOCALO.y + ZOCALO.d - 3.4, w: W - 16, d: 2.6, r: 0.6 };
  fija.push(S(k.slabOf(regla, 8, 0.5, P, 2), { tone: "lo", crease: "none", m: "metal" }));
  const marcas = k.topTicks(regla.x + 2, regla.x + regla.w - 2, 4, 5, regla.y + 2.6, 8.5, [-1, -1.8], P);
  fija.push(L(marcas.minor, { tone: "lo" }), L(marcas.major, { tone: "mid" }));

  // estructura de atrás: panel izquierdo y los dos rieles delanteros con su fila de agujeros
  fija.push(S(k.slabOf({ x: -3, y: 0, w: 3, d: yF, r: 0.5 }, 8, TECHO - 8, P, 2), { tone: "mid", m: "metal" }));
  for (const x of [0, W - 7]) {
    const riel = { x, y: FD - 7, w: 7, d: 6, r: 0.4 };
    const agujeros = [];
    for (let z = 12; z < TECHO - 2; z += 4.6) agujeros.push(at([x + 3.5, FD - 1, z]));
    fija.push(S(k.slabOf(riel, 8, TECHO - 8, P, 2), { tone: "mid", m: "acero" }));
    fija.push(D(agujeros, { size: 0.42, tone: "lo" }));
  }

  // los módulos, de abajo arriba
  const zToma = [];
  const pilotos = [];
  UNID.forEach(({ z, h }, i) => {
    const g = [];
    const tope = z + h;
    const datos = i === 0;
    g.push(S(k.slabOf({ x: 7, y: 2, w: W - 14, d: FD - 3, r: 0.6 }, z + 0.5, h - 1, P, 2, 0.4), { tone: "lo", m: "acero" }));
    const frente = { x: 0.5, y: FD - 1, w: W - 1, d: 2.5, r: 0.5 };
    const costura = k.sideSeam(frente, z + 1.6, P, 2);
    g.push(S(k.slabOf(frente, z, h, P, 2, 0.5), { tone: datos ? "hi" : "mid", m: datos ? "teal" : "papel", inner: L(costura, { tone: "faint" }) }));
    // orejas con dos tornillos por lado
    const torn = [];
    for (const x of [3.6, W - 3.6]) for (const zz of [z + 4.5, tope - 4.5]) torn.push([x, yF, zz]);
    g.push(L(torn.map((p) => k.sideRing(p, 1.3, "y", P, 14)).join(""), { tone: datos ? "mid" : "lo" }));
    g.push(D(torn.map(at), { size: 0.42 }));
    // asas verticales junto a las orejas
    for (const x of [7.6, W - 10.1]) {
      g.push(S(k.slabOf({ x, y: yF, w: 2.5, d: 1.6, r: 0.3 }, z + 4, 2, P, 1), { tone: "mid", crease: "none", m: "acero" }));
      g.push(S(k.slabOf({ x, y: yF, w: 2.5, d: 1.6, r: 0.3 }, tope - 6, 2, P, 1), { tone: "mid", crease: "none", m: "acero" }));
      g.push(S(k.slabOf({ x, y: yF + 1.6, w: 2.5, d: 2.2, r: 0.6 }, z + 4, h - 8, P, 2), { tone: "mid", m: "metal" }));
    }
    // placa de rótulo: la del módulo de datos lleva su nombre grabado; las demás, tres renglones
    const placaZ = datos ? tope - 15 : tope - 10;
    g.push(S(k.slabOf({ x: 14, y: yF, w: 20, d: 0.6, r: 0.3 }, placaZ, tope - 3.6 - placaZ, P, 1), { tone: "lo", crease: "none", m: "papel" }));
    g.push(D([at([15.3, yF + 0.6, tope - 4.9]), at([32.7, yF + 0.6, tope - 4.9])], { size: 0.36 }));
    if (datos) {
      g.push(k.faceTextSvg(k.sideMatrix([16, yF + 0.6], tope - 8.6, P, "left"), "Datos", { size: 3.4, tone: "hi" }));
      g.push(k.faceTextSvg(k.sideMatrix([16, yF + 0.6], tope - 12.8, P, "left"), `${fuentes} fuentes`, { size: 2.3, tone: "mid" }));
    } else {
      const reng = [17, 12, 14].map((largo, j) => tramo([15.6, yF + 0.6, tope - 6.2 - j * 1.6], [15.6 + largo, yF + 0.6, tope - 6.2 - j * 1.6], P));
      g.push(L(reng.join(""), { tone: "lo", free: true }));
    }
    const ventana = (x0, x1, z0, z1) => S(k.slabOf({ x: x0, y: yF, w: x1 - x0, d: 0.5, r: 0.3 }, z0, z1 - z0, P, 1), { tone: "lo", m: "bosque", crease: "none" });
    const tomaEn = (cx, zc) => {
      g.push(S(k.slabOf({ x: cx - 2.2, y: yF, w: 4.4, d: 0.7, r: 0.3 }, zc - 3, 6, P, 1), { tone: "lo", m: "bosque" }));
      g.push(L(k.sideRing([cx, yF + 0.7, zc], 1.1, "y", P, 12), { tone: "mid" }));
    };
    if (datos) {
      // un medidor por familia: ocho luces, encendidas en proporción a sus herramientas (dato fijo)
      const mayor = Math.max(...familias.map(([, n]) => n));
      familias.forEach(([nombre, n], j) => {
        const x0 = 38 + j * 6.4;
        g.push(ventana(x0, x0 + 4.4, z + 6, z + 29));
        const luces = Math.max(1, Math.round((n / mayor) * 8));
        const pts = Array.from({ length: 8 }, (_, q) => at([x0 + 2.2, yF + 0.5, z + 8.4 + q * 2.6]));
        g.push(`<g class="medidor" data-familia="${esc(nombre)}" data-n="${n}">`);
        g.push(`<g class="luz-on">${D(pts.slice(0, luces), { size: 0.62, tone: "hi" })}</g>`);
        g.push(`<g class="luz-off">${D(pts.slice(luces), { size: 0.5, tone: "faint" })}</g></g>`);
      });
      for (const cx of TOMAS) tomaEn(cx, z + 18);
      // interruptor y el piloto de servicio vivo (marca de estado, teal)
      // (bajo la placa, lejos de las asas)
      g.push(S(k.slabOf({ x: 26, y: yF, w: 6, d: 0.6, r: 0.3 }, z + 5, 9, P, 1), { tone: "lo", crease: "none", m: "acero" }));
      g.push(S(k.slabOf({ x: 27.7, y: yF + 0.6, w: 2.6, d: 1.6, r: 0.5 }, z + 9, 3.4, P, 1), { tone: "mid", m: "metal" }));
      g.push(L(k.sideRing([19, yF, z + 10.5], 1.3, "y", P, 14), { tone: "mid" }));
      g.push(`<g class="marca-vivo">${D([at([19, yF, z + 10.5])], { size: 0.85, tone: "hi" })}</g>`);
      zToma.push(z + 18);
    } else {
      const cx = TOMAS[i - 1];
      if (i === 1) {
        // Analítica: una ventana con la rejilla de una tabla
        g.push(ventana(40, 78, z + 4, tope - 4));
        const filas = [z + 8.5, z + 12.5, tope - 8.5].map((zz) => tramo([40, yF + 0.5, zz], [78, yF + 0.5, zz], P));
        const cols = [52, 64].map((xx) => tramo([xx, yF + 0.5, z + 4], [xx, yF + 0.5, tope - 4], P));
        g.push(L(filas.join("") + cols.join(""), { tone: "lo", className: "en-oscuro" }));
      } else if (i === 2) {
        // Automatización: seis pilotos de tareas con su bisel y una ranura de lectura
        const pil = Array.from({ length: 6 }, (_, q) => [42 + q * 6, yF, z + 14]);
        g.push(L(pil.map((p) => k.sideRing(p, 1.5, "y", P, 14)).join(""), { tone: "lo" }));
        g.push(D(pil.map(at), { size: 0.55, tone: "lo" }));
        g.push(ventana(42, 72, z + 5, z + 9));
      } else {
        // Agentes: una pantalla con tres renglones de texto
        g.push(ventana(40, 80, z + 4, tope - 4));
        const reng = [30, 22, 26].map((largo, j) => tramo([42.5, yF + 0.5, tope - 7.5 - j * 3.6], [42.5 + largo, yF + 0.5, tope - 7.5 - j * 3.6], P));
        g.push(L(reng.join(""), { tone: "lo", free: true, className: "en-oscuro" }));
      }
      tomaEn(cx, z + h / 2);
      zToma.push(z + h / 2);
      // piloto del módulo: un aro; se enciende (teal) cuando le llega el dato
      const pp = [W - 16, yF, tope - 5];
      g.push(L(k.sideRing(pp, 1.3, "y", P, 14), { tone: "mid" }));
      g.push(D([at(pp)], { size: 0.5, tone: "faint" }));
      pilotos.push(pp);
    }
    fija.push(`<g data-modulo="${i}">${g.join("")}</g>`);
  });

  // panel derecho con rejillas de ventilación (ranuras cerradas) y el techo
  const panel = { x: W, y: 0, w: 3, d: yF, r: 0.5 };
  const rejillas = [];
  for (let fila = 0; fila < 5; fila++) {
    const zz = 22 + fila * 16;
    for (const [y0, y1] of [[8, 26], [32, 50]]) {
      rejillas.push(k.pathOf([[W + 3, y0, zz], [W + 3, y1, zz], [W + 3, y1, zz + 2.2], [W + 3, y0, zz + 2.2]].map(at), true));
    }
  }
  fija.push(S(k.slabOf(panel, 8, TECHO - 8, P, 2), { tone: "mid", m: "metal", inner: L(rejillas.join(""), { tone: "lo" }) }));
  const techo = { x: -4, y: -1, w: W + 8, d: FD + 3, r: 1.5 };
  fija.push(S(k.slabOf(techo, TECHO, 6, P, 3, 0.8), { tone: "mid", m: "metal" }));
  fija.push(L(k.planOutline(k.insetPlan(techo, 3), TECHO + 6, P, 2), { tone: "faint" }));
  const tornT = k.corners(techo, 5.5);
  fija.push(L(tornT.map(([x, y]) => k.ring(x, y, 1.4, TECHO + 6, P, 12)).join(""), { tone: "lo" }));
  fija.push(D(tornT.map(([x, y]) => at([x, y, TECHO + 6])), { size: 0.45 }));

  // cables: de la toma de cada módulo a su toma en el de datos, por delante de los frentes
  const yC = yF + 2.4;
  const PAQ = 3.8; // alto del dato
  const viajes = [];
  const viva = [];
  modulos.forEach((_, j) => {
    const cx = TOMAS[j];
    const arriba = zToma[j + 1] - 2.4;
    const abajo = zToma[0] + 2.4;
    const d = k.pathOf([[cx, yC, arriba], [cx, yC, abajo]].map(at));
    const clavija = (zc) =>
      S(k.slabOf({ x: cx - 1.7, y: yF + 0.7, w: 3.4, d: 3.4, r: 0.6 }, zc - 2.4, 4.8, P, 2), { tone: "mid", m: "acero" }) +
      L(k.sideSeam({ x: cx - 1.7, y: yF + 0.7, w: 3.4, d: 3.4, r: 0.6 }, zc - 0.8, P, 2), { tone: "faint" });
    fija.push(`<g class="cable">${clavija(zToma[j + 1])}${clavija(zToma[0])}<path class="cable-forro" d="${d}"/><path class="cable-alma" d="${d}"/></g>`);
    // el dato: una pieza ámbar que sube por el cable, armada justo encima de la clavija de datos
    const z0 = abajo + 0.6, z1 = arriba - PAQ - 0.6;
    const paquete = { x: cx - 1.8, y: yC - 1.8, w: 3.6, d: 3.6, r: 1.2 };
    viva.push(`<g data-v="dato${j}" style="opacity:0">${S(k.slabOf(paquete, z0, PAQ, P, 3, 0.4), { tone: "mid", m: "ambar" })}</g>`);
    viajes.push(k.axisVector(P, [0, 0, z1 - z0]).map(r1));
  });
  // los pilotos de los módulos, encendidos (teal), aparecen cuando llega el dato
  pilotos.forEach((pp, j) => viva.push(`<g data-v="piloto${j}" class="marca-vivo" style="opacity:0">${D([at(pp)], { size: 0.85, tone: "hi" })}</g>`));

  // franjas de pantalla de cada módulo, para elegir con el puntero
  const franjas = UNID.map(({ z, h }) => {
    const [, y0] = at([W / 2, yF, z + h]);
    const [, y1] = at([W / 2, yF, z]);
    return [r1(y0), r1(y1)];
  });
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-capas",
    etiqueta: `Un bastidor de equipos. Abajo, el módulo de datos con ${fuentes} fuentes y ${herramientas} herramientas: un medidor por cada una de las ${familias.length} familias, encendido según cuántas tiene, y tres tomas. Encima, ${modulos.map((m) => `${m.nombre} (${m.puerta})`).join(", ")}, cada uno con un cable a su toma. El dato sube por el cable del módulo que pregunta.`,
    fija,
    viva,
    vivo: {
      viajes,
      franjas: franjas.slice(1),
      modulos: modulos.map((m) => ({ n: m.nombre.toLowerCase(), p: m.puerta, q: m.que })),
      reposo: `datos · ${fuentes} fuentes · ${herramientas} herramientas`,
    },
  });
}
