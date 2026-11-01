// Fig. cobertura: una maqueta de Colombia sobre su tablero. El tablero tiene la forma del país,
// patas, ranura, tornillos y el norte grabado; encima, la tierra en losetas de hexágonos con
// su grueso, y sobre ella una columna por celda con predios en la muestra SINIC (3 %), más alta
// cuantos más cuenta (raíz cuadrada) y de un solo material que va del agua (pocos) al teal hondo
// (muchos). Alfileres en las ciudades. Todo sale de datos/co.json, sumado en hexágonos de 0,21° por
// construir.py. Lo que se mueve: al entrar, las columnas crecen desde el piso (de Bogotá hacia
// afuera) y luego caen los alfileres; después, la columna que se mira se enciende en ámbar y la
// lectura da su conteo, su coordenada y la ciudad más cercana.
import { D, L, S, casco, encuadre, k, r1, svgDe } from "./comun.mjs";

// Una columna que crece de verdad (no aplastada por una escala): cada cara de lado se dibuja en su
// propio marco (u a lo largo de la arista del piso, v vertical en pantalla) y figuras.js le escala
// solo la v; la tapa (cara de arriba, su arista y su pliegue) sube con la altura. Mismo sombreado
// por orientación que el kit (extrude). Con transform a escala 1, la columna queda entera.
function columnaQueCrece(ring, z, h, P, m) {
  const n = ring.length;
  const area = ring.reduce((a, [x, y], i) => { const [x2, y2] = ring[(i + 1) % n]; return a + x * y2 - x2 * y; }, 0);
  const [vx, vy] = k.towardViewer(P);
  const { sinA, cosA } = k.cameraOf(P);
  const normals = ring.map(([ax, ay], i) => {
    const [bx, by] = ring[(i + 1) % n];
    const l = Math.hypot(bx - ax, by - ay) || 1;
    return area > 0 ? [(by - ay) / l, -(bx - ax) / l] : [-(by - ay) / l, (bx - ax) / l];
  });
  const facing = normals.map(([nx, ny]) => nx * vx + ny * vy > 1e-9);
  const top = ring.map(([x, y]) => k.iso([x, y, z + h], P)), bot = ring.map(([x, y]) => k.iso([x, y, z], P));
  const H = r1(bot[0][1] - top[0][1]);
  const f = (v) => Math.round(v * 100) / 100;
  const partes = [];
  // las caras de lado, en su marco
  ring.forEach((_, i) => {
    if (!facing[i]) return;
    const [nx, ny] = normals[i];
    const lit = (nx * -sinA + ny * cosA + 1) / 2;
    const shade = Math.min(k.SHADES - 1, Math.max(0, Math.floor(lit * k.SHADES)));
    const b1 = bot[i], b2 = bot[(i + 1) % n];
    const mm = [f(b2[0] - b1[0]), f(b2[1] - b1[1]), f(b1[0]), f(b1[1])];
    partes.push(`<path class="iso-shade" data-shade="${shade}" data-m="${mm.join(" ")}" style="transform:matrix(${mm[0]},${mm[1]},0,1,${mm[2]},${mm[3]})" d="M0 0H1V-${H}H0Z"/>`);
  });
  // las aristas verticales de la silueta, en su marco
  ring.forEach((_, i) => {
    if (facing[(i + n - 1) % n] === facing[i]) return;
    const mm = [1, 0, f(bot[i][0]), f(bot[i][1])];
    partes.push(`<path class="iso-line iso-edge" data-tone="hi" data-m="${mm.join(" ")}" style="transform:matrix(1,0,0,1,${mm[2]},${mm[3]})" d="M0 0V-${H}"/>`);
  });
  // la arista del piso (fija) y la tapa (sube): por cara, la de abajo y el pliegue de arriba si mira
  // al lector; la arista de arriba si no
  const seg = (pts, i) => k.pathOf([pts[i], pts[(i + 1) % n]]);
  const caras = ring.map((_, i) => i);
  partes.push(`<path class="iso-line iso-edge" data-tone="hi" d="${caras.filter((i) => facing[i]).map((i) => seg(bot, i)).join("")}"/>`);
  partes.push(`<path class="iso-top" data-tapa="${H}" d="${k.pathOf(top, true)}"/>`);
  partes.push(`<path class="iso-line iso-crease" data-tone="lo" data-tapa="${H}" d="${caras.filter((i) => facing[i]).map((i) => seg(top, i)).join("")}"/>`);
  partes.push(`<path class="iso-line iso-edge" data-tone="hi" data-tapa="${H}" d="${caras.filter((i) => !facing[i]).map((i) => seg(top, i)).join("")}"/>`);
  return `<g class="iso-solid m-${m}" data-crece="${H}">${partes.join("")}</g>`;
}

