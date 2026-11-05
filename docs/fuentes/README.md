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
| ADRES, afiliados de la BDUA por municipio y EPS (dos regímenes) | [adres.bdua.md](adres.bdua.md) |
| Banco de la República: TRM, tasa de política, IBR, DTF y UVR (SDMX) | [banrep.md](banrep.md) |
| Aerocivil: tráfico origen-destino y operaciones | [aerocivil.md](aerocivil.md) |
| SIC, sanciones en firme de protección al consumidor (`73dx-n59j`) | [sic.sanciones.md](sic.sanciones.md) |
| MinDefensa, homicidios en víctimas (`m8fd-ahd9`) | [mindefensa.homicidios.md](mindefensa.homicidios.md) |
| UPRA, precio comercial de la tierra rural (capa nacional y datos.gov.co) | [upra.precio_tierra.md](upra.precio_tierra.md) |
| IGAC, gestores catastrales de Colombia (`bhcx-bx97`) | [igac.gestores_catastrales.md](igac.gestores_catastrales.md) |
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
| Función Pública, SUIT: trámites inscritos (`dd24-8p6w`) | [funcionpublica.suit.md](funcionpublica.suit.md) |
| CAR Cundinamarca, POMCA (diez cuencas) | [car.pomca.md](car.pomca.md) |
| DANE, crecimiento del PIB trimestral (anexo de producción, copia) | [dane.pib_crecimiento_trimestral.md](dane.pib_crecimiento_trimestral.md) |
| IDEAM, temperatura del aire de las estaciones (`sbwg-7ju4`) | [ideam.temperatura.md](ideam.temperatura.md) |
| PNN, Registro Único Nacional de Áreas Protegidas (RUNAP, copia) | [pnn.runap.md](pnn.runap.md) |
| Colombia Compra, SECOP II pagos y facturas (`uymx-8p3j`, `ibyt-yi2f`) | [cce.secop2.pagos.md](cce.secop2.pagos.md) |
| Presidencia, víctimas de minas, Descontamina Colombia (`yhxn-eqqw`) | [presidencia.victimas_minas.md](presidencia.victimas_minas.md) |
| Corte Constitucional, índice de sentencias (`v2k4-2t8s`) | [corteconstitucional.sentencias.md](corteconstitucional.sentencias.md) |
| MinJusticia, SUIN-Juriscol (`fiev-nid6`) | [minjusticia.suin.md](minjusticia.suin.md) |
| ANT, zonas de reserva campesina constituidas | [ant.zonas_reserva_campesina.md](ant.zonas_reserva_campesina.md) |
| IDEAM, nivel de los ríos en las estaciones automáticas (`bdmn-sqnh`) | [ideam.nivel_rio.md](ideam.nivel_rio.md) |
| SDP Bogotá, POT 555: tratamiento, área de actividad y más (copia) | [sdp.pot555.md](sdp.pot555.md) |
| IDEAM, lluvia de las estaciones automáticas (`s54a-sgyg`) | [ideam.precipitacion.md](ideam.precipitacion.md) |
| IDEAM, calidad del aire del SISAIRE (`g4t8-zkc3`) | [ideam.calidad_aire.md](ideam.calidad_aire.md) |
| ANM, títulos mineros con explotador autorizado en el RUCOM (`42ha-fhvj`) | [anm.titulos_mineros.md](anm.titulos_mineros.md) |
| IDEAM, alertas diarias por deslizamiento e incendios (OSPA) | [ideam.alertas.md](ideam.alertas.md) |
| URT, zonas microfocalizadas para la restitución de tierras | [urt.microzonas.md](urt.microzonas.md) |
| SDP, estrato socioeconómico por manzana en Bogotá | [sdp.estratificacion_manzana.md](sdp.estratificacion_manzana.md) |
| UAECD, valor de referencia del m² de terreno por manzana en Bogotá | [uaecd.valor_referencia.md](uaecd.valor_referencia.md) |
| CREG, gestor normativo (resoluciones) | [creg.gestor_normativo.md](creg.gestor_normativo.md) |
| DIAN, Normograma (compilación jurídica) | [dian.normograma.md](dian.normograma.md) |
| ICFES, Saber 11 (copia agregada por grupos) | [icfes.saber11.md](icfes.saber11.md) |
| CAR Cundinamarca, rondas hídricas delimitadas | [car.rondas_delimitadas.md](car.rondas_delimitadas.md) |
| Corte Constitucional, texto de las sentencias (relatoría) | [corteconstitucional.relatoria.md](corteconstitucional.relatoria.md) |
| Colombia Compra Eficiente, relatoría (conceptos y providencias) | [ancp.relatoria.md](ancp.relatoria.md) |
| SECOP II, ubicaciones de ejecución | [cce.secop2.ubicaciones.md](cce.secop2.ubicaciones.md) |
| Catálogo DCAT de datos.gov.co y de la ICDE (el buscador del catálogo) | [descubrimiento.catalogo_dcat.md](descubrimiento.catalogo_dcat.md) |
| IGAC, catastro: terreno, registro, perímetro, vías, manzana y sector | [igac.catastro.md](igac.catastro.md) |
| IGAC, capacidad de uso de las tierras | [igac.agrologia.capacidad_uso.md](igac.agrologia.capacidad_uso.md) |
| ANT, resguardos indígenas formalizados | [ant.resguardos_indigenas.md](ant.resguardos_indigenas.md) |
| SINCHI, cambio del bosque en la Amazonia 2022-2024 | [sinchi.perdida_bosque.md](sinchi.perdida_bosque.md) |
| ESA WorldCover 2021 | [esa.worldcover.md](esa.worldcover.md) |
| SECOP I y II, multas y sanciones (`4n4q-k399`, `it5q-hg94`) | [cce.multas.md](cce.multas.md) |
| SECOP I, archivos de los procesos (`ps88-5e3v`) | [cce.secop1.archivos.md](cce.secop1.archivos.md) |
| SECOP I, proponentes (`tauh-5jvn`) | [cce.secop1.proponentes.md](cce.secop1.proponentes.md) |
| DIAN, usuarios aduaneros habilitados (archivo de la DIAN) | [dian.usuarios_aduaneros.md](dian.usuarios_aduaneros.md) |
| SECOP II, solicitudes de CDP (`a86w-fh92`) | [cce.secop2.cdps.md](cce.secop2.cdps.md) |
| SECOP I y II, convenios interadministrativos (`s484-c9k3`) | [cce.secop.convenios.md](cce.secop.convenios.md) |
| SECOP II, suspensiones de contratos (`u99c-7mfm`) | [cce.secop2.suspensiones.md](cce.secop2.suspensiones.md) |
| SECOP II, fechas del cronograma (`f3ev-294c`) | [cce.secop2.cronograma.md](cce.secop2.cronograma.md) |
| SECOP I, modificaciones a procesos (`36vw-pbq2`) | [cce.secop1.modificaciones_procesos.md](cce.secop1.modificaciones_procesos.md) |
| SECOP I, modificaciones a adjudicaciones (`u5b4-ae3s`) | [cce.secop1.modificaciones_adjudicaciones.md](cce.secop1.modificaciones_adjudicaciones.md) |
| SECOP I, origen de los recursos (`3xwx-53wt`) | [cce.secop1.origen_recursos.md](cce.secop1.origen_recursos.md) |
| ANI: puertos, aeropuertos y corredores férreos | [ani.modos.md](ani.modos.md) |
| ANI: recaudo mensual de los peajes | [ani.recaudo_peajes.md](ani.recaudo_peajes.md) |
| ANI: tráfico mensual de los peajes | [ani.trafico_peajes.md](ani.trafico_peajes.md) |
| Bogotá: equipamientos de emergencia | [bogota.equipamientos_emergencia.md](bogota.equipamientos_emergencia.md) |
| SECOP Integrado, SECOP I y II (`cce.secop.integrado`) | [cce.secop.integrado.md](cce.secop.integrado.md) |
| SECOP I: adiciones de las adjudicaciones | [cce.secop1.adiciones.md](cce.secop1.adiciones.md) |
| SECOP I: multas y sanciones a contratistas | [cce.secop1.multas.md](cce.secop1.multas.md) |
| SECOP I: planes anuales de adquisiciones | [cce.secop1.paa.md](cce.secop1.paa.md) |
| SECOP I: procesos, vigentes e históricos | [cce.secop1.procesos.md](cce.secop1.procesos.md) |
| SECOP II: el proyecto de inversión (BPIN) de un proceso | [cce.secop2.bpin.md](cce.secop2.bpin.md) |
| SECOP II, procesos de contratación (`cce.secop2.procesos`) | [cce.secop2.procesos.md](cce.secop2.procesos.md) |
| DANE: sedes educativas (SISE) | [dane.sedes_educativas.md](dane.sedes_educativas.md) |
| DNP: proyectos del Sistema General de Regalías | [dnp.proyectos_sgr.md](dnp.proyectos_sgr.md) |
| IDEAM (SIRH): puntos de captación de agua concesionados | [ideam.captaciones.md](ideam.captaciones.md) |
| IGAC: conflictos de uso de las tierras (2012) | [igac.agrologia.conflictos_uso.md](igac.agrologia.conflictos_uso.md) |
| IGAC: infraestructura de la cartografía básica 1:100 000 | [igac.infraestructura_100k.md](igac.infraestructura_100k.md) |
| INVÍAS: tarifas de los peajes | [invias.peajes.md](invias.peajes.md) |
| INVÍAS: puentes de la red vial nacional | [invias.puentes.md](invias.puentes.md) |
| INVÍAS: red vial nacional | [invias.red_vial.md](invias.red_vial.md) |
| MinSalud (SISPRO): sedes de prestadores de salud | [minsalud.sedes_prestadores.md](minsalud.sedes_prestadores.md) |
| NASA FIRMS: focos de calor por periodo | [nasa.firms.md](nasa.firms.md) |
| TransMilenio: estaciones troncales, TransMiCable y trazados troncales | [transmilenio.infraestructura_troncal.md](transmilenio.infraestructura_troncal.md) |
| TransMilenio: paraderos zonales del SITP | [transmilenio.paraderos_zonales.md](transmilenio.paraderos_zonales.md) |
| TransMilenio: servicios (rutas) del SITP | [transmilenio.rutas_sitp.md](transmilenio.rutas_sitp.md) |
| UNGRD: emergencias por municipio | [ungrd.emergencias.md](ungrd.emergencias.md) |
| UPME: infraestructura energética | [upme.infraestructura_energetica.md](upme.infraestructura_energetica.md) |
| USGS: catálogo mundial de sismos | [usgs.sismos.md](usgs.sismos.md) |
