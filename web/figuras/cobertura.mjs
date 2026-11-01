// Fig. cobertura: una maqueta de Colombia sobre un zócalo. La tierra es un mosaico de hexágonos y
// sobre él se levanta una columna por celda con predios en la muestra SINIC (3 %), más alta cuantos
// más predios cuenta (raíz cuadrada). Alfileres en las ciudades y una regla en kilómetros. Todo sale
// de datos/co.json, sumado en hexágonos de 0,21° por construir.py. Lo que se mueve: la columna que
// se mira se enciende y la lectura da su conteo, su coordenada y la ciudad más cercana.
import { D, L, S, base, encuadre, k, svgDe } from "./comun.mjs";

export function cobertura(DATOS, huella) {
  const { R, celdas, tierra, ciudades, total } = DATOS.cobertura;
  const K = 14, LON0 = -73.35, LAT0 = 3.57;
  const X = (lon) => (lon - LON0) * K, Y = (lat) => -(lat - LAT0) * K;
  const RR = R * K; // radio del hexágono en unidades
  const max = Math.max(...celdas.map((c) => c[2]));
  const alto = (n) => 0.8 + Math.sqrt(n / max) * 52;
  const xs = tierra.map(([lon]) => X(lon)), ys = tierra.map(([, lat]) => Y(lat));
  const PLACA = { x: Math.min(...xs) - 10, y: Math.min(...ys) - 10, w: Math.max(...xs) - Math.min(...xs) + 20, d: Math.max(...ys) - Math.min(...ys) + 26, r: 5 };
  const { P, ancho, alto: altoV } = encuadre([...k.boxCorners(PLACA, -14, 0), ...celdas.map(([lon, lat, n]) => [X(lon), Y(lat), alto(n) + 1])], { azimuth: 72 }); // el norte hacia atrás y un poco a la derecha: el mapa se reconoce
  const at = (p) => k.iso(p, P);
  const hex = (cx, cy, rr) => Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 2 + (i * Math.PI) / 3; return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]; });
  const out = [];

  out.push(base(PLACA, 0, 6, P, { patas: 16 }));
  // regla en kilómetros en el borde de adelante: marca cada 50 km, mayor cada 100 km
  const km = (K / 111.32) * 50;
  const tira = { x: PLACA.x + 12, y: PLACA.y + PLACA.d - 9, w: km * 8 + 4, d: 4, r: 0.8 };
  out.push(S(k.slabOf(tira, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const tk = k.topTicks(tira.x + 2, tira.x + 2 + km * 8 + 0.01, km, 2, tira.y + tira.d, 0.6, [-1.6, -2.8], P);
  out.push(L(tk.minor, { tone: "lo" }), L(tk.major, { tone: "mid" }));
  out.push(D([at([tira.x + 1, tira.y + 1, 0.6]), at([tira.x + tira.w - 1, tira.y + 1, 0.6])], { size: 0.38 }));

  // la tierra: un mosaico plano de hexágonos
  const mosaico = tierra.map(([lon, lat]) => k.pathOf(hex(X(lon), Y(lat), RR * 0.98).map(([x, y]) => at([x, y, 0])), true)).join("");
  out.push(`<path class="tierra" d="${mosaico}"/>`);

  // columnas y alfileres, de atrás hacia adelante
  const items = [];
  celdas.forEach(([lon, lat, n], i) => {
    const cx = X(lon), cy = Y(lat), h = alto(n);
    const sol = k.extrude(hex(cx, cy, RR * 0.82), 0, h, P, { convex: true });
    // la tapa se tiñe de teal según el conteo (el mismo dato que la altura)
    const t = Math.round(8 + 62 * Math.sqrt(n / max));
    items.push({ d: k.depthOf([cx, cy, 0], P), svg: `<g data-celda="${i}" style="--t:${t}%">${S(sol, { tone: "hi", crease: "lo" })}</g>` });
  });
  ciudades.forEach(([, lon, lat]) => {
    const cx = X(lon), cy = Y(lat);
    const svg = S(k.cylinder(cx, cy, 0.45, 0, 9, P, 10), { tone: "mid", crease: "none" }) + D([at([cx, cy, 9.6])], { size: 1.5, tone: "hi" });
    items.push({ d: k.depthOf([cx, cy, 0], P) + 0.01, svg });
  });
  items.sort((a, b) => a.d - b.d);
  out.push(items.map((x) => x.svg).join(""));

  const puntas = celdas.map(([lon, lat, n]) => at([X(lon), Y(lat), alto(n)]).map((v) => Math.round(v)));
  const orden = celdas.map((c, i) => [c[2], i]).sort((a, b) => b[0] - a[0]).slice(0, 6).map(([, i]) => i);
  return svgDe({
    huella,
    ancho,
    alto: altoV,
    clase: "fig-cobertura",
    etiqueta: `Una maqueta de Colombia: sobre un mosaico de hexágonos de tierra, ${celdas.length} columnas, una por celda con predios en la muestra SINIC del 3 % (${total.toLocaleString("es-CO")} predios), más alta cuantos más cuenta. Alfileres en ${ciudades.length} ciudades.`,
    cuerpo: out,
    vivo: { puntas, celdas, orden, ciudades },
  });
}
