# ADR-0036 · Monitores sobre las copias: avisar lo nuevo sin consultar al Estado

- **Estado:** aceptada (2026-11-02). Se implementa cuando un piloto lo pida. Sigue a la
  [ADR-0024](0024-conector-de-copia.md) y respeta la [ADR-0014](0014-datos-de-personas.md).
- **Contexto:**
  - Hoy Terrnova solo contesta cuando le preguntan. Quien vigila contratos o licencias tiene que
    repetir la consulta y comparar por su cuenta. Los monitores son la mayor brecha funcional frente
    a Croma.
  - Vigilar repitiendo consultas en vivo sería carga contra servidores del Estado, y esa regla no
    se negocia.
  - 27 fuentes ya tienen copia, y `AlmacenCopias.podar` conserva las dos últimas versiones de cada
    una: comparar entre refrescos no pide datos nuevos.
- **Decisión:**
  1. **Un monitor es una consulta guardada:** una herramienta servida por copia, sus argumentos y un
     destino. Pasa por la misma validación que una llamada normal.
  2. **Se evalúa después de cada refresco de la copia, no por reloj.** No toca la fuente: compara las
     dos versiones que ya están en PostGIS.
  3. **Se avisa lo que entró, por la clave de la copia.** Primero solo filas nuevas. Las filas cambiadas
     y las que salieron quedan para cuando alguien las pida, porque muchas fuentes reescriben columnas
     sin que cambie el fondo.
  4. **Sin personas:** no hay monitores por cédula ni por nombre de una persona natural. La lista blanca
     de campos también rige en el aviso.
  5. **Entrega por webhook HTTPS firmado** (HMAC con un secreto por monitor), con reintentos. El correo
     viene después si un piloto lo necesita.
  6. **Cada aviso dice de cuándo es la copia.** Un monitor es tan fresco como su copia, y hay copias que
     se refrescan a mano: nunca se presenta como tiempo real.
  7. **Se cobra por aviso con filas nuevas, no por evaluación.** El número de monitores por plan y los
     créditos se fijan con el primer piloto.
- **Consecuencias:**
  - Una fuente en vivo necesita copia antes de poder vigilarse.
  - La primera evaluación no avisa nada: fija el punto de partida.
  - Un refresco que falla no dispara avisos, y un monitor sobre una copia vencida debe decirlo.
  - Si una versión reescribe la clave de muchas filas, un aviso enorme sería falso. La spec le pone tope.
- **Alternativas descartadas:**
  - Evaluar en vivo por reloj: es carga contra el Estado.
  - Enviar la versión completa y dejar que el cliente compare: traslada el trabajo y no da valor.
  - Avisar por MCP: un agente no está escuchando entre sesiones.
