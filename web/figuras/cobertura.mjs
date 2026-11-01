// Fig. cobertura: una maqueta de Colombia sin zócalo. La tierra es un mosaico de hexágonos y
// sobre él se levanta una columna por celda con predios en la muestra SINIC (3 %), más alta cuantos
// más predios cuenta (raíz cuadrada) y de color teal → agua → ocre → ámbar. Alfileres en las ciudades. Todo sale
// de datos/co.json, sumado en hexágonos de 0,21° por construir.py. Lo que se mueve: la columna que
// se mira se enciende y la lectura da su conteo, su coordenada y la ciudad más cercana.
import { D, S, casco, encuadre, k, svgDe } from "./comun.mjs";

export function cobertura(DATOS, huella) {
  const { R, celdas, tierra, ciudades, total } = DATOS.cobertura;
  const K = 14, LON0 = -73.35, LAT0 = 3.57;
  const X = (lon) => (lon - LON0) * K, Y = (lat) => -(lat - LAT0) * K;
  const RR = R * K; // radio del hexágono en unidades
  const max = Math.max(...celdas.map((c) => c[2]));
  const alto = (n) => 0.8 + Math.sqrt(n / max) * 38;
  // el contorno de la sombra: envolvente convexa de la tierra con un margen corto
  const borde = [];
  for (const [lon, lat] of tierra) for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; borde.push([X(lon) + (RR + 2) * Math.cos(a), Y(lat) + (RR + 2) * Math.sin(a)]); }
  const zocalo = casco(borde);
  const { P, ancho, alto: altoV } = encuadre([...zocalo.map(([x, y]) => [x, y, -12]), ...zocalo.map(([x, y]) => [x, y, 0]), ...celdas.map(([lon, lat, n]) => [X(lon), Y(lat), alto(n) + 1])], { azimuth: 72 }); // el norte hacia atrás y un poco a la derecha: el mapa se reconoce
  const at = (p) => k.iso(p, P);
  const hex = (cx, cy, rr) => Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 2 + (i * Math.PI) / 3; return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]; });
  const out = [];

  // sin zócalo: los hexágonos de tierra descansan sobre una sombra suave con la forma del país
  out.push(`<path class="iso-halo sombra-pais" d="${k.pathOf(zocalo.map(([x, y]) => at([x, y, -1])), true)}"/>`);

  // la tierra: un mosaico plano de hexágonos
  const mosaico = tierra.map(([lon, lat]) => k.pathOf(hex(X(lon), Y(lat), RR * 0.98).map(([x, y]) => at([x, y, 0])), true)).join("");
  out.push(`<path class="tierra" d="${mosaico}"/>`);

  // una de cada cinco columnas lleva un piloto en la tapa que titila: la fuente responde
  const chispa = (cx, cy, h, i) => `<g class="parpadea piloto-claro" style="--p:${(1.8 + (i % 7) * 0.31).toFixed(2)}s;--d:-${((i * 13) % 17 * 0.21).toFixed(2)}s">${D([at([cx, cy, h])], { size: 1, tone: "hi" })}</g>`;
  // columnas y alfileres, de atrás hacia adelante
  const items = [];
  celdas.forEach(([lon, lat, n], i) => {
    const cx = X(lon), cy = Y(lat), h = alto(n);
    const sol = k.extrude(hex(cx, cy, RR * 0.82), 0, h, P, { convex: true });
    // el color sigue al conteo (el mismo dato que la altura), en cuatro tramos de la paleta:
    // teal, agua, ocre y ámbar, de menos a más predios
    const f = Math.sqrt(n / max);
    const mat = f < 0.25 ? "teal" : f < 0.5 ? "agua" : f < 0.75 ? "ocre" : "ambar";
    items.push({ d: k.depthOf([cx, cy, 0], P), svg: `<g data-celda="${i}">${S(sol, { m: mat, tone: "hi", crease: "lo" })}${i % 5 === 2 ? chispa(cx, cy, h, i) : ""}</g>` });
  });
  ciudades.forEach(([, lon, lat]) => {
    const cx = X(lon), cy = Y(lat);
    const svg = S(k.cylinder(cx, cy, 0.45, 0, 9, P, 10), { m: "acero", tone: "mid", crease: "none" }) + `<g class="piloto-ambar">${D([at([cx, cy, 9.6])], { size: 1.6, tone: "hi" })}</g>`;
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
