# Aerocivil: tráfico aéreo y operaciones (`aerocivil.*`)

Dos conjuntos de datos.gov.co, publicados por la Aeronáutica Civil con licencia CC BY-SA 4.0. Se
consultan en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `aerocivil.trafico_origen_destino` | `gb6w-ynu4` | `aerocivil_aeropuertos_buscar`, `aerocivil_trafico_aeropuerto` |
| `aerocivil.operaciones` | `jh8x-n6h6` | `aerocivil_operaciones_aeropuerto` |

## Qué publica

- **Tráfico origen-destino:** pasajeros y carga más correo (kg) del transporte comercial por ruta,
  año, mes y tráfico (N nacional, I internacional, E especial). Va desde 2020. Cuenta el viaje, no
  el movimiento físico del aeropuerto: quien conecta en él no se cuenta allí.
- **Operaciones:** llegadas, salidas y toques registrados por las torres de control, desde 2017.
  Incluye vuelos comerciales, aviación general y militares. El aeródromo va por su indicador OACI
  (SKBO, SKRG…).

## Campos que importan

- `origen` / `destino`: la sigla IATA (BOG, MDE). `ciudad_origen` es **el municipio donde está el
  aeropuerto**, no la ciudad a la que sirve.
- `n_mero_de_mes` (tráfico): número. `mes` (operaciones): texto «01», que sale como entero.
- `anio` (operaciones): texto.

## Cobertura

Medido el 2026-11-02:

- **el tráfico llega a junio de 2026** (meses 1 a 6);
- **las operaciones llegan a julio de 2026** (meses 01 a 07).

## Trampas medidas

1. **«Medellín» no daba el aeropuerto de Medellín.** El José María Córdova (MDE) está registrado
   con ciudad «RIONEGRO - ANTIOQUIA». Con «Medellín» salía solo el Olaya Herrera (EOH): 629 741
   pasajeros en 2025, frente a 6 790 249 del MDE. Pasa lo mismo con Apartadó: su aeropuerto (APO)
   está registrado en Carepa.
2. **El año a medias.** Sin decir el corte, MDE en 2026 (6 647 480 pasajeros en 6 meses) parece un
   año malo.
3. **Las demás ciudades grandes no tienen el problema.** Cali, Barranquilla, Bucaramanga y Armenia
   se registran con su nombre, aunque el aeropuerto quede en otro municipio. Los nombres sin tilde
   también encuentran (Montería, Cúcuta): la fuente trae las dos grafías.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `aerocivil_aeropuertos_buscar` | alto | alias Medellín → MDE y Apartadó → APO |
| `aerocivil_trafico_aeropuerto` | alto | da `meses_con_datos` y `hasta_mes`, y avisa si faltan |
| `aerocivil_operaciones_aeropuerto` | alto | igual; `mes` sale como entero |

## Decisiones

- **2026-11-02, errores 9 y 10 de la revisión de valor:**
  - La búsqueda suma dos alias medidos en la fuente, escritos en la consulta. No es una tabla
    general: solo hacía falta para esos dos aeropuertos.
  - Tráfico y operaciones dan `meses_con_datos` (derivado `distintos`) y `hasta_mes`, y avisan
    cuando el año no trae los doce meses.

## Tildes en la búsqueda (2026-11-05)

Desde 2022 la fuente escribe la ciudad con tilde (SAN JOSÉ DE CÚCUTA, IBAGUÉ, BOGOTÁ, D.C.) y antes,
sin ella. «Cucuta» solo encontraba CUC 2020-2021 (698 534 pasajeros) y perdía los 3,5 M de
2022-2026; «Cúcuta» perdía 2020-2021.

- Decisión: se quitan las tildes de las dos columnas en la consulta y del nombre pedido. Las dos
  grafías dan lo mismo, en 2 a 8 s.
- Se descartó `{x:vocales}`, porque el comodín traía ruido: «Pasto» encontraba Pistarini (Ezeiza)
  y Compostela.
- Avisos de vacío en las tres herramientas.
