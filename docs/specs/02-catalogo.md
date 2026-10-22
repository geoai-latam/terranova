# Catálogo de fuentes y herramientas

## 7.1 Fuente

```yaml
id: igac.catastro.terreno
titulo: Terrenos del dato fundamental de catastro
entidad: Instituto Geográfico Agustín Codazzi (IGAC)
competencia: autoridad catastral nacional (Ley 1955 de 2019, art. 79)
acto: Resolución 616 de 2020
licencia: {spdx: CC-BY-4.0, url: https://creativecommons.org/licenses/by/4.0/, verificada: <fecha>, evidencia: <licenseInfo del ítem>}
                             # por ítem: la base catastral pública en ArcGIS Online es CC-BY-SA-4.0
uso_comercial: si            # si | no | por_verificar
clase_acceso: api            # api | bulk | html_publico | interno_con_permiso (ADR-0018)
atribucion: "Fuente: IGAC, Dato fundamental de catastro"
protocolo: arcgis_rest       # arcgis_rest | wfs | wms | socrata | ckan | stac | api_propia | archivo
conector: arcgis-mcp
url: https://mapas.igac.gov.co/server/rest/services/Dato_Fundamental_Catastro/MapServer/1
modo: en_vivo                # en_vivo | copia | curado
frescura: {ttl_cache_s: 3600, sla_actualizacion: P30D}
cobertura: {pais: CO, excluye: ["11001 Bogotá (UAECD)"], indice: cobertura_catastral}
datos_personales: ninguno    # ninguno | filtrados | presentes (bloquea hasta ADR-0014)
campos:                      # lista blanca: nombre_fuente → nombre_rt, tipo, descripción
  CODIGO: {nombre: codigo_predial, tipo: str, desc: "número predial nacional de 30 dígitos"}
comportamiento: {p95_ms_medido: 1100, max_por_pagina: 2000, orden_coordenadas: lon_lat}
dcat: {publisher: IGAC, theme: catastro, accrualPeriodicity: irregular}
```

## 7.2 Herramienta

```yaml
id: igac_predio_en_punto
version: 1
familia: territorio
fuente: igac.catastro.terreno
pregunta: "¿Qué predio del catastro IGAC hay en este punto?"
descripcion: >
  Predio del dato fundamental de catastro del IGAC que contiene un punto: número predial, vereda,
  áreas y geometría. Cubre los municipios con catastro IGAC; Bogotá no (UAECD).
  (Fuente: IGAC; licencia: CC BY 4.0.)
entrada: {lon: float, lat: float}
consulta: {operacion: en_punto, capa: 1, campos: [CODIGO, …]}
salida: PredioEnPunto          # modelo Pydantic; de él salen OpenAPI y outputSchema
creditos: 10
canario:
  entrada: {lon: -74.0262, lat: 4.8619}
  verdad: {codigo_predial: "251750000000000050067000000000"}
  latencia_max_ms: 5000
```

## 7.3 Validación en CI

- Esquema Pydantic de ambos archivos; identificadores únicos; toda herramienta apunta a una fuente
  existente; toda fuente tiene licencia y atribución; ninguna fuente `datos_personales: presentes`
  publicada; toda herramienta tiene canario con verdad; descripción con cierre de fuente y licencia.
- Generación: el catálogo produce las rutas REST, las herramientas MCP, los modelos de salida
  declarados, la página de documentación y la tabla de estado.
