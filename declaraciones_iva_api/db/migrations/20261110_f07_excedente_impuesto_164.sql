-- F-07 v14: preparación NO EJECUTADA de persistencia de casilla 164.
-- Aplicar únicamente después de respaldar, revisar datos y aprobar la migración.
-- NULL significa "no conciliado", distinto de 0.00.
-- No cambia datos históricos, no calcula arrastres ni publica a producción.
BEGIN;

ALTER TABLE iva_liquidaciones
  ADD COLUMN IF NOT EXISTS excedente_impuesto_anterior NUMERIC(18,2);

COMMENT ON COLUMN iva_liquidaciones.excedente_impuesto_anterior IS
  'Casilla 164 F-07: saldo previo de excedente de impuesto; NULL = sin conciliación.';

COMMIT;
