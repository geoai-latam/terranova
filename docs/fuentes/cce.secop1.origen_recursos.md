# Colombia Compra: SECOP I, origen de los recursos (`cce.secop1.origen_recursos`)

De dónde salen los recursos de cada adjudicación de SECOP I: origen, BPIN, año, descripción y valor.
Colombia Compra lo publica en datos.gov.co (`3xwx-53wt`) con licencia CC BY-SA 4.0. Se consulta en
vivo, por el `id_adjudicacion` que da `secop1_proceso_por_constancia`.

## Qué publica

Una fila por fuente de recursos de una adjudicación, con:
- origen (lista cerrada de SECOP I);
- código y año del BPIN;
- descripción libre;
- valor.

## Cobertura

Medido el 2026-11-03, por origen:

| Origen | Filas |
|---|---|
| Recursos propios | 1 823 596 |
| Sistema General de Participaciones - SGP | 1 284 879 |
| Recursos Propios (Alcaldías, Gobernaciones y Resguardos Indígenas) | 863 849 |
| Otros recursos | 783 949 |
| Presupuesto General de la Nación – PGN | 431 358 |
| Sistema General de Regalías - SGR | 68 070 |
| Recursos de crédito | 26 471 |

## Trampas medidas

1. **«Otros recursos» no siempre es otro.** De sus 783 949 filas, 185 338 dicen «propios» en la
   descripción y 89 320 hablan del SGP. La adjudicación 10878821 está en «Otros recursos» con la
   descripción «SGP FUCIONAMIENTO».
2. **Hay dos orígenes para lo propio**: «Recursos propios» y «Recursos Propios (Alcaldías,
   Gobernaciones y Resguardos Indígenas)».
3. **El BPIN puede venir vacío de hecho**: en los dos casos probados dice «No Definido», con año
   «N/D».

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop1_origen_recursos_adjudicacion` (v2) | medio | avisa que «Otros recursos» esconde propios y SGP |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - El origen sale como lo publica la fuente. Un aviso, con datos, pide leer la descripción antes de
    sumar por origen.
  - La lentitud de la revisión (14,7 s) no se repitió: el canario tardó 1,3 s y una adjudicación en
    frío (10878821) 1,2 s en producción; la fuente responde en 0,5 s. El tope del canario (20 s) no
    se toca.
  - Medido en producción: el canario, la 10878821 y una adjudicación que no existe (vacío).
