-- Diagnóstico de SOLO LECTURA antes de activar la casilla 164.
-- Ejecutar en la base destino con credenciales de lectura.
-- No aplica migraciones ni corrige registros.
BEGIN READ ONLY;

-- 1. Estado de la columna 164 y su tipo real.
SELECT table_schema, table_name, column_name, data_type,
       numeric_precision, numeric_scale, is_nullable
FROM information_schema.columns
WHERE table_name = 'iva_liquidaciones'
  AND column_name = 'excedente_impuesto_anterior'
ORDER BY table_schema;

-- 2. Duplicados que impedirían identificar un único saldo por período.
SELECT empresa_id, anio, mes, COUNT(*) AS registros,
       ARRAY_AGG(id ORDER BY id) AS ids
FROM iva_liquidaciones
GROUP BY empresa_id, anio, mes
HAVING COUNT(*) > 1
ORDER BY registros DESC, empresa_id, anio, mes;

-- 3. Períodos fuera de formato esperado (sin transformar datos).
SELECT id, empresa_id, anio, mes
FROM iva_liquidaciones
WHERE anio !~ '^[0-9]{4}$'
   OR anio = '0000'
   OR mes !~ '^(0[1-9]|1[0-2])$'
ORDER BY empresa_id, anio, mes, id;

-- 4. Cantidad de períodos por empresa (sin importes personales).
SELECT empresa_id, COUNT(*) AS liquidaciones
FROM iva_liquidaciones
GROUP BY empresa_id
ORDER BY empresa_id;

ROLLBACK;
