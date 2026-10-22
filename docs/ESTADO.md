# Estado

*Actualizado: 2026-10-21.*

## Dónde estamos

**Fase F0 · Cimientos y decisiones.** F0.1 y F0.3 cerradas: hay esqueleto y una puerta mínima que responde por MCP.

| Spec F0 | Estado |
|---|---|
| F0.1 Repo y estructura | ✅ `pyproject` (uv, Python 3.13), ruff y mypy estricto fijados, pytest, pre-commit, CI; `make check` verde |
| F0.2 ADR aceptadas | ✅ las 20 aceptadas el 2026-10-21, con su validación escrita; 0005, 0007, 0010, 0014, 0018 y 0019 se corrigieron al revisarlas |
| F0.3 Spike de protocolo (FastMCP 4.1 ↔ conector `mcp` 1.28, Claude Code, Inspector) | ✅ las tres pruebas de ADR-0003 pasan; salto p95 3,1 ms ([informe](spikes/F0.3-protocolo.md)) |
| F0.4 Spike GeoResult en GEO Copilot | ⬜ |
| F0.5 Licencias de las fuentes M1 | ⬜ (humano) |
| F0.6 PR de amenazas y clima en GEO Copilot + Open-Meteo | ⬜ |
| F0.7 Banco de verdades del producto (40 preguntas) | ⬜ |
| F0.8 Solicitudes por derecho de petición | ⬜ (humano) |

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

1. **F0.4:** el hub de GEO Copilot pinta el bloque `geo_result` de `igac_predio_en_punto`, verificado en
   el navegador. La puerta ya devuelve el `geo_result` del conector tal cual.

Con F0.1–F0.4 verdes y las ADR aceptadas se cierra el gate F0 y empieza F1 (contrato y catálogo).

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

## Cómo correr las comprobaciones

`make check` (CI, Linux) o `uv run scripts/check.py` (Windows sin `make`): ruff, formato, mypy y
pytest. `make instalar` sincroniza dependencias e instala los ganchos de pre-commit.
