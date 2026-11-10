-- F-07: borrador de restricción de integridad, NO EJECUTADO.
-- Requiere preflight sin duplicados y aprobación antes de aplicar.
-- Previene dos liquidaciones para la misma empresa/año/mes.
-- IMPORTANTE: no resuelve por sí solo la concurrencia de escritura en 164.
BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM iva_liquidaciones
        GROUP BY empresa_id, anio, mes
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Existen liquidaciones duplicadas: revisar preflight antes de crear índice único';
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_iva_liquidaciones_empresa_periodo
    ON iva_liquidaciones (empresa_id, anio, mes);

COMMIT;
