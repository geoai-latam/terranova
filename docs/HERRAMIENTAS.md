# Herramientas

Generado del catálogo con `uv run scripts/descripcion.py`; no se edita a mano.

## ambiente

| Herramienta | Pregunta | Fuente | Licencia | Créditos |
|---|---|---|---|---|
| `ant_resguardos_en_punto` | ¿En qué resguardo indígena formalizado cae este punto? | Agencia Nacional de Tierras (ANT) | CC-BY-SA-4.0 | 10 |
| `ant_zonas_reserva_campesina_en_punto` | ¿En qué zona de reserva campesina constituida cae este punto? | Agencia Nacional de Tierras (ANT) | CC-BY-SA-4.0 | 10 |
| `esa_cobertura_suelo_en_punto` | ¿Qué cobertura del suelo hay alrededor de este punto? | European Space Agency (consorcio WorldCover) | CC-BY-4.0 | 20 |
| `ideam_estaciones_en_zona` | ¿Qué estaciones hidrometeorológicas hay en esta zona? | Instituto de Hidrología, Meteorología y Estudios Ambientales (IDEAM) | CC-BY-SA-4.0 | 5 |
| `open_meteo_clima_serie` | ¿Cuánto llovió y qué temperatura hizo en este punto en este periodo? | Open-Meteo (datos de Copernicus Climate Change Service, ERA5) | CC-BY-4.0 | 10 |
| `pnn_areas_protegidas_en_punto` | ¿Qué áreas protegidas del RUNAP contienen este punto? | Parques Nacionales Naturales de Colombia (PNN) | CC-BY-SA-4.0 | 10 |
| `pnn_areas_protegidas_en_zona` | ¿Qué áreas protegidas del RUNAP tocan esta zona? | Parques Nacionales Naturales de Colombia (PNN) | CC-BY-SA-4.0 | 20 |
| `usgs_sismos_en_zona` | ¿Qué sismos hubo en esta zona en este periodo? | U.S. Geological Survey (USGS) | LicenseRef-dominio-publico-EEUU | 10 |

## contratacion

| Herramienta | Pregunta | Fuente | Licencia | Créditos |
|---|---|---|---|---|
| `secop_contrato_por_id` | ¿Qué dice este contrato de SECOP II? | Agencia Nacional de Contratación Pública, Colombia Compra Eficiente (ANCP-CCE) | CC-BY-SA-4.0 | 2 |
| `secop_contratos_municipio` | ¿Cuántos contratos ha firmado el Estado en este municipio y por cuánto? | Agencia Nacional de Contratación Pública, Colombia Compra Eficiente (ANCP-CCE) | CC-BY-SA-4.0 | 5 |

## estadisticas

| Herramienta | Pregunta | Fuente | Licencia | Créditos |
|---|---|---|---|---|
| `dane_poblacion_municipio` | ¿Cuánta gente vive en este municipio según el censo 2018? | Departamento Administrativo Nacional de Estadística (DANE) | por verificar | 10 |
| `upra_precio_tierra_rural_municipio` | ¿Cuánto vale la tierra rural en este municipio, según UPRA? | Unidad de Planificación Rural Agropecuaria (UPRA) | CC-BY-SA-4.0 | 5 |

## territorio

| Herramienta | Pregunta | Fuente | Licencia | Créditos |
|---|---|---|---|---|
| `igac_capacidad_uso_en_punto` | ¿Cuál es la capacidad de uso de la tierra en este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-4.0 | 10 |
| `igac_caracteristicas_predio` | ¿Qué unidades construidas y zonas homogéneas tiene este predio en el catastro IGAC? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_conflictos_uso_en_punto` | ¿Hay conflicto de uso de la tierra en este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-4.0 | 10 |
| `igac_construcciones_en_predio` | ¿Qué construcciones tiene registradas este predio en el catastro IGAC? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_manzana_en_punto` | ¿En qué manzana urbana del catastro IGAC está este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_perimetro_urbano_en_punto` | ¿Este punto está dentro de un perímetro urbano del catastro IGAC? ¿Cuál? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_predio_en_punto` | ¿Qué predio del catastro IGAC hay en este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_predio_por_codigo` | ¿Qué predio del catastro IGAC tiene este número predial? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_registro_predio` | ¿Qué dirección, destino económico y áreas tiene este predio en el catastro IGAC? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_sector_en_punto` | ¿En qué sector catastral del IGAC está este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_vereda_en_punto` | ¿En qué vereda del catastro IGAC está este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-SA-4.0 | 10 |
| `igac_vocacion_uso_en_punto` | ¿Cuál es la vocación de uso de la tierra en este punto? | Instituto Geográfico Agustín Codazzi (IGAC) | CC-BY-4.0 | 10 |

## Ficha de un lugar

`ficha_lugar` (MCP en `/mcp` y `/mcp/territorio`; REST en `POST /v1/fichas`): Ficha de un lugar de Colombia por punto (lon, lat) o por número predial: predio y construcciones (IGAC), vereda, áreas protegidas (RUNAP), resguardos y zonas de reserva campesina (ANT), vocación, capacidad y conflictos de uso del suelo (IGAC), cobertura (ESA WorldCover), sismos M≥3 del último año a ~55 km (USGS), población (DANE) y precio de la tierra rural (UPRA). Partes en paralelo, cada una con su procedencia y licencia; si una falla, la ficha sale «parcial» con el error de esa parte. Tope de 12 s. Cuesta la suma de las partes que respondieron, hasta 50 créditos.
