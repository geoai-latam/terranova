# Spec 12 · Monitores sobre las copias

*2026-11-02.* Desarrolla la [ADR-0036](../decisions/0036-monitores-sobre-copias.md). **No se implementa
hasta que un piloto lo pida.** Esta spec fija el alcance para no improvisarlo entonces.

## Qué se puede vigilar

Una herramienta cuya fuente sea `modo: copia`, con sus argumentos. Ejemplo: contratos nuevos de una
entidad en SECOP. Queda fuera:

- cualquier herramienta en vivo;
- las que traigan datos de una persona natural como criterio (ADR-0014);
- las de valor único sin clave, como un agregado por municipio: no tienen «filas nuevas».

Cada fuente vigilable declara `monitores: true` en el catálogo, y su clave debe ser única según el perfil
(spec 07). Una clave que no es única no sirve para decir qué entró.

## API

Todo bajo `/v1`, con la llave de la organización. Errores RFC 9457, como el resto.

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/v1/monitores` | Crea: `herramienta`, `argumentos`, `destino`. Devuelve el secreto una sola vez |
| GET | `/v1/monitores` | Lista los de la organización, con su última evaluación |
| DELETE | `/v1/monitores/{id}` | Lo borra |
| POST | `/v1/monitores/{id}/probar` | Manda un aviso de prueba, sin datos |

Un monitor se crea desde REST, no desde MCP: un agente no debería dejar procesos corriendo por su cuenta.

## Evaluación

1. El job de copias termina un refresco correcto y queda una versión nueva.
2. Para cada monitor de esa fuente, se ejecuta su consulta sobre la versión nueva y sobre la anterior.
3. Las filas nuevas son las claves de la nueva que no estaban en la anterior.
4. Sin filas nuevas no se manda nada. Con filas nuevas se encola un aviso.

Una versión `repetida`, igual a la anterior, no evalúa nada. La primera evaluación solo fija el punto de
partida.

**Tope:** si las filas nuevas pasan de 1 000 o del 20 % de la copia, el aviso no lleva filas: dice que la
fuente cambió en bloque y cuántas son. Esos números se ajustan con datos reales.

## Aviso

```json
{
  "monitor": "mon_…",
  "herramienta": "secop_contratos_entidad",
  "copia": {"fuente": "…", "actualizada_en": "…", "version": "…"},
  "filas_nuevas": 3,
  "elementos": [],
  "licencia": "…",
  "atribucion": "…"
}
```

- `elementos` lleva la lista blanca de la herramienta, nada más.
- `X-Terrnova-Firma` es el HMAC-SHA256 del cuerpo con el secreto del monitor.
- Hasta 5 reintentos con espera creciente. Tras 3 días de fallos el monitor se pausa, y `GET` lo muestra.
- Si la copia está vencida no hay aviso, pero `GET` muestra de cuándo fue la última evaluación.

## Datos

`monitores` (id, org, herramienta, argumentos, destino, secreto cifrado, estado, última evaluación) y
`monitores_avisos` (monitor, versión, filas, estado de entrega, intentos). El contenido de `argumentos`
puede ser sensible para el cliente: no va a los registros.

## Aceptación

- Un monitor sobre una copia real avisa las filas que entraron entre dos versiones, y coinciden con una
  comparación hecha a mano.
- Una versión repetida no manda nada.
- El refresco no hace ninguna llamada de más a la fuente por tener monitores.
- Un destino caído no frena ni el refresco ni los demás monitores.
- Una firma alterada se detecta con el ejemplo de la documentación.
- Borrar la organización o el monitor corta los avisos.
