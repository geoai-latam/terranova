# SECOP II: ubicaciones de ejecución de los contratos (`cce.secop2.ubicaciones`)

Dónde se ejecuta cada contrato de SECOP II, como lo registra la entidad. Está en datos.gov.co
(`gra4-pcp2`), con licencia CC BY-SA 4.0, y se consulta en vivo por contrato.

## Qué publica

6 072 536 filas, una por lugar de ejecución de un contrato. Solo cuatro columnas:

- `id_contrato`;
- `localizaci_n`;
- `nombre_entidad`;
- `nit_entidad`.

La localización es un texto «país; departamento; municipio», con espacios irregulares:

| Localización | Filas |
|---|---|
| «Colombia; Bogotá;  Bogotá» | 943 714 |
| «Colombia; Bogotá» | 834 236 |
| «Colombia;  Valle del Cauca ;  Cali» | 404 421 |
| solo «Colombia» | 123 561 |

## Cobertura

Todos los contratos de SECOP II que registran lugar. No hay dirección ni coordenadas. A veces
falta el municipio, y a veces también el departamento.

## Trampas medidas

1. **La «í» partida.** En UTF-8, «í» es C3 AD. La fuente perdió el C3: queda U+FFFD seguido de un
   guion suave (U+00AD).
   - Pasa en «Medellín» (223 466 filas con «Medell�­n»), «Bolívar» y «Quindío».
   - Las demás tildes llegan bien.
   - Se repara en `sanear`, para toda fuente: ese par nunca es texto.
2. **Bogotá aparece de tres formas:** «Colombia; Bogotá», «Colombia; Bogotá;  Bogotá» y
   «Colombia; Bogotá; Bogotá».
3. **No responde «¿dónde exactamente?».** La revisión de valor la puso en BAJO porque repetía lo
   que ya dice el contrato. Sirve cuando un contrato tiene varios lugares: un PAE en varios
   municipios.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_ubicaciones_contrato` | bajo → medio | v2: `departamento` y `municipio` aparte; aviso de que no hay dirección; aviso de vacío |

## Decisiones

- **2026-11-03, revisión de valor:**
  - `departamento` y `municipio` salen de `localizaci_n` con `patron`. «Colombia; Bogotá» da el
    departamento y deja vacío el municipio.
  - Un aviso con datos dice que SECOP no publica la dirección. El vacío remite a
    `secop_contrato_por_id`.
  - Medido en producción:

    | Contrato | Lugar | Tiempo |
    |---|---|---|
    | CO1.PCCNTR.3795896 (canario) | Cali | 2,2 s |
    | CO1.PCCNTR.7180851 (PAE) | Chía | 1,1 s |
    | CO1.PCCNTR.2445002 | Medellín, con la «í» reparada | 1,4 s |
    | CO1.PCCNTR.1 | `no_encontrado` con aviso | |
