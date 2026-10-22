# ADR-0002 · La puerta llama a los conectores por MCP en red interna

- **Estado:** propuesta.
- **Contexto:** los 12 servicios ya resuelven protocolo, SSRF, tiempos y auth por servicio.
- **Decisión:** la puerta es el único servicio expuesto; los conectores viven en una red interna sin
  puerto publicado y se llaman por MCP con llave de servicio. La puerta no importa código de los
  conectores.
- **Alternativas:** importar los conectores como librería (acopla versiones y procesos, se pierde
  «cada pieza funciona sola»); reescribir los conectores dentro de la puerta (rehace lo validado).
- **Consecuencias:** un salto de red extra (~10–30 ms, a medir); dos contratos (el del conector y
  `rt/1`); la puerta solo enriquece con lo que sabe el catálogo.
- **Confirmación:** prueba de latencia del salto en F0; p95 del salto < 50 ms.
