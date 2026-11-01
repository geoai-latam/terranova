// Fig. asistente: un tablero de conmutación. Atrás, un panel con una toma por entidad (las que
// responden a las preguntas del asistente, del catálogo) y su piloto; adelante, la mesa del
// asistente con su pantalla y su teclado. Con cada pregunta, la clavija del cordón va a la toma de
// la entidad que publica el dato y su piloto se enciende. Preguntas, entidades y licencias: reales.
import { D, L, S, base, encuadre, k, porProf, regla, svgDe } from "./comun.mjs";

export function asistente(DATOS, huella) {
  const { preguntas, nodos } = DATOS.asistente;
  const COLS = 4, FILAS = Math.ceil(nodos.length / COLS);
  const PAN = { x: 0, y: -26, w: 132, d: 6 }; // panel: cara en y = -20
  const YC = PAN.y + PAN.d; // cara del panel
  const ZT = 80; // tope del panel
  const toma = (j) => [17 + (j % COLS) * 32.6, YC, ZT - 16 - Math.floor(j / COLS) * 15];
  const MESA = { x: 20, y: 2, w: 92, d: 30, r: 2 };
  const ZM = 22; // cara de la mesa
  const PUERTO = [MESA.x + 64, MESA.y + 8, ZM];
  const PLACA = { x: -16, y: -36, w: 164, d: 74, r: 4 };
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -14, 0), [PAN.x, PAN.y, ZT + 4], [PAN.x + PAN.w, PAN.y, ZT + 4]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const out = [];

  out.push(base(PLACA, 0, 5, P));
  out.push(regla(PLACA.x + 12, PLACA.x + PLACA.w - 12, PLACA.y + PLACA.d, 0, P));

  // el panel: zócalo, marco, cara con sus tomas, pilotos y regletas; tapa con tornillos
  out.push(S(k.slabOf({ x: PAN.x - 4, y: PAN.y - 4, w: PAN.w + 8, d: PAN.d + 8, r: 1.5 }, 0, 4, P, 3, 0.5), { m: "bosque", tone: "lo" }));
  const marco = { x: PAN.x, y: PAN.y, w: PAN.w, d: PAN.d, r: 1 };
  out.push(S(k.slabOf(marco, 4, ZT - 4, P, 2, 0.5), { m: "ambar", tone: "mid", inner: L(k.sideSeam(marco, 10, P, 2), { tone: "faint" }) }));
  const cara = [];
  const pilotos = [];
  nodos.forEach((_, j) => {
    const [x, y, z] = toma(j);
    cara.push(L(k.sideRing([x, y, z], 3.4, "y", P, 22), { tone: "mid" }));
    cara.push(`<path class="boca" d="${k.pathOf(Array.from({ length: 16 }, (_, q) => { const a = (q / 16) * Math.PI * 2; return at([x + Math.cos(a) * 1.7, y, z + Math.sin(a) * 1.7]); }), true)}"/>`);
    pilotos.push(`<g data-piloto="${j}" class="late piloto-claro" style="--p:${(3 + (j % 5) * 0.55).toFixed(2)}s;--d:-${((j * 7) % 11 * 0.4).toFixed(1)}s">${D([at([x, y, z + 6.4])], { size: 2.2, tone: "mid" })}</g>`);
  });
  // regletas bajo cada fila (texto impreso)
  for (let f = 0; f < FILAS; f++) {
    const zz = ZT - 16 - f * 15 - 6.5;
    for (let c = 0; c < COLS; c++) {
      const x = 17 + c * 32.6;
      cara.push(L(k.segment([x - 7, YC, zz], [x + 7, YC, zz], P), { tone: "lo", free: true }));
    }
  }
  out.push(cara.join(""), pilotos.join(""));
  out.push(D([[4, 8], [PAN.w - 4, 8], [4, ZT - 4], [PAN.w - 4, ZT - 4]].map(([x, z]) => at([x, YC, z])), { size: 0.42 }));
  const tapa = { x: PAN.x - 2, y: PAN.y - 2, w: PAN.w + 4, d: PAN.d + 4, r: 1.2 };
  out.push(S(k.slabOf(tapa, ZT, 3.5, P, 2, 0.5), { m: "bosque", tone: "mid" }));
  out.push(D(k.corners(tapa, 2.4).map(([x, y]) => at([x, y, ZT + 3.5])), { size: 0.4 }));

  // la mesa: patas, tablero, cajón, pantalla, teclado y el puerto del cordón
  for (const [x, y] of porProf(k.corners(MESA, 4), P)) {
    out.push(S(k.slabOf({ x: x - 2, y: y - 2, w: 4, d: 4, r: 0.8 }, 0, ZM - 3, P, 2), { m: "acero", tone: "mid", crease: "none" }));
  }
  out.push(S(k.slabOf(MESA, ZM - 3, 3, P, 3, 0.6), { m: "bosque", tone: "mid", inner: L(k.sideSeam(MESA, ZM - 1.5, P, 3), { tone: "faint" }) }));
  const cajon = { x: MESA.x + 30, y: MESA.y + MESA.d, w: 32, d: 0.6, r: 0.3 };
  out.push(S(k.slabOf(cajon, ZM - 2.6, 2.2, P, 1), { m: "ocre", tone: "lo", crease: "none" }));
  // pantalla: pie, cuerpo y la ventana con renglones
  const pant = { x: MESA.x + 6, y: MESA.y + 4, w: 30, d: 10, r: 1.5 };
  out.push(S(k.slabOf({ x: pant.x + 10, y: pant.y + 2, w: 10, d: 6, r: 1 }, ZM, 2, P, 2), { m: "acero", tone: "mid" }));
  out.push(S(k.slabOf(pant, ZM + 2, 22, P, 3, 0.6), { m: "papel", tone: "hi", inner: L(k.sideSeam(pant, ZM + 6, P, 3), { tone: "faint" }) }));
  const yv = pant.y + pant.d;
  out.push(S(k.slabOf({ x: pant.x + 3, y: yv, w: pant.w - 6, d: 0.5, r: 0.3 }, ZM + 8, 14, P, 1), { tone: "lo", className: "oscuro", crease: "none" }));
  const reng = [18, 12, 15].map((l, q) => k.segment([pant.x + 5, yv + 0.5, ZM + 19 - q * 3.4], [pant.x + 5 + l, yv + 0.5, ZM + 19 - q * 3.4], P));
  out.push(`<g data-renglones class="escribe">${L(reng.join(""), { tone: "lo", free: true, className: "en-oscuro" })}</g>`);
  // teclado
  const tec = { x: MESA.x + 6, y: MESA.y + 18, w: 36, d: 10, r: 1 };
  out.push(S(k.slabOf(tec, ZM, 1.6, P, 2, 0.4), { m: "papel", tone: "hi" }));
  const teclas = [];
  for (let f = 0; f < 3; f++) for (let c = 0; c < 10; c++) teclas.push(at([tec.x + 3 + c * 3.3, tec.y + 2.4 + f * 2.7, ZM + 1.6]));
  out.push(D(teclas, { size: 0.5, tone: "lo" }));
  // puerto del cordón con su aro
  const [px, py, pz] = PUERTO;
  out.push(S(k.cylinder(px, py, 3.2, pz, 1.4, P, 22), { m: "ocre", tone: "mid" }));
  out.push(L(k.ring(px, py, 1.6, pz + 1.4, P, 14), { tone: "lo" }));

  // el cordón y la clavija: figuras.js los rehace en cada cuadro
  out.push(`<g class="cordon"><path class="cable-forro" d=""/><path class="cable-alma" d=""/></g>`);
  out.push(`<circle class="clavija" r="2.4" cx="0" cy="0"/>`);

  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-asistente",
    etiqueta: `Un tablero de conmutación: un panel con ${nodos.length} tomas, una por entidad (${nodos.join(", ")}), y la mesa del asistente con su pantalla. Con cada pregunta, la clavija del cordón va a la toma de la entidad que publica el dato.`,
    cuerpo: out,
    vivo: {
      P,
      puerto: [px, py, pz + 1.4],
      tomas: nodos.map((_, j) => toma(j)),
      preguntas: preguntas.map((q) => ({ p: q.p, e: q.e, l: q.l, j: nodos.indexOf(q.e) })),
    },
  });
}
