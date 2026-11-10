# Procedimiento de conciliación histórica — casilla 164 (F-07)

**Estado:** desarrollo y validación; no autoriza presentación fiscal ni despliegue.

## Objetivo

Identificar por empresa y período saldos de excedente de impuesto anterior (casilla 164) y comprobar su procedencia documental. Un saldo guardado no es, por sí solo, un saldo fiscalmente validado. La casilla 164 no debe confundirse con el remanente de crédito fiscal (110/155).

## Condiciones previas

1. Disponer de respaldo verificado y de la autorización para operar sobre el ambiente elegido.
2. Ejecutar primero el preflight de solo lectura y revisar duplicados por empresa/año/mes, períodos inválidos y presencia de columna 164.
3. Confirmar, mediante procedimiento separado y aprobado, las migraciones de columna 164, unicidad de período y auditoría. **No se han aplicado a producción como parte de este trabajo.**
4. Con las tablas presentes, ejecutar las consultas de solo lectura:
   - `db/migrations/20261110_f07_164_inventario_historico_readonly.sql`
   - `db/migrations/20261110_f07_164_resumen_historico_readonly.sql`

## Interpretación del inventario

| Estado | Significado | Tratamiento |
| --- | --- | --- |
| `coincidente` | Importe y período coinciden con la auditoría registrada | Revisar documentación y norma; no implica aceptación fiscal automática |
| `saldo_sin_auditoria` | Existe saldo 164, pero no registro de procedencia | Obtener declaración previa o conciliación documentada |
| `auditoria_sin_saldo` | Existe respaldo sin importe en liquidación | Investigar; no asignar cero |
| `importe_discrepante` | Importe auditado distinto del saldo | Bloquear aceptación y revisar fuente original |
| `periodo_discrepante` | Empresa/año/mes no coinciden | Bloquear aceptación; investigar relación de registros |
| `auditoria_huerfana` | Auditoría sin liquidación asociada | Investigar integridad referencial y migración |
| `sin_saldo` | Ni saldo ni auditoría | Se excluye del inventario; no equivale a declaración en cero |

## Criterios para aceptar un período

La aceptación exige **todas** estas condiciones:

- Empresa y período verificados contra la declaración y documentación original.
- Fuente del excedente anterior identificada, con referencia real y verificable.
- Saldo 164 y auditoría coincidentes, sin duplicidad ni inconsistencias.
- Validación normativa de la relación entre casillas 164, 167, 168 y 203, pendiente de completar.
- Revisión fiscal independiente, con evidencia de quién aprobó y cuándo.
- Sin ajustes locales del navegador pendientes de migración o conciliación que afecten el resultado.

**No** se deben inventar referencias, asignar cero a datos ausentes, cambiar saldos históricos en bloque ni marcar períodos como conciliados únicamente por el estado `coincidente`.

## Evidencia de pruebas y límites

La integración CI usa PostgreSQL efímero `f07_ci`, no la base de Render. Las pruebas comprueban la transición de saldo sin auditoría a coincidente y la detección de discrepancias; no sustituyen una revisión fiscal de documentos reales. Los cambios deben seguir en la rama de desarrollo hasta aprobación explícita de despliegue.
