// Fig. asistente: un tablero de conmutación. Atrás, un panel en bosque (con el filo claro) con una
// boca de aro metálico por entidad (las que responden a las preguntas del asistente, del catálogo),
// su piloto y su regleta con rótulo; adelante, la mesa del asistente con su pantalla, su teclado y
// la toma del cordón. Con cada pregunta, la clavija sale de la boca anterior y entra en la de la
// entidad que publica el dato; su piloto se enciende (lo único ámbar) y la pantalla escribe la
// respuesta. Preguntas, entidades y licencias: reales.
import { D, L, S, encuadre, k, porProf, r1, sombra, svgDe } from "./comun.mjs";

export function asistente(DATOS, huella) {
  const { preguntas, nodos } = DATOS.asistente;
  const COLS = 4, FILAS = Math.ceil(nodos.length / COLS);
  const PAN = { x: 0, y: -26, w: 132, d: 6 }; // panel: cara en y = -20
  const YC = PAN.y + PAN.d; // cara del panel
  const ZT = 80; // tope del panel
  const toma = (j) => [17 + (j % COLS) * 32.6, YC, ZT - 16 - Math.floor(j / COLS) * 19];
  const MESA = { x: 20, y: 2, w: 92, d: 30, r: 2 };
  const ZM = 22; // cara de la mesa
  const PUERTO = [MESA.x + 66, MESA.y + 7, ZM];
  const PLACA = { x: -10, y: -32, w: 152, d: 70, r: 4 }; // el banco, recortado al panel y la mesa
  const { P, ancho, alto } = encuadre([...k.boxCorners(PLACA, -10, 0), [PAN.x, PAN.y, ZT + 4], [PAN.x + PAN.w, PAN.y, ZT + 4]], { azimuth: 57 });
  const at = (p) => k.iso(p, P);
  const fija = [];
  const viva = [];

  // el banco: una losa baja sobre patas, con ranura y tornillos
  fija.push(sombra(PLACA, -10, P, { pad: 6 }));
  for (const [x, y] of porProf(k.corners(PLACA, 10), P)) {
    fija.push(S(k.cylinder(x, y, 4.6, -10, 1.4, P, 24), { tone: "lo", m: "acero" }));
    fija.push(S(k.cylinder(x, y, 3.4, -8.6, 4.6, P, 24), { tone: "mid", m: "metal" }));
  }
  fija.push(S(k.slabOf(PLACA, -4, 4, P, 6, 1.2), { tone: "lo", m: "trabajo" }));
  fija.push(L(k.planOutline(k.insetPlan(PLACA, 4), 0, P, 4), { tone: "faint" }));
  const torn = k.corners(PLACA, 7.5);
  fija.push(L(torn.map(([x, y]) => k.ring(x, y, 1.7, 0, P, 14)).join(""), { tone: "lo" }));
  fija.push(D(torn.map(([x, y]) => at([x, y, 0])), { size: 0.45 }));

  // el panel: zócalo, cuerpo en bosque con su costura, tapa y tornillos
  fija.push(S(k.slabOf({ x: PAN.x - 4, y: PAN.y - 4, w: PAN.w + 8, d: PAN.d + 8, r: 1.5 }, 0, 4, P, 3, 0.5), { m: "metal", tone: "lo" }));
  const marco = { x: PAN.x, y: PAN.y, w: PAN.w, d: PAN.d, r: 1 };
  fija.push(S(k.slabOf(marco, 4, ZT - 4, P, 2, 0.5), { m: "bosque", tone: "mid", inner: L(k.sideSeam(marco, 10, P, 2), { tone: "lo" }) }));
  // las bocas: aro de metal (relleno entre dos círculos), boca oscura y el piloto encima
  const enCara = (x, z, r, pasos = 24) => Array.from({ length: pasos }, (_, q) => { const a = (q / pasos) * Math.PI * 2; return at([x + Math.cos(a) * r, YC, z + Math.sin(a) * r]); });
  const anillo = (x, z, r0, r1_) => k.pathOf(enCara(x, z, r0), true) + k.pathOf(enCara(x, z, r1_).reverse(), true);
  const cara = [];
  nodos.forEach((_, j) => {
    const [x, , z] = toma(j);
    cara.push(`<path class="boca-aro" d="${anillo(x, z, 3.4, 2)}"/>`);
    cara.push(`<path class="boca" d="${k.pathOf(enCara(x, z, 2), true)}"/>`);
    cara.push(L(k.sideRing([x, YC, z + 6.8], 1.3, "y", P, 14), { tone: "mid" }));
    cara.push(D([at([x, YC, z + 6.8])], { size: 0.5, tone: "faint" }));
  });
  // regletas: bajo cada boca, su placa de rótulo (papel, dos renglones impresos y dos tornillos)
  nodos.forEach((_, j) => {
    const [x, , z] = toma(j);
    const zz = z - 7.6;
    cara.push(S(k.slabOf({ x: x - 8, y: YC, w: 16, d: 0.5, r: 0.3 }, zz - 2, 4, P, 1), { m: "papel", tone: "lo", crease: "none" }));
    cara.push(L(k.segment([x - 6, YC + 0.5, zz + 0.7], [x + [5, 3, 6, 4][j % 4], YC + 0.5, zz + 0.7], P) + k.segment([x - 6, YC + 0.5, zz - 0.8], [x + [1, 3, 0, 2][j % 4], YC + 0.5, zz - 0.8], P), { tone: "lo", free: true }));
    cara.push(D([at([x - 7.2, YC + 0.5, zz]), at([x + 7.2, YC + 0.5, zz])], { size: 0.28 }));
  });
  // la cara del panel con su marco interior: una ranura cerrada a todo lo ancho
  cara.push(L(k.pathOf([[5, YC, 10], [PAN.w - 5, YC, 10], [PAN.w - 5, YC, ZT - 5], [5, YC, ZT - 5]].map(at), true), { tone: "lo" }));
  fija.push(cara.join(""));
  fija.push(D([[4, 8], [PAN.w - 4, 8], [4, ZT - 4], [PAN.w - 4, ZT - 4]].map(([x, z]) => at([x, YC, z])), { size: 0.42 }));
  const tapa = { x: PAN.x - 2, y: PAN.y - 2, w: PAN.w + 4, d: PAN.d + 4, r: 1.2 };
  fija.push(S(k.slabOf(tapa, ZT, 3.5, P, 2, 0.5), { m: "metal", tone: "mid" }));
  fija.push(D(k.corners(tapa, 2.4).map(([x, y]) => at([x, y, ZT + 3.5])), { size: 0.4 }));

  // la mesa: patas, tablero, cajón y la toma del cordón
  for (const [x, y] of porProf(k.corners(MESA, 4), P)) {
    fija.push(S(k.slabOf({ x: x - 2, y: y - 2, w: 4, d: 4, r: 0.8 }, 0, ZM - 3, P, 2), { m: "metal", tone: "mid", crease: "none" }));
  }
  fija.push(S(k.slabOf(MESA, ZM - 3, 3, P, 3, 0.6), { m: "papel", tone: "mid", inner: L(k.sideSeam(MESA, ZM - 1.5, P, 3), { tone: "faint" }) }));
  const cajon = { x: MESA.x + 30, y: MESA.y + MESA.d, w: 32, d: 0.6, r: 0.3 };
  fija.push(S(k.slabOf(cajon, ZM - 2.6, 2.2, P, 1), { m: "metal", tone: "lo", crease: "none" }));
  const [px, py, pz] = PUERTO;
  fija.push(S(k.cylinder(px, py, 3.2, pz, 1.4, P, 22), { m: "acero", tone: "mid" }));
  fija.push(L(k.ring(px, py, 1.6, pz + 1.4, P, 14), { tone: "mid" }));

  // ----- capa viva: un cordón y una clavija por boca (solo uno a la vista), los pilotos ámbar y,
  // encima, la pantalla y el teclado (el cordón pasa detrás de la pantalla)
  const cordones = [], clavijas = [], ambar = [];
  const base = [px, py, pz + 1.4];
  nodos.forEach((_, j) => {
    const [x, y, z] = toma(j);
    const cola = [x, y + 9.4, z]; // donde termina el manguito
    // el cordón sube de la toma de la mesa a la clavija con un vientre hacia el frente, sin bajar de la mesa
    const m = [(base[0] + cola[0]) / 2, (base[1] + cola[1]) / 2 + 7, Math.max((base[2] + cola[2]) / 2 - 3, base[2] + 3)];
    const pts = [];
    for (let q = 0; q <= 24; q++) {
      const t = q / 24, u = 1 - t;
      pts.push(at([0, 1, 2].map((c) => u * u * base[c] + 2 * u * t * m[c] + t * t * cola[c])));
    }
    const d = k.pathOf(pts);
    cordones.push(`<g data-v="cordon${j}" style="opacity:0"><path class="cordon-forro" d="${d}"/><path class="cordon-alma" d="${d}"/></g>`);
    // la clavija: punta de metal (entra en la boca), cuerpo con dos estrías y el manguito oscuro
    const cl = [];
    cl.push(S(k.slabOf({ x: x - 0.8, y: y, w: 1.6, d: 1.6, r: 0.7 }, z - 0.8, 1.6, P, 2), { m: "acero", tone: "mid", crease: "none" }));
    const cuerpo = { x: x - 1.8, y: y + 1.6, w: 3.6, d: 5.4, r: 1.4 };
    cl.push(S(k.slabOf(cuerpo, z - 1.8, 3.6, P, 3, 0.4), { m: "metal", tone: "hi", inner: L(k.sideSeam({ ...cuerpo, y: cuerpo.y + 1.6, d: 1 }, z, P, 3), { tone: "faint" }) }));
    cl.push(S(k.slabOf({ x: x - 1.2, y: y + 7, w: 2.4, d: 2.4, r: 1 }, z - 1.2, 2.4, P, 2), { m: "bosque", tone: "mid", crease: "none" }));
    clavijas.push(`<g data-v="clavija${j}" style="opacity:0">${cl.join("")}</g>`);
    ambar.push(`<g data-v="piloto${j}" class="marca-ambar" style="opacity:0">${D([at([x, YC, z + 6.8])], { size: 1.1, tone: "hi" })}</g>`);
  });
  viva.push(cordones.join(""), clavijas.join(""), ambar.join(""));

  // pantalla: pie, cuerpo, la ventana con dos renglones y la respuesta que se escribe; teclado
  const pant = { x: MESA.x + 6, y: MESA.y + 4, w: 30, d: 10, r: 1.5 };
  viva.push(S(k.slabOf({ x: pant.x + 10, y: pant.y + 2, w: 10, d: 6, r: 1 }, ZM, 2, P, 2), { m: "metal", tone: "mid" }));
  viva.push(S(k.slabOf(pant, ZM + 2, 22, P, 3, 0.6), { m: "papel", tone: "hi", inner: L(k.sideSeam(pant, ZM + 6, P, 3), { tone: "faint" }) }));
  const yv = pant.y + pant.d;
  viva.push(S(k.slabOf({ x: pant.x + 3, y: yv, w: pant.w - 6, d: 0.5, r: 0.3 }, ZM + 8, 14, P, 1), { tone: "lo", m: "bosque", crease: "none" }));
  const reng = (zz, l) => k.segment([pant.x + 5, yv + 0.5, zz], [pant.x + 5 + l, yv + 0.5, zz], P);
  viva.push(L(reng(ZM + 19, 16), { tone: "lo", free: true, className: "en-oscuro" }));
  viva.push(`<g data-v="respuesta" style="opacity:0">${L(reng(ZM + 15.6, 18) + reng(ZM + 12.2, 12), { tone: "lo", free: true, className: "en-oscuro" })}</g>`);
  const tec = { x: MESA.x + 6, y: MESA.y + 18, w: 36, d: 10, r: 1 };
  viva.push(S(k.slabOf(tec, ZM, 1.6, P, 2, 0.4), { m: "metal", tone: "hi" }));
  const teclas = [];
  for (let f = 0; f < 3; f++) for (let c = 0; c < 10; c++) teclas.push(at([tec.x + 3 + c * 3.3, tec.y + 2.4 + f * 2.7, ZM + 1.6]));
  viva.push(D(teclas, { size: 0.5, tone: "lo" }));

  return svgDe({
    huella,
    ancho,
    alto,
    clase: "fig-asistente",
    etiqueta: `Un tablero de conmutación: un panel con ${nodos.length} bocas, una por entidad (${nodos.join(", ")}), y la mesa del asistente con su pantalla. Con cada pregunta, la clavija del cordón entra en la boca de la entidad que publica el dato y su piloto se enciende.`,
    fija,
    viva,
    vivo: {
      sale: k.axisVector(P, [0, 6, 0]).map(r1),
      bocas: nodos.map((_, j) => at(toma(j)).map((v) => Math.round(v))),
      preguntas: preguntas.map((q) => ({ p: q.corta, e: q.e, l: q.l, j: nodos.indexOf(q.e) })),
    },
  });
}
