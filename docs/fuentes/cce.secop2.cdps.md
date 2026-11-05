# Colombia Compra: SECOP II, solicitudes de CDP (`cce.secop2.cdps`)

Las solicitudes de certificado de disponibilidad presupuestal (CDP) de los contratos de SECOP II, con
su estado en el SIIF. Colombia Compra las publica en datos.gov.co (`a86w-fh92`) con licencia CC BY-SA
4.0. Se consulta en vivo, por contrato (CO1.PCCNTR.…).

## Qué publica

Una fila por CDP y por proyecto de inversión (BPIN) que financia, con:
- identificador del CDP en el SIIF y BPIN;
- estado en el SIIF;
- destino del gasto;
- saldo del CDP, saldo de vigencias futuras, valor utilizado y saldo por comprometer;
- fecha de consulta al SIIF;
- entidad y contratista, con su documento (ADR-0025).

## Cobertura

10 489 907 filas, medido el 2026-11-03.

## Trampas medidas

1. **El estado es el de la integración con el SIIF Nación.** Medido el 2026-11-03:

   | Estado | Filas |
   |---|---|
   | No iniciado | 7 928 480 |
   | No definido | 1 103 041 |
   | Generado | 973 077 |
   | Con compromiso | 448 988 |
   | Realizado | 36 043 |
   | Cancelado | 278 |

   - «No iniciado» es sobre todo de entidades territoriales, que no usan el SIIF Nación: Gobernación
     de Risaralda (369 193), Departamento de Antioquia (340 631), Cali, distritos y municipios.
   - «Con compromiso» es de entidades nacionales: ANT (49 275), ICA, Agencia de Desarrollo Rural,
     INVIAS.
   - En el PAE de Chía (CO1.PCCNTR.7180851), el estado es «No iniciado», el saldo del CDP es 0, y el
     valor utilizado y el saldo por comprometer valen los dos 64 938 millones, el valor del contrato.
     La revisión de valor lo leyó como «la fuente no está al día», con el contrato pagado al 54 %.
2. **Los saldos no cuadran entre sí.** En el canario (Támesis, CO1.PCCNTR.5588480) el saldo por
   comprometer es 276 963 184, más que el saldo del CDP, 242 025 092.
3. **La fecha de consulta al SIIF viene vacía** en 8 785 287 filas (84 %). Las que la traen van del
   2015-06-11 al 2026-11-02.
4. **Cada CDP se repite por BPIN, y cada par dos veces** (spec 07). La herramienta usa `distinct`.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_cdp_contrato` (v2) | medio | avisa que el estado y los saldos son del SIIF Nación y remite a los pagos; vacío con aviso |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - Un aviso, con datos, dice que el estado y los saldos son de la integración con el SIIF Nación,
    con la distribución medida, y remite a `secop_pagos_contrato` para lo pagado.
  - La fuente tiene aviso de vacío: no tener CDP aquí no quiere decir que el contrato no tenga
    disponibilidad. Remite a `secop_bpin_proceso`.
  - Los campos salen como los publica la fuente: no se recalcula ningún saldo.
  - Medido en producción: el canario (Támesis, 2 filas, 7,3 s en frío), el PAE de Chía (1 fila,
    1,1 s) y un contrato que no existe (vacío con aviso).
- **2026-11-04, revisión de valor (v3):**
  - El CDP de Támesis (CO1.PCCNTR.5588480) sale en dos filas, una por BPIN, ambas con 242 025 092
    de saldo. Se agregaron `cdps` (cuántos certificados distintos hay) y un aviso de que esos
    saldos no se suman.
  - La fuente define `saldo_cdp` como el «CDP generado para el contrato electrónico». En el
    contrato del SENA en Buga (CO1.PCCNTR.6893653), con estado «Con compromiso», el saldo del CDP
    es 1 111 805 062 y el valor utilizado 4 676 667. Ese `id_siif` no está en otro contrato, así
    que no se afirma que el CDP se comparta: se publica como viene.
  - El canario tardó 9,2 s, cerca del tope de 10 s.
