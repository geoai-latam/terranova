# Runbook de operación (F7.3)

Qué hacer ante los cuatro incidentes de la spec F7.3. Cada procedimiento dice cómo se nota, qué se
revisa, qué se hace y cómo se confirma que quedó resuelto. Los comandos suponen el compose de
`docker/` en la VM (ADR-0015):

```sh
C="docker compose -f docker/compose.yml --env-file docker/.env"
```

Al cerrar cualquier incidente, se anota en el registro (§5) con la fecha, qué pasó y qué se cambió.

## 1. Fuente caída

**Cómo se nota.** Canario rojo con `fuente_no_disponible` o `fuente_lenta` (alerta por
`TERRANOVA_ALERTA_URL`), `GET /v1/estado` con la fuente en `rojo`, la alerta `CircuitoAbierto` de
Prometheus o respuestas `parcial` en la ficha.

**Qué hace la puerta sola.** Tras 3 fallas seguidas, el cortacircuitos de esa fuente se abre 30 s y
responde `fuente_no_disponible` en menos de 1 s, sin tocarla. Si hay copia en caché, sirve
`obsoleto` con su `consultado_en` original y un aviso (ADR-0008). Las demás fuentes siguen normales.

**Qué revisar.**

1. ¿Es la fuente o el conector? `$C logs --since 30m arcgis-mcp` y la página pública de la fuente.
   Si el conector está caído, `$C restart arcgis-mcp`.
2. ¿Es de la fuente? Se prueba una sola vez la URL del catálogo (`catalogo/fuentes/<id>.yaml`),
   nunca en bucle: **no se hace carga contra servidores del Estado**.

**Qué hacer.** Si la fuente está caída, se espera. No se apaga la herramienta ni se inventa un dato.
Si la caída pasa de un día, se agrega a la ficha de la fuente una nota en `avisos` y se publica en
el estado.

**Cómo confirmar.** `uv run terranova canarios` (o el siguiente ciclo del servicio) da verde y
`/v1/estado` vuelve a `verde`.

## 2. Cambio de esquema en la fuente

**Cómo se nota.**

- Canario rojo con `esquema_cambiado`: un campo de `canario.campos` ya no llega. La lista blanca
  deja fuera, sin error, un campo que la fuente renombró o quitó.
- Canario rojo con `verdad_distinta`, si cambió un valor o su formato.
- `fuente_respuesta_invalida`: la respuesta no tiene la forma esperada.
- En IGAC: el corte mensual de la base catastral cambia de nombre
  (`Base_Catastral_Publica_del_Gestor_IGAC_<MM>_<AAAA>`). `uv run scripts/corte_igac.py` dice cuál es el
  vigente; con `--escribir` actualiza las fichas (luego se regraban las doradas).

**Qué revisar.** El detalle del canario (`/v1/estado`) dice qué campo falta. Se compara la respuesta
actual del conector con la grabada en `tests/doradas/<herramienta>.json`.

**Qué hacer.**

1. En una rama `feat/…`, se ajusta el mapeo `campos:` de `catalogo/fuentes/<id>.yaml`: el nombre
   nuevo en la fuente, apuntando al **mismo** nombre `rt/1`, para que el contrato no cambie para
   quien llama.
2. Si cambió el sentido del dato y no solo su nombre, se versiona la herramienta (`@2`) en lugar de
   cambiarla en silencio.
3. Se vuelve a grabar la dorada (`uv run scripts/grabar_doradas.py <herramienta>`), que hace **una**
   llamada por canario, y después `uv run scripts/campos_canario.py`.
4. `make check` y PR. Se fusiona con el CI en verde.

**Cómo confirmar.** El canario de esa herramienta vuelve a verde en vivo.

## 3. Llave filtrada

**Cómo se nota.** La llave aparece en un repositorio, un log o un mensaje; gitleaks la detecta; o hay
consumo anómalo (panel «Créditos por nivel» de Grafana; por organización, la tabla `eventos`) o un
`ultimo_uso` reciente en una llave que no debería usarse.

**Qué hacer, en este orden.**

1. **Revocar ya**: `$C exec puerta-a terranova llaves revocar llv_…`. Surte efecto en la siguiente
   petición, en las dos réplicas (E2E-03: 401 en menos de 5 s).
2. Crear la llave de reemplazo para la organización (`terranova llaves crear --org … --scopes …`) y
   entregarla por un canal privado. Nunca por correo en claro ni en la URL.
3. Revisar el uso de la llave filtrada: `terranova llaves listar --org …` (`ultimo_uso`) y los
   eventos de la tabla `eventos` desde la fecha de la filtración.
4. Si se filtró la **pimienta** (`TERRANOVA_PIMIENTA`) o la llave de servicio de los conectores, el
   incidente es mayor:
   - Una pimienta nueva invalida **todas** las llaves. Se avisa a las organizaciones y se emiten de
     nuevo.
   - La llave de servicio se cambia en `docker/.env` y en los conectores, y se reinicia.
5. Si la llave quedó en un repositorio público, se borra del historial **después** de revocarla. La
   revocación es lo que protege; borrar solo oculta.

**Cómo confirmar.** Una petición con la llave revocada da 401 por REST y por MCP. La de reemplazo
funciona.

