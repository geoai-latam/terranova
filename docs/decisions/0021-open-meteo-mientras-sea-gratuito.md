# ADR-0021 · Open-Meteo mientras Terranova sea gratuito

- **Estado:** aceptada (2026-10-21).
- **Contexto:**
  - GloFAS (caudales) y ERA5 (clima) llegan a GEO Copilot por Open-Meteo (`amenazas-mcp`).
  - El API gratis de Open-Meteo es solo para uso no comercial. Sus términos ponen como ejemplo
    válido los «sitios o apps privados o sin ánimo de lucro que no tienen suscripciones ni
    publicidad».
  - El límite del API gratis es de 10 000 llamadas al día, 5 000 por hora y 600 por minuto, contado
    por IP.
  - Los datos que entrega están bajo CC BY 4.0, con un enlace obligatorio a open-meteo.com. ERA5
    exige además la frase «Generated using Copernicus Climate Change Service information».
  - Los términos no dicen nada explícito sobre servir los resultados a terceros desde un servidor.
  - El plan comercial más barato (Standard) no incluye el API histórico (ERA5): eso pide el plan
    Professional.
- **Decisión:**
  - Mientras rija ADR-0020 (gratuito, sin publicidad ni suscripciones), se usa el API gratis.
  - En el catálogo va como `licencia: CC-BY-4.0` y `uso_comercial: no`, porque los términos del API
    son no comerciales. Por ADR-0007 responde con aviso en `procedencia`.
  - Atribución en cada respuesta: el enlace a Open-Meteo y, para ERA5, la frase de Copernicus.
  - Caché obligatoria con TTL largo (las series históricas no cambian) y tope propio por debajo del
    límite, porque toda la puerta sale por una IP. Si se acerca al tope, se responde
    `fuente_no_disponible`, nunca un dato viejo disfrazado de actual.
  - Antes de abrir Terranova al público se pide confirmación escrita a info@open-meteo.com para el uso
    desde un servidor que reparte resultados. El borrador está en `interno/`; lo envía el dueño.
- **Salida (en M2, o antes si cambia ADR-0020 o Open-Meteo dice que no):** ir directo a Copernicus,
  a ERA5 en el CDS y a GloFAS en el EWDS. Así se quita la dependencia no comercial y el límite por IP.
  Pagar Open-Meteo Professional queda como respaldo.
- **Consecuencias:**
  - El clima y los caudales funcionan desde M1 sin costo.
  - Esas fuentes quedan marcadas «no comercial» hasta pasar a Copernicus.
- **Confirmación:**
  - El catálogo declara `uso_comercial: no`, la atribución y el tope.
  - Una prueba verifica el aviso y la atribución en el sobre.
  - La respuesta de Open-Meteo queda registrada en el catálogo.
