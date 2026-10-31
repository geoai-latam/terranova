# ADR-0029 · De gratuito a freemium de pago

- **Estado:** aceptada (2026-10-27). **Reemplaza:** ADR-0020 (gratuito al inicio). **Enmienda:**
  ADR-0010 (el saldo agotado pasa de 429 a 402).
- **Contexto:**
  - Terrnova es un producto comercial (ADR-0001 enmendada) y tiene que sostenerse con ingresos.
  - El servicio comparable más cercano ya cobra por lo mismo (API y MCP sobre datos oficiales) con
    créditos mensuales: gratis para empezar, planes por volumen y un plan gratuito para gobierno.
  - El medidor, la identidad por llave y el saldo mensual ya existen (ADR-0009, ADR-0010). Falta el
    cobro, que se hace fuera de la puerta.
- **Decisión:**
  1. **Freemium de pago.** Un nivel gratis y planes de pago por saldo mensual de créditos. Se cobra
     el servicio (acceso, mantenimiento de las fuentes, caché, procedencia), nunca el dato: el dato
     conserva la licencia de su fuente (ADR-0019).
  2. **Niveles** (`NIVELES` en `src/terranova/cuota.py`, créditos al mes):

     | Nivel | Créditos al mes | Para |
     |---|---|---|
     | `con_llave` | 1.500 | gratis, para probar |
     | `basico` | 25.000 | plan de pago |
     | `pro` | 110.000 | plan de pago |
     | `empresa` | 375.000 | plan de pago |
     | `escala` | 1.100.000 | plan de pago |
     | `ampliado` | 200.000 | entidades públicas, academia y uso interno, a pedido |

     Los precios no viven en el código ni en el repo: los fija el negocio y los cobra la pasarela.
     Un volumen mayor va por contrato.
  3. **El saldo se renueva el día 1 de cada mes (UTC) y no se acumula.** Lo no gastado se pierde.
     En un plan anual el saldo llega mes a mes. Las fallas, la caché y `fuera_de_cobertura` siguen
     sin descontar (ADR-0010).
  4. **Saldo agotado: 402 `saldo_agotado`**, con `Retry-After` hasta el reinicio. El mensaje dice
     la fecha de reinicio y, si `TERRANOVA_URL_PLANES` está definida, dónde subir de plan, igual
     por REST y por MCP (ADR-0004). **429 queda solo para la tasa** (`limite_tasa`), que un cliente
     sí debe reintentar. `GET /v1/uso` dice el saldo y la fecha de reinicio (`reinicia`).
  5. **El cobro vive fuera de la puerta.** Un servicio comercial registra al cliente y cobra. La
     puerta solo sabe el nivel de cada organización: `terranova orgs nivel <org> <nivel>`. La falta
     de pago baja la organización a `con_llave`; no revoca sus llaves.
  6. **Sin excedentes por ahora.** Al agotar el saldo se sube de plan o se espera al reinicio. El
     cobro por consumo o los paquetes adicionales se deciden aparte.
- **Consecuencias:**
  - Reaparecen los términos de servicio, la facturación y la atención al cliente que la ADR-0020
    había evitado. Los términos son requisito antes del primer cobro.
  - **Licencias:** una fuente sin uso comercial (`uso_comercial: no`, como Open-Meteo) sigue
    diciendo «sin uso comercial» en cada respuesta. Hay que decidir si sale de los planes de pago o
    se paga su plan comercial (ADR-0021). Las fuentes con términos ambiguos (DANE) necesitan base
    legal escrita antes de venderlas.
  - **Antes de desplegar el nuevo gratis** hay que pasar a `ampliado` las organizaciones internas
    (clientes propios, pruebas y evaluación). `terranova orgs listar` muestra las que no tienen
    nivel fijado y quedarían con 1.500 créditos.
  - Un cliente que reintenta a ciegas ante 429 no debe hacerlo ante 402: es un error de saldo, no
    de tasa.
- **Alternativas descartadas:**
  - Seguir gratis (ADR-0020): no sostiene el producto.
  - Cobrar por el dato: va contra las licencias abiertas de las fuentes.
  - Cobro por consulta sin planes: la cuenta del cliente se vuelve impredecible y obliga a facturar
    por uso desde el primer día.
