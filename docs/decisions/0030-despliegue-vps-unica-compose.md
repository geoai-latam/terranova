# ADR-0030 · Despliegue en una VPS única con Docker Compose (no nube gestionada) para el arranque

- **Estado:** aceptada (2026-10-27). Validación: decisión del dueño tras comparar costos; el
  `docker compose` de despliegue ya existe (F3.7) y no requiere re-arquitectura.
- **Contexto:**
  - Terranova es un servicio **stateful y always-on** (puerta con sesiones MCP persistentes, Postgres
    con las copias y pgvector, Redis, conectores, jobs de copia/descubrimiento por lotes que bajan
    ~1,5 GB), de **carga baja y predecible** mientras no haya clientes.
  - La puerta **no usa LLM** ([ADR-0012](0012-la-puerta-no-usa-llm.md)) y los embeddings corren en **CPU
    local**: no hay factura de inferencia. El costo variable es casi cero; el costo real es «una caja
    encendida 24/7».
  - El objetivo de esta fase es **minimizar el costo fijo** hasta conseguir clientes
    ([ADR-0020](0020-gratuito-al-inicio.md)).
  - Comparación de costos medida (oct 2026), para specs equivalentes (≈8 vCPU / 24 GB):
    - **VPS única (Contabo/Netcup):** ~$8–23/mes, con **tráfico ilimitado**.
    - **Nube grande, una sola VM** (EC2/Azure VM): ~$130–245/mes on-demand (≈10–18×).
    - **Nube grande, separado/gestionado** (VM + Postgres + Redis + LB + NAT): ~$280–400+/mes (≈20–30×).
    - Causas: la VM cloud cuesta ~10–15× por las mismas specs, el **egreso** se cobra (~$0,09/GB) y cada
      servicio gestionado tiene piso mínimo + HA que no se necesita aún.
- **Decisión:** desplegar **todo el `docker compose` en una sola VPS**, sin servicios gestionados.
  - **Proveedor y plan:** **Contabo Cloud VPS 6** — 6 vCPU, **12 GB RAM**, 200 GB SSD, 300 Mbit/s,
    tráfico ilimitado; **región Unión Europea**; **Ubuntu 24.04 LTS**; contrato 12 meses.
  - **Sin gestionados:** Postgres y Redis en contenedor; sin balanceador de pago (**Caddy** con
    Let's Encrypt); observabilidad (Prometheus/Grafana) solo local, no en la nube.
  - **Ajustes del compose a 12 GB:** **1 réplica** de la puerta (la 2.ª réplica y la HA esperan a una
    segunda máquina); Redis con `maxmemory`; jobs de copia y de re-embebida del catálogo
    **secuenciales y de madrugada**, sin solaparse (el re-embed completo —ADR-0028— no corre a la vez
    que una copia grande); `mem_limit` por servicio (auditoría WS5). En 12 GB entran MiniLM **y**
    e5-large (el modelo vive en su propio contenedor, ~2–3 GB FP32 / ~1–1,5 GB cuantizado).
  - **Respaldo:** **sin** Auto Backup del proveedor. Lo único irremplazable es la base de **identidad**
    (llaves, orgs, consumo), diminuta: se respalda con `pg_dump` a **Backblaze B2** (off-site, ~$1/mes,
    servicio `respaldo` del compose). Las **copias de datos no se respaldan**: se re-ingieren desde las
    fuentes públicas.
  - **Dominio:** **`terrnova.com`** (nombre público; `terranova` ya está tomado) vía Cloudflare
    (registro a costo + DNS); TLS por Caddy.
  - **Datos operativos** (IP, credenciales, cuenta del proveedor) van en `interno/`, **nunca
    versionados**.
- **Consecuencias:**
  - Costo de arranque ≈ **$9/mes** todo incluido (VPS $7,65 + ~$1 B2); **costo marginal por cliente ≈ 0**
    mientras el tráfico quepa en la VPS.
  - **Punto único de fallo** (una sola VPS): aceptable antes de tener SLA con clientes. La resiliencia
    de proceso la dan el reinicio de contenedores y el cortacircuitos por fuente; la del host, no.
  - El **rendimiento de Contabo es menos consistente** (nodos compartidos, soporte más lento):
    aceptable pre-clientes. Se reevalúa mover la puerta a Netcup/Hetzner cuando haya clientes con SLA.
  - Migrar de plan en Contabo implica reinstalar/migrar (no es en caliente): subir a 24 GB, si hace
    falta por e5-large o carga, es una tarea futura planificada.
- **Alternativas descartadas:**
  - **Hetzner:** era la más barata, pero en 2026 subió precios dos veces y los planes ARM baratos (CAX)
    aparecen no ordenables; descartada para el arranque.
  - **Netcup:** más fiable, pero más caro por GB (VPS 2000, 16 GB, ≈€22,62/mes).
  - **Nube gestionada (AWS/Azure):** 10–30× más cara (VM y egreso). **Excepción:** si se obtienen
    **créditos de startup** (AWS Activate / Microsoft for Startups), reevaluar — saldría «gratis» 1–2 años.
  - **Vercel/serverless:** modelo equivocado para una puerta stateful always-on (límites de ejecución,
    sin BD propia). Sirve para **GEO Copilot** (el cliente/frontend), no para la puerta.
- **Pendiente del dueño (para el cobro, [borrador ADR-0029 freemium]):** los microdatos del DANE se
  declaran **CC BY-SA 4.0** en datos.gov.co (permite uso comercial), pero los términos generales del
  portal DANE mencionan no-comercialización; si esa cláusula alcanza a terceros reutilizadores es
  ambiguo. Irrelevante mientras Terranova sea gratis; **verificar antes de activar cobro**.
