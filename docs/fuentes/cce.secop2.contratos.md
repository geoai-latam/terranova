# SECOP II, contratos electrónicos (`cce.secop2.contratos`)

Conjunto `jbjy-vk9h` de datos.gov.co. Lo publica Colombia Compra Eficiente (ANCP-CCE). Licencia
CC BY-SA 4.0, verificada el 2026-10-21. Se consulta en vivo y se actualiza a diario. Para buscar en
texto hay una copia aparte (`cce.secop2.contratos_copia`).

## Qué publica

Una fila por contrato electrónico firmado en SECOP II, con la clave `id_contrato`
(`CO1.PCCNTR.…`). Trae la entidad contratante (nombre y NIT), el contratista (nombre y documento,
que son de divulgación obligatoria, ADR-0025), el objeto, el tipo, la modalidad, el valor, lo
pagado, las fechas y el enlace al proceso.

No trae SECOP I ni la Tienda Virtual del Estado: esos están en otros conjuntos.

## Campos que importan

- `nit_entidad`: el NIT **sin** dígito de verificación (la puerta lo quita si viene). No identifica a una sola entidad (ver
  trampa 1).
- `nombre_entidad`: el nombre que la entidad usa en SECOP. Cambia con el tiempo: Medellín sale como
  «DISTRITO ESPECIAL DE CIENCIA TECNOLOGIA E INNOVACION DE MEDELLIN».
- `ciudad`: el municipio de la entidad, **no** el lugar donde se ejecuta el contrato.
- `proceso_de_compra`: el portafolio `CO1.BDOS.…`. Los proponentes cuelgan del proceso
  `CO1.REQ.…`, que está en otro conjunto (ver `cce.secop2.procesos`).
- `valor_del_contrato`: el valor en pesos. Tiene errores de digitación enormes (trampa 3).
- `fecha_de_firma`: puede venir vacía (trampa 2).

## Cobertura

- Todo el país, desde 2017. Los primeros años tienen pocos contratos: SECOP II se volvió
  obligatorio de forma gradual, y Chía tiene 6 contratos en 2017 y 5 en 2019.
- El año en curso va hasta la última firma publicada (medido el 2026-11-02: Pitalito hasta el
  2026-10-31, Chía hasta el 2026-10-29).

## Trampas medidas

1. **Un NIT, varias entidades** (medido el 2026-11-02).
   - La alcaldía, la personería y el concejo de un municipio suelen publicar con el mismo NIT:
     - el NIT 899999172 cubre la Alcaldía y la Personería de Chía;
     - el 891180077, el Municipio, la Personería y el Concejo de Pitalito;
     - el 890905211, el Distrito, el Concejo y la Personería de Medellín.
   - Cuánto pesa cada una, en Chía en 2025: la Alcaldía firmó 1 143 contratos por
     144 958 millones y la Personería 51 por 1 444 millones.
   - Quien agrega por NIT y pone un solo nombre se equivoca de entidad.
2. **Contratos sin fecha de firma** (2026-11-02).
   - Chía tiene 15 (13 de la Alcaldía y 2 de la Personería) y Pitalito 9.
   - Al agrupar por año salen en una fila sin año.
3. **Valores imposibles.**
   - Un contrato de Medellín dice 440 000 billones de pesos.
   - Los de 20 billones o más no se suman y se cuentan aparte en `contratos_valor_atipico`.
4. **Empréstitos mezclados con compras.**
   - En Chía, tres préstamos de entre 40 000 y 50 000 millones (2022 y 2024) están entre los seis
     contratos más grandes.
   - Una suma de «lo que contrató» los incluye.
5. **El año en curso parece completo y no lo es.**
   - Hay que mostrar hasta qué fecha va (`ultima_firma`).
6. **Entidades con sigla** (2026-11-03).
   - El IGAC (NIT 899999004) publica como «IGAC Sede Central *», con 19 884 contratos desde 2023.
     Buscar «Instituto Geográfico Agustín Codazzi» no lo encuentra; «Codazzi» trae el municipio
     del Cesar.
