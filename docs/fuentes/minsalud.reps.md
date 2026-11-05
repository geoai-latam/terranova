# Ministerio de Salud, REPS en datos.gov.co (`minsalud.reps`)

## Qué publica

- Una fila por sede de prestador habilitado en el Registro Especial de Prestadores de Servicios
  de Salud (REPS), en datos.gov.co (`c36g-9fc2`). Licencia CC BY-SA 4.0.
- El campo `fecha_corte_reps` dice el corte: «Mar 12 2026» en la consulta del 2026-11-05. Es más
  nuevo que el REPS georreferenciado del SISPRO (`minsalud.sedes_prestadores`, corte de 2023), pero
  no trae el punto.

## Campos que importan

- `codigohabilitacionsede` y `codigoprestador`: los códigos de la sede y del prestador.
- `naturalezajuridica` (Privada, Pública), `ese` (SI, NO) y `claseprestador`.
- `tipoid`: Terrnova filtra `NI` (prestadores con NIT). Las personas naturales y los profesionales
  independientes no salen (ADR-0014).

## Trampas medidas (2026-11-05)

1. **«Objeto social diferente» es una clase:** en Chía, 20 de 138 sedes son de entidades cuyo
   objeto no es prestar salud (116 IPS y 2 de transporte de pacientes).
2. Chía tiene una sola sede pública, que es la única ESE. Cubarral (50223), dos sedes: la ESE
   Hospital Local de Cubarral y una privada, igual que en el SISPRO.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `reps_sedes_municipio` (v2) | alto | lista con corte de 2026; ahora con `por_clase`, `por_naturaleza` y `por_ese`, y avisos |

## Decisiones

- **2026-11-05, revisión de valor:** la lista no tenía conteos ni avisos. Se suman los tres
  conteos (los vacíos cuentan como «sin dato», como en el SISPRO), un aviso con el corte y la
  remisión a `minsalud_sedes_salud_municipio` para el punto, y un aviso en el vacío.
