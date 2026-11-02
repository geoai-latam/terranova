# Fuentes: lo que sabemos de cada una

Un archivo por fuente del catálogo (`catalogo/fuentes/<id>.yaml`), con el mismo nombre:
`<id>.md`. La ficha YAML dice **cómo** se consulta. Este archivo dice **qué es** la fuente y qué
aprendimos midiéndola. Tiene cinco partes:

1. **Qué publica:** la unidad de cada fila, quién la produce y con qué frecuencia.
2. **Campos que importan:** lo que significan de verdad, no lo que dice su nombre.
3. **Cobertura:** qué años, lugares y entidades hay, y qué falta.
4. **Trampas medidas:** cada una con el caso real, la fecha y la cifra medida en la fuente.
5. **Decisiones:** qué hace Terrnova con cada trampa, y en qué PR.

Reglas:
- Solo se escribe lo medido en la fuente, con fecha. Si algo no se midió, se dice «sin medir».
- Cada herramienta que usa la fuente aparece con su estado de valor (alto, medio o bajo) y lo que
  le falta.
- Se actualiza en el mismo PR que cambia la ficha o la herramienta.
- Datos públicos y decisiones técnicas, nada más: la estrategia y lo legal van en `interno/`.

| Fuente | Archivo |
|---|---|
| SECOP II, contratos (`jbjy-vk9h`) | [cce.secop2.contratos.md](cce.secop2.contratos.md) |
| SECOP II, modificaciones (`u8cx-r425`), con su hermano «adiciones» (`cb9c-h8sn`) | [cce.secop2.modificaciones.md](cce.secop2.modificaciones.md) |
| SECOP II, proponentes (`hgi6-6wh3`) | [cce.secop2.proponentes.md](cce.secop2.proponentes.md) |
