# Colombia Compra: convenios interadministrativos de SECOP I y II (`cce.secop.convenios`)

Los contratos que las entidades registraron como convenio interadministrativo en SECOP I y SECOP II
desde el 1 de enero de 2019. Colombia Compra los publica en datos.gov.co (`s484-c9k3`) con licencia
CC BY-SA 4.0. Se consulta en vivo, por el identificador del contrato (constancia de SECOP I o
CO1.PCCNTR.… de SECOP II).

## Qué publica

Una fila por contrato, con:
- identificador del contrato y del proceso;
- entidad, departamento y municipio;
- modalidad y tipo de contrato;
- objeto;
- valor con adiciones;
- contraparte (`contratista`) y su documento;
- fecha de firma, estado y enlace.

## Cobertura

88 850 convenios, medido el 2026-11-03.

## Trampas medidas

1. **No todos son entre entidades públicas.** 3 644 tienen de contraparte una junta de acción
   comunal; el canario es uno (Ortega, Tolima, placa huella con la JAC de la vereda San Nicolás).
   Otras contrapartes no se pudieron clasificar por el nombre: «corporación» incluye a las CAR, que
   son públicas, y hay empresas municipales que son S.A.S.
2. **El tipo de contrato no ayuda.** Lo más común es «Otro» por contratación directa (33 870) y
   «Prestación de Servicios» en «Contratos y convenios con más de dos partes» (22 381).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_convenio_interadministrativo` (v2) | medio → alto | dice que la contraparte no siempre es pública; vacío que remite al contrato |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - La descripción ya no promete «entre entidades públicas» ni «otra entidad». Un aviso, con
    datos, dice que hay convenios con juntas de acción comunal y pide mirar `contratista`.
  - El vacío remite a `secop_contrato_por_id` y a `secop1_proceso_por_constancia`.
  - Medido en producción: el canario (6,6 s en frío), un contrato de SECOP II que no es convenio
    (el PAE de Chía) y un identificador que no existe; los dos vacíos con aviso.
