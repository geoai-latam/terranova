# IDEAM (SIRH): puntos de captación de agua concesionados

Fuente `ideam.captaciones`. Herramientas: `ideam_captaciones_en_zona`, `ideam_captaciones_municipio`
y `ideam_captaciones_buscar`.

## Qué es

Los puntos de captación de agua superficial de las concesiones que otorgan las autoridades
ambientales: bocatomas de acueductos, de riego, de industria y otras. Las autoridades los cargan
al Sistema de Información del Recurso Hídrico (SIRH), que coordina el IDEAM.

- **Conjunto:** `4q6d-6s7b` de datos.gov.co.
- **Tamaño:** 81 731 captaciones de 73 083 concesiones, todas de fuente superficial.
- **Corte:** 2026-10-27 (`fechaproceso`); datos.gov.co dice que se actualiza cada mes.
- **Sin titulares:** no trae al titular de la concesión. `descripcion_acceso` es texto libre de la
  autoridad: sale como se publica y no se busca por él.

## Licencia

CC BY-SA 4.0, según la ficha del conjunto en datos.gov.co (verificada el 2026-11-05).

## El punto

La fuente no publica un punto: publica grados, minutos y segundos de latitud y longitud. La copia
arma el punto con `copia.punto_gms`, nuevo para el origen `socrata`.

- **Signo:** va en los grados. Por eso, con 0 grados de latitud no se sabe el hemisferio. Esas
  443 filas (casi todas de CORPOAMAZONIA) quedan sin punto: no se inventa una ubicación.
- **Relleno:** 985 filas traen 5°5'5" N 75°5'5" O, un mismo punto de relleno. Quedan sin punto.
- **Latitud sur:** solo vale en Amazonas, Putumayo, Caquetá y Vaupés. Hay 14 de autoridades del
  norte (CVC, CARDIQUE) con el signo mal, que quedan sin punto.
- **Fuera de Colombia:** 44 más caen fuera del país o no traen los grados.
- **Resultado:** 80 245 con punto y 1 486 sin él.
  - Las que no tienen punto no salen en una zona, pero sí por municipio y en la búsqueda.
- **Datum:**
  - 44 703 vienen en WGS 84 y 36 727 en MAGNA-SIRGAS, que son prácticamente iguales.
  - 301 vienen en el datum Bogotá: pueden quedar corridos y no se transforman.
- **Puntos repetidos:** 61 244 distintos para 80 245 captaciones. Una concesión puede tener
  varias captaciones en el mismo sitio.

## Lo medido (2026-11-05)

- **Caudales y ofertas:** usan -1 para decir «sin dato». Algunos traen ruido de coma flotante de
  la fuente (0.469999998807907): salen tal cual.
- **Estado:** «No registra» en 14 528.
- **Tipo de captación:** «No registra» en 24 727.
- **Canarios:**
  - 12 captaciones de la CAR en [-74.1, 4.85, -74.0, 4.9], en Chía;
  - 2 de CORMACARENA en Cubarral (50223);
  - 1 en el caño Arenas Blancas.

## Lo que no trae

- Aguas subterráneas.
- Usos de cada concesión: están en `dq2g-rw28`.
- Vertimientos: están en `7peu-q4hn`.
- Concesiones que la autoridad ambiental no ha cargado al SIRH.
