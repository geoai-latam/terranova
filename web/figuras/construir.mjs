// Dibuja las figuras isométricas del sitio con el kit de Anatomy (kit/iso-kit.mjs, MIT).
//
//   node web/figuras/construir.mjs [nombre…]   # lee datos.json y escribe web/publico/img/figuras/*.svg
//
// Lo que muestran sale de datos.json, que escribe web/construir.py desde el catálogo; su huella
// (datos, cada .mjs de esta carpeta y el kit) queda en cada SVG (data-datos) y construir.py se
// niega a publicar un dibujo viejo. El movimiento vive en web/publico/js/figuras.js, que lee
// data-vivo; sin él, cada figura queda armada y quieta.
import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { asistente } from "./asistente.mjs";
import { capas } from "./capas.mjs";
import { cobertura } from "./cobertura.mjs";
import { prueba } from "./prueba.mjs";
import { revision } from "./revision.mjs";
import { ruta } from "./ruta.mjs";
import { tablero } from "./tablero.mjs";
import { vigilancia } from "./vigilancia.mjs";

const AQUI = dirname(fileURLToPath(import.meta.url));
const SALIDA = join(AQUI, "..", "publico", "img", "figuras");
const crudo = readFileSync(join(AQUI, "datos.json"), "utf8");
// La huella cubre los datos, los scripts (en orden de nombre) y el kit: construir.py la recalcula igual.
const lf = (f) => readFileSync(join(AQUI, f)).toString("latin1").replace(/\r\n/g, "\n");
const h = createHash("sha256").update(crudo, "utf8");
for (const f of readdirSync(AQUI).filter((n) => n.endsWith(".mjs")).sort()) h.update(lf(f), "latin1");
// y la hoja del sitio: la capa fija lleva dentro sus reglas
h.update(lf("kit/iso-kit.mjs"), "latin1");
const HUELLA = h.update(lf("../publico/estilo.css"), "latin1").digest("hex").slice(0, 12);
const DATOS = JSON.parse(crudo);

const FIGURAS = { capas, ruta, prueba, revision, tablero, vigilancia, asistente, cobertura };

