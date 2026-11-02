# ADR-0037 · OAuth 2.1 en la propia puerta para los conectores remotos

- **Estado:** aceptada (2026-11-02). Enmienda la [ADR-0009](0009-identidad.md), que proponía Keycloak.
- **Contexto:**
  - claude.ai y la interfaz web de ChatGPT solo conectan un MCP remoto con OAuth. Es el embudo de
    quienes no van a editar un archivo de configuración.
  - Arrancamos en una VPS de 12 GB. Keycloak sumaría un servicio pesado para un solo caso.
  - Cada organización ya tiene llaves, con plan, scopes, saldo y revocación. Un segundo sistema de
    usuarios partiría esa identidad en dos.
- **Decisión:**
  1. **Servidor de autorización mínimo dentro de la puerta,** con el flujo de código y refresco.
     Metadatos por RFC 9728 y RFC 8414, y `WWW-Authenticate` en el 401 de MCP.
  2. **Se autoriza con una llave de Terrnova,** pegada en nuestra página de consentimiento. El cliente
     nunca la ve. El token queda atado a esa llave y hereda plan, scopes, saldo y revocación: los dos
     caminos llegan al mismo principal, como pedía la ADR-0009.
  3. **Sin secretos de cliente, con PKCE S256 obligatorio.** El cliente se identifica con la URL de
     sus metadatos (CIMD) o por registro dinámico (RFC 7591). Ese `client_id` va firmado y lleva sus
     datos, así que registrar no llena ninguna tabla.
  4. **Los tokens solo sirven en MCP** (RFC 8707). Uno de `/mcp` vale en todos los perfiles; el de un
     perfil, solo en ese. La API REST sigue pidiendo llave.
  5. **Acceso de 1 hora y refresco de 30 días que rota.** Reusar un refresco o un código tumba toda la
     familia. Códigos y tokens solo se guardan como HMAC.
  6. **Las URL de redirección se comparan exactas** (en `localhost`, sin el puerto). Solo https, http
     hacia la propia máquina, o el esquema de un editor conocido (`cursor://`, `vscode://`). Una que no
     coincide se muestra como error y no se sigue.
  7. **Al leer metadatos de un cliente no se sale a la red interna:** solo https, sin redirecciones, con
     tope de 16 KB y 3 s, y el nombre debe resolver solo a direcciones públicas.
  8. **Apagado salvo `TERRANOVA_OAUTH=1`:** sin esa variable la puerta se comporta como siempre.
- **Consecuencias:**
  - Quien conecta necesita una llave, aunque sea la de prueba. Entrar con correo y sin llave queda para
    cuando haya cuentas de usuario.
  - Revocar una llave corta sus tokens al instante, y no hay que revocar nada más.
  - Entre comprobar el nombre del cliente y conectar, un DNS que cambie podría apuntar a la red interna.
    El riesgo es bajo porque solo se lee un JSON de 16 KB, sin credenciales y sin devolverlo; si un
    cliente lo justifica, se fija la IP resuelta.
  - No se dio de alta ningún cliente: cualquiera puede pedir autorización, y es la persona con su
    llave quien decide. La página muestra el nombre y a dónde se vuelve.
  - Un refresco reusado no tiene gracia: si se pierde la respuesta del servidor, toca autorizar de
    nuevo. Se prefiere eso a abrir una ventana de reuso.
  - Sin CORS: los clientes que conectan desde el navegador, como el Inspector de MCP, no entran. Se
    suma si alguien lo pide.
  - La aceptación real solo existe tras desplegar: conectar desde claude.ai y ChatGPT.
- **Alternativas descartadas:**
  - Keycloak u otro servicio aparte: demasiado para una VPS y para un caso.
  - Pasar la llave por URL: la ADR-0009 lo prohíbe.
  - Entrar por enlace al correo: exige que todas las llaves tengan un correo verificado, y las de
    organizaciones hechas a mano no lo tienen.