## 4. Restauración de un respaldo

**Respaldos.** El servicio `respaldo` del compose deja un `pg_dump -Fc` diario en
`TERRANOVA_RESPALDOS` (por defecto `docker/respaldos/`) y conserva 14 días. Esa carpeta **se copia
fuera de la VM**: una copia en la misma máquina no sobrevive a la pérdida de la máquina. En la base
están las llaves, la medición de uso, los canarios, el dataset curado y las copias. Los dos últimos
también se reconstruyen desde las fuentes: `scripts/dataset_restricciones.py --postgis` y
`terranova copias actualizar`.

**Cuándo.** Pérdida del volumen de Postgres, una VM nueva o datos corrompidos.

**Qué hacer.**

1. Detener lo que escribe en la base: `$C stop puerta-a puerta-b canarios respaldo`.
2. Elegir el respaldo más reciente y sano. `pg_restore -l <archivo>` lista su contenido sin
   restaurar.
3. Con Postgres vacío y arriba (`$C up -d postgres`), restaurar:

   ```sh
   $C exec -T postgres pg_restore -U terranova -d terranova --clean --if-exists --no-owner \
     < docker/respaldos/terranova-AAAAMMDDTHHMMZ.dump
   ```

4. Levantar la puerta: `$C up -d puerta-a puerta-b canarios respaldo`.

**Cómo confirmar.** Los conteos de `llaves`, `eventos`, `canarios` y `curado.restricciones` coinciden
con los anteriores al incidente. Una llave existente responde 200. `GET /v1/estado` muestra el
historial de canarios. Lo que pasó entre el último respaldo y el incidente se pierde y se anota.

## 5. Registro de simulacros e incidentes

| Fecha | Procedimiento | Resultado |
|---|---|---|
| 2026-10-22 | §2 Cambio de esquema (en prueba) | `tests/test_vigilancia.py`: la fuente renombra `CODIGO_ANTERIOR`; la verdad del canario sigue igual y el canario sale `esquema_cambiado` señalando `codigo_vereda_anterior` |
| 2026-10-22 | §4 Restauración (compose local) | El servicio `respaldo` generó el dump al arrancar (87 MB). Se restauró en un Postgres nuevo, como en una VM recién creada, en 15 s y sin errores: 1 llave, 1 evento, 2955 filas curadas y su versión, iguales al original. Una puerta sobre esa base respondió 200 con la llave existente y 401 sin llave |
| 2026-10-22 | §1 Fuente caída (compose local) | Con `arcgis-mcp` detenido: `fuente_no_disponible` (502) en 3–6 s las primeras veces; con el circuito abierto, en 0,2 s y sin tocar la fuente. `rt_circuito_abierto{fuente="igac.catastro.terreno"} 1` en las dos réplicas (cada una lleva su circuito); `/metrics` da 404 desde afuera. Lo que estaba en caché siguió respondiendo 200. Los canarios salieron rojos, la alerta llegó al webhook con el detalle y `/v1/estado` mostró las fuentes en rojo. Al levantar el conector, la primera 200 llegó a los 10 s y la otra réplica se recuperó al terminar su enfriamiento (30 s). Hubo un 502 de cuerpo vacío durante la recuperación que no se repitió y que Caddy no registró |
| 2026-10-22 | §3 Llave filtrada (compose local) | Tras `llaves revocar`, 401 por REST y por MCP en las dos réplicas a los 1,07 s, contando las propias pruebas (meta: < 5 s). `llaves listar` mostró el `ultimo_uso` de la llave |

**Lecciones de los simulacros.**

- El compose solo traía `arcgis-mcp`: los 10 canarios de amenazas, DANE, datos abiertos e imágenes
  habrían salido rojos para siempre en la VM. Ya están los cinco conectores.
- Una imagen vieja de un conector convirtió un tiempo agotado (`fuente_lenta`) en `error_interno`:
  le faltaba el código de error del kit. **Al desplegar, las imágenes de los conectores se
  construyen desde `main` de geo-copilot**, no se reutilizan las que haya en la máquina.

## 6. Alertas: cómo llegan y cómo probarlas

Prometheus evalúa las reglas de `docker/observabilidad/reglas.yml` y manda lo que dispara a
Alertmanager, que lo envía por Telegram al dueño. El destino va en el `.env` del servidor:

- `ALERTAS_TELEGRAM_TOKEN`: el token del bot (de @BotFather);
- `ALERTAS_TELEGRAM_CHAT`: el chat que recibe (el id del dueño o de un grupo).

Sin las dos, Alertmanager arranca igual y avisa en su log que las alertas no llegan a nadie.

**Simulacro** (después de cada cambio de destino, y anotarlo en la sección 5):

```bash
cd /opt/terranova/docker
docker compose --profile observabilidad up -d alertmanager prometheus
docker compose exec alertmanager amtool alert add Simulacro severidad=baja \
  --annotation=resumen="Simulacro: si esto llega, las alertas llegan" \
  --alertmanager.url=http://localhost:9093
```

El mensaje llega en menos de un minuto. Si no llega: `docker compose logs alertmanager` (token o
chat mal puestos, o el bot no tiene permiso de escribir en el grupo).

Prometheus guarda 400 días de historia: alcanza para medir el SLA de cualquier mes del año.
