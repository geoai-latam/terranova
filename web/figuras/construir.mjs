// Dibuja las figuras isométricas del sitio con el kit de Anatomy (kit/iso-kit.mjs, MIT).
//
//   node web/figuras/construir.mjs [nombre…]   # lee datos.json y escribe web/publico/img/figuras/*.svg
//
// Lo que muestran sale de datos.json, que escribe web/construir.py desde el catálogo; su huella
// (datos, cada .mjs de esta carpeta y el kit) queda en cada SVG (data-datos) y construir.py se
// niega a publicar un dibujo viejo. El movimiento vive en web/publico/js/figuras.js, que lee
// data-vivo; sin él, cada figura queda armada y quieta.
import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { asistente } from "./asistente.mjs";
import { capas } from "./capas.mjs";
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
const HUELLA = h.update(lf("kit/iso-kit.mjs"), "latin1").digest("hex").slice(0, 12);
const DATOS = JSON.parse(crudo);

const FIGURAS = { capas, ruta, prueba, revision, tablero, vigilancia, asistente };

mkdirSync(SALIDA, { recursive: true });
const solo = process.argv.slice(2);
for (const [nombre, dibujar] of Object.entries(FIGURAS)) {
  if (solo.length && !solo.includes(nombre)) continue;
  writeFileSync(join(SALIDA, `${nombre}.svg`), dibujar(DATOS, HUELLA) + "\n");
}
console.log(`figuras escritas (datos ${HUELLA})`);
