# Terranova: guía para cada sesión

## Lee primero

1. `docs/ESTADO.md`: dónde estamos y el siguiente paso. **Actualízalo al cerrar cada tarea.**
2. `docs/ROADMAP.md`: la fase actual, sus specs, su aceptación y su gate.
3. Las ADR que toque la tarea (`docs/decisions/`) y la spec correspondiente (`docs/specs/`).
4. Contexto interno, si hace falta (estrategia, comparación con otros servicios, legal):
   `interno/`. No se versiona.

## Qué es

Puerta única (MCP + REST `/v1`) sobre fuentes oficiales colombianas y globales, con el contrato
`rt/1`. Cada respuesta lleva procedencia, licencia, completitud y `servido_desde`. Es open source y
gratuita. Los conectores viven en `../GEO_COPILOT/services/` (repo público
`geoai-latam/geo-copilot`), y GEO Copilot es el primer cliente.

## Reglas del proyecto

- **Idioma:** español en documentos, mensajes de commit, nombres de dominio y herramientas.
- **Repo público:** nada interno ni personal se versiona. Ni secretos, ni datos personales, ni notas
  de estrategia o legales (eso va en `interno/`). Antes de cada commit, revisa
  `git diff --cached --stat`.
- **Por fases con gate:** no se empieza una fase sin cerrar el gate de la anterior. Cada spec se
  cierra con su criterio de aceptación medido, no con «parece que funciona».
- **La puerta no usa LLM** (ADR-0012). La lógica de las fuentes sale del catálogo, no de código
  suelto.
- **Fuentes** (ADR-0018):
  - solo API o bulk publicados y HTML público sin captcha;
  - backends internos solo con permiso escrito registrado en el catálogo;
  - **nunca** captchas, logins ajenos ni retos de identidad.
- **Licencia por ítem** (ADR-0019): sin licencia verificada, una fuente no sale a producción. Si no
  se sabe, se trata como BY-SA.
- **Personas:** sin perfiles ni búsquedas por cédula o nombre (ADR-0014). Lista blanca de campos.
- **Honestidad de estado:** «no encontrado» ≠ «no se pudo»; nunca un dato inventado ni uno viejo
  disfrazado de actual.
- **Pruebas:**
  - Nunca se hace carga contra servidores del Estado.
  - Los canarios usan verdades medidas en la fuente.
  - Las pruebas de juicio de agente usan LLM real (modelo mini para rutina) y cada resultado se
    revisa críticamente, no solo el verde.
  - Lo que toca a GEO Copilot se valida en el navegador.

## Git y GitHub

- Si la cuenta activa de gh no tiene acceso, usa
  `GH_TOKEN=$(gh auth token -u geoai-latam) gh … -R geoai-latam/terranova`. El `git push` ya tiene
  un credential helper local con el token de geoai-latam.
- Trabaja en ramas `feat/…` o `docs/…` y abre un PR. **Fusiona solo con el CI en verde**, mirando los
  checks en un paso aparte, y revisa `git show --stat` antes de `gh pr merge`.
- El autor de los commits es «GeoAI LATAM».

## Entorno

- Windows 11, Git Bash y PowerShell. Python con uv.
- Los conectores se levantan desde `../GEO_COPILOT/docker/docker-compose.yml` (perfil por servicio).
  Las llaves van en `<SVC>_MCP_KEYS` / `<SVC>_MCP_APP_KEY`.

## Gotchas conocidos

- El nombre de la base catastral IGAC en ArcGIS Online cambia cada mes
  (`Base_Catastral_Publica_del_Gestor_IGAC_<MM>_<AAAA>`), así que hay que descubrir el corte
  vigente.
- datos.gov.co: un `count(*)` sin índice sobre SECOP puede pasar de 90 s. Para buscar en texto se
  usa copia.
- `datos_abiertos_mcp` no acepta `$group` (ola 1 lo agrega en GEO Copilot).
- `ogc_mcp` sirve capas del SGC, cuya licencia es restrictiva: quedan fuera del catálogo de
  Terranova.
- GloFAS y ERA5 llegan por Open-Meteo: su API gratis es solo no comercial.
