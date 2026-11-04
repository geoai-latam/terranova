# Colombia Compra: SECOP I, archivos de los procesos (`cce.secop1.archivos`)

Los documentos que una entidad sube a un proceso de SECOP I: plan anual, certificado BPIN, ficha
MGA, CDP, estudios previos, pliegos, actas. Colombia Compra los publica en datos.gov.co (`ps88-5e3v`)
con licencia CC BY-SA 4.0. Se consulta en vivo, por la constancia del proceso (aa-n-nnnnnn).

## Qué publica

Una fila por documento, con:
- constancia;
- identificador;
- nombre del archivo y título;
- descripción (lo que es: «PAA», «CERTIFICADO BPIN», «FICHA MGA»);
- tipo MIME y extensión;
- fecha de creación;
- enlace de descarga.

`usuario_creacion` y `usuario_ultima_modificacion` no salen: son personas (ADR-0014).

## Trampas medidas

1. **El enlace es una IP sin dominio y sin cifrado.**
   - Es `http://20.96.127.85/descarga/<id>`, como lo publica la fuente.
   - El 2026-11-03 respondió 200 por HTTP (141 708 bytes). Por HTTPS no responde.
   - Algunos navegadores y clientes bloquean las descargas por HTTP.
2. **El tipo de la descarga es genérico.** Llega como `application/octet-stream`. El nombre sí
   viene, en `Content-Disposition` (`DA_PROCESO_26-21-55446_218150011_140159118.pdf`). La extensión
   confiable es la del campo `extension`.
3. **No se puede recorrer todo el conjunto.** Un conteo con un filtro sobre la URL, en todo
   `ps88-5e3v`, devolvió 403 (2026-11-03). Se consulta solo por constancia.

Medido el 2026-11-03: el canario (26-21-55446, PUC n.º 20) tiene 36 documentos; el 2026-10-22
eran 32.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop1_documentos_proceso` (v2) | alto | avisa que el enlace es HTTP a una IP |

## Decisiones

- **2026-11-03, revisión de valor:**
  - El enlace se entrega como lo publica la fuente: no se reescribe a HTTPS, porque no responde.
  - La descripción y un aviso dicen que es una IP sin cifrado, y de dónde sacar la extensión.

## Revisión de valor (2026-11-04)

- **Probado en producción:** el canario (26-21-55446, 36 documentos) y una constancia inventada
  (vacío, que no decía nada).
- **Hallazgo:** el `titulo` es la etiqueta del almacenamiento de SECOP I («Nuevo Sistema de
  Almacenamiento de Archivos PUC NO.18/19/20»), igual en casi todos. Se midió en 8 filas de la
  fuente al azar. Lo que dice qué es cada documento es la `descripcion`: estudios previos,
  evaluación, CDP, ficha MGA.
- **Arreglo:**
  - La descripción de la herramienta y la de los dos campos lo dicen.
  - Se agregó un aviso en el vacío.
