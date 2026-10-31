# Spec 07 · Perfil de la fuente

*2026-10-22.* Antes de su primera herramienta, cada fuente se perfila: se mide qué es una fila, qué
llave es confiable, qué trae mal y cómo responde. Con eso se diseña la herramienta, no al revés.

## Por qué

Las fuentes abiertas parecen tablas limpias y no lo son. Lo medido en la ola 1 y la ola 2:

| Fuente | Lo que parecía | Lo que es |
|---|---|---|
| SECOP II, ofertas por proceso | una fila por oferta | 32 895 filas para 25 ofertas: cada oferta repetida ~1 300 veces |
| SECOP II, contratos | `id_contrato` único | 3 repetidos entre 334 431 |
| SECOP II, proveedores registrados | `nit` de la empresa | cédulas de personas, y un «ECOPETROL S.A.» con la cédula de alguien |
| SECOP I, PAA | una fila por plan | una por versión del plan (11 para el mismo) |
| IGAC, perímetro urbano | `codigo_municipio` | 23175 para Chía (es 25175) |
| Supersociedades, 10 000 empresas | cifras en pesos | en billones, como texto (`$84.95`) |
| BanRep, SDMX | filtro por fechas | el servicio no filtra: solo las últimas N |
| Estadísticas catastrales del IGAC | un dato por año | un bloque «actualizado» y otro «desactualizado» el mismo año |
| ICFES, Saber 11 | una fila por estudiante | en 20181, 20194 y 20224, estudiantes repetidos: Chía 20224 daba 3 372 (son 1 686) y en 20181 un promedio de 317,0 (es 306,2) |
| SECOP Integrado | una fila por contrato | una por cada estado del contrato: Pitalito 2025 sumaba $174 000 millones (son $63 157 millones) |
| INVIMA, CUM | una fila por presentación | una por presentación y rol: 3 019 filas para 1 822 presentaciones con ibuprofeno |

Una herramienta hecha sin saber esto responde mal y con aplomo: «32 895 ofertas». Eso es peor que
no responder.

## El perfil

Cada ficha de fuente lleva un bloque `perfil:`, medido en la fuente (nunca copiado de la respuesta de
Terrnova) y fechado:

```yaml
perfil:
  medido: 2026-10-22
  fila: "una fila por ítem de cada oferta; 25 ofertas → 32 895 filas en CO1.BDOS.6343828"
  clave: {columna: identificador_de_la_oferta, unica: false}
  operaciones: {filtrar: 0.6, contar: 48, ordenar: null, agrupar: null}  # segundos; null = no responde en 300 s
  hallazgos:
    - "cada oferta se repite una vez por ítem: contar filas no es contar ofertas"
  decision: "copia (G3) deduplicada por oferta; en vivo, solo contar ofertas distintas"
```

| Campo | Qué mide |
|---|---|
| `medido` | la fecha de la medición; se repite cuando el canario marca un cambio |
| `fila` | qué representa una fila, con un ejemplo medido |
| `clave` | la columna que identifica un registro y si de verdad es única (filas = distintos) |
| `operaciones` | segundos que tarda filtrar, contar, ordenar y agrupar sobre un ejemplo; `null` si no responde en 300 s |
| `hallazgos` | lo que está mal o engaña: duplicados, códigos errados, unidades, personas, ventanas |
| `decision` | qué se hace con eso: en vivo, copia, agregado, excluir un campo, no servir la fuente |

## Cómo se mide

`scripts/perfilar_fuente.py` mide sobre una muestra (un filtro concreto, no la tabla entera):

1. filas totales y valores distintos de la clave;
2. nulos de cada columna de la lista blanca;
3. latencia de filtrar, contar, ordenar y agrupar, con 300 s de tope y 3 s de espera entre cada una.

Son pocas consultas, separadas en el tiempo: no es carga sobre la fuente. Lo que el script no ve
(qué significa un código, si un `nit` trae cédulas, en qué unidad viene una cifra) lo revisa una
persona y lo escribe en `hallazgos`.

## Herramientas para lo que se encuentra

| Hallazgo | Qué se hace | Ejemplo |
|---|---|---|
| copias exactas | `select distinct` (el conector no lo confunde con un corte) | modificaciones de SECOP II |
| el registro se repite y hay que agregar | etapa previa (`previo_select` + `previo_group`): se agrupa por registro y luego se agrega | ICFES, SECOP Integrado |
| filas «iguales» porque la lista blanca oculta lo que las distingue | se agrega la columna, si no es de personas | BPIN del CDP, póliza, rol del CUM |
| la columna que distingue es de personas | se deduplica sin ella (ADR-0014) | roles de dispositivos médicos |
| contar filas no es contar lo que se pregunta | `count(distinct …)` con nombre propio | resoluciones de la SIC |

## Reglas

- **Toda fuente nueva entra con perfil.** `tests/test_catalogo.py` lo exige: las fuentes sin
  perfil al 2026-10-22 están en una lista de deuda que solo puede encoger, y una fuente nueva sin
  perfil rompe el CI. Las de la lista se perfilan en la revisión de la ola en curso.
- **La herramienta respeta la decisión.** Si la clave no es única, la herramienta no cuenta filas:
  agrega, deduplica o usa la copia.
- **Si la fuente engaña y no tiene arreglo, no se sirve** (como los proveedores de SECOP) y queda
  escrito por qué en el plan.
- **El canario vuelve a medir.** Si cambia la verdad o el esquema, se repite el perfil antes de
  arreglar la ficha (runbook §2).

## Evaluación por fuente (el arnés)

El canario mira un dato. El perfil, la fuente. Falta saber si la herramienta **responde bien la
pregunta**: cada familia tendrá un banco de preguntas reales («¿cuántas ofertas tuvo este proceso?»),
con su respuesta medida a mano en la fuente, contestadas por un agente con LLM real y revisadas una a
una (spec 04, banco de agente ≥ 90 %). Ese banco se arma sobre `catalogo/verdades_producto.yaml`.
