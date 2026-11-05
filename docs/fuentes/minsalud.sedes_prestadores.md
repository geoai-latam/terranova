# MinSalud (SISPRO): sedes de prestadores de salud

Fuente `minsalud.sedes_prestadores`. Herramientas: `minsalud_sedes_salud_en_zona`,
`minsalud_sedes_salud_municipio` y `minsalud_sedes_salud_buscar`.

## Qué es

El punto de cada sede de un prestador de salud habilitado en el REPS (IPS, hospitales públicos),
como lo publica el visor de Protección Social del SISPRO.

- **Servicio:** capa 2 «Prestadores Salud - IPS - Sede» de
  `sig.sispro.gov.co/arcgis_msp/rest/services/Visor/MPS_Proteccion_Social/FeatureServer`.
- **Tamaño:** 19 913 sedes en la capa; la copia guarda 19 911 (sin las 2 de personas naturales).
  3 422 son de una ESE (hospitales públicos).
- **Corte:** `FechaREPS` va de 2023-03-31 a 2023-08-31, así que el corte tiene unos 26 meses. Las
  herramientas lo dicen.
- **Copia:** va en una copia espacial (ADR-0024).
  - La VPS no llega al SISPRO: no hay respuesta desde el datacenter. Por eso la copia se baja a
    mano desde Colombia.
  - El WAF del SISPRO rechaza los `where` compuestos (paréntesis, `OR`, `IS NULL` juntos). Por eso
    las personas naturales se dejan fuera con `copia.excluir`, que filtra al copiar, y no con un
    `filtro`.
  - No se sondea más: una petición a la vez.

## Licencia

El servicio dice «Propietario: Ministerio de Salud y Protección Social, Publicador: SISPRO» y no
declara licencia (`copyrightText` vacío). Es dato público de una entidad pública: ámbar (enmienda de
la ADR-0019), con aviso. El mismo REPS está en datos.gov.co (`c36g-9fc2`) en CC BY-SA 4.0, pero
esa no es la licencia de este servicio. Pedir la licencia al Ministerio es decisión del dueño.

## Lo medido (2026-11-05)

- **La capa 4 (ESE) está dentro de la 2:** hay 3 422 sedes con `Ese = 1` en la capa 2, el mismo
  número de la capa 4. Solo se copia la 2.
- **`TipoPersona`:** 19 652 jurídicas, 2 naturales y 259 sin dato. Las 2 naturales no se copian
  (ADR-0014).
- **Cómo se ubicó el punto (`MetodoUbicacion`):**
  - 14 624 se geocodificaron por la dirección;
  - 718 se ubicaron a mano;
  - 188 por un sitio de interés;
  - 620 están en el centroide del municipio;
  - 3 763 no traen el dato.

  Las herramientas sacan el método para que un visor no tome un centroide por una sede.
- **`ClaseDePrestador`:** solo trae IPS (1) o vacío. La capa 3, de profesionales independientes, es
  de personas y no se toca.
- **Códigos:** sus significados salen de los dominios del propio servicio (`codigos_norma` los
  cita), no se inventan.
- **`contacto` (campo `URL`):** casi siempre trae un correo del prestador, muchos de gmail, y a veces
  un sitio web.
  - Sale como lo publica el REPS, y no se busca por él.
  - En las doradas del repo va tapado.
- **Fuera de la copia:** NIT, tipo de identificación y teléfono no se copian.
- **Canarios:**
  - 183 sedes en [-74.09, 4.6, -74.06, 4.63], en el centro de Bogotá;
  - 2 en Cubarral (50223), una de ellas la ESE Hospital Local de Cubarral;
  - 68 con «Hospital San Vicente».

## Lo que no trae

- Servicios habilitados y capacidad instalada (camas): eso va por el REPS en datos.gov.co.
- Profesionales independientes (capa 3): son personas.
