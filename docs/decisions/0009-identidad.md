# ADR-0009 · Identidad

- **Estado:** aceptada (2026-10-21).
- **Decisión:** organizaciones con varias llaves; formato `rt_live_<32 bytes>` / `rt_test_…`; se
  muestra una vez; se guarda HMAC-SHA256 con pimienta del servidor; scopes por familia; expiración,
  `ultimo_uso`, revocación inmediata. Solo `Authorization: Bearer`, nunca en la URL. OAuth 2.1 con
  Keycloak (RFC 9728) después de M1, cuando un cliente lo exija; los dos caminos resuelven al mismo
  principal `(org, llave, plan, scopes)`.
- **Confirmación:** pruebas de matriz de permisos y de revocación (< 5 s en surtir efecto).
- **Validación (2026-10-21):** Sin conflictos. HMAC con pimienta en lugar de solo sha256 (lo que hace hoy geo_mcp_kit) es lo correcto para llaves públicas. Se prueba en F3.
