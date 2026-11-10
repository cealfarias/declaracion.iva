-- Inventario de conciliación histórica F-07 casilla 164.
-- SOLO LECTURA: no inserta, modifica ni corrige datos; ejecutar tras migraciones.
-- Los importes sin auditoría requieren respaldo real, nunca referencias inventadas.
WITH periodos AS (
    SELECT
        COALESCE(l.id, a.liquidacion_id) AS liquidacion_id,
        COALESCE(l.empresa_id, a.empresa_id) AS empresa_id,
        COALESCE(l.anio, a.anio) AS anio,
        COALESCE(l.mes, a.mes) AS mes,
        l.excedente_impuesto_anterior AS saldo_164,
        a.id AS auditoria_id,
        a.importe AS importe_auditado,
        a.origen,
        a.referencia,
        a.usuario_id,
        a.registrado_en,
        CASE
            WHEN l.id IS NULL AND a.id IS NOT NULL
                THEN 'auditoria_huerfana'
            WHEN a.id IS NOT NULL AND (
                a.empresa_id IS DISTINCT FROM l.empresa_id
                OR a.anio IS DISTINCT FROM l.anio
                OR a.mes IS DISTINCT FROM l.mes
            ) THEN 'periodo_discrepante'
            WHEN l.excedente_impuesto_anterior IS NULL AND a.id IS NULL
                THEN 'sin_saldo'
            WHEN l.excedente_impuesto_anterior IS NOT NULL AND a.id IS NULL
                THEN 'saldo_sin_auditoria'
            WHEN l.excedente_impuesto_anterior IS NULL AND a.id IS NOT NULL
                THEN 'auditoria_sin_saldo'
            WHEN a.importe IS DISTINCT FROM l.excedente_impuesto_anterior
                THEN 'importe_discrepante'
            ELSE 'coincidente'
        END AS estado
    FROM iva_liquidaciones AS l
    FULL OUTER JOIN iva_excedentes_164_auditoria AS a
      ON a.liquidacion_id = l.id
)
SELECT liquidacion_id, empresa_id, anio, mes, saldo_164,
       auditoria_id, importe_auditado, origen, referencia, usuario_id,
       registrado_en, estado
FROM periodos
WHERE estado <> 'sin_saldo'
ORDER BY empresa_id, anio, mes, liquidacion_id;
