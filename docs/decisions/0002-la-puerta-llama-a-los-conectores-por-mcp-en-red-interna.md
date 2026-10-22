# ADR-0002 · La puerta llama a los conectores por MCP en red interna

- **Estado:** aceptada (2026-10-21).
- **Contexto:** los 12 servicios ya resuelven protocolo, SSRF, tiempos y auth por servicio.
- **Decisión:** la puerta es el único servicio expuesto; los conectores viven en una red interna sin
  puerto publicado y se llaman por MCP con llave de servicio. La puerta no importa código de los
  conectores.
- **Alternativas:** importar los conectores como librería (acopla versiones y procesos, se pierde
  «cada pieza funciona sola»); reescribir los conectores dentro de la puerta (rehace lo validado).
- **Consecuencias:** un salto de red extra (~10–30 ms, a medir); dos contratos (el del conector y
  `rt/1`); la puerta solo enriquece con lo que sabe el catálogo.
- **Confirmación:** prueba de latencia del salto en F0; p95 del salto < 50 ms.
- **Validación (2026-10-21):** Confirmada en el spike F0.3: salto p95 3,1 ms en loopback, con tope de 50 ms ([informe](../spikes/F0.3-protocolo.md)). Se vuelve a medir en la red de Docker en F2.
