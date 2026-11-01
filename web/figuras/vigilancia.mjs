// Fig. vigilancia: un puesto de guardia. Cuatro buzones (teal) en fila, uno por sistema que vigilas
// (SECOP II, SUIN-Juriscol, SECOP I, SIC: los del catálogo), cada uno con su puerta, cerradura,
// placa y su banderita al costado; un carro con su lector que los recorre por una viga; y una
// impresora al final. Lo que se mueve: el carro va al buzón, lo lee, la banderita (lo único ámbar)
// se levanta si algo cambió, y solo entonces el registro corre por la canaleta hasta la impresora,
// que saca su tique. Lo que cambia y cuándo es ilustrativo; los sistemas, reales.
import { D, L, S, base, encuadre, k, lampara, matrizPlano, r1, regla, sombra, svgDe } from "./comun.mjs";

export function vigilancia(DATOS, huella) {
  const { carriles } = DATOS.vigilancia;
  const n = carriles.length;
  const BX = (i) => 18 + i * 38; // centro de cada buzón
  const B = { w: 24, d: 22, h: 20 };
  const ZV = 44; // viga
  const YV = -22;
  const PLACA = { x: -26, y: -36, w: 236, d: 66, r: 4 };
  const IMP = { x: 168, y: -13, w: 26, d: 26, h: 16 }; // impresora
  const CAN = { y: 14.5, d: 7 }; // canaleta del registro, delante de los buzones
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -14, 0), [-12, YV, ZV + 6], [160, YV, ZV + 6], [BX(0) + B.w / 2, 0, B.h + 12]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const fija = [];
  const viva = [];

  fija.push(base(PLACA, 0, 5, P));
  fija.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // pórtico: dos postes atrás y la viga, con su regla de pasos
  const postes = [-12, 160];
  for (const x of postes) {
    fija.push(S(k.slabOf({ x: x - 5, y: YV - 5, w: 10, d: 10, r: 1.2 }, 0, 2, P, 2), { m: "acero", tone: "lo" }));
    fija.push(D([[x - 3.4, YV - 3.4], [x + 3.4, YV + 3.4]].map(([a, b]) => at([a, b, 2])), { size: 0.36 }));
    fija.push(S(k.slabOf({ x: x - 3, y: YV - 3, w: 6, d: 6, r: 0.8 }, 2, ZV - 2, P, 2, 0.4), { m: "metal", tone: "mid", inner: L(k.sideSeam({ x: x - 3, y: YV - 3, w: 6, d: 6, r: 0.8 }, 8, P, 2), { tone: "faint" }) }));
  }
  const viga = { x: -16, y: YV - 3, w: 180, d: 6, r: 0.8 };
  fija.push(S(k.slabOf(viga, ZV, 5, P, 2, 0.5), { m: "papel", tone: "mid", inner: L(k.sideSeam(viga, ZV + 2.5, P, 2), { tone: "faint" }) }));
  const marcas = k.sideTicks(-4, 152, 4, 5, YV + 3, ZV + 5, [1.2, 2.2], P);
  fija.push(L(marcas.minor, { tone: "lo" }), L(marcas.major, { tone: "mid" }));
  fija.push(D(postes.map((x) => at([x, YV, ZV + 5])), { size: 0.45 }));

  // la canaleta por donde corre el registro: de los buzones a la impresora
  const canal = { x: 2, y: CAN.y, w: IMP.x - 2, d: CAN.d, r: 0.8 };
  fija.push(S(k.slabOf(canal, 0, 1.4, P, 2, 0.3), { m: "acero", tone: "lo" }));
  fija.push(L(k.planOutline({ x: canal.x + 1.2, y: CAN.y + 1.3, w: canal.w - 2.4, d: 1.4, r: 0.7 }, 1.4, P, 2), { tone: "mid" }));

  // los buzones, de izquierda (lejos) a derecha (cerca)
  const banderas = [];
  carriles.forEach((c, i) => {
    const x0 = BX(i) - B.w / 2, y0 = -B.d / 2, yF = y0 + B.d;
    const cuerpo = { x: x0, y: y0, w: B.w, d: B.d, r: 1.5 };
    const g = [];
    g.push(sombra({ x: x0 - 1.5, y: y0 - 1.5, w: B.w + 3, d: B.d + 3, r: 2 }, 0, P, { pad: 2 }));
    g.push(S(k.slabOf({ x: x0 - 1.5, y: y0 - 1.5, w: B.w + 3, d: B.d + 3, r: 2 }, 0, 1.6, P, 3), { m: "metal", tone: "lo" }));
    g.push(S(k.slabOf(cuerpo, 1.6, B.h - 1.6, P, 3, 0.6), { m: "teal-fuerte", tone: "hi", inner: L(k.sideSeam(cuerpo, B.h - 4, P, 3), { tone: "lo" }) }));
    // la ranura de la tapa y sus cuatro tornillos
    g.push(L(k.planOutline({ x: BX(i) - 6, y: -1.2, w: 12, d: 2.4, r: 1 }, B.h, P, 2), { tone: "hi" }));
    g.push(D([at([x0 + 3, y0 + B.d - 3, B.h]), at([x0 + B.w - 3, y0 + B.d - 3, B.h]), at([x0 + 3, y0 + 3, B.h]), at([x0 + B.w - 3, y0 + 3, B.h])], { size: 0.4 }));
    // la puerta del frente: su contorno, dos bisagras, la placa con tres renglones y la cerradura
    const puerta = k.pathOf([[x0 + 2.5, yF, 3.4], [x0 + B.w - 2.5, yF, 3.4], [x0 + B.w - 2.5, yF, B.h - 5.6], [x0 + 2.5, yF, B.h - 5.6]].map(at), true);
    g.push(L(puerta, { tone: "lo" }));
    for (const zz of [5.4, B.h - 7.6]) g.push(S(k.slabOf({ x: x0 + 1.5, y: yF, w: 1.6, d: 0.8, r: 0.3 }, zz, 1.6, P, 1), { m: "acero", tone: "mid", crease: "none" }));
    g.push(S(k.slabOf({ x: x0 + 5, y: yF, w: 12, d: 0.5, r: 0.3 }, 6, 6.4, P, 1), { m: "papel", tone: "lo", crease: "none" }));
    const reng = [8.4, 6, 7.2].map((l, j) => k.segment([x0 + 6.4, yF + 0.5, 10.8 - j * 1.8], [x0 + 6.4 + l, yF + 0.5, 10.8 - j * 1.8], P));
    g.push(L(reng.join(""), { tone: "lo", free: true }));
    g.push(D([at([x0 + 5.8, yF + 0.5, 11.8]), at([x0 + 16.2, yF + 0.5, 11.8])], { size: 0.3 }));
    const cerradura = [x0 + B.w - 5, yF, 9.2];
    g.push(L(k.sideRing(cerradura, 1.2, "y", P, 14), { tone: "mid" }));
    g.push(D([at(cerradura)], { size: 0.45, tone: "hi" }));
    // el eje de la banderita, en el costado
    const eje = [x0 + B.w, 4, 13];
    g.push(L(k.sideRing(eje, 1.1, "x", P, 12), { tone: "mid" }));
    fija.push(`<g data-buzon="${i}">${g.join("")}</g>`);
    // la banderita, en el plano del costado (u = y, v = z): un brazo de metal y la placa ámbar
    const M = matrizPlano(P, "x", x0 + B.w + 0.6);
    const [u0, v0] = [eje[1], eje[2]];
    const brazo = `<path class="ban-brazo" d="M${r1(u0 - 12)} ${r1(v0 - 0.55)}H${r1(u0 + 0.6)}V${r1(v0 + 0.55)}H${r1(u0 - 12)}Z"/>`;
    // la placa es de metal mientras está abajo; levantada, se enciende (la única ámbar)
    const placaD = `M${r1(u0 - 12)} ${r1(v0 + 0.55)}H${r1(u0 - 1.8)}V${r1(v0 + 6.6)}H${r1(u0 - 12)}Z`;
    const placa = `<path class="ban-placa-metal" d="${placaD}"/><path class="ban-placa" data-v="banderaA${i}" style="opacity:0" d="${placaD}"/>`;
    banderas.push(`<g transform="matrix(${M.join(" ")})"><g data-v="bandera${i}" data-pivote="${u0} ${v0}">${brazo}${placa}</g><circle class="ban-eje" cx="${u0}" cy="${v0}" r="0.8"/></g>`);
  });

  // impresora del registro: cuerpo, boca, perilla y su piloto
  const cuerpoI = { x: IMP.x, y: IMP.y, w: IMP.w, d: IMP.d, r: 1.2 };
  fija.push(sombra(cuerpoI, 0, P, { pad: 2 }));
  fija.push(S(k.slabOf({ x: IMP.x - 1.5, y: IMP.y - 1.5, w: IMP.w + 3, d: IMP.d + 3, r: 2 }, 0, 1.6, P, 3), { m: "metal", tone: "lo" }));
  fija.push(S(k.slabOf(cuerpoI, 1.6, IMP.h - 1.6, P, 2, 0.5), { m: "ocre-fuerte", tone: "mid", inner: L(k.sideSeam(cuerpoI, 5, P, 2), { tone: "lo" }) }));
  const ticket = { x: IMP.x + 5, y: -0.3, w: IMP.w - 10, d: 0.6, r: 0.1 };
  fija.push(L(k.planOutline({ x: ticket.x - 1, y: -1, w: ticket.w + 2, d: 2, r: 0.8 }, IMP.h, P, 2), { tone: "mid" }));
  fija.push(D(k.corners(cuerpoI, 2.4).map(([x, y]) => at([x, y, IMP.h])), { size: 0.4 }));
  fija.push(S(k.cylinder(IMP.x + 6, IMP.y + IMP.d - 5, 2.6, IMP.h, 2.4, P, 20), { m: "acero", tone: "mid" }));
  fija.push(L(k.knurl(IMP.x + 6, IMP.y + IMP.d - 5, 2.6, IMP.h, IMP.h + 2.4, 18, P), { tone: "lo" }));
  const lImp = lampara([IMP.x + IMP.w - 5, IMP.y + IMP.d, 9.4], 1.9, "y", P);
  fija.push(lImp.fija);
  // la boca de la canaleta en la impresora
  fija.push(S(k.slabOf({ x: IMP.x - 1, y: CAN.y - 0.5, w: 3, d: CAN.d + 1, r: 0.5 }, 0, 4, P, 2), { m: "acero", tone: "mid" }));

  // ----- capa viva
  viva.push(banderas.join(""));
  // el registro: una cápsula oscura que corre por la canaleta, armada frente al primer buzón
  // el registro: una cápsula en tinta con el filo claro, del doble de la de antes (se lee a 1x)
  const reg = { x: BX(0) - 4.8, y: CAN.y + 1, w: 9.6, d: 5, r: 2.4 };
  const [rx, ry] = at([BX(0), CAN.y + CAN.d / 2, 3.2]);
  viva.push(`<g data-v="registro" data-c="${r1(rx)} ${r1(ry)}" style="transform:scale(0);opacity:0">${S(k.slabOf(reg, 1.4, 3.6, P, 3, 0.6), { m: "bosque", tone: "mid" })}</g>`);
  // el tique, recortado por el plano de la tapa en la boca: lo que queda dentro no se ve
  const yb = 0;
  const rT = [0.8, 0.55, 0.7, 0.45].map((f, j) => k.segment([ticket.x + 2, yb + 0.3, IMP.h - 3.5 - j * 2.6], [ticket.x + 2 + (ticket.w - 4) * f, yb + 0.3, IMP.h - 3.5 - j * 2.6], P));
  const corteI = [at([IMP.x - 10, yb, IMP.h]), at([IMP.x + IMP.w + 10, yb, IMP.h])];
  viva.push(`<clipPath id="vg-t"><path d="${k.pathOf([corteI[0], corteI[1], [corteI[1][0], corteI[1][1] - 200], [corteI[0][0], corteI[0][1] - 200]], true)}"/></clipPath>`);
  viva.push(`<g clip-path="url(#vg-t)"><g data-v="tique">${S(k.slabOf(ticket, 2, IMP.h - 2.4, P, 1), { m: "papel", tone: "hi", inner: L(rT.join(""), { tone: "lo", free: true }) })}</g></g>`);
  viva.push(lImp.luz("marca-vivo", "impreso"));

  // el carro del lector, armado sobre el buzón 0: patín en la viga, brazo, lector y su piloto (vivo)
  const X0 = BX(0);
  const c = [];
  const patin = { x: X0 - 7, y: YV - 5, w: 14, d: 10, r: 1.2 };
  c.push(S(k.slabOf(patin, ZV - 3, 11, P, 2, 0.5), { m: "metal", tone: "mid", inner: L(k.sideSeam(patin, ZV + 2.5, P, 2), { tone: "faint" }) }));
  c.push(D([at([X0 - 4, YV - 2, ZV + 8]), at([X0 + 4, YV - 2, ZV + 8])], { size: 0.42 }));
  const brazo = { x: X0 - 3, y: YV + 5, w: 6, d: -YV - 2, r: 0.8 };
  c.push(S(k.slabOf(brazo, ZV - 1, 4, P, 2, 0.4), { m: "acero", tone: "mid" }));
  c.push(S(k.cylinder(X0, 0, 3.4, ZV - 9, 8, P, 24, 0.6), { m: "papel", tone: "hi" }));
  c.push(L(k.sideArc(X0, 0, 3.4, ZV - 5, P, 18), { tone: "faint" }));
  c.push(S(k.cylinder(X0, 0, 2.2, ZV - 11, 2, P, 20), { m: "bosque", tone: "lo" }));
  // el piloto del lector, en el frente del patín: late mientras vigila
  const lL = lampara([X0 + 3, YV + 5, ZV + 2.6], 1.9, "y", P);
  c.push(lL.fija, lL.luz("marca-vivo", "lector", { visible: true }));
  viva.push(`<g data-v="carro">${c.join("")}</g>`);

  const r3 = (v) => Math.round(v * 1000) / 1000;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-vigilancia",
    etiqueta: `Un puesto de guardia: ${n} buzones, uno por sistema vigilado (${carriles.map((c) => c.s).join(", ")}), y un carro con su lector que los recorre por una viga. Donde algo cambió, el buzón levanta su banderita y el registro corre hasta la impresora, que saca su tique. Los cambios que muestra son ilustrativos.`,
    fija,
    viva,
    vivo: {
      ex: k.axisVector(P, [1, 0, 0]).map(r3),
      ez: k.axisVector(P, [0, 0, 1]).map(r3),
      x: carriles.map((_, i) => BX(i) - X0),
      imp: IMP.x - 3 - X0,
      saca: 11,
      carriles: carriles.map((c) => ({ s: c.s, e: c.e, ev: c.ev.charAt(0).toLowerCase() + c.ev.slice(1) })),
      cajas: carriles.map((_, i) => r1(at([BX(i), 0, B.h / 2])[0])),
    },
  });
}
