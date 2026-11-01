# ADR-0034 · Llave de prueba con correo verificado y formulario de contacto propio

- **Estado:** aceptada (2026-10-31). Enmienda la [ADR-0009](0009-identidad.md) en el alta:
  la llave se crea sin intervención, pero solo con un correo verificado.
- **Contexto:**
  - La auditoría integral del 2026-10-31 encontró que el embudo convierte cero. Todo botón de alta
    terminaba en un correo a `soporte@`, el dominio no tenía MX y la llave se creaba a mano por SSH.
  - El dueño pidió el alta en 15 días, con un correo de por medio y pocos créditos: «no podemos
    dejarlo tan libre». Se descartó el acceso sin llave.
  - Los filtros de correo (Outlook, Gmail, antivirus) abren los enlaces para revisarlos. Si la llave
    se creara con solo abrir el enlace, la gastaría el filtro.
- **Decisión:**
  1. **Alta:** el formulario de `/precios#empezar` hace `POST /v1/alta` con nombre, correo,
     organización y uso, y la aceptación de la política de privacidad. Responde siempre lo mismo,
     exista o no el correo, para no revelar quién tiene llave.
  2. **Enlace de un solo uso** que vence en 24 h, guardado como HMAC con la pimienta del servidor.
     Abrirlo (`GET /v1/alta/confirmar`) solo muestra un botón. La llave se crea al confirmar
     (`POST`) y se muestra **una sola vez**, con `Cache-Control: no-store`. Nunca va por correo.
  3. **Una llave por correo.** Si ya tiene una, el correo lo dice y remite a soporte. Dos enlaces
     del mismo correo dan una sola llave.
  4. **Llave de prueba:** nivel `prueba`, con pocos créditos al mes (`NIVELES["prueba"]`, hoy 300),
     todas las familias y vencimiento a 15 días (decisión del dueño del 2026-11-01). El plan Gratis y los de pago se piden a soporte.
  5. **Topes:** cinco altas y diez mensajes de contacto por hora por IP. De la IP solo se guarda su
     HMAC. Los correos desechables más usados no reciben llave. Un campo trampa oculto descarta los
     robots sin captcha.
  6. **Contacto:** `POST /v1/contacto` guarda el mensaje en la base y lo reenvía a soporte.
  7. **Correo saliente** por SMTP con TLS (`TERRANOVA_SMTP_URL`, `TERRANOVA_CORREO_DE`). Sin él, el
     alta responde que no está disponible y remite a soporte; el contacto se guarda igual.
  8. Las rutas no van en el OpenAPI (`include_in_schema=False`): no son de la API de datos, y así
     Schemathesis no las ejercita.
- **Consecuencias:**
  - Una persona tiene llave en dos minutos sin que el dueño haga nada.
  - Hace falta un proveedor de correo saliente con SPF y DKIM del dominio. Es pendiente del dueño.
  - Se guardan datos personales: nombre, correo, organización y mensajes. La política de privacidad
    lo dice, y la revisión legal debe confirmarlo.
  - OAuth (claude.ai, ChatGPT, directorios de conectores) sigue pendiente. Llegará con su propia ADR
    sobre las mismas organizaciones.
