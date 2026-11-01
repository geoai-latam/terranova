// Fig. cobertura: una maqueta de Colombia sobre su tablero. El tablero tiene la forma del país,
// patas, ranura, tornillos y el norte grabado; encima, la tierra en losetas de hexágonos con
// su grueso, y sobre ella una columna por celda con predios en la muestra SINIC (3 %), más alta
// cuantos más cuenta (raíz cuadrada) y de un solo material que va del agua (pocos) al teal hondo
// (muchos). Alfileres en las ciudades. Todo sale de datos/co.json, sumado en hexágonos de 0,21° por
// construir.py. Lo que se mueve: al entrar, las columnas crecen desde el piso (de Bogotá hacia
// afuera) y luego caen los alfileres; después, la columna que se mira se enciende en ámbar y la
// lectura da su conteo, su coordenada y la ciudad más cercana.
import { D, L, S, casco, encuadre, k, r1, svgDe } from "./comun.mjs";

export function cobertura(DATOS, huella) {
  const { R, celdas, tierra, ciudades, total } = DATOS.cobertura;
  const K = 14, LON0 = -73.35, LAT0 = 3.57;
  const X = (lon) => (lon - LON0) * K, Y = (lat) => -(lat - LAT0) * K;
  const RR = R * K; // radio del hexágono en unidades
  const ZT = 0; // cara del tablero
  const ZL = 1.8; // cara de la tierra (las losetas tienen grueso)
  const max = Math.max(...celdas.map((c) => c[2]));
  const alto = (n) => 0.8 + Math.sqrt(n / max) * 22;
  const nivel = (n) => Math.min(4, Math.floor(Math.sqrt(n / max) * 5));
  const pts = tierra.map(([lon, lat]) => [X(lon), Y(lat)]);
  // el tablero toma la forma del país: la envolvente de la tierra con un margen (así el país llena
  // la maqueta y no queda tablero vacío)
  const borde = [];
  for (const [x, y] of pts) for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; borde.push([x + (RR + 5) * Math.cos(a), y + (RR + 5) * Math.sin(a)]); }
  const contorno = casco(borde);
  const { P, ancho, alto: altoV } = encuadre(
    [...contorno.map(([x, y]) => [x, y, -12]), ...contorno.map(([x, y]) => [x, y, 0]), ...celdas.map(([lon, lat, n]) => [X(lon), Y(lat), ZL + alto(n) + 10]), ...ciudades.map(([, lon, lat]) => [X(lon), Y(lat), ZL + 15])],
    { azimuth: 72, pad: 8 },
  ); // el norte hacia atrás y un poco a la derecha: el mapa se reconoce
  const at = (p) => k.iso(p, P);
  const hex = (cx, cy, rr) => Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 2 + (i * Math.PI) / 3; return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]; });
  const fija = [];
  const viva = [];

  // el tablero de la maqueta: la losa con la forma del país, cuatro patas, el borde y el norte grabado
  const cx0 = contorno.reduce((a, [x]) => a + x, 0) / contorno.length, cy0 = contorno.reduce((a, [, y]) => a + y, 0) / contorno.length;
  const hacia = ([x, y], d) => { const l = Math.hypot(x - cx0, y - cy0) || 1; return [x + ((cx0 - x) / l) * d, y + ((cy0 - y) / l) * d]; };
  const sombraPais = [6, 4, 2].map((g) => `<path class="sombra" d="${k.pathOf(contorno.map((q) => hacia(q, -g)).map(([x, y]) => at([x, y, -12])), true)}"/>`);
  fija.push(sombraPais.join(""));
  const extremo = (f) => contorno.reduce((m, q) => (f(q) > f(m) ? q : m));
  const patas = [extremo(([x]) => -x), extremo(([x]) => x), extremo(([, y]) => -y), extremo(([, y]) => y)].map((q) => hacia(q, 9));
  const porProf = (ps) => [...ps].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  for (const [x, y] of porProf(patas)) {
    fija.push(S(k.cylinder(x, y, 5, -12, 1.4, P, 24), { tone: "lo", m: "acero" }));
    fija.push(S(k.cylinder(x, y, 3.6, -10.6, 4.6, P, 24), { tone: "mid", m: "metal" }));
  }
  fija.push(S(k.extrude(contorno, -6, 6, P, { convex: true, bevel: 1.2 }), { tone: "lo", m: "trabajo" }));
  fija.push(L(k.pathOf(contorno.map((q) => hacia(q, 3.5)).map(([x, y]) => at([x, y, ZT])), true), { tone: "faint" }));
  const torn = patas.map((q) => hacia(q, 3));
  fija.push(L(torn.map(([x, y]) => k.ring(x, y, 1.8, ZT, P, 14)).join(""), { tone: "lo" }));
  fija.push(D(torn.map(([x, y]) => at([x, y, ZT])), { size: 0.45 }));
  // el norte, grabado donde el tablero queda más libre de tierra (lejos de toda loseta), con su anillo
  const dentro = ([x, y], m) => contorno.every(([ax, ay], i) => {
    const [bx, by] = contorno[(i + 1) % contorno.length];
    const l = Math.hypot(bx - ax, by - ay);
    return ((bx - ax) * (y - ay) - (by - ay) * (x - ax)) / l >= m;
  });
  const signo = Math.sign(((contorno[1][0] - contorno[0][0]) * (contorno[2][1] - contorno[0][1]) - (contorno[1][1] - contorno[0][1]) * (contorno[2][0] - contorno[0][0]))) || 1;
  let libre = [cx0, cy0], holgura = -1;
  for (let x = Math.min(...contorno.map((q) => q[0])); x < Math.max(...contorno.map((q) => q[0])); x += 2)
    for (let y = Math.min(...contorno.map((q) => q[1])); y < Math.max(...contorno.map((q) => q[1])); y += 2) {
      if (!dentro([x, y], 9 * signo) && !dentro([x, y], -9 * signo)) continue;
      if (!contorno.every(([ax, ay], i) => { const [bx, by] = contorno[(i + 1) % contorno.length]; return signo * ((bx - ax) * (y - ay) - (by - ay) * (x - ax)) / Math.hypot(bx - ax, by - ay) >= 9; })) continue;
      const d = Math.min(...pts.map(([px, py]) => Math.hypot(px - x, py - y)));
      if (d > holgura) { holgura = d; libre = [x, y]; }
    }
  const [nx, ny] = libre;
  fija.push(L(k.ring(nx, ny, 6, ZT, P, 32), { tone: "mid" }));
  fija.push(`<path class="norte" d="${k.pathOf([[nx, ny - 5.2], [nx + 2.4, ny + 3], [nx, ny + 1.4], [nx - 2.4, ny + 3]].map(([x, y]) => at([x, y, ZT])), true)}"/>`);

  // la tierra: losetas de hexágono con grueso (el canto, más oscuro, asoma bajo la cara) y la costa:
  // los lados de hexágono que no comparte ninguna loseta vecina, en linea-media
  const losetas = (z) => pts.map(([x, y]) => k.pathOf(hex(x, y, RR * 0.97).map(([a, b]) => at([a, b, z])), true)).join("");
  fija.push(`<path class="tierra-canto" d="${losetas(ZT)}"/>`);
  fija.push(`<path class="tierra" d="${losetas(ZL)}"/>`);
  const lados = new Map();
  const llave = ([x, y]) => `${Math.round(x * 2)},${Math.round(y * 2)}`;
  for (const [x, y] of pts) {
    const h = hex(x, y, RR);
    for (let i = 0; i < 6; i++) {
      const a = h[i], b = h[(i + 1) % 6];
      const c = llave([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]); // el punto medio: lo comparten las dos losetas
      lados.set(c, lados.has(c) ? null : [a, b]);
    }
  }
  const costa = [...lados.values()].filter(Boolean).map(([a, b]) => k.pathOf([at([a[0], a[1], ZL]), at([b[0], b[1], ZL])])).join("");
  fija.push(`<path class="costa" d="${costa}"/>`);

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
  // alfileres: aguja de metal y cabeza oscura con su remate, siempre más altos que la columna de
  // su celda (si no, quedarían dentro de ella)
  ciudades.forEach(([, lon, lat], j) => {
    const cx = X(lon), cy = Y(lat);
    const c = cerca(lon, lat);
    const largo = Math.max(12, (c >= 0 ? alto(celdas[c][2]) : 0) + 7);
    const svg =
      `<g data-v="pin${j}" style="opacity:0">${S(k.cylinder(cx, cy, 0.4, ZL, largo, P, 10), { m: "metal", tone: "mid", crease: "none" })}` +
      `${S(k.cylinder(cx, cy, 1.9, ZL + largo, 1.4, P, 18), { m: "bosque", tone: "mid", crease: "none" })}` +
      `${S(k.cylinder(cx, cy, 1.1, ZL + largo + 1.4, 1, P, 14), { m: "bosque", tone: "mid", crease: "none" })}</g>`;
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
