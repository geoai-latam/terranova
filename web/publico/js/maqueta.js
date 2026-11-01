// La maqueta del héroe: la geometría que comparten el póster SVG (web/figuras/heroe.mjs, dibujado
// con el kit de Anatomy) y la escena 3D (escena-predios.js), para que sean la misma escena con la
// misma cámara. Mundo en metros con los ejes del kit: x al este, y al sur, z arriba; el origen es
// el punto consultado. Los linderos son del SINIC (datos/sm.json) y las calles de OpenStreetMap
// (datos/calles.json). El grosor de los predios y la subida del consultado son simbólicos.
export const AZIMUT = 45;
export const ELEVACION = 30;
export const R = 100; // recorte: el cuadrado de lado 2R alrededor del punto consultado
export const BORDE = 12; // lo que la base sobresale del recorte
export const H = 5; // grosor de los predios
export const ALTO = 30; // altura del predio consultado cuando llega su respuesta
export const GRUESO = 7; // grosor de la base
export const PATA = { r: 6, alto: 6, dentro: 20 };
export const LADO = R + BORDE;
// Sombra de contacto bajo la base: tres escalones de tinta verde translúcida, sin desenfoque.
export const SOMBRA = { pasos: [2, 4.5, 8], opacidad: 0.09 };
export const PLACA = { x: -LADO, y: -LADO, w: 2 * LADO, d: 2 * LADO, r: 4 };
// La regla del borde delantero izquierdo (y = +LADO), en metros de verdad: marca cada 10 m.
export const REGLA = { x0: -R, x1: R, y: R + 3.5, ancho: 6, paso: 10, cada: 5 };
// Flecha del norte grabada en el borde delantero derecho (x = +LADO); el norte es −y.
export const NORTE = { x: R + 6, y: R - 16, largo: 12, ancho: 5 };
// La onda de la respuesta: un anillo que sale del pie del consultado una sola vez.
export const ONDA = { r0: 6, r1: 46, ms: 700 };

const encoge = (pts) => {
  // Cada lindero se recorta medio metro hacia su centro: los huecos dibujan las calles.
  const c = pts.reduce((a, [x, y]) => [a[0] + x / pts.length, a[1] + y / pts.length], [0, 0]);
  const out = pts.map(([x, y]) => {
    const dx = x - c[0], dy = y - c[1], L = Math.hypot(dx, dy);
    return L > 1.2 ? [c[0] + (dx * (L - 0.55)) / L, c[1] + (dy * (L - 0.55)) / L] : [x, y];
  });
  return { anillo: out, centro: c };
};

const area = (pts) => pts.reduce((s, [ax, ay], i) => {
  const [bx, by] = pts[(i + 1) % pts.length];
  return s + (ax * by - bx * ay) / 2;
}, 0);

// La maqueta corta los predios en el borde del recorte, como una maqueta de verdad cortada a
// sierra (Sutherland–Hodgman contra el cuadrado |x|, |y| ≤ R).
function recorta(pts) {
  let out = pts;
  for (const [eje, signo] of [[0, 1], [0, -1], [1, 1], [1, -1]]) {
    const dentro = (p) => signo * p[eje] <= R;
    const corte = (a, b) => {
      const t = (signo * R - a[eje]) / (b[eje] - a[eje]);
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    };
    const sig = [];
    out.forEach((b, i) => {
      const a = out[(i + out.length - 1) % out.length];
      if (dentro(b)) {
        if (!dentro(a)) sig.push(corte(a, b));
        sig.push(b);
      } else if (dentro(a)) sig.push(corte(a, b));
    });
    out = sig;
    if (!out.length) break;
  }
  return out;
}

// sm: { polys: [[x0, y0, x1, y1…]] en metros (y al norte), codes, obj }; calles: { calles, barrio }.
export function maqueta(sm, calles) {
  const predios = [];
  let consultado = null;
  sm.polys.forEach((flat, i) => {
    const pts = [];
    for (let j = 0; j < flat.length; j += 2) pts.push([flat[j], -flat[j + 1]]);
    const cortado = recorta(pts);
    if (cortado.length < 3 || Math.abs(area(cortado)) < 6) return;
    const p = { ...encoge(cortado), codigo: sm.codes[i] };
    if (i === sm.obj) consultado = p;
    else predios.push(p);
  });
  // Rótulos de calle: los ejes de OpenStreetMap (datos/calles.json). Cada nombre se rotula una vez,
  // en el tramo recto más largo que cabe entero en la maqueta (13 m a cada lado del rótulo), lejos
  // del consultado y de los otros rótulos; el rótulo va a lo largo del eje, sobre la calle.
  // El consultado sube y tapa en pantalla una franja del piso detrás de él (lejos de la cámara):
  // ahí no va ningún rótulo.
  const va = (AZIMUT * Math.PI) / 180, fondo = ALTO / Math.tan((ELEVACION * Math.PI) / 180) + 12;
  const tapa = (x, y) => {
    const ux = -Math.cos(va), uy = -Math.sin(va);
    const t = Math.max(0, Math.min(fondo, x * ux + y * uy));
    return Math.hypot(x - ux * t, y - uy * t) < 24;
  };
  const cabe = (x, y) => Math.abs(x) < R - 10 && Math.abs(y) < R - 10;
  const candidatos = [];
  for (const via of calles.vias || []) {
    const p = via.p.map(([x, y]) => [x, -y]);
    for (let i = 0; i + 1 < p.length; i++) {
      const [ax, ay] = p[i], [bx, by] = p[i + 1];
      const L = Math.hypot(bx - ax, by - ay);
      if (L < 26) continue;
      const ux = (bx - ax) / L, uy = (by - ay) / L;
      for (let t = 13; t <= L - 13; t += 3) {
        const x = ax + ux * t, y = ay + uy * t;
        if (!cabe(x - ux * 13, y - uy * 13) || !cabe(x + ux * 13, y + uy * 13)) continue;
        if (Math.hypot(x, y) < 30 || tapa(x, y)) continue;
        candidatos.push({ t: via.n, x, y, dx: ux, dy: uy, peso: Math.min(t, L - t) });
      }
    }
  }
  candidatos.sort((a, b) => b.peso - a.peso);
  const rotulos = [];
  for (const c of candidatos) {
    if (rotulos.length >= 4) break;
    if (rotulos.some((r) => r.t === c.t || Math.hypot(r.x - c.x, r.y - c.y) < 44)) continue;
    rotulos.push(c);
  }
  return { predios, consultado, rotulos, barrio: calles.barrio || "" };
}
