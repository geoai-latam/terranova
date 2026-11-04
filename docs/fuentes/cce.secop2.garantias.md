# SECOP II, garantías (`cce.secop2.garantias`)

Conjunto `gjp9-cutm` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0. Se consulta en vivo.

## Qué publica

Una fila por póliza de un contrato de SECOP II: aseguradora, número, tipo y subtipo de póliza,
valor, estado y fechas de creación, envío y fin.

Columnas (medido el 2026-11-02): `id_contrato`, `aseguradora`, `numeropoliza`, `asegurado`,
`beneficiario`, `fechadecreacionpoliza`, `fechaenviopoliza`, `fechafinpoliza`, `ladopoliza`,
`estado`, `tipopoliza`, `subtipopoliza`, `valor` y `fecha_de_creacion`.

## Cobertura

- **Casi nada.** Medido el 2026-11-02: 48 949 pólizas de 22 081 contratos, creadas entre el
  2020-12-15 y el 2026-10-25. En ese periodo SECOP II tiene unos 4,9 millones de contratos
  firmados (desde 2021). La cobertura es menor al 0,5 %.
- El PAE de Chía (CO1.PCCNTR.7180851, 64 938 millones) no tiene ninguna póliza publicada, aunque
  una licitación de ese tamaño exige garantía.

## Trampas medidas

1. **El vacío no es «no hay garantía».** Antes salía «no encontrado» sin más, y se leía como un
   contrato sin póliza.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_garantias_contrato` | medio | contesta cuando hay datos. Desde el 2026-11-02, el vacío lleva el aviso de cobertura (`cobertura.aviso_vacio`) |

## Decisiones

- **2026-11-02:** `cobertura.aviso_vacio` con la cobertura medida. El motor lo pone en cada «no
  encontrado» de la fuente (patrón A de la revisión de valor).
- **2026-11-03, revisión de valor:** verificado en producción con el PAE de Chía
  (CO1.PCCNTR.7180851): el vacío sale con el aviso de cobertura. Sin más cambios.
