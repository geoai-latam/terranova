# Estado

*Actualizado: 2026-10-21.*

## Dónde estamos

**Gate F0 cerrado (2026-10-21)**: ADR aceptadas, spikes F0.3 y F0.4 en verde, licencias M1 decididas. Empieza **F1 · Contrato y catálogo**. F0.6 a F0.8 siguen en paralelo, porque el gate no las exige.

| Spec F0 | Estado |
|---|---|
| F0.1 Repo y estructura | ✅ `pyproject` (uv, Python 3.13), ruff y mypy estricto fijados, pytest, pre-commit, CI; `make check` verde |
| F0.2 ADR aceptadas | ✅ las 20 aceptadas el 2026-10-21, con su validación escrita; 0005, 0007, 0010, 0014, 0018 y 0019 se corrigieron al revisarlas |
| F0.3 Spike de protocolo (FastMCP 4.1 ↔ conector `mcp` 1.28, Claude Code, Inspector) | ✅ las tres pruebas de ADR-0003 pasan; salto p95 3,1 ms ([informe](spikes/F0.3-protocolo.md)) |
| F0.4 Spike GeoResult en GEO Copilot | ✅ pintado en el navegador ([informe](spikes/F0.4-geo-result.md)); el hub desanida el sobre (geo-copilot#43) |
| F0.5 Licencias de las fuentes M1 | ✅ decididas con evidencia en [`catalogo/licencias/m1.yaml`](../catalogo/licencias/m1.yaml): 12 a producción, 4 a evaluación (DANE, IDEAM geoservicios, SIAC, ambiente alojado en IGAC), SGC fuera |
| F0.6 PR de amenazas y clima en GEO Copilot + Open-Meteo | ⬜ |
| F0.7 Banco de verdades del producto (40 preguntas) | ⬜ |
| F0.8 Solicitudes por derecho de petición | ⬜ (humano) |

## F1 · Contrato y catálogo

| Spec F1 | Estado |
|---|---|
| F1.1 Modelos `rt/1` + JSON Schema `--check` + propiedades | ✅ `src/terranova/contrato.py`: reglas 1–9 como validadores, la 10 como función; esquemas en `esquemas/`; 38 pruebas (propiedades y casos), verificadas por mutación |
| F1.2 Modelos del catálogo + validador CI | ✅ `src/terranova/catalogo.py` + `scripts/validar_catalogo.py` en `make check`; 19 reglas rotas probadas; semilla: `igac.catastro.terreno` e `igac_predio_en_punto` |
| F1.3 Códigos de error y completitud en el kit (GEO Copilot) | 🟡 kit y `arcgis-mcp` en geo-copilot#45; la puerta ya lee `codigo` y `completitud` (los `fuente_*` pasan, el resto es `error_interno`) |
| F1.4 Catálogo inicial M1 | ✅ 18 fuentes y 20 herramientas, cada canario medido en la fuente el 2026-10-21; las fichas con `where` usan tipos con patrón (no hay `str` libre dentro de un texto: inyección) |
| F1.5 Índice de cobertura catastral | ✅ `catalogo/cobertura/cobertura_catastral.yaml`, medido por los sectores de la base: 780 municipios con datos. Bogotá y El Carmen de Viboral dan `fuera_de_cobertura` (0 créditos), verificado en vivo |

## Decisiones tomadas

- Nombre **Terranova**; repo público `geoai-latam/terranova`.
- **Todo open source y gratuito** al inicio: código Apache 2.0, datos CC BY-SA 4.0. Los créditos son
  cuota (protegen las fuentes y el gasto), no cobro.
- Hitos: **M1** (puerta, contrato, catálogo, ficha, GEO Copilot como cliente, sobre las fuentes que
  ya existen) y **M2** (las ~139 herramientas de [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md), lotes,
  trabajos lentos).
- Personas por cédula o nombre: fuera. Captchas y backends sin permiso: nunca, en ningún plan (ADR-0018).
- Cuota agotada: 429 `saldo_agotado`, sin 402 (ADR-0010). Licencia `por_verificar`: solo llaves de evaluación (ADR-0007).
- Open-Meteo: API gratis mientras Terranova sea gratuito, con caché y tope propio; salida a Copernicus directo (ADR-0021).
- Escaneo de secretos (gitleaks) en CI, sobre toda la historia (ADR-0001).
- Boletines de Contraloría y BDME: se evalúan con asesoría legal antes de incluirlos.

## Pendiente de decidir


## Siguiente paso concreto

1. **Cerrar el gate F1:** falta que los conectores M1 restantes (`datos-abiertos-mcp`, `dane-mcp`,
   `imagery-mcp` y `amenazas-mcp`, que espera el PR geo-copilot#38) emitan `completitud`. Los códigos
   de error ya salen de todos por el `ToolRunner` (geo-copilot#45).
2. **F2.1:** ejecutor genérico, catálogo → conector → lista blanca → `rt/1`, con pruebas doradas.
   Reemplaza la puerta escrita a mano.
3. **En paralelo:**
   - **F0.6:** repetir la tanda V5 del PR geo-copilot#38 (la que quedó a medias por falta de memoria)
     y fusionarlo. También fusionar geo-copilot#43.
   - **F0.7:** banco de 40 verdades medidas en la fuente.
   - **F0.8:** las solicitudes por derecho de petición están en borrador en `interno/borradores/`;
     las envía el dueño. Se sumaron DANE (redistribución del MGN y el CNPV) y SGC (la licencia de
     MIIG choca con los ítems CC BY en ArcGIS Online).

## Hechos medidos que sirven de canario

| Verdad | Valor |
|---|---|
| Predio en (-74.0262, 4.8619), Chía | `251750000000000050067000000000` (R_TERRENO, corte 06_2026), ~0,5 s directo |
| SECOP, contratos de Chía | 12 147 contratos, $1,29 billones, 1,7 s |
| RUNAP en el bbox de prueba | 169 áreas |
| Población de Bogotá (CNPV 2018) | 7 181 469 |
| REGISTRO_1 IGAC (corte 06-2026) | 6 812 177 predios |
| Transacciones inmobiliarias IGAC | 30,9 M |

## Versiones de referencia (2026-10-21)

| Pieza | Versión |
|---|---|
| Especificación MCP | 2026-07-28 |
| FastMCP | 4.1.3 |
| SDK `mcp` (Python) | 2.3.0 (los conectores de GEO Copilot siguen en 1.28.1) |
| Herramientas en los conectores de GEO Copilot | 49, en 12 servicios |

## Hallazgos abiertos

- IGAC: `codigo_municipio` errado en la fuente (Chía sale `23175`). Hace falta un canario en F1.
- IGAC: el último corte mensual es `06_2026`; revisar `Base_Catastral_Publica_IGAC_de_octubre` en F1.5.

- IGAC: El Carmen de Viboral (05148) figura con gestor IGAC y no tiene datos en la base; 63 municipios
  están igual. Por eso la cobertura se mide y no sale del registro de gestores.
- IDEAM `hp9r-jxuu`: la columna `ubicaci_n` trae latitud y longitud cruzadas; la herramienta usa
  `latitud`/`longitud`.
- SECOP: los totales de un municipio crecen cada día, así que el canario usa `minimos`. Las peticiones
  tienen que ir en UTF-8 («Chía»).
- FIRMS y GloFAS no tienen ventana fija para medir una verdad: sin herramienta en el catálogo hasta que
  haya canarios estructurales (F2).
- Minambiente: las reservas forestales con geometría no tienen licencia; RUNAP ya las cubre (BY-SA).

## Cómo correr las comprobaciones

`make check` (CI, Linux) o `uv run scripts/check.py` (Windows sin `make`): ruff, formato, mypy y
pytest. `make instalar` sincroniza dependencias e instala los ganchos de pre-commit.
