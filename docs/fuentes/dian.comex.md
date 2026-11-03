# DANE y DIAN: comercio exterior por subpartida (`dian.comex_exportaciones`, `dian.comex_importaciones`)

Dos microdatos del DANE, armados con las declaraciones de exportación e importación ante la DIAN.
Licencia CC BY-SA 4.0. Terrnova los **copia** y los preagrega (ADR-0024).

| Fuente | Origen | Herramientas |
|---|---|---|
| `dian.comex_exportaciones` | ANDA 859, ZIP por año | `dian_comex_exportaciones_por_subpartida` |
| `dian.comex_importaciones` | ANDA 856, ZIP por semestre | `dian_comex_importaciones_por_subpartida` |

## Qué publica

Una fila por línea de declaración: el mes, la aduana, el país, la subpartida NANDINA de 10 dígitos,
el valor (FOB en exportaciones; FOB y CIF en importaciones), el peso y la cantidad en su unidad.
**No trae NIT ni nombre de la empresa.** Las cifras son estadísticas, no probatorias.

La copia suma por año, mes, subpartida y país. La herramienta suma el año de una subpartida.

## Campos que importan

- `POSAR` (expo) y `NABAN` (impo): la subpartida.
- `CANTI` (expo) y `CANU` (impo): la cantidad, **en la unidad física de la subpartida**.
- `CODUNI2` (expo) y `CODA` (impo): la sigla de esa unidad. La copia no la guarda; la herramienta
  la toma de `catalogo/codigos/unidad_subpartida.yaml`.
- Los números vienen en formato europeo («225.490,42»), con espacios alrededor en algunos meses.

## Cobertura

Desde enero de 2025, hasta donde llegue la copia (la procedencia dice su fecha). Los ZIP de
importaciones de 2025 vienen en dos semestres.

## Trampas medidas

1. **La cantidad no es siempre kilos.** Medido el 2026-11-02 en los ZIP de 2025 y 2026: 7 007
   subpartidas, cada una con una sola unidad. Las más comunes son kilogramos (2 486 subpartidas en
   exportaciones) y unidades (2 317). También hay m², m³, litros, pares, millares, quilates, kWh y
   cm³.
2. **El crudo va en metros cúbicos, no en barriles.** 2709000000 en 2025: 25 835 739 m³ (unos 162
   millones de barriles) y 23 886 millones de kg, es decir, 0,92 kg por litro. El diésel
   (2710192100) da 0,84; las esmeraldas (7103912000), 0,21 g por quilate.
3. **En el café la cantidad es igual al peso** porque su unidad es el kilogramo, no por error.
4. **El conector en proceso devuelve Decimal.** Las sumas de la copia (Postgres `numeric`) no se
   podían grabar como dorada; `scripts/grabar_doradas.py` las pasa a número.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `dian_comex_exportaciones_por_subpartida` | alto | v2: dice `unidad_cantidad` |
| `dian_comex_importaciones_por_subpartida` | alto | v2: igual |

## Decisiones

- **2026-11-02, patrón D de la revisión de valor:**
  - La unidad sale de una lista compartida, no de la copia. Así no hay que reconstruir la copia en
    producción, y la lista se vuelve a armar con `scripts/codigos_unidad_subpartida.py` si llega
    una subpartida nueva. El script falla si una subpartida trae dos unidades.
  - Una subpartida que no esté en la lista sale con `unidad_cantidad` vacía: no se adivina.
  - El catálogo suma `valores_lista` en los derivados `codigo`, como `codigos_lista` en los campos.
- **Pendiente:**
  - los decimales de sobra en las sumas (9 930 919 822,169998);
  - un buscador de subpartidas por producto: hoy hay que saberse los 10 dígitos.
- **2026-11-02, patrón E (decimales de sobra):**
  - Los valores en dólares y pesos, el peso neto y la cantidad salen con dos decimales
    (`decimales: 2`).
  - La suma en la copia dejaba ruido de coma flotante: 9930919822.169998 ahora es 9930919822.17.
