// Fig. prueba: un fichero de cinco fichas sobre un banco, con su sello y su tampón. Cada ficha es
// una capa de la prueba que trae toda respuesta rt/1 (dato y estado, procedencia, licencia,
// servido_desde y huella), con los valores de una respuesta real de banrep_trm_recientes. Lo que se
// mueve: una ficha sube del fichero para leerse y baja; con la huella, el sello baja al tampón.
import { D, L, S, base, encuadre, k, regla, svgDe } from "./comun.mjs";

export function prueba(DATOS, huella) {
  const { capas } = DATOS.prueba;
  const W = 86, FD = 96; // caja: x 0..W, y 0..FD (el frente mira a +y)
  const T = 2.6; // grueso de las paredes
  const PISO = 3.5;
  const ALTO_F = 46, TAB = 6.5, ANCHO_T = 14; // ficha y pestaña
  const SUBE = 30;
  const PLACA = { x: -16, y: -14, w: W + 92, d: FD + 30, r: 4 };
  // De atrás (huella) hacia adelante (dato): la ficha del frente es la primera capa.
  const yFicha = (i) => FD - 16 - i * 14.5;
  const xTab = (i) => 7 + i * 14.6;
  const n = capas.length;
  const PAD = { x: W + 14, y: FD - 40, w: 28, d: 22, r: 2 }; // tampón
  const SELLO = [PAD.x + PAD.w + 19, PAD.y + PAD.d / 2]; // el sello espera a la derecha del tampón
  const CRUZA = PAD.x + PAD.w / 2 - SELLO[0];

  const { P, ancho, alto } = encuadre(
    [...k.boxCorners(PLACA, -14, 0), [0, yFicha(n - 1), PISO + ALTO_F + TAB + SUBE], [W, 0, 44], [W, FD, 30]],
    { azimuth: 58 },
  );
  const at = (p) => k.iso(p, P);
  const out = [];

  out.push(base(PLACA, 0, 5, P));
  out.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // caja: piso, pared trasera e izquierda (atrás de las fichas)
  const caja = { x: 0, y: 0, w: W, d: FD, r: 1.2 };
  out.push(`<path class="iso-halo" d="${k.haloOf(caja, 0, 3, P)}"/>`);
  out.push(S(k.slabOf(caja, 0, PISO, P, 3, 0.5), { tone: "mid" }));
  out.push(S(k.slabOf({ x: 0, y: 0, w: W, d: T, r: 0.4 }, PISO, 40, P, 2), { tone: "mid" }));
  out.push(S(k.slabOf({ x: 0, y: 0, w: T, d: FD, r: 0.4 }, PISO, 34, P, 2), { tone: "mid" }));
  // riel del tope en el piso y el tope trasero con su tornillo
  out.push(L(k.planOutline({ x: W / 2 - 2, y: T + 1.5, w: 4, d: FD - 30, r: 2 }, PISO, P, 3), { tone: "lo" }));
  const tope = { x: W / 2 - 18, y: yFicha(n - 1) - 9, w: 36, d: 7, r: 1 };
  out.push(S(k.slabOf(tope, PISO, 24, P, 2, 0.4), { tone: "mid", inner: L(k.sideSeam(tope, PISO + 5, P, 2), { tone: "faint" }) }));
  out.push(S(k.slabOf({ x: W / 2 - 1.5, y: T, w: 3, d: tope.y - T, r: 1.4 }, PISO + 15, 3, P, 3), { tone: "lo", crease: "none" }));
  out.push(D([at([W / 2 - 12, tope.y + 3.5, PISO + 24]), at([W / 2 + 12, tope.y + 3.5, PISO + 24])], { size: 0.45 }));

  // las fichas, de atrás hacia adelante; cada una en su grupo para subir
  for (let i = n - 1; i >= 0; i--) {
    const y = yFicha(i);
    const g = [];
    const ficha = { x: 5, y, w: W - 10, d: 0.9, r: 0.2 };
    const z0 = PISO, z1 = PISO + ALTO_F;
    // renglones de la cara (texto impreso): cabecera, filete y cuatro renglones, en la mitad de arriba
    const yf = y + 0.9;
    const reng = (zz, x1) => k.segment([10, yf, zz], [x1, yf, zz], P);
    const cara =
      L(reng(z1 - 7, 10 + 26 + (i % 2) * 8), { tone: "mid", free: true }) +
      L([reng(z1 - 14, W - 14), reng(z1 - 19, W - 24 - i * 3), reng(z1 - 24, W - 18), reng(z1 - 29, W - 38 + i * 2)].join(""), { tone: "lo", free: true });
    const filete = k.sideSeam(ficha, z1 - 10.5, P, 1);
    // perforación de la varilla, abajo en el centro (una ranura cerrada)
    const ranura = k.pathOf([[W / 2 - 3, yf, z0 + 4], [W / 2 + 3, yf, z0 + 4], [W / 2 + 3, yf, z0 + 6.4], [W / 2 - 3, yf, z0 + 6.4]].map(at), true);
    g.push(S(k.slabOf(ficha, z0, ALTO_F, P, 1), { tone: "hi", crease: "faint", inner: cara + L(filete, { tone: "faint" }) + L(ranura, { tone: "lo" }) }));
    // pestaña de celuloide que abraza el canto, con su renglón
    const tab = { x: xTab(i), y: y - 0.6, w: ANCHO_T, d: 2.1, r: 0.5 };
    g.push(`<g data-pestana>${S(k.slabOf(tab, z1 - 1.4, TAB + 1.4, P, 2), { tone: "hi", crease: "lo" })}</g>`);
    g.push(L(k.segment([tab.x + 2.4, y + 1.5, z1 + 3], [tab.x + ANCHO_T - 3.6, y + 1.5, z1 + 3], P), { tone: "mid", free: true }));
    out.push(`<g data-ficha="${i}">${g.join("")}</g>`);
  }

  // pared derecha y frente bajo, con portaetiqueta, tirador y cantoneras
  const der = { x: W - T, y: 0, w: T, d: FD, r: 0.4 };
  out.push(S(k.slabOf(der, PISO, 34, P, 2), { tone: "mid", inner: L(k.sideSeam(der, PISO + 5, P, 2), { tone: "faint" }) }));
  const frente = { x: 0, y: FD - T, w: W, d: T, r: 0.4 };
  out.push(S(k.slabOf(frente, PISO, 22, P, 2), { tone: "mid", inner: L(k.sideSeam(frente, PISO + 5, P, 2), { tone: "faint" }) }));
  const yF = FD;
  const etiqueta = { x: W / 2 - 13, y: yF, w: 26, d: 0.7, r: 0.3 };
  out.push(S(k.slabOf(etiqueta, PISO + 12, 8, P, 1), { tone: "lo", crease: "none" }));
  out.push(k.faceTextSvg(k.sideMatrix([W / 2 - 9.4, yF + 0.7], PISO + 14.6, P, "left"), "rt/1", { size: 4.2, tone: "hi" }));
  out.push(D([at([W / 2 - 11.4, yF + 0.7, PISO + 16]), at([W / 2 + 11.4, yF + 0.7, PISO + 16])], { size: 0.4 }));
  // tirador: dos postes y la barra
  for (const x of [W / 2 - 10, W / 2 + 7.6]) out.push(S(k.slabOf({ x, y: yF, w: 2.4, d: 3, r: 0.5 }, PISO + 4.4, 2.4, P, 1), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: W / 2 - 10.8, y: yF + 3, w: 21.6, d: 2, r: 0.9 }, PISO + 4, 3.2, P, 2), { tone: "mid" }));
  // la varilla que atraviesa las fichas asoma por el frente con su tuerca moleteada
  out.push(S(k.slabOf({ x: W / 2 - 1.2, y: yF, w: 2.4, d: 4, r: 1.1 }, PISO + 9.4, 2.4, P, 3), { tone: "lo", crease: "none" }));
  // cantoneras en las cuatro esquinas de arriba
  const canto = (x, y, z) => S(k.slabOf({ x, y, w: 4.6, d: 4.6, r: 0.6 }, z, 1.3, P, 2), { tone: "mid" });
  out.push(canto(-0.9, -0.9, PISO + 40), canto(W - 3.7, -0.9, PISO + 40), canto(-0.9, FD - 3.7, PISO + 22), canto(W - 3.7, FD - 3.7, PISO + 22));
  out.push(
    D(
      [[1.4, 1.4, 41.3], [W - 1.4, 1.4, 41.3], [1.4, FD - 1.4, 23.3], [W - 1.4, FD - 1.4, 23.3]].map(([x, y, z]) => at([x, y, PISO + z])),
      { size: 0.4 },
    ),
  );

  // el tampón: caja con la tapa abierta detrás y el fieltro entintado
  out.push(S(k.slabOf({ x: PAD.x - 1, y: PAD.y - 7.5, w: PAD.w + 2, d: 6.5, r: 1 }, 0, 2.2, P, 2), { tone: "lo" }));
  out.push(S(k.slabOf(PAD, 0, 6, P, 3, 0.5), { tone: "mid", inner: L(k.sideSeam(PAD, 2, P, 3), { tone: "faint" }) }));
  out.push(S(k.slabOf(k.insetPlan(PAD, 3), 6, 0.4, P, 3), { tone: "lo", className: "teal", crease: "none" }));
  out.push(D(k.corners(PAD, 1.6).map(([x, y]) => at([x, y, 6])), { size: 0.38 }));

  // el sello: base de goma, cuerpo, cuello y pomo moleteado; baja al tampón con la huella
  const [sx, sy] = SELLO;
  const sello = [];
  const cuerpo = { x: sx - 9, y: sy - 6, w: 18, d: 12, r: 1.2 };
  sello.push(`<path class="iso-halo" d="${k.haloOf(cuerpo, 0, 2, P)}"/>`);
  sello.push(S(k.slabOf(k.insetPlan(cuerpo, 0.8), 0, 2, P, 2), { tone: "lo", className: "teal" }));
  sello.push(S(k.slabOf(cuerpo, 2, 6, P, 3, 0.6), { tone: "hi", inner: L(k.sideSeam(cuerpo, 4.5, P, 3), { tone: "faint" }) }));
  sello.push(S(k.cylinder(sx, sy, 2.6, 8, 9, P, 20), { tone: "mid", crease: "none" }));
  sello.push(L(k.sideArc(sx, sy, 2.6, 12, P, 16), { tone: "faint" }));
  sello.push(S(k.cylinder(sx, sy, 5.2, 17, 7, P, 28, 0.8), { tone: "mid" }));
  sello.push(L(k.sideArc(sx, sy, 5.2, 19.4, P, 28) + k.sideArc(sx, sy, 5.2, 21.6, P, 28), { tone: "faint" }));
  out.push(`<g data-sello>${sello.join("")}</g>`);

  // pestañas en pantalla, para elegir con el puntero
  const pestanas = capas.map((_, i) => {
    const [x, y] = at([xTab(i) + ANCHO_T / 2, yFicha(i), PISO + ALTO_F + TAB]);
    return [Math.round(x), Math.round(y)];
  });
  const r1 = (v) => Math.round(v * 10) / 10;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-prueba",
    etiqueta: `Un fichero con ${n} fichas, una por cada capa de la prueba de una respuesta: ${capas.map((c) => c.campo).join(", ")}. Una ficha sube para leerse y vuelve a su lugar; con la huella, el sello baja al tampón.`,
    cuerpo: out,
    vivo: {
      sube: k.axisVector(P, [0, 0, SUBE]).map(r1),
      // el sello cruza hasta el tampón (x), sube 12 en el camino y baja a 6,4 (el fieltro)
      sello: { cruza: k.axisVector(P, [CRUZA, 0, 0]).map(r1), arriba: k.axisVector(P, [0, 0, 1]).map((v) => Math.round(v * 1000) / 1000), fieltro: 6.4, salto: 12 },
      pestanas,
      lecturas: capas.map((c) => `${c.campo} · ${c.valor}`),
    },
  });
}
