# Contrato de respuesta `rt/1`

## 6.1 Sobre

```json
{
  "contrato": "rt/1",
  "solicitud_id": "req_01JB…",
  "herramienta": "igac_predio_en_punto@1",
  "estado": "encontrado",
  "entrada": {"lon": -74.0262, "lat": 4.8619},
  "zona_usada": {"tipo": "punto", "valor": [-74.0262, 4.8619], "crs": "EPSG:4326"},
  "datos": {"codigo_predial": "251750000000000050067000000000", "area_terreno_m2": 0, "…": "…"},
  "huella": "sha256:…",
  "geo_result": {"geo_result": "1", "artifacts": [{"kind": "feature_collection", "crs": "EPSG:4326", "data": {}}], "facts": {}},
  "procedencia": [{
    "fuente_id": "igac.catastro.terreno",
    "entidad": "Instituto Geográfico Agustín Codazzi (IGAC)",
    "acto": "Resolución 616 de 2020 (datos abiertos)",
    "url": "https://mapas.igac.gov.co/server/rest/services/Dato_Fundamental_Catastro/MapServer/1",
    "licencia": {"spdx": "CC-BY-4.0", "url": "https://creativecommons.org/licenses/by/4.0/", "uso_comercial": "si"},
    "atribucion": "Fuente: IGAC, Dato fundamental de catastro",
    "servido_desde": "fuente",
    "consultado_en": "2026-10-21T16:20:00Z",
    "version_dataset": null,
    "consulta": {"geometry": "-74.0262,4.8619", "spatialRel": "esriSpatialRelIntersects"},
    "completitud": {"vistos": 1, "total": 1, "truncado": false, "motivo": null},
    "cache": {"acierto": false, "edad_s": 0},
    "transformaciones": ["EPSG:3116→EPSG:4326"],
    "conector": "arcgis-mcp@1.4.0",
    "huella": "sha256:…"
  }],
  "avisos": [],
  "errores": [],
  "creditos": 10
}
```

## 6.2 Reglas (invariantes que se prueban)

1. `estado` ∈ {`encontrado`, `no_encontrado`, `fuera_de_cobertura`, `parcial`}; un fallo total no es
   un sobre: es un error (ver códigos abajo).
2. `no_encontrado` es respuesta definitiva y descuenta cuota; `fuera_de_cobertura` dice que la
   fuente no cubre esa zona (índice de cobertura) y no descuenta.
3. Toda fuente consultada aparece en `procedencia` con licencia y atribución, aunque no haya
   encontrado nada.
4. `vistos ≤ total`; `truncado ⇔ vistos < total`; si `total` es desconocido, `null` y aviso.
5. `parcial ⇒ errores ≠ []` y cada error nombra su `fuente_id`.
6. `servido_desde` ∈ {`fuente`, `copia`, `curado`, `cache`, `obsoleto`}; `obsoleto ⇒ aviso` y
   `consultado_en` es la fecha original.
7. `huella` (en la raíz) = sha256 del JSON canónico de `datos`: claves ordenadas, sin espacios,
   UTF-8. Misma respuesta ⇒ misma huella. La `huella` de cada `procedencia` es la de lo que aportó
   esa fuente.
8. Geometría siempre GeoJSON EPSG:4326 (lon, lat); EPSG:9377 solo si se pide y se declara.
9. Texto libre de las fuentes: sin caracteres de control (salvo `
` y `	`) ni marcas bidi, con
   un máximo de 4000 caracteres por campo y solo dentro de `datos` y de las propiedades de la capa.
10. Ningún campo fuera de la lista blanca del catálogo.

## 6.3 Códigos de error (estables)

| Código | HTTP | Cuándo | ¿Descuenta cuota? |
|---|---|---|---|
| `parametro_invalido` | 400 | entrada no válida (con `param`) | no |
| `zona_demasiado_grande` | 400 | polígono o bbox sobre el tope de la herramienta | no |
| `no_autenticado` | 401 | falta llave o es inválida | no |
| `sin_permiso` | 403 | la llave no tiene el scope | no |
| `licencia_no_habilitada` | 403 | fuente con licencia `por_verificar` y llave que no es de evaluación (ADR-0007) | no |
| `no_existe` | 404 | herramienta o recurso inexistente | no |
| `saldo_agotado` | 429 | créditos del mes agotados (con `Retry-After` hasta el reinicio del mes; sin 402: es gratuito) | no |
| `limite_tasa` | 429 | exceso de tasa (con `Retry-After`) | no |
| `fuente_no_disponible` | 502 | la fuente respondió error o no conecta | no |
| `fuente_respuesta_invalida` | 502 | la fuente cambió de esquema o respondió basura | no |
| `fuente_lenta` | 504 | la fuente no respondió a tiempo | no |
| `error_interno` | 500 | fallo nuestro | no |

Mismo objeto en MCP (`isError: true`, `structuredContent` = problem+json).

## 6.4 Implementación

- Modelos en `src/terranova/contrato.py`. Las reglas 1 a 9 son validadores: un sobre que no las
  cumple no se puede construir. La 10 es `fuera_de_lista_blanca(sobre, campos)`, con los campos que
  declara el catálogo.
- JSON Schema versionado en `esquemas/` (`uv run scripts/esquema.py`). El check de CI falla si
  quedó viejo.
- Pruebas de propiedad con Hypothesis en `tests/test_contrato.py`: hay una por regla, y se
  comprobaron desactivando reglas a mano (mutación).
- `uso_comercial` ∈ {`si`, `no`, `por_verificar`}, igual que en el catálogo. Los errores de una parte
  (`errores[]`) llevan `codigo`, `fuente_id`, `detalle` y `reintentar_en_s`.
