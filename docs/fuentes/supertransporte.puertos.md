# Supertransporte: tráfico portuario y contenedores (`supertransporte.trafico_portuario`, `supertransporte.contenedores`)

Dos conjuntos de datos.gov.co de la Superintendencia de Transporte, con licencia CC BY-SA 4.0. Se
consultan en vivo. Tienen la misma forma: una fila por zona portuaria, sociedad portuaria, tipo de
carga (o de embalaje) y mes.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `supertransporte.trafico_portuario` | `5r3g-zv5z` | `supertransporte_trafico_portuario` |
| `supertransporte.contenedores` | `7tvr-cx9w` | `supertransporte_contenedores_puerto` |

## Qué publica

- **Tráfico:** toneladas por tipo de tráfico (exportación, importación, transbordo, tránsito
  internacional, cabotaje, fluvial, movilizaciones a bordo y carga transitoria). Unas 9 700 filas
  desde 2018 (perfil del 2026-10-28). La Supertransporte avisa que las cifras son referenciales y se
  corrigen cuando una sociedad retransmite.
- **Contenedores:** TEU llenos o vacíos por tipo de tráfico. Unas 2 800 filas desde 2018.

## Campos que importan

- `zona_portuaria`: 12 zonas sin tildes y abreviadas (CIENAGA, G. MORROSQUILLO, Z.P. RIO MAGDALENA).
- `sociedad_portuaria`: sin tildes, con la Ñ («COMPAÑIA DE PUERTOS ASOCIADOS S.A.»). En el tráfico
  la Ñ llega rota, con el carácter de reemplazo U+FFFD («COMPA�IA»): así lo publica la fuente y así
  sale.
- En contenedores, los tipos de tráfico sin movimiento vienen vacíos, no en cero; en el tráfico,
  ninguna columna de toneladas viene vacía.

## Cobertura

De 2018 al año en curso. Medido el 2026-11-05: en 2026 cada sociedad llega a un mes distinto
(contenedores de Buenaventura: una sociedad hasta julio y otra hasta septiembre; tráfico de Ciénaga,
hasta septiembre).

## Trampas medidas

1. **«Compañía» no encontraba nada** (2026-11-05). La búsqueda solo pasaba a mayúsculas: «Compañía
   de Puertos» en 2025 salía «no encontrado» en las dos herramientas, porque la fuente escribe
   «COMPAÑIA» (sin tilde en la I) y, en el tráfico, «COMPA�IA». Lo mismo con «Ciénaga» frente a
   CIENAGA.
2. **El año en curso parecía completo.** Buenaventura 2026 daba 1 193 518 TEU sin ningún aviso; solo
   `hasta_mes` de cada fila decía que faltaban meses.
3. **El vacío no explicaba nada.** Un año antes de 2018 o un nombre que no existe salían «no
   encontrado» sin aviso.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `supertransporte_trafico_portuario` | alto | toneladas por sociedad y tipo de carga, con el total del año y el último mes |
| `supertransporte_contenedores_puerto` | alto | TEU por sociedad y embalaje, con el total del año y el último mes |

## Decisiones

- **2026-11-05, revisión de valor:**
  - A lo que escribe la persona se le quitan las tildes, y la Ñ (sana o rota) se compara como N a
    los dos lados. «Compañía de Puertos» da 2 grupos en contenedores (161 305 TEU en 2025) y 9 en
    el tráfico; «Ciénaga» encuentra CIENAGA. Al nombre de la fuente solo se le cambia la Ñ: con las
    ocho sustituciones a los dos lados el tráfico llegó a 11 s, por encima del tope del canario.
  - `hasta_mes_anio`: el último mes con datos de la respuesta. Si no llega a diciembre, un aviso
    dice que el total no es el de un año completo y que cada sociedad puede llegar a un mes distinto.
  - El vacío dice que hay datos desde 2018 y cómo buscar la zona o la sociedad.
