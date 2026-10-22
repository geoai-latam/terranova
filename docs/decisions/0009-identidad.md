# ADR-0009 · Identidad

- **Estado:** propuesta.
- **Decisión:** organizaciones con varias llaves; formato `rt_live_<32 bytes>` / `rt_test_…`; se
  muestra una vez; se guarda HMAC-SHA256 con pimienta del servidor; scopes por familia; expiración,
  `ultimo_uso`, revocación inmediata. Solo `Authorization: Bearer`, nunca en la URL. OAuth 2.1 con
  Keycloak (RFC 9728) después de M1, cuando un cliente lo exija; los dos caminos resuelven al mismo
  principal `(org, llave, plan, scopes)`.
- **Confirmación:** pruebas de matriz de permisos y de revocación (< 5 s en surtir efecto).
