"""Verificación de preparación de migración F-07 164 sin modificar tablas.

El proceso puede ejecutarse antes de aplicar DDL en PostgreSQL.
Se detiene si existen duplicados, fechas inválidas o tipos inesperados.
"""
from sqlalchemy import text


def verificar_preflight_164(db):
    """Devuelve el estado estructural; no hace COMMIT ni modifica datos."""
    dialecto = db.get_bind().dialect.name
    if dialecto != "postgresql":
        raise ValueError("Este preflight exige PostgreSQL; SQLite no sustituye la verificación real.")

    columnas = db.execute(text("""
        SELECT column_name, data_type, numeric_precision, numeric_scale, is_nullable
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'iva_liquidaciones'
          AND column_name = 'excedente_impuesto_anterior'
    """)).mappings().all()
    duplicados = db.execute(text("""
        SELECT empresa_id, anio, mes, COUNT(*) AS registros
        FROM iva_liquidaciones
        GROUP BY empresa_id, anio, mes
        HAVING COUNT(*) > 1
        LIMIT 20
    """)).mappings().all()
    invalidos = db.execute(text("""
        SELECT id, empresa_id, anio, mes
        FROM iva_liquidaciones
        WHERE anio !~ '^[0-9]{4}$'
           OR anio = '0000'
           OR mes !~ '^(0[1-9]|1[0-2])$'
        LIMIT 20
    """)).mappings().all()
    columna = dict(columnas[0]) if len(columnas) == 1 else None
    columna_valida = (
        columna is not None
        and columna["data_type"] == "numeric"
        and columna["numeric_precision"] == 18
        and columna["numeric_scale"] == 2
        and columna["is_nullable"] == "YES"
    )
    return {
        "dialecto": dialecto,
        "columna_164_presente": columna is not None,
        "columna_164_tipo_valido": columna_valida,
        "duplicados": [dict(fila) for fila in duplicados],
        "periodos_invalidos": [dict(fila) for fila in invalidos],
        "apto_para_activar_164": columna_valida and not duplicados and not invalidos,
    }