7. **La búsqueda por nombre de una ciudad grande es lenta en frío** (2026-11-03, copia del 03-11).
   - «medellin» toca 50 142 contratos y «bogota» 35 746. Leerlos del disco tarda 16 s y 14 s, y la
     herramienta se corta a los 15 s (`QueryCanceled`).
   - Con el caché caliente, la misma consulta agrupada tarda 0,6 s. El costo es leer filas sueltas
     de 3,6 millones, no agrupar. «chia» (6 766 contratos) tarda 0,1 s, que no cabe sin el
     índice de trigramas.
   - La correlación física de `nit_entidad` era −0,03: los contratos de una entidad estaban
     regados por toda la tabla. Se arregla con `orden_fisico` (ver Decisiones).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_contratos_entidad` | alto desde #242 | agrupa por año **y entidad**, de lo más reciente a lo más viejo, con `ultima_firma`. Antes salía todo a nombre de la Personería (trampa 1) |
| `secop_contratos_entidad_anio` | alto | ya agrupaba por entidad. El NIT, como texto o número, con o sin dígito de verificación |
| `secop_contratos_municipio` | medio | el aviso «la fuente no dijo cuántos elementos» sale sin sentido en una suma; no da el rango de años; mete los empréstitos (trampa 4) |
| `secop_entidades_buscar` | alto, lenta en frío | v3: `contratos_desde_2023` y `valor_desde_2023`. Se corta en frío con ciudades grandes (trampa 7) |
| `secop_entidades_municipio` | alto | da el NIT como número |
| `secop_contratos_proveedor` | alto | |
| `secop_contratos_buscar` | alto | |
| `secop_contrato_por_id` | alto | entrega `id_proceso` como BDOS; desde #243 la herramienta de proponentes lo acepta |

## Decisiones

- **#242 (2026-11-02):** `secop_contratos_entidad` agrupa por `nombre_entidad`, ordena con
  `anio DESC NULL LAST` y agrega `ultima_firma`. El canario vigila que la primera fila de Pitalito
  sea del Municipio.
- **2026-11-03, NIT normalizado** (patrón H de la revisión de valor; hallazgo de GEO Copilot y del
  caso de compras de la URT):
  - **El fallo:** con el dígito de verificación pegado (`8999991728`), el `int` dejaba pasar ese
    número de 10 dígitos y la fuente respondía «no encontrado» sin aviso. Con puntos o guion, se
    rechazaba.
  - **El tipo nuevo:** `nit_entidad` (y `nit_empresa`) acepta `899999172`, `899.999.172`,
    `899999172-8`, `899.999.172-8`, `8999991728` o el número. La puerta lo deja en 9 dígitos y
    comprueba el dígito de verificación con el módulo 11 de la DIAN. Si no cuadra, el error dice
    cuál es el correcto.
  - **Siete herramientas pasan de `int` a `nit_entidad`:** las de contratos por entidad, el
    SECOP Integrado, los dos PAA y los dos del SUIT. El esquema acepta texto o número, así que un
    cliente que mandaba el entero sigue igual.
  - **Probado en producción el 2026-11-03:** `899.999.172-8` y `8999991728` dan los 1119 contratos
    de la Alcaldía de Chía en 2026, y `899999172-3` da «el dígito de verificación no cuadra: el de
    899999172 es 8».
  - Los números que empiezan por 1 a 7 (cédulas) siguen fuera (ADR-0014).
- **2026-11-03, el periodo en el nombre del campo** (hallazgo #14 de GEO Copilot):
  `secop_entidades_buscar` v3 devuelve `contratos_desde_2023` y `valor_desde_2023` en vez de
  `contratos` y `valor`. La descripción ya decía la ventana, pero «contratos: 4 298» se leía como
  todos los de la entidad. La descripción también nombra la sigla del IGAC (trampa 6).
- **2026-11-03, filas ordenadas por NIT en el disco** (trampa 7):
  - La copia lleva `orden_fisico: nit_entidad`. Al reconstruirse, CLUSTER deja juntos los contratos
    de cada NIT, y una búsqueda lee pocas páginas aunque nada esté en caché. Lo aprovechan también
    las herramientas que filtran por NIT.
  - Se descartó una tabla aparte de las 5 282 entidades: pide una fuente nueva en el catálogo y
    solo sirve a una herramienta.
  - La copia se reconstruye sola cada día a las 08:00 UTC.
- **2026-11-04, medido con el orden físico.** La copia se reconstruyó a mano a las 04:01 UTC con el
  código desplegado: 3 679 244 filas desde 2023, 263 repetidas en la fuente, en 2354 s. Quedó
  ordenada por `nit_entidad` (índice `…_orden` marcado para CLUSTER). Cada caso se midió una vez y
  luego se repitió; el tope de los canarios es 10 s.

  | Pregunta | Antes | Primera llamada | Repetida |
  |---|---|---|---|
  | `secop_entidades_buscar` «medellin» | 16 s | 4,8 s | 3,4 s |
  | `secop_entidades_buscar` «cali» | — | 4,0 s | — |
  | `secop_contratos_entidad` Cali (890399011) | 15 s | 2,7 s | 1,9 s |
  | `secop_contratos_entidad` Medellín (890905211) | 0,6 s caliente | 6,8 s | 1,2 s |
  | `secop_contratos_entidad` Pitalito (canario) | — | 1,8 s | 5,3 s |

  Pitalito tardó más la segunda vez: el tiempo varía con la carga del servidor.

## Revisión de valor: pagos y origen del dinero (2026-11-04)

- `secop_contrato_por_id` daba `valor_pagado: 0` en el canario, un predio de 2 602 millones
  cerrado en 2023, sin decir nada más. La fuente sí dice más, y se pidió con una sola consulta:
  - `valor_facturado` 0 y `valor_pendiente_de_pago` 2 602 628 368: en SECOP II no se registró
    factura ni pago. Leer solo `valor_pagado` sugería que no se pagó nada.
  - El dinero sale todo de `recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_`;
    el gasto es de inversión y no se sumaron días al plazo.
- Se sumaron a la ficha, con nombre corto: lo facturado, lo pendiente de pago y de ejecución, el
  pago adelantado, los días adicionados, la duración, el destino del gasto, el origen de los
  recursos, el sector, el orden, la categoría UNSPSC y lo que pone cada bolsa (PGN, SGP, SGR,
  recursos propios territoriales, crédito y otros recursos propios). Ninguno es dato personal.
- Siguen fuera el representante legal, el ordenador del gasto, el supervisor, el ordenador de
  pago y la cuenta bancaria.
- Las fechas de la fuente ahora traen hora (`2023-06-26T18:15:18.040`); la ficha las da como
  fecha, igual que antes.
- Un id que no existe (`CO1.PCCNTR.1`) da `no_encontrado` en 4,9 s.

## Revisión de valor: buscar en el texto de una entidad (2026-11-04)

- `secop_contratos_buscar` busca en todo el país. «mantenimiento de vías terciarias» da 1 308
  contratos; salen los 50 más recientes y el aviso pide acotar «por zona, periodo o filtro», pero
  la herramienta solo recibe el texto.
- Nueva `secop_contratos_buscar_entidad` (NIT + texto) sobre la misma copia, que está ordenada por
  `nit_entidad`. Pitalito (891180077) con «mantenimiento vías» da 31 contratos, todos del tema
  (volquetas, material de cantera, maquinaria, apoyo a la meta de vías), sin tope.
- Verdad del canario, medida en la fuente con `like '%MANTENIMIENTO%VÍAS%'` (con y sin tilde)
  desde 2023: 27. La búsqueda pide las palabras en cualquier orden y encuentra 31.
- La dorada solo guarda las filas de empresas (SAS); el total de la copia queda en 31.