// En un prisma convexo, la tapa y las caras de lado cubren la silueta: el relleno de abajo sobra
// (son 200 columnas: así pesa menos).
const sinRelleno = (svg) => svg.replace(/<path class="iso-fill" d="[^"]*"\/>/, "");

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
  // en cuatro franjas de atrás hacia adelante (canto y cara de cada una): trazos más cortos, que el
  // navegador lee en trozos de imagen distintos
  const losetas = (lista, z) => lista.map(([x, y]) => k.pathOf(hex(x, y, RR * 0.97).map(([a, b]) => at([a, b, z])), true)).join("");
  const enOrden = [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  const FRANJAS = 4, porFranja = Math.ceil(enOrden.length / FRANJAS);
  for (let f = 0; f < FRANJAS; f++) {
    const lista = enOrden.slice(f * porFranja, (f + 1) * porFranja);
    fija.push(`<path class="tierra-canto" d="${losetas(lista, ZT)}"/><path class="tierra" d="${losetas(lista, ZL)}"/>`);
  }
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

  // columnas, encendidas y alfileres, de atrás hacia adelante. Las altas crecen y los alfileres caen
  // (capa viva); las bajas están quietas desde el principio y van en la capa fija, salvo las que
  // tapan a una pieza viva (delante de ella en el mundo y encima en pantalla): esas van en la viva,
  // después de lo que tapan, para que el orden de pintura siga siendo el del mundo.
  const [bx, by] = [-74.08, 4.61]; // Bogotá: de aquí sale el crecimiento
  const caja = (pts) => { const xs = pts.map(([x]) => x), ys = pts.map(([, y]) => y); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
  const choca = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  const items = [];
  celdas.forEach(([lon, lat, n], i) => {
    const cx = X(lon), cy = Y(lat), h = alto(n);
    const anillo = hex(cx, cy, RR * 0.8);
    const sol = k.extrude(anillo, ZL, h, P, { convex: true });
    // las altas crecen de verdad (sus caras se alargan); las bajas están desde el principio
    const alta = h >= 12;
    let svg = alta
      ? `<g data-v="c${i}">${columnaQueCrece(anillo, ZL, h, P, `cob${nivel(n)}`)}</g>`
      : `<g data-v="c${i}">${sinRelleno(S(sol, { m: `cob${nivel(n)}`, tone: "hi", crease: "lo" }))}</g>`;
    const luz = candidatas.includes(i);
    if (luz) svg += `<g data-v="luz${i}" style="opacity:0">${sinRelleno(S(sol, { m: "ambar", tone: "hi", crease: "lo" }))}</g>`;
    const bb = caja(anillo.flatMap(([x, y]) => [k.iso([x, y, ZL], P), k.iso([x, y, ZL + h], P)]));
    items.push({ d: k.depthOf([cx, cy, 0], P), svg, vivo: alta || luz, bb });
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
    // la caja incluye la caída del alfiler (entra desde arriba)
    const bb = caja([k.iso([cx - 2, cy - 2, ZL], P), k.iso([cx + 2, cy + 2, ZL + largo + 2.4 + 14], P), k.iso([cx + 2, cy - 2, ZL], P), k.iso([cx - 2, cy + 2, ZL + largo + 16], P)]);
    items.push({ d: k.depthOf([cx, cy, 0], P) + 0.01, svg, vivo: true, bb });
  });
  items.sort((a, b) => a.d - b.d);
  const vivos = items.filter((x) => x.vivo);
  for (const x of items) if (!x.vivo && vivos.some((v) => v.d < x.d && choca(v.bb, x.bb))) x.tapa = true;
  fija.push(...items.filter((x) => !x.vivo && !x.tapa).map((x) => x.svg));
  viva.push(items.filter((x) => x.vivo || x.tapa).map((x) => x.svg).join(""));

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
