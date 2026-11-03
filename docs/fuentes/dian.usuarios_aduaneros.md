# DIAN: usuarios aduaneros habilitados (`dian.usuarios_aduaneros`)

El archivo que publica la DIAN con los usuarios que tienen una habilitación aduanera vigente. Se
descubre en la página de Usuarios Aduaneros (`Usuarios-aduaneros-<dd-mm-aaaa>.xlsx`) y se filtra
por NIT. **Uso no comercial:** los términos de la DIAN prohíben los fines de lucro y no conceden
licencia. Solo responde a llaves de evaluación (`excepcion_uso_comercial`, ADR-0007 enmendada);
venderla pide permiso escrito de la DIAN, y esa decisión es del dueño.

## Qué publica

Una fila por habilitación, con:
- NIT y nombre;
- tipo de registro (la calidad aduanera);
- número de registro;
- seccional de aduanas;
- códigos SYGA y MUISCA;
- nombre del área.

Trae unas 140 personas naturales (observadores de importación) con su nombre. La herramienta solo
consulta por NIT de empresa (ADR-0014).

## Tipos medidos (archivo del 28-10-2026, 2 322 habilitaciones)

| Tipo | Filas |
|---|---|
| Sociedad de Comercialización Internacional | 398 |
| Agente de carga internacional marítimo | 363 |
| Usuario Aduanero con Trámite Simplificado | 351 |
| Tránsito Aduanero Nacional | 125 |
| Tránsito Internacional Comunitario | 113 |
| Agencia de Aduanas Nivel 2 | 105 |
| Depósito Público | 92 |
| Transportador Terrestre Régimen Importación Exportación | 80 |
| Usuario Operador de Zona Franca Permanente Especial | 71 |
| … 36 tipos más, de 66 a 1 filas | |

No hay «operador económico autorizado» en el archivo.

## Trampas medidas

1. **No es el directorio de importadores y exportadores.** Alpina (860025900) y Bancolombia
   (890903938) dan «no encontrado» (2026-11-03): no tienen habilitación especial, aunque Alpina
   exporta. Para importar o exportar no hace falta estar aquí. El directorio de importadores y
   exportadores no se publica como archivo.
2. **El archivo «diario» no siempre es de hoy.** El 2026-11-03, el más reciente en la página era el
   del 28-10-2026.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `dian_usuario_aduanero_por_nit` (v2) | medio, no vendible | el vacío dice que no estar aquí no es «no comercia» |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - El aviso de vacío nombra las calidades que sí están y aclara que no aparecer no es «no importa
    ni exporta».
  - Remite a `dian_comex_*`, y dice que esas van por subpartida, no por empresa.
  - La descripción dice lo mismo.
