# Fuentes: lo que sabemos de cada una

Un archivo por fuente del catálogo (`catalogo/fuentes/<id>.yaml`), con el mismo nombre:
`<id>.md`. Una familia de conjuntos con la misma forma comparte uno, como los once del CNMH.
La ficha YAML dice **cómo** se consulta. Este archivo dice **qué es** la fuente y qué aprendimos
midiéndola. Tiene cinco partes:

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
| SECOP II, garantías (`gjp9-cutm`) | [cce.secop2.garantias.md](cce.secop2.garantias.md) |
| SECOP II, ejecución (`mfmm-jqmq`) | [cce.secop2.ejecucion.md](cce.secop2.ejecucion.md) |
| SECOP II, compromisos (`skc9-met7`) | [cce.secop2.compromisos.md](cce.secop2.compromisos.md) |
| SECOP II, rubros (`cwhv-7fnp`) | [cce.secop2.rubros.md](cce.secop2.rubros.md) |
| CNMH, SIEVCAC: once conjuntos de víctimas por modalidad, con la misma forma | [cnmh.sievcac.md](cnmh.sievcac.md) |
| Supersolidaria, entidades del sector solidario (`kg2d-yfyg`) | [supersolidaria.entidades.md](supersolidaria.entidades.md) |
| INVIMA, Código Único de Medicamentos: cuatro conjuntos, uno por estado | [invima.cum.md](invima.cum.md) |
| Supersociedades: estados financieros NIIF (cinco conjuntos) y las 10 000 empresas | [supersociedades.md](supersociedades.md) |
| Policía Nacional, delitos denunciados (SIEDCO): siete conjuntos con la misma forma | [policia.siedco.md](policia.siedco.md) |
| ANH: producción de crudo y gas, y regalías liquidadas | [anh.md](anh.md) |
| Aerocivil: tráfico origen-destino y operaciones | [aerocivil.md](aerocivil.md) |
| SIC, sanciones en firme de protección al consumidor (`73dx-n59j`) | [sic.sanciones.md](sic.sanciones.md) |
| MinDefensa, homicidios en víctimas (`m8fd-ahd9`) | [mindefensa.homicidios.md](mindefensa.homicidios.md) |
| UPRA, precio comercial de la tierra rural (capa nacional y datos.gov.co) | [upra.precio_tierra.md](upra.precio_tierra.md) |
| Superfinanciera, entidades vigiladas (`sr9n-792w`) | [superfinanciera.vigiladas.md](superfinanciera.vigiladas.md) |
| RUES, empresas y establecimientos (Confecámaras) | [confecamaras.rues.md](confecamaras.rues.md) |
| Función Pública, servidores públicos del SIGEP (`2jzx-383z`) | [funcionpublica.sigep.md](funcionpublica.sigep.md) |
| DANE y DIAN, comercio exterior por subpartida (copias de los microdatos) | [dian.comex.md](dian.comex.md) |
| IDEAM, normales climatológicas (`nsz2-kzcq`) | [ideam.normales_climatologicas.md](ideam.normales_climatologicas.md) |
| ANI, concesiones viales (capa 3 de ANIscopio) | [ani.concesiones_viales.md](ani.concesiones_viales.md) |
| DANE, mercado laboral total nacional (anexo de la GEIH, copia) | [dane.geih_nacional.md](dane.geih_nacional.md) |
| DANE, índice de precios al consumidor (anexo de índices, copia) | [dane.ipc_indices.md](dane.ipc_indices.md) |
| INS, calidad del agua, IRCA (`nxt2-39c3`) | [ins.calidad_agua_irca.md](ins.calidad_agua_irca.md) |
| MinEducación, educación básica y media (municipio, departamento y ETC) | [men.educacion.md](men.educacion.md) |
| DANE, pobreza multidimensional municipal y sus privaciones (censo 2018, copia) | [dane.ipm_municipal_2018.md](dane.ipm_municipal_2018.md) |
| MinTIC, accesos a internet fijo (`hwrp-3su3` y la serie vieja `n48w-gutb`) | [mintic.internet_fijo.md](mintic.internet_fijo.md) |
| Colombia Compra, planes anuales de adquisiciones (SECOP I y II) | [cce.paa.md](cce.paa.md) |