// La capa fija va como <img>: un SVG aparte que no ve la hoja de la página, así que lleva dentro las
// reglas de estilo.css que pinta (los tokens de :root y las de las figuras), y svgo deja solo las
// que usa. La viva va en línea y toma las de la página.
const CSS = readFileSync(join(AQUI, "..", "publico", "estilo.css"), "utf8").replace(/\r\n/g, "\n");
const DE_FIGURA = /(^|[\s,>])\.(iso-|m-|sombra|marca-|sello-marca|en-pantalla|medidor|luz|lamp-|cable|fig-(?!iso)|franja|aguja|serie|ban-|boca|cordon|tierra|costa|norte|brazo|banda|cubo|nervio)/;
// Las reglas de figura de la hoja (y las variables de :root y de .fig-iso, aparte).
function reglasDeFigura() {
  const sinComentarios = CSS.replace(/\/\*[\s\S]*?\*\//g, "");
  const reglas = [], vars = new Map();
  let i = 0;
  while (i < sinComentarios.length) {
    const a = sinComentarios.indexOf("{", i);
    if (a < 0) break;
    const sel = sinComentarios.slice(i, a).trim();
    // bloque con su anidado (@media, @font-face): se salta entero
    let prof = 1, b = a + 1;
    while (prof && b < sinComentarios.length) { if (sinComentarios[b] === "{") prof++; else if (sinComentarios[b] === "}") prof--; b++; }
    const cuerpo = sinComentarios.slice(a + 1, b - 1).trim();
    i = b;
    if (sel.startsWith("@")) continue;
    if (sel === ":root" || sel === ".fig-iso") {
      for (const d of cuerpo.split(";")) {
        const m = d.trim().match(/^(--[\w-]+)\s*:\s*([\s\S]+)$/);
        if (m) vars.set(m[1], m[2].replace("var(--papel, var(--fondo))", "var(--fondo)").trim());
      }
    } else if (DE_FIGURA.test(sel)) reglas.push({ sel, cuerpo });
  }
  return { reglas, vars };
}
const { reglas: REGLAS, vars: VARS } = reglasDeFigura();
// El estilo de un trozo: solo las reglas cuyas clases aparecen en él y las variables que esas
// reglas usan (con sus dependencias). Así cada imagen lleva lo suyo y nada más.
function estiloDe(svg) {
  const clases = new Set();
  for (const m of svg.matchAll(/class="([^"]*)"/g)) for (const c of m[1].split(/\s+/)) clases.add(c);
  const usa = (sel) => sel.split(",").some((parte) => (parte.match(/\.[\w-]+/g) || []).every((c) => clases.has(c.slice(1))));
  const reglas = REGLAS.filter((r) => usa(r.sel));
  const pend = reglas.flatMap((r) => [...r.cuerpo.matchAll(/var\((--[\w-]+)/g)].map((m) => m[1]));
  const usadas = new Set();
  while (pend.length) {
    const v = pend.pop();
    if (usadas.has(v) || !VARS.has(v)) continue;
    usadas.add(v);
    for (const m of VARS.get(v).matchAll(/var\((--[\w-]+)/g)) pend.push(m[1]);
  }
  const raiz = [...usadas].map((v) => `${v}:${VARS.get(v)}`).join(";");
  return `svg{${raiz}}\n` + reglas.map((r) => `${r.sel}{${r.cuerpo}}`).join("\n");
}

// svgo: decimales a 1 en los trazos, estilos sin repetir; nada que cambie la geometría de los planos
// (las matrices conservan 3 decimales), ni ids (dos figuras viven en la misma página), ni piezas
// escondidas (las vivas empiezan con opacidad 0).
const { optimize } = await import("svgo");
const opciones = (viva) => ({
  multipass: true,
  floatPrecision: 1,
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          cleanupIds: false,
          removeEmptyAttrs: false, // data-free="" marca los renglones impresos (lines.mjs)
          removeHiddenElems: false,
          mergePaths: false,
          convertTransform: { floatPrecision: 3 },
          inlineStyles: false,
          collapseGroups: viva ? false : undefined,
          moveElemsAttrsToGroup: false,
          moveGroupAttrsToElems: false,
          convertShapeToPath: false,
          removeUnknownsAndDefaults: { keepDataAttrs: true, keepAriaAttrs: true, keepRoleAttr: true },
        },
      },
    },
  ],
});
const opt = (svg, viva) => optimize(svg, opciones(viva)).data;

mkdirSync(SALIDA, { recursive: true });
const solo = process.argv.slice(2);
let kb = 0;
for (const [nombre, dibujar] of Object.entries(FIGURAS)) {
  if (solo.length && !solo.includes(nombre)) continue;
  const { fijas, viva } = dibujar(DATOS, HUELLA);
  // fuera los trozos de una construcción anterior (si ahora son menos)
  for (const f of readdirSync(SALIDA)) if (f.startsWith(`${nombre}-`) && /^-\d+\.svg$/.test(f.slice(nombre.length))) unlinkSync(join(SALIDA, f));
  // los trozos de la capa fija: <nombre>.svg, <nombre>-2.svg…; svgo deja en cada uno solo sus reglas
  fijas.forEach((fija, i) => {
    const a = opt(fija.replace(/(<svg[^>]*>)/, `$1<style>${estiloDe(fija)}</style>`), false);
    writeFileSync(join(SALIDA, `${nombre}${i ? `-${i + 1}` : ""}.svg`), a + "\n");
    kb += a.length / 1024;
  });
  const b = opt(viva, true);
  writeFileSync(join(SALIDA, `${nombre}-viva.svg`), b + "\n");
  kb += b.length / 1024;
}
console.log(`figuras escritas (datos ${HUELLA}, ${Math.round(kb)} KB)`);
