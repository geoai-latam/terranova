# Colombia Compra Eficiente: planes anuales de adquisiciones (`cce.secop2.paa`, `cce.secop1.paa*`)

Los planes anuales de adquisiciones (PAA): lo que cada entidad pública dice que va a comprar en el
año. Tres conjuntos de datos.gov.co de Colombia Compra Eficiente, con licencia CC BY-SA 4.0. Se
consultan en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `cce.secop2.paa` | `9sue-ezhx` | `secop2_paa_entidad`, `secop2_paa_items` |
| `cce.secop1.paa` | `prdx-nxyp` | `secop1_paa_entidad` |
| `cce.secop1.paa_detalle` | `azeg-sgqg` | `secop1_paa_detalle` |

## Qué publica

- **SECOP II:** cada ítem del plan, con su descripción, mes de inicio, duración, modalidad, origen
  de los recursos, valor estimado y si requiere vigencias futuras. El plan es por entidad (código
  de SECOP) y año, con su versión.
- **SECOP I:** la cabecera del plan (presupuesto, topes de menor y mínima cuantía, versiones) y
  sus ítems por `idpaa`.

## Campos que importan

- **SECOP II:** `fecha_esperada_de_inicio` es solo el mes («Octubre»), del año del plan.
- **SECOP I:**
  - `valor_estimado` es texto, así que se ordena con `::number`;
  - `fecha_inicio` trae mes y año («Octubre 2024»).
- **La modalidad en SECOP I es texto libre.** Medido en todo `azeg-sgqg` el 2026-11-02:
  «CONTRATACIONDIRECTA» (184 908), «CONTRATACION DIRECTA» (40 253), «CONTRATACIN DIRECTA»
  (18 495), «Contratacin Directa» (17 110), «DIRECTA» (16 664)… Hay más de 30 formas para unas
  pocas modalidades. En SECOP II es un vocabulario cerrado.

## Cobertura

El PAA de SECOP II no cambia desde el 2026-09-23, aunque declara actualización diaria. El de
SECOP I llega a 2024.

## Trampas medidas

1. **Un ítem se repite por cada categoría UNSPSC.**
   - Chía 2026: 2 047 filas para 1 814 ítems.
   - Sumar las filas cuenta doble. Agrupando, el total de los ítems de Chía da 555 962 383 288,
     el mismo valor que publica el plan.
2. **El volcado no tenía resumen ni orden.** El `distinct` ordenado no respondía en 300 s. Agrupar
   por todas las columnas, con un `count(*)`, responde en 2 s y deja ordenar por valor.
3. **Los valores de SECOP I los digita la entidad sin revisión.** El plan 2024 de Vergara (352782)
   declara un presupuesto de 12 784 015 387 875 pesos (12,8 billones), y sus 260 ítems suman
   132 782 millones. Su ítem más grande es un acueducto de 115 000 millones.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop2_paa_entidad` | alto | da el código que pide la siguiente |
| `secop2_paa_items` | medio → alto | v2: del más caro al más barato; total planeado y contratación directa arriba; categorías UNSPSC por ítem |
| `secop1_paa_entidad` | medio | sin cambios: llega a 2026 |
| `secop1_paa_detalle` | medio | v2: del más caro al más barato, total planeado, aviso de errores de digitación |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor (volcados sin resumen):**
  - En SECOP II, `items_contratacion_directa` y `valor_contratacion_directa` cuentan
    «CONTRATACION DIRECTA» y «CONTRATACION DIRECTA (CON OFERTAS)». En Chía 2026 son 1 586 de
    1 814 ítems y 107 756 millones.
  - En SECOP I no se resume por modalidad: el texto libre no se deja agrupar sin inventar una
    normalización.
- **2026-11-03, revisión de valor de `secop1_paa_entidad`:** sin cambios. La revisión anotó «llega
  a 2023», pero eso era el canario (Cabuyaro, 2020 a 2023). La fuente tiene planes hasta 2026
  (423 538 filas de ese año, medido el 2026-11-03; datos.gov.co la actualizó ese mismo día), más
  unas pocas filas con años de 2027, 2028 y 2060, digitados por las entidades.

## Revisión de valor (2026-11-04)

- **`secop2_paa_entidad`:**
  - Pitalito 2025 da 3 entidades del NIT (municipio, personería y concejo) y cuadra con el canario.
  - Chía 2026 da 1 814 ítems y 555 962 millones.
  - Pitalito 2019 da la versión 2, con 412 ítems.
  - Los datos salen bien, pero tardaron 37,8 s, 74 s y más de 100 s, contra el tope de 30 s.
- **`secop2_paa_items`:**
  - El canario está bien: 582 ítems, 482 por contratación directa y 35 490 millones.
  - Tardó 32,6 s.
- **Pendiente:** pasar el PAA de SECOP II a copia (o agregar por año en la ingesta). El agrupado en
  vivo de `9sue-ezhx` pasa del tope. El tope no se relaja.
