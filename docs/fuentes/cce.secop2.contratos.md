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

- `nit_entidad`: el NIT **sin** dígito de verificación. No identifica a una sola entidad (ver
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

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_contratos_entidad` | alto desde #242 | agrupa por año **y entidad**, de lo más reciente a lo más viejo, con `ultima_firma`. Antes salía todo a nombre de la Personería (trampa 1) |
| `secop_contratos_entidad_anio` | alto | ya agrupaba por entidad. Pide el NIT como entero |
| `secop_contratos_municipio` | medio | el aviso «la fuente no dijo cuántos elementos» sale sin sentido en una suma; no da el rango de años; mete los empréstitos (trampa 4) |
| `secop_entidades_buscar` | alto, lenta | 15,9 s pese al índice de #241 (sin medir si el índice se usa). Da el NIT como texto |
| `secop_entidades_municipio` | alto | da el NIT como número |
| `secop_contratos_proveedor` | alto | |
| `secop_contratos_buscar` | alto | |
| `secop_contrato_por_id` | alto | entrega `id_proceso` como BDOS, que la herramienta de proponentes no acepta (en arreglo) |

## Decisiones

- **#242 (2026-11-02):** `secop_contratos_entidad` agrupa por `nombre_entidad`, ordena con
  `anio DESC NULL LAST` y agrega `ultima_firma`. El canario vigila que la primera fila de Pitalito
  sea del Municipio.
- **Pendiente:** aceptar el NIT como texto o como número en toda la familia (hoy unas herramientas
  lo piden entero y otras lo dan como texto).
