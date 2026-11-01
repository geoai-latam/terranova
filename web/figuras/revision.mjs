// Fig. revision: una banda de inspección. De la pila de tu lista sale una ficha (un predio, una
// empresa o un contrato; en ocre, el sujeto), avanza con la banda y para bajo cuatro estaciones, una
// por fuente oficial (las del catálogo para ese tipo). Cada estación cuelga de su poste de atrás,
// baja su palpador y marca su piloto: teal si no hay hallazgo; si hay algo que revisar, el piloto en
// ámbar y una banderita ámbar que se levanta (lo único ámbar). Al final la ficha cae a la bandeja
// del expediente. Los hallazgos son ilustrativos; los tipos, las herramientas y las fuentes, reales.
import { D, L, S, base, encuadre, k, lampara, r1, regla, sombra, svgDe } from "./comun.mjs";

// minúscula al empezar, salvo siglas («áreas protegidas (RUNAP)», «SECOP II»)
const minuscula = (t) => (/^\p{Lu}\p{Ll}/u.test(t) ? t[0].toLowerCase() + t.slice(1) : t);

export function revision(DATOS, huella) {
  const { tipos, hallazgo } = DATOS.revision;
  const ZB = 14; // cara de la banda
  const BANDA = { x: 8, y: -13, w: 180, d: 26, r: 1 };
  const EST = [56, 88, 120, 152]; // x de cada estación
  const YP = -24; // los postes, atrás de la banda
  const ZT = 44; // brazo de la estación
  const BAND = { x: 197, y: -17, w: 30, d: 34, r: 1.5 }; // bandeja del expediente
  const FICHA = { w: 22, d: 17 };
  const X0 = 22; // la ficha sale de la pila aquí
  const SALE = 34; // primera posición de la ficha fuera de la pila
  const PLACA = { x: -32, y: -34, w: 272, d: 66, r: 4 };
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -14, 0), [EST[0], YP, ZT + 16], [EST[3], YP, ZT + 16]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const fija = [];
  const viva = [];

  fija.push(base(PLACA, 0, 5, P));
  fija.push(regla(PLACA.x + 14, PLACA.x + PLACA.w - 14, PLACA.y + PLACA.d, 0, P));

  // motor al principio de la banda: caja con rejilla, perilla moleteada y su piloto (vivo)
  const motor = { x: -24, y: -20, w: 26, d: 26, r: 2 };
  fija.push(sombra(motor, 0, P, { pad: 2 }));
  fija.push(S(k.slabOf(motor, 0, 22, P, 3, 0.6), { m: "ocre-fuerte", tone: "mid", inner: L(k.sideSeam(motor, 5, P, 3), { tone: "faint" }) }));
  const rejas = [];
  for (let q = 0; q < 4; q++) rejas.push(k.planOutline({ x: -20 + q * 5, y: -15, w: 2, d: 14, r: 1 }, 22, P, 3));
  fija.push(L(rejas.join(""), { tone: "lo" }));
  fija.push(D(k.corners(motor, 2.4).map(([x, y]) => at([x, y, 22])), { size: 0.4 }));
  fija.push(S(k.cylinder(-6, 2, 3.4, 22, 3, P, 24), { m: "acero", tone: "mid" }));
  fija.push(L(k.knurl(-6, 2, 3.4, 22, 25, 22, P), { tone: "lo" }));
  // el piloto del motor, en su frente: encendido (la banda está en marcha)
  const pm = lampara([-15, 6, 13], 2.1, "y", P);
  fija.push(pm.fija, pm.luz("marca-vivo", null, { visible: true }));

  // postes de las estaciones (atrás de todo), con su zapata y dos tornillos
  for (const x of EST) {
    fija.push(S(k.slabOf({ x: x - 4.5, y: YP - 4.5, w: 9, d: 9, r: 1.2 }, 0, 1.6, P, 2), { m: "acero", tone: "lo" }));
    fija.push(D([[x - 3, YP - 3], [x + 3, YP + 3]].map(([a, b]) => at([a, b, 1.6])), { size: 0.36 }));
    fija.push(S(k.cylinder(x, YP, 2.6, 1.6, ZT + 3.4, P, 20), { m: "metal", tone: "mid", crease: "none" }));
    fija.push(L(k.sideArc(x, YP, 2.6, 8, P, 14) + k.sideArc(x, YP, 2.6, ZT - 6, P, 14), { tone: "faint" }));
  }

  // la banda: rieles más bajos que su cara (no tapan la ficha), lecho, tambores y costuras
  const rielT = { x: 4, y: -16.5, w: 188, d: 3.5, r: 0.6 };
  const rielD = { x: 4, y: 13, w: 188, d: 3.5, r: 0.6 };
  fija.push(S(k.slabOf(rielT, 0, 12.6, P, 2, 0.4), { m: "metal", tone: "mid", inner: L(k.sideSeam(rielT, 4, P, 2), { tone: "faint" }) }));
  // la banda: caucho en bosque (el color de la marca), con sus bordes claros
  fija.push(S(k.slabOf(BANDA, 10, ZB - 10, P, 4), { m: "bosque", tone: "lo" }));
  const borde = (y) => k.lineOnTop([BANDA.x, y], [BANDA.x + BANDA.w, y], ZB, P);
  fija.push(L(borde(-11) + borde(11), { tone: "lo", className: "en-oscuro" }));
  fija.push(S(k.slabOf(rielD, 0, 12.6, P, 2, 0.4), { m: "metal", tone: "mid", inner: L(k.sideSeam(rielD, 4, P, 2), { tone: "faint" }) }));
  // tambores: un cubo en cada punta del riel delantero, con su eje
  for (const x of [10, 186]) {
    fija.push(L(k.sideRing([x, 16.5, 9], 2.6, "y", P, 20), { tone: "mid" }));
    fija.push(D([at([x, 16.5, 9])], { size: 0.55 }));
  }
  fija.push(D([40, 72, 104, 136, 168].map((x) => at([x, 16.5, 5])), { size: 0.4 }));

  // bandeja del expediente: piso, paredes de atrás y la carpeta con las fichas que ya pasaron
  fija.push(sombra(BAND, 0, P, { pad: 2 }));
  fija.push(S(k.slabOf(BAND, 0, 2.4, P, 3, 0.4), { m: "ocre-fuerte", tone: "mid" }));
  fija.push(S(k.slabOf({ x: BAND.x, y: BAND.y, w: BAND.w, d: 2, r: 0.4 }, 2.4, 5, P, 2), { m: "ocre-fuerte", tone: "mid" }));
  fija.push(S(k.slabOf({ x: BAND.x, y: BAND.y, w: 2, d: BAND.d, r: 0.4 }, 2.4, 5, P, 2), { m: "ocre-fuerte", tone: "mid" }));
  const carpeta = { x: BAND.x + 3, y: BAND.y + 3, w: BAND.w - 6, d: BAND.d - 6, r: 0.8 };
  fija.push(S(k.slabOf(carpeta, 2.4, 0.8, P, 2), { m: "papel", tone: "mid" }));
  const enBandeja = { x: BAND.x + BAND.w / 2 - FICHA.w / 2, y: -FICHA.d / 2, w: FICHA.w, d: FICHA.d, r: 0.8 };
  for (let q = 0; q < 2; q++) fija.push(S(k.slabOf(enBandeja, 3.2 + q * 1.4, 1.4, P, 2), { m: "ocre-fuerte", tone: "hi", crease: "lo" }));

  // ----- capa viva: la cinta (con la ficha), la ficha, la pila, las estaciones y el frente de la bandeja
  // la cinta: travesaños que avanzan solo con la ficha, recortados a la cara de la banda
  const ribs = [];
  for (let x = BANDA.x - 6; x < BANDA.x + BANDA.w + 6; x += 6) ribs.push(k.lineOnTop([x, -11], [x, 11], ZB, P));
  viva.push(`<clipPath id="rv-banda"><path d="${k.planOutline({ ...BANDA, y: -11, d: 22 }, ZB, P, 4)}"/></clipPath>`);
  viva.push(`<g clip-path="url(#rv-banda)"><g data-v="cinta">${L(ribs.join(""), { tone: "lo", className: "nervio" })}</g></g>`);
  // la ficha que corre (armada en X0, bajo la pila)
  const ficha = { x: X0 - FICHA.w / 2, y: -FICHA.d / 2, w: FICHA.w, d: FICHA.d, r: 0.8 };
  const GF = 2.4; // grueso de la ficha: se lee como una ficha, no como una lámina
  const renglones = [0.7, 0.5, 0.62].map((f, j) => k.lineOnTop([ficha.x + 3.4, ficha.y + 4 + j * 3.6], [ficha.x + 3.4 + (FICHA.w - 7) * f, ficha.y + 4 + j * 3.6], ZB + GF, P));
  const [fcx, fcy] = at([X0, 0, ZB + GF / 2]);
  viva.push(`<g data-v="ficha" data-c="${r1(fcx)} ${r1(fcy)}">${S(k.slabOf(ficha, ZB, GF, P, 2, 0.4), { m: "ocre-fuerte", tone: "hi", crease: "lo", inner: L(renglones.join(""), { tone: "mid", free: true }) })}</g>`);
  // la pila de tu lista: placa trasera, dos guías y seis fichas
  viva.push(S(k.slabOf({ x: X0 - FICHA.w / 2 - 3, y: -9, w: 2, d: 18, r: 0.4 }, ZB + 1.8, 14, P, 2), { m: "ocre-fuerte", tone: "mid" }));
  for (let q = 0; q < 6; q++) viva.push(S(k.slabOf(ficha, ZB + 1.8 + q * 1.5, 1.4, P, 2), { m: "ocre", tone: q === 5 ? "hi" : "mid", crease: "lo" }));
  for (const y of [-9.4, 8]) viva.push(S(k.slabOf({ x: X0 + FICHA.w / 2 + 0.2, y, w: 1.6, d: 1.4, r: 0.4 }, ZB + 1.8, 14, P, 1), { m: "acero", tone: "mid", crease: "none" }));

  // las estaciones, de atrás hacia adelante: brazo desde el poste, cabezal colgado, palpador, piloto y bandera
  for (const [j, x] of EST.entries()) {
    const g = [];
    const brazo = { x: x - 3.2, y: YP - 3, w: 6.4, d: -YP + 7, r: 1 };
    g.push(S(k.slabOf(brazo, ZT, 5, P, 2, 0.4), { m: "metal", tone: "mid", inner: L(k.sideSeam(brazo, ZT + 2.5, P, 2), { tone: "faint" }) }));
    g.push(D([[x, YP], [x, 0]].map(([a, b]) => at([a, b, ZT + 5])), { size: 0.45 }));
    const cab = { x: x - 6, y: -6, w: 12, d: 12, r: 1.5 };
    // el palpador (varilla y zapata) baja: va antes del cabezal, que lo tapa arriba
    g.push(
      `<g data-v="palpador${j}">${S(k.cylinder(x, 0, 1.3, ZB + 8.4, ZT - 9 - ZB - 8.4 + 2, P, 16), { m: "acero", tone: "mid", crease: "none" })}` +
        `${S(k.cylinder(x, 0, 3.4, ZB + 6.4, 2, P, 24), { m: "metal", tone: "mid" })}</g>`,
    );
    g.push(S(k.slabOf(cab, ZT - 9, 9, P, 3, 0.5), { m: "papel", tone: "hi", inner: L(k.sideSeam(cab, ZT - 3, P, 3), { tone: "faint" }) }));
    // el piloto en la cara del cabezal: un aro; dentro, teal (sin hallazgo) o ámbar (revisar)
    const lp = lampara([x + 1.6, 6, ZT - 4.6], 2.1, "y", P);
    g.push(lp.fija, lp.luz("marca-vivo", `ok${j}`), lp.luz("marca-revisar", `rev${j}`));
    // la banderita: un pasador y una placa ámbar que se levantan del cabezal si hay algo que revisar
    const bx = x + 4.6;
    const [qx, qy] = at([bx, 0, ZT]);
    g.push(
      `<g data-v="bandera${j}" data-c="${r1(qx)} ${r1(qy)}" style="transform:scale(0);opacity:0">` +
        S(k.slabOf({ x: bx - 0.5, y: -0.5, w: 1, d: 1, r: 0.3 }, ZT, 15, P, 1), { m: "acero", tone: "mid", crease: "none" }) +
        S(k.slabOf({ x: bx - 0.45, y: 0.5, w: 0.9, d: 11, r: 0.2 }, ZT + 7.4, 7.4, P, 1), { m: "ambar", tone: "mid" }) +
        `</g>`,
    );
    viva.push(g.join(""));
  }
  // paredes delanteras de la bandeja, bajas: la ficha que cae queda a la vista sobre las demás
  viva.push(S(k.slabOf({ x: BAND.x + BAND.w - 2, y: BAND.y, w: 2, d: BAND.d, r: 0.4 }, 2.4, 5, P, 2), { m: "ocre-fuerte", tone: "mid" }));
  viva.push(S(k.slabOf({ x: BAND.x, y: BAND.y + BAND.d - 2, w: BAND.w, d: 2, r: 0.4 }, 2.4, 5, P, 2), { m: "ocre-fuerte", tone: "mid" }));
  viva.push(D([at([BAND.x + 3, BAND.y + BAND.d, 5]), at([BAND.x + BAND.w - 3, BAND.y + BAND.d, 5])], { size: 0.38 }));

  const ex = k.axisVector(P, [1, 0, 0]), ez = k.axisVector(P, [0, 0, 1]);
  const r3 = (v) => Math.round(v * 1000) / 1000;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-revision",
    etiqueta: `Una banda de inspección. De la pila de tu lista sale una ficha (${tipos.map((t) => t.tipo.toLowerCase()).join(", ")}) y para bajo cuatro estaciones, una por fuente oficial; cada una marca su piloto, teal sin hallazgo y ámbar con una banderita si hay algo que revisar. Al final cae a la bandeja del expediente. Los hallazgos son ilustrativos.`,
    fija,
    viva,
    vivo: {
      ex: ex.map(r3),
      ez: ez.map(r3),
      sale: SALE - X0,
      est: EST.map((x) => x - X0),
      fin: BANDA.x + BANDA.w + 4 - X0,
      bandeja: BAND.x + BAND.w / 2 - X0,
      cae: ZB - (3.2 + 2 * 1.4),
      gf: GF,
      baja: 6,
      paso: 6,
      tipos: tipos.map((t, i) => ({ t: t.tipo.toLowerCase(), c: t.como, f: t.fuentes.map((f) => [minuscula(f.t), f.e]), h: hallazgo[i] })),
    },
  });
}
