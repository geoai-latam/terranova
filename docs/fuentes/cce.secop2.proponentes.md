# SECOP II, proponentes por proceso (`cce.secop2.proponentes`)

Conjunto `hgi6-6wh3` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0,
verificada el 2026-10-22. Se consulta en vivo y se actualiza a diario.

## Qué publica

Una fila por proponente en una fase de un proceso de SECOP II. Trae la fase (`id_procedimiento`,
`CO1.REQ.…`), el nombre del procedimiento, la entidad compradora y su NIT, el proponente y su
documento (de divulgación obligatoria, ADR-0025), y la fecha de publicación.

Las columnas son 9: `codigo_entidad`, `codigo_proveedor`, `entidad_compradora`,
`fecha_publicaci_n`, `id_procedimiento`, `nit_entidad`, `nit_proveedor`, `nombre_procedimiento` y
`proveedor`.

## Campos que importan

- `id_procedimiento`: **solo la fase** (`CO1.REQ`). No trae el proceso de compra (`CO1.BDOS`), que
  es lo que entrega cada contrato en `proceso_de_compra`. Para pasar de uno a otro hay que ir a
  procesos (`p6dx-8zbt`), con `id_del_portafolio` → `id_del_proceso`.
- `proveedor`: tiene letras dañadas en la fuente. «UNIÓN TEMPORAL … ACCIÓN» llega como
  «UNIoN TEMPORAL … ACCIoN».

## Cobertura

- Las fases que reciben ofertas. Un proceso de compra puede tener varias fases, y los proponentes
  suelen estar en la de oferta:
  - el de Pitalito (CO1.BDOS.2898382) tiene CO1.REQ.2978420 y CO1.REQ.3004001, y su único
    proponente está en la segunda;
  - el PAE de Chía (CO1.BDOS.7088717) tiene «Presentación de observaciones» (CO1.REQ.7226140, sin
    respuestas) y «Presentación de oferta» (CO1.REQ.7304794, un proponente).
- Las fases se llaman de muchas formas. Medido en procesos el 2026-11-02: «Presentación de oferta»
  (8,2 M), «Fase de ofertas» (870 549), «Presentación de observaciones» (161 774), sin fase
  (88 965), «Manifestación de interés (Menor Cuantía)» (67 142) y otras, algunas en inglés
  («Clarification submission», «Estimate Phase»).

## Trampas medidas

1. **El id del contrato no sirve tal cual.** Con el `CO1.BDOS` del contrato la herramienta decía
   «no encontrado», y el agente concluía que nadie se presentó. Medido el 2026-11-02 con el PAE de
   Chía: una licitación pública de 64 938 millones con **un solo proponente**, la Unión Temporal
   Avanzando y Nutriendo en Acción. Es justo lo que un veedor busca.
2. **Lo lento es la primera llamada.** En producción, la primera llamada en frío tardó 12-21 s y las
   siguientes, unos 3 s. En la fuente, cada consulta tarda ~0,5 s (una en frío llegó a 7,3 s).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_proponentes_proceso` (v2) | alto | acepta el `CO1.BDOS` del contrato o la fase `CO1.REQ`. Una consulta previa a procesos la traduce a sus fases |

## Decisiones

- **2026-11-02:**
  - El motor suma la consulta `previa`: va primero a otro conjunto y pasa sus valores a la
    consulta principal como lista SoQL.
  - Solo entran los valores que cumplen el patrón `id_secop`: lo que venga de la fuente no entra
    crudo a la consulta.
  - Sin fases, la lista es `''` y la respuesta es «no encontrado».
  - La procedencia lista las dos fuentes.
- **2026-11-02, patrón A:**
  - Con un solo proponente, la respuesta avisa que en una licitación, una selección abreviada o un
    concurso eso quiere decir que no hubo competencia, y que en contratación directa es lo normal.
  - El vacío explica las dos causas posibles.
- **Pendiente:** saber la modalidad sin otra llamada, para avisar solo en las competitivas.
