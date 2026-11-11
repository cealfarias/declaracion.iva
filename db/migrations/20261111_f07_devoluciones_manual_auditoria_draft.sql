-- BORRADOR F-07: ejecutar únicamente tras revisión y preflight en entorno aislado.
-- No modifica importes DTE 05 ni liquidaciones; almacena propuestas documentadas.
-- La interpretación sustitución/adición está pendiente de aprobación tributaria.
BEGIN;

CREATE TABLE IF NOT EXISTS iva_devoluciones_manual_auditoria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES iva_empresas(id),
    usuario_id INTEGER NOT NULL REFERENCES iva_usuarios(id),
    anio VARCHAR(4) NOT NULL,
    mes VARCHAR(2) NOT NULL,
    version_dte INTEGER NOT NULL DEFAULT 1,
    neto NUMERIC(18,2) NOT NULL,
    credito NUMERIC(18,2) NOT NULL,
    referencia VARCHAR(250) NOT NULL,
    motivo VARCHAR(500) NOT NULL,
    estado VARCHAR(24) NOT NULL DEFAULT 'pendiente_conciliacion',
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_iva_devoluciones_manual_anio CHECK (anio ~ '^[0-9]{4}$'),
    CONSTRAINT ck_iva_devoluciones_manual_mes CHECK (mes ~ '^(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_iva_devoluciones_manual_version CHECK (version_dte >= 1),
    CONSTRAINT ck_iva_devoluciones_manual_neto CHECK (neto >= 0),
    CONSTRAINT ck_iva_devoluciones_manual_credito CHECK (credito >= 0),
    CONSTRAINT ck_iva_devoluciones_manual_referencia CHECK (length(btrim(referencia)) BETWEEN 3 AND 250),
    CONSTRAINT ck_iva_devoluciones_manual_motivo CHECK (length(btrim(motivo)) BETWEEN 5 AND 500),
    CONSTRAINT ck_iva_devoluciones_manual_estado CHECK (estado = 'pendiente_conciliacion')
);

CREATE INDEX IF NOT EXISTS ix_iva_devoluciones_manual_empresa_periodo
    ON iva_devoluciones_manual_auditoria (empresa_id, anio, mes, version_dte, registrado_en);

COMMENT ON TABLE iva_devoluciones_manual_auditoria IS
    'Borrador de registro documental de devoluciones manuales: no sumar ni sustituir DTE 05 automáticamente.';

COMMIT;
