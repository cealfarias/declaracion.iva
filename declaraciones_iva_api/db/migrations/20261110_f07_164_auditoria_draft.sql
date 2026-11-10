-- Registro de procedencia para la casilla 164.
-- BORRADOR: no ejecutado sobre datos existentes.
-- Solo se aceptan saldos con referencia verificable y origen identificado.
BEGIN;

CREATE TABLE IF NOT EXISTS iva_excedentes_164_auditoria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    liquidacion_id INTEGER NOT NULL REFERENCES iva_liquidaciones(id),
    empresa_id INTEGER NOT NULL REFERENCES iva_empresas(id),
    anio VARCHAR(4) NOT NULL,
    mes VARCHAR(2) NOT NULL,
    importe NUMERIC(18,2) NOT NULL CHECK (importe >= 0),
    origen VARCHAR(32) NOT NULL CHECK (origen IN ('declaracion_previa', 'conciliacion_manual')),
    referencia VARCHAR(250) NOT NULL CHECK (LENGTH(TRIM(referencia)) >= 3),
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_excedentes_164_liquidacion UNIQUE (liquidacion_id),
    CONSTRAINT uq_excedentes_164_empresa_periodo UNIQUE (empresa_id, anio, mes)
);

COMMENT ON TABLE iva_excedentes_164_auditoria IS
  'Trazabilidad inicial de saldos casilla 164; no sustituye conciliación fiscal ni auditoría de cambios.';

COMMIT;
