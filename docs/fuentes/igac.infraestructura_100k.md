# IGAC: infraestructura de la cartografía básica 1:100 000

Fuente `igac.infraestructura_100k`. Herramienta: `igac_infraestructura_en_zona`.

## Qué es

Son cinco capas de la cartografía básica 1:100 000 de 2019 del IGAC
(`mapas2.igac.gov.co/server/rest/services/carto/carto100000colombia2019/MapServer`), juntas en
una copia espacial con una columna `tipo`, como `upme.infraestructura_energetica`.

| Capa | Tipo | n | Geometría |
|---|---|---|---|
| 9 Aeropuerto_P | aeródromo | 399 | punto |
| 10 Puerto_P | puerto | 33 | punto |
| 22 Embarcadero_Muelle | embarcadero o muelle | 4 | punto |
| 16 Via_Ferrea | vía férrea | 49 | línea |
| 42 Embalse | embalse | 72 | polígono |

La copia trae las 557 filas (149 s, bajada desde Colombia).

## Licencia

La cartografía básica está en el art. 3 de la Resolución 616 de 2020 del IGAC, que la pone en
CC BY 4.0 (art. 7). Es la misma evidencia de agrología (`catalogo/licencias/m1.yaml`).

## Lo medido (2026-11-05)

- **Aeródromos:** 238 de los 399 no traen nombre. Los demás traen el del aeropuerto o el del
  lugar.
- **`TIPO_VIA_FERREA`:** vale 1480 (45 tramos), 1481 (2) o 1482 (2). El servicio no trae dominio:
  sale tal cual, sin significado.
- **Embalses:** están Guavio, Chivor, El Peñol, Urrá, Betania, Prado y Salvajina. No están
  Hidroituango, El Quimbo ni Sogamoso, que son posteriores a la cartografía. La herramienta lo
  avisa.
- **`FECHA`:** viene vacía en todas las filas, así que no se copia.
- **Canario:** 4 embalses en el oriente antioqueño (San Lorenzo, Las Playas, y El Peñol en dos
  polígonos).

## Otras capas del mismo servicio

El servicio también publica capas que no entran en esta copia:
- `Torre` (134 puntos, sin nombre ni tipo);
- `Red_Alta_Tension` (191 tramos; `upme.infraestructura_energetica` trae las líneas con tensión
  y propietario);
- pistas y puertos como polígonos.
