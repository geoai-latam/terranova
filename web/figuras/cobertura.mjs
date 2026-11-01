// Fig. cobertura: una maqueta de Colombia sobre su tablero. El tablero tiene patas, ranura,
// tornillos, la regla en el borde y el norte grabado; encima, la tierra en losetas de hexágonos con
// su grueso, y sobre ella una columna por celda con predios en la muestra SINIC (3 %), más alta
// cuantos más cuenta (raíz cuadrada) y de un solo material que va del agua (pocos) al teal hondo
// (muchos). Alfileres en las ciudades. Todo sale de datos/co.json, sumado en hexágonos de 0,21° por
// construir.py. Lo que se mueve: al entrar, las columnas crecen desde el piso (de Bogotá hacia
// afuera) y luego caen los alfileres; después, la columna que se mira se enciende en ámbar y la
// lectura da su conteo, su coordenada y la ciudad más cercana.
import { D, L, S, encuadre, k, r1, regla, sombra, svgDe } from "./comun.mjs";

export function cobertura(DATOS, huella) {
  const { R, celdas, tierra, ciudades, total } = DATOS.cobertura;
  const K = 14, LON0 = -73.35, LAT0 = 3.57;
  const X = (lon) => (lon - LON0) * K, Y = (lat) => -(lat - LAT0) * K;
  const RR = R * K; // radio del hexágono en unidades
  const ZT = 0; // cara del tablero
  const ZL = 1.8; // cara de la tierra (las losetas tienen grueso)
  const max = Math.max(...celdas.map((c) => c[2]));
  const alto = (n) => 0.8 + Math.sqrt(n / max) * 38;
  const nivel = (n) => Math.min(4, Math.floor(Math.sqrt(n / max) * 5));
  const pts = tierra.map(([lon, lat]) => [X(lon), Y(lat)]);
  const xs = pts.map(([x]) => x), ys = pts.map(([, y]) => y);
  const TAB = { x: Math.min(...xs) - 14, y: Math.min(...ys) - 12, w: Math.max(...xs) - Math.min(...xs) + 28, d: Math.max(...ys) - Math.min(...ys) + 30, r: 4 };
  const { P, ancho, alto: altoV } = encuadre(
    [...k.boxCorners(TAB, -12, 0), ...celdas.map(([lon, lat, n]) => [X(lon), Y(lat), ZL + alto(n) + 1])],
    { azimuth: 72, pad: 8 },
  ); // el norte hacia atrás y un poco a la derecha: el mapa se reconoce
  const at = (p) => k.iso(p, P);
  const hex = (cx, cy, rr) => Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 2 + (i * Math.PI) / 3; return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]; });
  const fija = [];
  const viva = [];

  // el tablero de la maqueta: patas, losa, ranura, tornillos, regla, placa y el norte grabado
  fija.push(sombra(TAB, -12, P, { pad: 8 }));
  const porProf = (ps) => [...ps].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  for (const [x, y] of porProf(k.corners(TAB, 12))) {
    fija.push(S(k.cylinder(x, y, 5, -12, 1.4, P, 24), { tone: "lo", m: "acero" }));
    fija.push(S(k.cylinder(x, y, 3.6, -10.6, 4.6, P, 24), { tone: "mid", m: "metal" }));
  }
  fija.push(S(k.slabOf(TAB, -6, 6, P, 6, 1.2), { tone: "lo", m: "trabajo" }));
  fija.push(L(k.planOutline(k.insetPlan(TAB, 4), ZT, P, 4), { tone: "faint" }));
  const torn = k.corners(TAB, 7.5);
  fija.push(L(torn.map(([x, y]) => k.ring(x, y, 1.8, ZT, P, 14)).join(""), { tone: "lo" }));
  fija.push(D(torn.map(([x, y]) => at([x, y, ZT])), { size: 0.45 }));
  fija.push(regla(TAB.x + 14, TAB.x + TAB.w - 40, TAB.y + TAB.d - 1, ZT, P));
  // el norte: una flecha grabada en la esquina de atrás a la derecha, con su anillo
  const [nx, ny] = [TAB.x + TAB.w - 14, TAB.y + 16];
  fija.push(L(k.ring(nx, ny, 6, ZT, P, 32), { tone: "lo" }));
  fija.push(`<path class="norte" d="${k.pathOf([[nx, ny - 5.2], [nx + 2.4, ny + 3], [nx, ny + 1.4], [nx - 2.4, ny + 3]].map(([x, y]) => at([x, y, ZT])), true)}"/>`);
  // placa de rótulo en la esquina delantera derecha: tres renglones y dos tornillos
  const placa = { x: TAB.x + TAB.w - 34, y: TAB.y + TAB.d - 18, w: 26, d: 11, r: 1 };
  fija.push(S(k.slabOf(placa, ZT, 0.6, P, 3), { tone: "lo", m: "papel" }));
  fija.push(L(k.planOutline(k.insetPlan(placa, 1.2), ZT + 0.6, P, 2), { tone: "faint" }));
  fija.push(L([0.8, 0.55, 0.68].map((f, j) => k.lineOnTop([placa.x + 3, placa.y + 3 + j * 2.6], [placa.x + 3 + (placa.w - 8) * f, placa.y + 3 + j * 2.6], ZT + 0.6, P)).join(""), { tone: "lo", free: true }));
  fija.push(D([at([placa.x + placa.w - 2, placa.y + 2, ZT + 0.6]), at([placa.x + placa.w - 2, placa.y + placa.d - 2, ZT + 0.6])], { size: 0.38 }));

  // la tierra: losetas de hexágono con grueso (el canto, más oscuro, asoma bajo la cara)
  const losetas = (z) => pts.map(([x, y]) => k.pathOf(hex(x, y, RR * 0.97).map(([a, b]) => at([a, b, z])), true)).join("");
  fija.push(`<path class="tierra-canto" d="${losetas(ZT)}"/>`);
  fija.push(`<path class="tierra" d="${losetas(ZL)}"/>`);

  // candidatas a encenderse: las seis celdas con más predios y la más cercana a cada ciudad
  const cerca = (lon, lat) => {
    let mejor = -1, d = Infinity;
    celdas.forEach(([a, b], i) => { const q = Math.hypot(a - lon, b - lat); if (q < d) { d = q; mejor = i; } });
    return d < 0.5 ? mejor : -1;
  };
  const mayores = celdas.map((c, i) => [c[2], i]).sort((a, b) => b[0] - a[0]).slice(0, 6).map(([, i]) => i);
  const candidatas = [...new Set([...mayores, ...ciudades.map(([, lon, lat]) => cerca(lon, lat)).filter((i) => i >= 0)])];

  // columnas, encendidas y alfileres, de atrás hacia adelante (todo en la capa viva: crecen)
  const [bx, by] = [-74.08, 4.61]; // Bogotá: de aquí sale el crecimiento
  const items = [];
  celdas.forEach(([lon, lat, n], i) => {
    const cx = X(lon), cy = Y(lat), h = alto(n);
    const sol = k.extrude(hex(cx, cy, RR * 0.8), ZL, h, P, { convex: true });
    const [, piso] = at([cx, cy, ZL]);
    let svg = `<g data-v="c${i}" data-eje="y ${r1(piso)}">${S(sol, { m: `cob${nivel(n)}`, tone: "hi", crease: "lo" })}</g>`;
    if (candidatas.includes(i)) svg += `<g data-v="luz${i}" style="opacity:0">${S(sol, { m: "ambar", tone: "hi", crease: "lo" })}</g>`;
    items.push({ d: k.depthOf([cx, cy, 0], P), svg });
  });
  ciudades.forEach(([, lon, lat], j) => {
    const cx = X(lon), cy = Y(lat);
    const svg =
      `<g data-v="pin${j}" style="opacity:0">${S(k.cylinder(cx, cy, 0.45, ZL, 10, P, 10), { m: "acero", tone: "mid", crease: "none" })}` +
      `${S(k.cylinder(cx, cy, 1.5, ZL + 10, 1.8, P, 16), { m: "bosque", tone: "mid", crease: "none" })}</g>`;
    items.push({ d: k.depthOf([cx, cy, 0], P) + 0.01, svg });
  });
  items.sort((a, b) => a.d - b.d);
  viva.push(items.map((x) => x.svg).join(""));

  const puntas = candidatas.map((i) => { const [lon, lat, n] = celdas[i]; return at([X(lon), Y(lat), ZL + alto(n)]).map((v) => Math.round(v)); });
  return svgDe({
    huella,
    ancho,
    alto: altoV,
    clase: "fig-cobertura",
    etiqueta: `Una maqueta de Colombia sobre su tablero: sobre las losetas de tierra, ${celdas.length} columnas, una por celda con predios en la muestra SINIC del 3 % (${total.toLocaleString("es-CO")} predios), más alta y más honda de color cuantos más cuenta. Alfileres en ${ciudades.length} ciudades.`,
    fija,
    viva,
    vivo: {
      // [lon, lat, predios, distancia a Bogotá (°), 1 si es alta y crece a la vista]
      celdas: celdas.map(([lon, lat, n]) => [lon, lat, n, r1(Math.hypot(lon - bx, lat - by)), alto(n) >= 12 ? 1 : 0]),
      candidatas,
      puntas,
      ciudades,
      total,
      sube: r1(k.axisVector(P, [0, 0, -14])[1]),
    },
  });
}
