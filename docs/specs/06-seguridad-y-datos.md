# Seguridad, licencias y datos de personas

## 13.1 Seguridad (OWASP MCP Top 10)

| Riesgo | Control |
|---|---|
| Secretos expuestos | llaves en HMAC con pimienta; secretos de fuentes solo en el servidor; escaneo de secretos con prefijo `rt_` |
| Alcance excesivo | scopes por familia; mínimo privilegio |
| Envenenamiento de herramientas | descripciones generadas del catálogo y revisadas; pinning de esquemas en snapshot |
| Inyección por datos | saneamiento, largo máximo, texto solo en `datos`, lista blanca de campos |
| SSRF | la puerta **no acepta URLs**: solo fuentes del catálogo; los conectores mantienen su pinning |
| Autenticación débil | Bearer obligatorio; sin llaves en la URL; revocación inmediata |
| Falta de auditoría | evento por solicitud con `solicitud_id`, org, herramienta, huella |
| Multitenencia | org solo desde la credencial; RLS en tablas de uso y llaves; caché compartida solo para datos públicos |
| Reenvío de tokens | prohibido; la puerta usa sus propias llaves hacia los conectores |

## 13.2 Licencias

Compuerta de ADR-0007; atribución en cada respuesta; términos de servicio sin restricciones sobre lo
BY/BY-SA; salidas derivadas de fuentes BY-SA marcadas BY-SA.

## 13.3 Datos de personas

| Clase | Ejemplos | Regla |
|---|---|---|
| Persona como **parte de un registro público** buscada por número | radicado, SPOA, queja SFC, contrato SECOP por id | dentro |
| Persona en **divulgación obligatoria** | contratistas SECOP, accionistas SIMEV, comerciantes RUES | dentro, sin teléfonos ni correos, cédulas enmascaradas por defecto, **sin perfiles que crucen fuentes** sin finalidad declarada |
| **Boletines oficiales negativos** | BRF Contraloría, BDME | dudosa: desde el boletín publicado, con finalidad registrada; se decide con asesoría legal |
| Búsqueda **por nombre o documento de una persona** | Rama Judicial por nombre, Procuraduría, SIMIT, SICAAC | fuera del MVP; sería otro producto (KYC) |
| **Sensibles, prohibidos o con reto de identidad** | antecedentes de Policía (sus términos lo prohíben), RUAF, ADRES, Sisbén, RUNT por persona, registro civil | fuera |
| **Credenciales del usuario** | DIAN MUISCA y facturación, bancos | fuera |

Si algún día se abre la línea de personas, hace falta todo esto: rol de encargado por contrato,
política de tratamiento, oficial de datos, RNBD si aplica, campo de finalidad por consulta,
auditoría inmutable, sin caché, reglas de la Ley 1266 para el dato negativo, solo canales oficiales
por convenio (ANI, RUNT) y póliza.
