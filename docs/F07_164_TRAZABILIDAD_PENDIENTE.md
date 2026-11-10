# Casilla 164 — procedencia y activación controlada

Estado: **diseño en desarrollo; NO habilitado para producción**.

La casilla 164 se almacena actualmente en `iva_liquidaciones.excedente_impuesto_anterior`.
El endpoint `POST /{empresa_id}/excedente-impuesto-anterior` registra importes
no negativos y evita sobrescribir un valor previamente almacenado. **Aún no
exige ni persiste documento de respaldo**; por tanto, el registro existente
no constituye una conciliación fiscal auditada.

## Diseño de trazabilidad pendiente de integración

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

**No ejecutar la migración de auditoría ni activar su escritura todavía**.
El diseño no equivale a implementación ni aprobación fiscal.

## Implementación parcial en rama de desarrollo (2026-11-10)

- `POST /{empresa_id}/excedente-impuesto-anterior-auditado` registra
  importe, origen, referencia y usuario JWT en una misma transacción.
- El modelo `Excedente164Auditoria` y la migración borrador están en el
  repositorio. La tabla de auditoría debe existir antes de invocar el endpoint.
- La prueba aislada verifica persistencia, rechazo de duplicados y validación
  de referencia; se agregó una prueba adicional de reversión ante error.
- **Bloqueante:** el endpoint histórico
  `POST /{empresa_id}/excedente-impuesto-anterior` sigue aceptando
  importes sin respaldo. No declarar obligatoria la trazabilidad hasta
  deshabilitarlo o migrarlo de forma compatible con los clientes existentes.
- **Bloqueante:** comprobar que las autorizaciones de empresa y el usuario
  JWT se apliquen en pruebas HTTP reales sin anular dependencias.
- No aplicar migraciones en producción ni habilitar operaciones fiscales
  sin preflight, respaldo, reversión y aprobación expresa.
