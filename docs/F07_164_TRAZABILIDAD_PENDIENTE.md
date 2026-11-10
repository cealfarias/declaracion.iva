# Casilla 164 — procedencia y activación controlada

Estado: **diseño en desarrollo; NO habilitado para producción**.

La casilla 164 se almacena actualmente en `iva_liquidaciones.excedente_impuesto_anterior`.
El endpoint histórico `POST /{empresa_id}/excedente-impuesto-anterior` está bloqueado en la rama de desarrollo (HTTP 409). La nueva escritura auditada requiere origen, referencia documental y usuario autenticado. Los saldos históricos sin respaldo continúan sin aceptación fiscal.

## Requisitos de trazabilidad y aceptación pendientes

El borrador `db/migrations/20261110_f07_164_auditoria_draft.sql`
propone conservar importe, empresa, período, liquidación, tipo de origen,
referencia documental y fecha. Antes de activar el uso fiscal se debe:

1. Verificar coherencia entre empresa/período de la auditoría y la liquidación
   referenciada, mediante lógica transaccional o restricción compuesta.
2. Capturar identidad del usuario autorizado que realiza el registro y
   conservarla como dato de auditoría.
3. Registrar el saldo y su procedencia **en una sola transacción**; no permitir
   registros sin respaldo. Evitar duplicación en reintentos.
4. Resolver el tratamiento de saldos ya almacenados sin referencia; no
   asignarles automáticamente procedencia ni considerarlos conciliados.
5. Verificar con documentación oficial la correspondencia de la casilla 164
   con el período anterior y el arrastre de la 167.
6. Validar migraciones en PostgreSQL efímero, luego preflight sobre la base
   de destino, respaldo, plan de reversión y aprobación explícita.

**No ejecutar la migración de auditoría en producción sin preflight, respaldo, reversión y aprobación explícita.** La implementación en la rama no equivale a aceptación fiscal.

## Implementación parcial en rama de desarrollo (2026-11-10)

- `POST /{empresa_id}/excedente-impuesto-anterior-auditado` registra
  importe, origen, referencia y usuario JWT en una misma transacción.
- El modelo `Excedente164Auditoria` y la migración borrador están en el
  repositorio. La tabla de auditoría debe existir antes de invocar el endpoint.
- La prueba aislada verifica persistencia, rechazo de duplicados y validación
  de referencia; se agregó una prueba adicional de reversión ante error.
- **Resuelto en rama:** el endpoint histórico está bloqueado con HTTP 409.
- **Probado en CI:** pruebas HTTP con JWT real, acceso multiempresa, vínculos archivados y lectura auditada; no se anulan las dependencias de identidad ni autorización.
- **Pendiente:** aceptación fiscal, revisión de compatibilidad con clientes antiguos y migraciones en el entorno definitivo.
- No aplicar migraciones en producción ni habilitar operaciones fiscales
  sin preflight, respaldo, reversión y aprobación expresa.

## Cierre de vía antigua en rama de desarrollo

El endpoint histórico `POST /{empresa_id}/excedente-impuesto-anterior`
ahora responde HTTP 409 sin efectuar escrituras; se preserva la ruta para
informar a los clientes del cambio. El endpoint auditado exige origen y
referencia documental, además de la identidad JWT. Esta decisión **rompe
intencionalmente el contrato de escritura anterior** y requiere validación
de compatibilidad antes de cualquier despliegue. Los saldos históricos
existentes sin auditoría siguen pendientes de conciliación; no se inventan
referencias retrospectivas.

## Inventario y visibilidad (rama de desarrollo)

- `GET /{empresa_id}/excedente-impuesto-anterior-auditoria` exige acceso a la empresa y distingue respaldo coincidente, saldo sin auditoría y ausencia de registro. Devuelve 409 cuando existe discrepancia entre importe guardado y auditoría.
- La pantalla de liquidación muestra origen, referencia, usuario, fecha y estado documental, con advertencia explícita de que la coincidencia **no** equivale a aceptación fiscal.
- `db/migrations/20261110_f07_164_inventario_historico_readonly.sql` y `20261110_f07_164_resumen_historico_readonly.sql` identifican y contabilizan períodos pendientes de revisión sin modificar datos.
- `docs/F07_164_PROCEDIMIENTO_CONCILIACION_HISTORICA.md` define criterios de revisión documental y normativa.
- Las pruebas de PostgreSQL efímero y HTTP han pasado CI hasta el commit `aa2c500`; **no** representan prueba de datos reales, migración en Render ni despliegue.
