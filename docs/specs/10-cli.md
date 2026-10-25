# CLI de cliente

El canal de terminal para quien pregunta: un **cliente delgado del REST `/v1`** (ADR-0027). No agrega
lógica — formatea el sobre `rt/1`, hace batch y exporta. Complementa la sección 8 de
[03-superficie.md](03-superficie.md) (8.1 REST, 8.2 MCP, 8.3 ficha → **8.4 CLI**).

## 10.1 Alcance

- **Sí:** consultar una herramienta por lugar/código; buscar en el catálogo (G6); listar herramientas
  y fuentes; exportar a GeoJSON/GPKG/CSV; **batch** sobre un archivo de lugares (el caso EUDR); ver la
  cuota; autenticar con llave.
- **No:** lógica de negocio (vive en la puerta); revisión humana ni trabajo de campo (capa de
  Automatización); embeber las fuentes o la base (habla REST, respeta cuota/scopes/auditoría).

## 10.2 Autenticación y configuración

```bash
export TERRANOVA_LLAVE=rt_live_…          # o rt_test_… (plan evaluación); nunca se imprime
export TERRANOVA_PUERTA=https://…         # o --puerta; por defecto el endpoint público
```

El prefijo de la llave fija el plan (`rt_live_` / `rt_test_`), como en Stripe. La llave va en
`Authorization: Bearer`; nunca se escribe en disco ni se muestra.

## 10.3 Comandos (cliente)

```bash
# Consultar una herramienta (una por ficha del catálogo)
terranova consultar igac_predio_en_punto --lon -74.0262 --lat 4.8619
terranova consultar secop_contratos_municipio --municipio Chía --departamento Cundinamarca --json

# Descubrimiento (front de terminal de G6)
terranova catalogo buscar "restricciones ambientales de un polígono"   # entidad, licencia, id
terranova catalogo listar [--familia territorio]
terranova fuentes listar
terranova herramientas listar [--familia contratacion]

# Exportar (geoespacial)
terranova exportar pnn_areas_protegidas_en_zona --bbox -74.1,4.6,-74.0,4.7 --a areas.gpkg  # GPKG/GeoJSON/CSV

# Batch — el comando estrella (caso EUDR, láminas 15–18)
terranova verificar parcelas.csv --obligacion eudr --salida expediente/

# Cuota de la llave
terranova uso
```

Cada comando `consultar/catalogo/exportar/uso/fuentes/herramientas` es **una ruta `/v1` + formateo**;
`verificar` es muchas consultas por lote con su expediente. Los comandos admin (`llaves`, `orgs`,
`canarios`, `copias`, `serve`) siguen en el mismo `terranova`, pero cargan el núcleo (ADR-0027).

## 10.4 Salida y exit codes (honestidad)

- **Por defecto:** legible, con **estado `rt/1`, el dato, procedencia, licencia y frescura**; el aviso
  («Datos no recientes», homónimo…) va a stderr.
- **`--json`:** el sobre `rt/1` crudo a stdout (para `jq` y pipes, estilo `datasette`/`gh`).
- **Exit codes** (para `set -e` en CI):

| Situación | stdout | exit |
|---|---|---|
| `encontrado` | el dato / el sobre | 0 |
| `no_encontrado` | «no hay», con su procedencia; aviso a stderr | 0 |
| «no se pudo»: `fuente_no_disponible`, `fuente_lenta`, 4xx/5xx, error de red | nada; motivo a stderr | ≠0 |

«No encontrado ≠ no se pudo»: un pipeline distingue «ese predio no existe» (sigue) de «la fuente se
cayó» (falla).

## 10.5 `verificar <archivo>` (batch)

El caso EUDR en una línea, acotado a «cruza y entrega expediente» (ADR-0027):

- **Entrada:** CSV o GeoJSON de lugares (punto o polígono); normaliza a WGS 84 con seis decimales
  (lámina 15) y avisa de las geometrías que no puede arreglar.
- **Proceso:** cada lugar contra las herramientas que pide la obligación, con **copia firmada** de cada
  consulta.
- **Salida en `--salida`:** GeoJSON validado como lo pide la UE (si una tiene hallazgos o está
  pendiente, no sale), Excel por lugar (resultado, fuente, fecha, motivo) y **expediente firmado**
  (huella + sello de tiempo).
- **No hace:** revisión humana de los dudosos ni trabajo de campo (eso es la capa de Automatización);
  marca los «no concluyentes» y para ahí.

## 10.6 Diseño

- **Typer (Python)**, módulo `src/terranova/cliente/`; **reusa `contrato.py`** para parsear el sobre.
- **Cliente delgado del REST `/v1`**: ningún acceso a fuentes ni a la base; un comando que no se pueda
  hacer solo con REST es un hueco **del REST**, no del CLI.
- **Instalación aparte:** `pipx install "terranova[cliente]"` no arrastra FastAPI ni PostGIS; `serve` y
  los comandos admin están en `terranova[puerta]`.
- **Export geoespacial** apoyado en GDAL/`fiona` (no se reinventa; ver `ogr2ogr`).
- Patrón de UX: estructura de `gh` (`sustantivo verbo`, `--json`), llaves `rt_test_`/`rt_live_` como
  `stripe`, pipes como `datasette`.

## 10.7 Compuerta del CLI

- Cada comando cliente probado **sin red** contra un REST mockeado (ruta, formateo, `--json`).
- Los **exit codes** verificados en un `set -e` (encontrado / no_encontrado / no se pudo).
- `verificar` sobre un CSV pequeño deja GeoJSON + Excel + expediente, con copia firmada por consulta.
- `catalogo buscar` devuelve candidatos de G6 con entidad, licencia e id.
- `terranova[cliente]` instala **sin** FastAPI/PostGIS (prueba de que el cliente es delgado).
