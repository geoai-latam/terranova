// Fig. revision: una banda de inspección. De la pila de tu lista sale una ficha (un predio, una
// empresa o un contratista), pasa bajo cuatro estaciones, una por fuente oficial (las del catálogo
// para ese tipo), cada una baja su palpador y enciende su piloto: verde si no hay hallazgo, ámbar
// si hay algo que revisar (y la ficha levanta una bandera). Al final cae a la bandeja del
// expediente. Los hallazgos son ilustrativos; los tipos y las fuentes, reales.
import { D, L, S, base, encuadre, k, porProf, regla, svgDe } from "./comun.mjs";

export function revision(DATOS, huella) {
  const { tipos, hallazgo } = DATOS.revision;
  const ZB = 14; // cara de la banda
  const BANDA = { x: 8, y: -13, w: 180, d: 26, r: 1 };
  const EST = [56, 88, 120, 152]; // x de cada estación
  const YP = 21; // postes a ±YP
  const ZT = 46; // travesaño
  const BAND = { x: 196, y: -17, w: 30, d: 34, r: 1.5 }; // bandeja
  const FICHA = { w: 18, d: 14 };
  const X0 = 20; // la ficha sale de la pila aquí
  const PLACA = { x: -32, y: -34, w: 270, d: 68, r: 4 };
  const P0 = encuadre([...k.boxCorners(PLACA, -14, 0), [EST[0], -YP, ZT + 8], [EST[3], YP, ZT + 8]], { azimuth: 57 });
  const { P, ancho, alto } = P0;
  const at = (p) => k.iso(p, P);
  const out = [];

  out.push(base(PLACA, 0, 5, P));
  out.push(regla(PLACA.x + 14, PLACA.x + PLACA.w - 14, PLACA.y + PLACA.d, 0, P));

  // motor al principio de la banda: caja con ranuras, piloto y perilla moleteada
  const motor = { x: -24, y: -20, w: 26, d: 26, r: 2 };
  out.push(S(k.slabOf(motor, 0, 22, P, 3, 0.6), { tone: "mid", inner: L(k.sideSeam(motor, 5, P, 3), { tone: "faint" }) }));
  const rejas = [];
  for (let q = 0; q < 4; q++) rejas.push(k.planOutline({ x: -20 + q * 5, y: -15, w: 2, d: 14, r: 1 }, 22, P, 3));
  out.push(L(rejas.join(""), { tone: "lo" }));
  out.push(D(k.corners(motor, 2.4).map(([x, y]) => at([x, y, 22])), { size: 0.4 }));
  out.push(S(k.cylinder(-6, 2, 3.4, 22, 3, P, 24), { tone: "mid" }));
  out.push(L(k.knurl(-6, 2, 3.4, 22, 25, 22, P), { tone: "lo" }));
  out.push(`<g data-motor>${D([at([-17, 3.5, 22])], { size: 0.9, tone: "mid" })}</g>`);

  // postes de atrás (detrás del riel trasero)
  const poste = (x, y) => S(k.cylinder(x, y, 2.4, 0, ZT, P, 20), { tone: "mid", crease: "none" }) + L(k.sideArc(x, y, 2.4, 6, P, 14), { tone: "faint" });
  const zapata = (x, y) => S(k.slabOf({ x: x - 4, y: y - 4, w: 8, d: 8, r: 1.2 }, 0, 1.6, P, 2), { tone: "lo" }) + D([[x - 2.6, y - 2.6], [x + 2.6, y + 2.6]].map(([a, b]) => at([a, b, 1.6])), { size: 0.36 });
  for (const x of EST) out.push(zapata(x, -YP) + poste(x, -YP));

  // riel trasero
  const rielT = { x: 4, y: -16.5, w: 188, d: 3.5, r: 0.6 };
  out.push(S(k.slabOf(rielT, 0, 17, P, 2, 0.4), { tone: "mid", inner: L(k.sideSeam(rielT, 4, P, 2), { tone: "faint" }) }));

  // bandeja del expediente: piso, paredes de atrás y la pila que ya hay
  out.push(S(k.slabOf(BAND, 0, 2.4, P, 3, 0.4), { tone: "mid" }));
  out.push(S(k.slabOf({ x: BAND.x, y: BAND.y, w: BAND.w, d: 2, r: 0.4 }, 2.4, 10, P, 2), { tone: "mid" }));
  out.push(S(k.slabOf({ x: BAND.x, y: BAND.y, w: 2, d: BAND.d, r: 0.4 }, 2.4, 10, P, 2), { tone: "mid" }));
  const enBandeja = { x: BAND.x + BAND.w / 2 - FICHA.w / 2, y: -FICHA.d / 2 };
  for (let q = 0; q < 2; q++) out.push(S(k.slabOf({ ...enBandeja, w: FICHA.w, d: FICHA.d, r: 0.8 }, 2.4 + q * 1.4, 1.4, P, 2), { tone: "hi" }));

  // la banda: lecho, costuras de los bordes y travesaños entre ellas
  out.push(S(k.slabOf(BANDA, 10, ZB - 10, P, 4), { tone: "lo" }));
  const borde = (y) => k.lineOnTop([BANDA.x, y], [BANDA.x + BANDA.w, y], ZB, P);
  out.push(L(borde(-11) + borde(11), { tone: "lo" }));
  const ribs = [];
  for (let x = BANDA.x + 6; x < BANDA.x + BANDA.w - 4; x += 6) ribs.push(k.lineOnTop([x, -11], [x, 11], ZB, P));
  out.push(L(ribs.join(""), { tone: "faint" }));

  // la ficha que corre (con su bandera, oculta hasta que haya hallazgo)
  const ficha = { x: X0 - FICHA.w / 2, y: -FICHA.d / 2, w: FICHA.w, d: FICHA.d, r: 0.8 };
  const renglones = [0.7, 0.5, 0.62].map((f, j) => k.lineOnTop([ficha.x + 3, ficha.y + 3.5 + j * 3], [ficha.x + 3 + (FICHA.w - 6) * f, ficha.y + 3.5 + j * 3], ZB + 1.4, P));
  const bandera =
    S(k.slabOf({ x: ficha.x + FICHA.w - 4, y: ficha.y + 2, w: 0.9, d: 0.9, r: 0.2 }, ZB + 1.4, 9, P, 1), { tone: "mid", crease: "none" }) +
    S(k.slabOf({ x: ficha.x + FICHA.w - 9.1, y: ficha.y + 2, w: 5, d: 0.7, r: 0.2 }, ZB + 6.4, 4, P, 1), { tone: "hi", lit: true });
  out.push(
    `<g data-ficha>${S(k.slabOf(ficha, ZB, 1.4, P, 2), { tone: "hi", inner: L(renglones.join(""), { tone: "lo", free: true }) })}` +
      `<g data-bandera>${bandera}</g></g>`,
  );

  // la pila de tu lista: placa trasera, dos guías y seis fichas
  out.push(S(k.slabOf({ x: X0 - FICHA.w / 2 - 3, y: -9, w: 2, d: 18, r: 0.4 }, ZB + 1.8, 14, P, 2), { tone: "mid" }));
  for (let q = 0; q < 6; q++) out.push(S(k.slabOf({ ...ficha, x: ficha.x }, ZB + 1.8 + q * 1.5, 1.4, P, 2), { tone: q === 5 ? "hi" : "mid", crease: "lo" }));
  for (const y of [-9.4, 8]) out.push(S(k.slabOf({ x: X0 + FICHA.w / 2 + 0.2, y, w: 1.6, d: 1.4, r: 0.4 }, ZB + 1.8, 14, P, 1), { tone: "mid", crease: "none" }));

  // riel delantero, paredes delanteras de la bandeja y postes de adelante (antes de los travesaños,
  // que tapan la cabeza de los postes)
  const rielD = { x: 4, y: 13, w: 188, d: 3.5, r: 0.6 };
  out.push(S(k.slabOf(rielD, 0, 17, P, 2, 0.4), { tone: "mid", inner: L(k.sideSeam(rielD, 4, P, 2), { tone: "faint" }) }));
  out.push(D([12, 60, 108, 156, 184].map((x) => at([x, 16.5, 12])), { size: 0.4 }));
  out.push(S(k.slabOf({ x: BAND.x + BAND.w - 2, y: BAND.y, w: 2, d: BAND.d, r: 0.4 }, 2.4, 10, P, 2), { tone: "mid" }));
  out.push(S(k.slabOf({ x: BAND.x, y: BAND.y + BAND.d - 2, w: BAND.w, d: 2, r: 0.4 }, 2.4, 10, P, 2), { tone: "mid" }));

  for (const x of porProf(EST.map((x) => [x, YP]), P).map(([x]) => x)) out.push(zapata(x, YP) + poste(x, YP));

  // estaciones: travesaño, cabezal, palpador y piloto, de atrás hacia adelante
  const palp = [];
  for (const [j, x] of EST.entries()) {
    const g = [];
    g.push(S(k.slabOf({ x: x - 4, y: -YP - 3, w: 8, d: 2 * YP + 6, r: 1 }, ZT, 5, P, 2, 0.4), { tone: "mid", inner: L(k.sideSeam({ x: x - 4, y: -YP - 3, w: 8, d: 2 * YP + 6, r: 1 }, ZT + 2.5, P, 2), { tone: "faint" }) }));
    g.push(D([[x, -YP], [x, YP]].map(([a, b]) => at([a, b, ZT + 5])), { size: 0.45 }));
    const cab = { x: x - 6, y: -6, w: 12, d: 12, r: 1.5 };
    g.push(S(k.slabOf(cab, ZT - 9, 9, P, 3, 0.5), { tone: "hi", inner: L(k.sideSeam(cab, ZT - 3, P, 3), { tone: "faint" }) }));
    // palpador: varilla y zapata, bajan juntos
    g.push(
      `<g data-palpador="${j}">${S(k.cylinder(x, 0, 1.3, ZB + 8.4, ZT - 9 - ZB - 8.4, P, 16), { tone: "mid", crease: "none" })}` +
        `${S(k.cylinder(x, 0, 3.4, ZB + 6.4, 2, P, 24), { tone: "mid" })}</g>`,
    );
    g.push(S(k.cylinder(x, 0, 2.4, ZT + 5, 1.6, P, 20), { tone: "mid" }));
    g.push(`<g data-piloto="${j}">${D([at([x, 0, ZT + 6.6])], { size: 1.5, tone: "mid" })}</g>`);
    palp.push(g.join(""));
  }
  out.push(palp.join(""));

  const ex = k.axisVector(P, [1, 0, 0]), ez = k.axisVector(P, [0, 0, 1]);
  const r3 = (v) => Math.round(v * 1000) / 1000;
  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-revision",
    etiqueta: `Una banda de inspección. De la pila de tu lista sale una ficha (${tipos.map((t) => t.tipo.toLowerCase()).join(", ")}) y pasa bajo cuatro estaciones, una por fuente oficial; cada una enciende su piloto, verde sin hallazgo y ámbar si hay algo que revisar. Al final cae a la bandeja del expediente. Los hallazgos son ilustrativos.`,
    cuerpo: out,
    vivo: {
      ex: ex.map(r3),
      ez: ez.map(r3),
      x0: X0,
      est: EST,
      fin: BANDA.x + BANDA.w,
      bandeja: BAND.x + BAND.w / 2,
      cae: ZB - (2.4 + 2 * 1.4),
      baja: ZB + 6.4 - (ZB + 1.4),
      tipos: tipos.map((t, i) => ({ t: t.tipo.toLowerCase(), c: t.como, f: t.fuentes.map((f) => `${f.t} · ${f.e}`), h: hallazgo[i] })),
    },
  });
}
