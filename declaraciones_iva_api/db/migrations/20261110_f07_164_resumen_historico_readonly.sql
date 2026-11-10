-- Resumen por empresa de conciliación histórica F-07 casilla 164.
-- SOLO LECTURA; requiere las migraciones de casilla y auditoría.
-- Incluye únicamente períodos con saldo o auditoría; sin saldo no implica cero.
WITH inventario AS (
    SELECT
        COALESCE(l.empresa_id, a.empresa_id) AS empresa_id,
        CASE
            WHEN l.id IS NULL AND a.id IS NOT NULL THEN 'auditoria_huerfana'
            WHEN a.id IS NOT NULL AND (
                a.empresa_id IS DISTINCT FROM l.empresa_id
                OR a.anio IS DISTINCT FROM l.anio
                OR a.mes IS DISTINCT FROM l.mes
            ) THEN 'periodo_discrepante'
            WHEN l.excedente_impuesto_anterior IS NOT NULL AND a.id IS NULL
                THEN 'saldo_sin_auditoria'
            WHEN l.excedente_impuesto_anterior IS NULL AND a.id IS NOT NULL
                THEN 'auditoria_sin_saldo'
            WHEN a.importe IS DISTINCT FROM l.excedente_impuesto_anterior
                THEN 'importe_discrepante'
            WHEN l.excedente_impuesto_anterior IS NULL AND a.id IS NULL
                THEN 'sin_saldo'
            ELSE 'coincidente'
        END AS estado
    FROM iva_liquidaciones AS l
    FULL OUTER JOIN iva_excedentes_164_auditoria AS a
      ON a.liquidacion_id = l.id
)
SELECT empresa_id,
       COUNT(*) FILTER (WHERE estado <> 'sin_saldo') AS periodos_revisados,
       COUNT(*) FILTER (WHERE estado = 'coincidente') AS coincidentes,
       COUNT(*) FILTER (WHERE estado = 'saldo_sin_auditoria') AS saldos_sin_auditoria,
       COUNT(*) FILTER (WHERE estado = 'auditoria_sin_saldo') AS auditorias_sin_saldo,
       COUNT(*) FILTER (WHERE estado = 'importe_discrepante') AS importes_discrepantes,
       COUNT(*) FILTER (WHERE estado = 'periodo_discrepante') AS periodos_discrepantes,
       COUNT(*) FILTER (WHERE estado = 'auditoria_huerfana') AS auditorias_huerfanas,
       COUNT(*) FILTER (WHERE estado NOT IN ('coincidente', 'sin_saldo')) AS periodos_pendientes_revision
FROM inventario
WHERE estado <> 'sin_saldo'
GROUP BY empresa_id
ORDER BY empresa_id;
