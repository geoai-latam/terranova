// Fig. cobertura: una maqueta de Colombia sobre un zócalo. La tierra es un mosaico de hexágonos y
// sobre él se levanta una columna por celda con predios en la muestra SINIC (3 %), más alta cuantos
// más predios cuenta (raíz cuadrada). Alfileres en las ciudades. Todo sale
// de datos/co.json, sumado en hexágonos de 0,21° por construir.py. Lo que se mueve: la columna que
// se mira se enciende y la lectura da su conteo, su coordenada y la ciudad más cercana.
import { D, L, S, casco, encuadre, k, porProf, svgDe } from "./comun.mjs";

export function cobertura(DATOS, huella) {
  const { R, celdas, tierra, ciudades, total } = DATOS.cobertura;
  const K = 14, LON0 = -73.35, LAT0 = 3.57;
  const X = (lon) => (lon - LON0) * K, Y = (lat) => -(lat - LAT0) * K;
  const RR = R * K; // radio del hexágono en unidades
  const max = Math.max(...celdas.map((c) => c[2]));
  const alto = (n) => 0.8 + Math.sqrt(n / max) * 38;
  // el zócalo, cortado a la forma del país: envolvente convexa de la tierra con un margen corto
  const borde = [];
  for (const [lon, lat] of tierra) for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; borde.push([X(lon) + (RR + 7) * Math.cos(a), Y(lat) + (RR + 7) * Math.sin(a)]); }
  const zocalo = casco(borde);
  const { P, ancho, alto: altoV } = encuadre([...zocalo.map(([x, y]) => [x, y, -12]), ...zocalo.map(([x, y]) => [x, y, 0]), ...celdas.map(([lon, lat, n]) => [X(lon), Y(lat), alto(n) + 1])], { azimuth: 72 }); // el norte hacia atrás y un poco a la derecha: el mapa se reconoce
  const at = (p) => k.iso(p, P);
  const hex = (cx, cy, rr) => Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 2 + (i * Math.PI) / 3; return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]; });
  const out = [];

  // halo, patas en seis puntos del borde, la losa biselada y su ranura
  out.push(`<path class="iso-halo" d="${k.extrude(zocalo, -12, 12, P).fill}"/>`);
  const cx0 = zocalo.reduce((a, [x]) => a + x, 0) / zocalo.length, cy0 = zocalo.reduce((a, [, y]) => a + y, 0) / zocalo.length;
  const patas = [0, 1, 2, 3, 4, 5].map((i) => zocalo[Math.floor((i / 6) * zocalo.length)]).map(([x, y]) => [x + (cx0 - x) * 0.1, y + (cy0 - y) * 0.1]);
  for (const [x, y] of porProf(patas, P)) {
    out.push(S(k.cylinder(x, y, 5.2, -12, 1.4, P, 24), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 3.8, -10.6, 4.6, P, 24), { tone: "mid" }));
  }
  out.push(S(k.extrude(zocalo, -6, 6, P, { convex: true, bevel: 1.2 }), { tone: "lo" }));
  const adentro = zocalo.map(([x, y]) => [x + (cx0 - x) * 0.025, y + (cy0 - y) * 0.025]);
  out.push(L(k.pathOf(adentro.map(([x, y]) => at([x, y, 0])), true), { tone: "faint" }));

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
