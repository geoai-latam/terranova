// Fig. vigilancia: un puesto de guardia. Cuatro buzones en fila, uno por sistema que vigilas
// (SECOP II, SUIN-Juriscol, SECOP I, SIC: los del catálogo), y un carro con su lector que los
// recorre por una viga. Donde algo cambió, el buzón levanta su bandera y la impresora del extremo
// saca el registro del cambio. Lo que cambia y cuándo es ilustrativo; los sistemas, reales.
import { D, L, S, base, encuadre, k, regla, svgDe } from "./comun.mjs";

export function vigilancia(DATOS, huella) {
  const { carriles } = DATOS.vigilancia;
  const n = carriles.length;
  const BX = (i) => 18 + i * 38; // centro de cada buzón
  const B = { w: 24, d: 22, h: 20 };
  const ZV = 44; // viga
  const YV = -22;
  const PLACA = { x: -26, y: -36, w: 236, d: 66, r: 4 };
  const IMP = { x: 168, y: -13, w: 26, d: 26, h: 16 }; // impresora
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -14, 0), [-12, YV, ZV + 6], [160, YV, ZV + 6]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const out = [];

  out.push(base(PLACA, 0, 5, P));
  out.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // pórtico: dos postes atrás y la viga, con su regla de pasos
  const postes = [-12, 160];
  for (const x of postes) {
    out.push(S(k.slabOf({ x: x - 5, y: YV - 5, w: 10, d: 10, r: 1.2 }, 0, 2, P, 2), { m: "bosque", tone: "lo" }));
    out.push(S(k.slabOf({ x: x - 3, y: YV - 3, w: 6, d: 6, r: 0.8 }, 2, ZV - 2, P, 2, 0.4), { m: "acero", tone: "mid", inner: L(k.sideSeam({ x: x - 3, y: YV - 3, w: 6, d: 6, r: 0.8 }, 8, P, 2), { tone: "faint" }) }));
  }
  const viga = { x: -16, y: YV - 3, w: 180, d: 6, r: 0.8 };
  out.push(S(k.slabOf(viga, ZV, 5, P, 2, 0.5), { m: "papel", tone: "mid", inner: L(k.sideSeam(viga, ZV + 2.5, P, 2), { tone: "faint" }) }));
  const marcas = k.sideTicks(-4, 152, 4, 5, YV + 3, ZV + 5, [1.2, 2.2], P);
  out.push(L(marcas.minor, { tone: "lo" }), L(marcas.major, { tone: "mid" }));
  out.push(D(postes.map((x) => at([x, YV, ZV + 5])), { size: 0.45 }));
  // por dónde viajan los registros: el canto de la viga y el poste hasta la impresora (sin trazo)
  out.push(`<path class="ruta-dato" d="${k.pathOf([at([-6, YV + 3, ZV]), at([160, YV + 3, ZV]), at([160, YV + 3, 3])])}"/>`);

  // los buzones, de izquierda (lejos) a derecha (cerca)
  carriles.forEach((c, i) => {
    const x0 = BX(i) - B.w / 2, y0 = -B.d / 2;
    const cuerpo = { x: x0, y: y0, w: B.w, d: B.d, r: 1.5 };
    const g = [];
    g.push(S(k.slabOf({ x: x0 - 1.5, y: y0 - 1.5, w: B.w + 3, d: B.d + 3, r: 2 }, 0, 1.6, P, 3), { m: "bosque", tone: "lo" }));
    // el cuerpo entero; la bandera se pinta después, recortada por el plano de la tapa en la
    // ranura (y = 0): lo que queda bajo la tapa no se ve.
    g.push(S(k.slabOf(cuerpo, 1.6, B.h - 1.6, P, 3, 0.6), { m: "azul", tone: "hi", inner: L(k.sideSeam(cuerpo, B.h - 5, P, 3), { tone: "faint" }) }));
    g.push(L(k.planOutline({ x: BX(i) - 1, y: -0.8, w: 8.6, d: 1.6, r: 0.6 }, B.h, P, 2), { tone: "lo" }));
    g.push(D([at([x0 + 3, y0 + B.d - 3, B.h]), at([x0 + B.w - 3, y0 + B.d - 3, B.h]), at([x0 + 3, y0 + 3, B.h]), at([x0 + B.w - 3, y0 + 3, B.h])], { size: 0.4 }));
    const ban = [];
    ban.push(S(k.slabOf({ x: BX(i) + 5.6, y: -0.25, w: 1.2, d: 0.5, r: 0.2 }, B.h - 20, 20.4, P, 1), { m: "acero", tone: "mid", crease: "none" }));
    ban.push(S(k.slabOf({ x: BX(i) - 0.4, y: -0.2, w: 6, d: 0.4, r: 0.1 }, B.h - 5, 4.6, P, 1), { m: "ambar", tone: "hi", lit: true }));
    const corte = [at([BX(i) - 30, 0, B.h]), at([BX(i) + 30, 0, B.h])];
    const clip = k.pathOf([corte[0], corte[1], [corte[1][0], corte[1][1] - 200], [corte[0][0], corte[0][1] - 200]], true);
    g.push(`<clipPath id="vg-b${i}"><path d="${clip}"/></clipPath>`);
    g.push(`<g clip-path="url(#vg-b${i})"><g data-bandera="${i}">${ban.join("")}</g></g>`);
    // frente: placa con tres renglones (el nombre del sistema va en la lectura)
    const yF = y0 + B.d;
    g.push(S(k.slabOf({ x: x0 + 4, y: yF, w: 14, d: 0.6, r: 0.3 }, 5, 7, P, 1), { m: "papel", tone: "lo", crease: "none" }));
    const reng = [9, 6.5, 8].map((l, j) => k.segment([x0 + 5.6, yF + 0.6, 10.2 - j * 2], [x0 + 5.6 + l, yF + 0.6, 10.2 - j * 2], P));
    g.push(L(reng.join(""), { tone: "lo", free: true }));
    // piloto en el frente
    g.push(`<g data-piloto="${i}" class="late piloto-teal" style="--p:${(2.6 + i * 0.45).toFixed(2)}s;--d:-${(i * 0.8).toFixed(1)}s">${D([at([x0 + B.w - 4, yF, 15])], { size: 1.3, tone: "mid" })}</g>`);
    out.push(`<g data-buzon="${i}">${g.join("")}</g>`);
  });

  // impresora del registro: el cuerpo entero y el ticket, recortado por el plano de la tapa en la boca
  const yb = 0;
  const cuerpoI = { x: IMP.x, y: IMP.y, w: IMP.w, d: IMP.d, r: 1.2 };
  out.push(S(k.slabOf({ x: IMP.x - 1.5, y: IMP.y - 1.5, w: IMP.w + 3, d: IMP.d + 3, r: 2 }, 0, 1.6, P, 3), { m: "bosque", tone: "lo" }));
  out.push(S(k.slabOf(cuerpoI, 1.6, IMP.h - 1.6, P, 2, 0.5), { m: "ocre", tone: "mid", inner: L(k.sideSeam(cuerpoI, 5, P, 2), { tone: "faint" }) }));
  const ticket = { x: IMP.x + 5, y: yb - 0.3, w: IMP.w - 10, d: 0.6, r: 0.1 };
  out.push(L(k.planOutline({ x: ticket.x - 1, y: -1, w: ticket.w + 2, d: 2, r: 0.8 }, IMP.h, P, 2), { tone: "lo" }));
  const rT = [0.8, 0.55, 0.7, 0.45].map((f, j) => k.segment([ticket.x + 2, yb + 0.3, IMP.h - 3.5 - j * 2.6], [ticket.x + 2 + (ticket.w - 4) * f, yb + 0.3, IMP.h - 3.5 - j * 2.6], P));
  const corteI = [at([IMP.x - 10, yb, IMP.h]), at([IMP.x + IMP.w + 10, yb, IMP.h])];
  out.push(`<clipPath id="vg-t"><path d="${k.pathOf([corteI[0], corteI[1], [corteI[1][0], corteI[1][1] - 200], [corteI[0][0], corteI[0][1] - 200]], true)}"/></clipPath>`);
  out.push(`<g clip-path="url(#vg-t)"><g data-ticket>${S(k.slabOf(ticket, 2, IMP.h - 2.4, P, 1), { tone: "hi", inner: L(rT.join(""), { tone: "lo", free: true }) })}</g></g>`);
  out.push(D(k.corners(cuerpoI, 2.4).map(([x, y]) => at([x, y, IMP.h])), { size: 0.4 }));
  out.push(`<g data-piloto="imp">${D([at([IMP.x + IMP.w - 4, IMP.y + IMP.d, 10])], { size: 0.95, tone: "mid" })}</g>`);
  out.push(S(k.cylinder(IMP.x + 6, IMP.y + IMP.d - 5, 2.6, IMP.h, 2.4, P, 20), { m: "bosque", tone: "mid" }));
  out.push(L(k.knurl(IMP.x + 6, IMP.y + IMP.d - 5, 2.6, IMP.h, IMP.h + 2.4, 18, P), { tone: "lo" }));

  // el carro del lector, armado sobre el buzón 0: patín en la viga, brazo y lector
  const X0 = BX(0);
  const c = [];
  const patin = { x: X0 - 7, y: YV - 5, w: 14, d: 10, r: 1.2 };
  c.push(S(k.slabOf(patin, ZV - 3, 11, P, 2, 0.5), { m: "ocre", tone: "hi", inner: L(k.sideSeam(patin, ZV + 2.5, P, 2), { tone: "faint" }) }));
  c.push(D([at([X0 - 4, YV - 2, ZV + 8]), at([X0 + 4, YV - 2, ZV + 8])], { size: 0.42 }));
  const brazo = { x: X0 - 3, y: YV + 5, w: 6, d: -YV - 2, r: 0.8 };
  c.push(S(k.slabOf(brazo, ZV - 1, 4, P, 2, 0.4), { m: "acero", tone: "mid" }));
  c.push(S(k.cylinder(X0, 0, 3.4, ZV - 9, 8, P, 24, 0.6), { m: "papel", tone: "hi" }));
  c.push(L(k.sideArc(X0, 0, 3.4, ZV - 5, P, 18), { tone: "faint" }));
  c.push(S(k.cylinder(X0, 0, 2.2, ZV - 11, 2, P, 20), { tone: "lo", className: "oscuro" }));
  c.push(`<g data-lector>${D([at([X0 + 1.6, 3.6, ZV - 4])], { size: 0.7, tone: "mid" })}</g>`);
  out.push(`<g data-carro>${c.join("")}</g>`);

  const r3 = (v) => Math.round(v * 1000) / 1000;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-vigilancia",
    etiqueta: `Un puesto de guardia: ${n} buzones, uno por sistema vigilado (${carriles.map((c) => c.s).join(", ")}), y un carro con su lector que los recorre por una viga. Donde algo cambió, el buzón levanta su bandera y la impresora saca el registro. Los cambios que muestra son ilustrativos.`,
    cuerpo: out,
    vivo: {
      ex: k.axisVector(P, [1, 0, 0]).map(r3),
      ez: k.axisVector(P, [0, 0, 1]).map(r3),
      x: carriles.map((_, i) => BX(i) - X0),
      sube: 10,
      saca: 11,
      carriles: carriles.map((c) => ({ s: c.s, e: c.e, ev: c.ev.charAt(0).toLowerCase() + c.ev.slice(1) })),
    },
  });
}
