"""Integración F-07 164 contra PostgreSQL efímero de CI.

No usa la base Render. Requiere F07_TEST_DATABASE_URL, exclusivamente de prueba.
"""
import os
from pathlib import Path
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.preflight_f07_164 import verificar_preflight_164
from app.models.models import Empresa, Liquidacion


@pytest.mark.skipif(
    not os.getenv("F07_TEST_DATABASE_URL"),
    reason="Solo se ejecuta con PostgreSQL efímero de CI",
)
def test_migracion_164_y_unicidad_en_postgresql():
    url = os.environ["F07_TEST_DATABASE_URL"]
    assert url.startswith(("postgresql://", "postgresql+psycopg2://"))
    # Solo se admite la base de datos temporal dedicada a esta prueba.
    from sqlalchemy.engine import make_url
    parsed = make_url(url)
    assert parsed.database == "f07_ci", "Se prohíbe ejecutar sobre otra base de datos."

    engine = create_engine(url)
    raiz = Path(__file__).resolve().parents[1]
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS f07_ci_test"))
        conn.execute(text("SET search_path TO f07_ci_test"))
        Empresa.__table__.create(conn, checkfirst=True)
        # Crear esquema anterior sin la columna 164 para probar migración real.
        # Crear todas las columnas heredadas que el ORM necesita;
        # retirar únicamente la nueva columna para reproducir la migración.
        Liquidacion.__table__.create(conn, checkfirst=True)
        conn.execute(text(
            "ALTER TABLE iva_liquidaciones DROP COLUMN excedente_impuesto_anterior"
        ))
        conn.execute(text("""
            INSERT INTO iva_empresas (id, razon_social, nit, nrc)
            VALUES (1, 'Empresa CI', 'CI-001', 'CI-001')
        """))
        conn.execute(text("""
            INSERT INTO iva_liquidaciones (empresa_id, anio, mes)
            VALUES (1, '2027', '01')
        """))

    # Conexiones aisladas con search_path de prueba; nunca esquema public.
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_schema(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET search_path TO f07_ci_test")
        cursor.close()
        dbapi_connection.commit()

    # Reutilizar una conexión asegurando search_path incluso si existía en el pool.
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO f07_ci_test"))
        conn.commit()
        with Session(bind=conn) as db:
            previo = verificar_preflight_164(db)
            assert previo["columna_164_presente"] is False

        migration = (raiz / "db/migrations/20261110_f07_excedente_impuesto_164.sql").read_text()
        unique = (raiz / "db/migrations/20261110_f07_periodo_unico_draft.sql").read_text()
        # psycopg2 permite ejecutar los bloques SQL de migración en una conexión.
        raw = conn.connection.driver_connection
        cursor = raw.cursor()
        cursor.execute(migration)
        cursor.execute(unique)
        raw.commit()
        cursor.close()

        with Session(bind=conn) as db:
            posterior = verificar_preflight_164(db)
            assert posterior["apto_para_activar_164"] is True
            fila = db.query(Liquidacion).filter_by(empresa_id=1, anio="2027", mes="01").one()
            assert fila.excedente_impuesto_anterior is None
            fila.excedente_impuesto_anterior = Decimal("45.67")
            db.commit()
            db.refresh(fila)
            assert fila.excedente_impuesto_anterior == Decimal("45.67")
            assert db.query(Liquidacion).count() == 1

    engine.dispose()
