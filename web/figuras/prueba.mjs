// Fig. prueba: un fichero oscuro (bosque, con el filo claro) de cinco fichas sobre un banco, con su
// tampón y su sello al lado de la última ficha, la de la huella. Cada ficha es una capa de la
// prueba que trae toda respuesta rt/1 (dato y estado, procedencia, licencia, servido_desde y
// huella), con los valores de la respuesta real del predio de Santa Marta (sinic_predio_en_punto). Lo que se mueve: la ficha
// que se lee sube y su pestaña se enciende (el único ámbar); con la huella, el sello se entinta en
// el tampón y la ficha queda sellada.
import { D, L, S, base, encuadre, k, r1, regla, sombra, svgDe } from "./comun.mjs";

export function prueba(DATOS, huella) {
  const { capas } = DATOS.prueba;
  const W = 86, FD = 96; // caja: x 0..W, y 0..FD (el frente mira a +y)
  const T = 2.6; // grueso de las paredes
  const PISO = 3.5;
  const ALTO_F = 46, TAB = 6.5, ANCHO_T = 14; // ficha y pestaña
  const SUBE = 24;
  const PLACA = { x: -16, y: -14, w: W + 66, d: FD + 30, r: 4 };
  // De atrás (huella) hacia adelante (dato): la ficha del frente es la primera capa.
  const yFicha = (i) => FD - 16 - i * 14.5;
  const xTab = (i) => 7 + i * 14.6;
  const n = capas.length;
  // el tampón y el sello, junto a la pared derecha, a la altura de la ficha de la huella
  const PAD = { x: W + 9, y: yFicha(n - 1) - 12, w: 26, d: 22, r: 2 };
  const [sx, sy] = [PAD.x + PAD.w / 2, PAD.y + PAD.d / 2];
  const ZF = 6; // cara del tampón

  const { P, ancho, alto } = encuadre(
    [...k.boxCorners(PLACA, -14, 0), [0, yFicha(n - 1), PISO + ALTO_F + TAB + SUBE], [W, 0, 44], [W, FD, 30], [sx, sy, ZF + 32]],
    { azimuth: 58 },
  );
  const at = (p) => k.iso(p, P);
  const fija = [];
  const viva = [];

  fija.push(base(PLACA, 0, 5, P));
  fija.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // caja: piso, pared trasera e izquierda (atrás de las fichas), todo en bosque con el filo claro
  const caja = { x: 0, y: 0, w: W, d: FD, r: 1.2 };
  fija.push(sombra(caja, 0, P, { pad: 3 }));
  fija.push(S(k.slabOf(caja, 0, PISO, P, 3, 0.5), { m: "bosque", tone: "mid" }));
  const trasera = { x: 0, y: 0, w: W, d: T, r: 0.4 };
  fija.push(S(k.slabOf(trasera, PISO, 40, P, 2), { m: "bosque", tone: "mid", inner: L(k.sideSeam(trasera, PISO + 34, P, 2), { tone: "lo" }) }));
  fija.push(S(k.slabOf({ x: 0, y: 0, w: T, d: FD, r: 0.4 }, PISO, 34, P, 2), { m: "bosque", tone: "mid" }));
  // riel del tope en el piso y el tope trasero con su tornillo
  fija.push(L(k.planOutline({ x: W / 2 - 2, y: T + 1.5, w: 4, d: FD - 30, r: 2 }, PISO, P, 3), { tone: "mid" }));
  const tope = { x: W / 2 - 18, y: yFicha(n - 1) - 9, w: 36, d: 7, r: 1 };
  fija.push(S(k.slabOf(tope, PISO, 24, P, 2, 0.4), { m: "metal", tone: "mid", inner: L(k.sideSeam(tope, PISO + 5, P, 2), { tone: "faint" }) }));
  fija.push(S(k.slabOf({ x: W / 2 - 1.5, y: T, w: 3, d: tope.y - T, r: 1.4 }, PISO + 15, 3, P, 3), { m: "acero", tone: "lo", crease: "none" }));
  fija.push(D([at([W / 2 - 12, tope.y + 3.5, PISO + 24]), at([W / 2 + 12, tope.y + 3.5, PISO + 24])], { size: 0.45 }));

  // el tampón: base, tapa abierta detrás, caja y el fieltro entintado
  fija.push(sombra(PAD, 0, P, { pad: 3 }));
  const tapa = { x: PAD.x - 1, y: PAD.y - 7.5, w: PAD.w + 2, d: 6.5, r: 1 };
  fija.push(S(k.slabOf(tapa, 0, 2.2, P, 2), { m: "metal", tone: "lo" }));
  fija.push(L(k.planOutline(k.insetPlan(tapa, 1.2), 2.2, P, 2), { tone: "faint" }));
  fija.push(S(k.slabOf(PAD, 0, ZF, P, 3, 0.5), { m: "metal", tone: "mid", inner: L(k.sideSeam(PAD, 2, P, 3), { tone: "faint" }) }));
  fija.push(S(k.slabOf(k.insetPlan(PAD, 2.6), ZF, 0.4, P, 3), { m: "bosque", tone: "lo", crease: "none" }));
  fija.push(D(k.corners(PAD, 1.4).map(([x, y]) => at([x, y, ZF])), { size: 0.38 }));

  // las fichas (capa viva: una sube y las de adelante la tapan), de atrás hacia adelante
  const pestanas = [];
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
    g.push(S(k.slabOf(ficha, z0, ALTO_F, P, 1), { m: "ficha", tone: "hi", crease: "lo", inner: cara + L(filete, { tone: "faint" }) + L(ranura, { tone: "lo" }) }));
    // pestaña de celuloide que abraza el canto, con su renglón; encendida, en ámbar
    const tab = { x: xTab(i), y: y - 0.6, w: ANCHO_T, d: 2.1, r: 0.5 };
    const renglon = L(k.segment([tab.x + 2.4, y + 1.5, z1 + 3], [tab.x + ANCHO_T - 3.6, y + 1.5, z1 + 3], P), { tone: "mid", free: true });
    g.push(S(k.slabOf(tab, z1 - 1.4, TAB + 1.4, P, 2), { m: "metal", tone: "mid", crease: "lo" }), renglon);
    g.push(`<g data-v="pestana${i}" style="opacity:0">${S(k.slabOf(tab, z1 - 1.4, TAB + 1.4, P, 2), { m: "ambar", tone: "mid", crease: "lo" })}${renglon}</g>`);
    // la ficha de la huella lleva el sello cuando se comprueba: un aro teal con su marca
    if (i === n - 1) {
      const c = [W - 20, yf + 0.05, z1 - 9];
      const [cx, cy] = at(c);
      g.push(`<g data-v="sello" data-c="${r1(cx)} ${r1(cy)}" style="transform:scale(0);opacity:0">` +
        `<path class="sello-marca" d="${k.sideRing(c, 4.2, "y", P, 28) + k.sideRing(c, 3.2, "y", P, 24)}"/>` +
        `<path class="sello-marca" d="${k.pathOf([[c[0] - 1.6, yf, c[2]], [c[0] - 0.3, yf, c[2] - 1.3], [c[0] + 1.8, yf, c[2] + 1.4]].map(at))}"/></g>`);
    }
    viva.push(`<g data-v="ficha${i}">${g.join("")}</g>`);
    const [px, py] = at([xTab(i) + ANCHO_T / 2, y, PISO + ALTO_F + TAB]);
    pestanas.push([Math.round(px), Math.round(py)]);
  }

  // pared derecha y frente bajo, con portaetiqueta, tirador y cantoneras: tapan las fichas
  const der = { x: W - T, y: 0, w: T, d: FD, r: 0.4 };
  viva.push(S(k.slabOf(der, PISO, 34, P, 2), { m: "bosque", tone: "mid", inner: L(k.sideSeam(der, PISO + 5, P, 2), { tone: "lo" }) }));
  const frente = { x: 0, y: FD - T, w: W, d: T, r: 0.4 };
  viva.push(S(k.slabOf(frente, PISO, 22, P, 2), { m: "bosque", tone: "mid", inner: L(k.sideSeam(frente, PISO + 5, P, 2), { tone: "lo" }) }));
  const yF = FD;
  const etiqueta = { x: W / 2 - 13, y: yF, w: 26, d: 0.7, r: 0.3 };
  viva.push(S(k.slabOf(etiqueta, PISO + 12, 8, P, 1), { m: "papel", tone: "lo", crease: "none" }));
  viva.push(k.faceTextSvg(k.sideMatrix([W / 2 - 9.4, yF + 0.7], PISO + 14.6, P, "left"), "rt/1", { size: 4.2, tone: "hi" }));
  viva.push(D([at([W / 2 - 11.4, yF + 0.7, PISO + 16]), at([W / 2 + 11.4, yF + 0.7, PISO + 16])], { size: 0.4 }));
  // tirador: dos postes y la barra
  for (const x of [W / 2 - 10, W / 2 + 7.6]) viva.push(S(k.slabOf({ x, y: yF, w: 2.4, d: 3, r: 0.5 }, PISO + 4.4, 2.4, P, 1), { m: "metal", tone: "mid", crease: "none" }));
  viva.push(S(k.slabOf({ x: W / 2 - 10.8, y: yF + 3, w: 21.6, d: 2, r: 0.9 }, PISO + 4, 3.2, P, 2), { m: "metal", tone: "mid" }));
  // la varilla que atraviesa las fichas asoma por el frente con su tuerca
  viva.push(S(k.slabOf({ x: W / 2 - 1.2, y: yF, w: 2.4, d: 4, r: 1.1 }, PISO + 9.4, 2.4, P, 3), { m: "acero", tone: "lo", crease: "none" }));
  // cantoneras de metal en las cuatro esquinas de arriba
  const canto = (x, y, z) => S(k.slabOf({ x, y, w: 4.6, d: 4.6, r: 0.6 }, z, 1.3, P, 2), { m: "metal", tone: "mid" });
  viva.push(canto(-0.9, -0.9, PISO + 40), canto(W - 3.7, -0.9, PISO + 40), canto(-0.9, FD - 3.7, PISO + 22), canto(W - 3.7, FD - 3.7, PISO + 22));
  viva.push(
    D(
      [[1.4, 1.4, 41.3], [W - 1.4, 1.4, 41.3], [1.4, FD - 1.4, 23.3], [W - 1.4, FD - 1.4, 23.3]].map(([x, y, z]) => at([x, y, PISO + z])),
      { size: 0.4 },
    ),
  );

  // el sello, sobre el tampón: base de goma, cuerpo, cuello y pomo moleteado
  const sello = [];
  const cuerpo = { x: sx - 8, y: sy - 5.5, w: 16, d: 11, r: 1.2 };
  sello.push(S(k.slabOf(k.insetPlan(cuerpo, 0.8), ZF + 0.4, 2, P, 2), { m: "bosque", tone: "lo" }));
  sello.push(S(k.slabOf(cuerpo, ZF + 2.4, 6, P, 3, 0.6), { m: "papel", tone: "hi", inner: L(k.sideSeam(cuerpo, ZF + 4.9, P, 3), { tone: "faint" }) }));
  sello.push(S(k.cylinder(sx, sy, 2.4, ZF + 8.4, 8, P, 20), { m: "acero", tone: "mid", crease: "none" }));
  sello.push(L(k.sideArc(sx, sy, 2.4, ZF + 12, P, 16), { tone: "faint" }));
  sello.push(S(k.cylinder(sx, sy, 4.8, ZF + 16.4, 6.4, P, 28, 0.8), { m: "metal", tone: "mid" }));
  sello.push(L(k.knurl(sx, sy, 4.8, ZF + 16.4, ZF + 22.8, 30, P), { tone: "lo" }));
  viva.push(`<g data-v="sellador">${sello.join("")}</g>`);

  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-prueba",
    etiqueta: `Un fichero con ${n} fichas, una por cada capa de la prueba de una respuesta: ${capas.map((c) => c.campo).join(", ")}. La ficha que se lee sube; con la huella, el sello se entinta en el tampón y la ficha queda sellada.`,
    fija,
    viva,
    vivo: {
      sube: k.axisVector(P, [0, 0, SUBE]).map(r1),
      alza: k.axisVector(P, [0, 0, 10]).map(r1),
      pestanas,
      lecturas: capas.map((c) => `${c.campo} · ${c.valor}`),
    },
  });
}
