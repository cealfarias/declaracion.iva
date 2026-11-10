"""Integración F-07 164 contra PostgreSQL efímero de CI.

No usa la base Render. Requiere F07_TEST_DATABASE_URL, exclusivamente de prueba.
"""
import os
from pathlib import Path
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.preflight_f07_164 import verificar_preflight_164
from app.models.models import Empresa, Liquidacion, Usuario


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
        Usuario.__table__.create(conn, checkfirst=True)
        Empresa.__table__.create(conn, checkfirst=True)
        conn.execute(text("INSERT INTO iva_usuarios (id, email, password_hash, nombre) VALUES (1, 'ci@example.invalid', 'ci-no-login', 'CI')"))
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
        audit = (raiz / "db/migrations/20261110_f07_164_auditoria_draft.sql").read_text()
        # psycopg2 permite ejecutar los bloques SQL de migración en una conexión.
        raw = conn.connection.driver_connection
        cursor = raw.cursor()
        cursor.execute(migration)
        cursor.execute(unique)
        cursor.execute(audit)
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
            # El inventario identifica saldos existentes sin inventar procedencia.
            inventario_sql = (raiz / "db/migrations/20261110_f07_164_inventario_historico_readonly.sql").read_text()
            antes = db.execute(text(inventario_sql)).mappings().all()
            assert len(antes) == 1
            assert antes[0]["estado"] == "saldo_sin_auditoria"
            assert antes[0]["saldo_164"] == Decimal("45.67")
            assert antes[0]["referencia"] is None
            resumen_sql = (raiz / "db/migrations/20261110_f07_164_resumen_historico_readonly.sql").read_text()
            resumen_antes = db.execute(text(resumen_sql)).mappings().one()
            assert resumen_antes["empresa_id"] == 1
            assert resumen_antes["periodos_revisados"] == 1
            assert resumen_antes["saldos_sin_auditoria"] == 1
            assert resumen_antes["coincidentes"] == 0
            # La procedencia no puede referenciar una empresa o período distintos.
            db.execute(text("""
                INSERT INTO iva_excedentes_164_auditoria
                    (liquidacion_id, empresa_id, usuario_id, anio, mes,
                     importe, origen, referencia)
                VALUES (:liquidacion_id, 1, 1, '2027', '01',
                        45.67, 'declaracion_previa', 'F07-2026-12')
            """), {"liquidacion_id": fila.id})
            db.commit()
            with pytest.raises(IntegrityError):
                db.execute(text("""
                    INSERT INTO iva_excedentes_164_auditoria
                        (liquidacion_id, empresa_id, usuario_id, anio, mes,
                         importe, origen, referencia)
                    VALUES (:liquidacion_id, 1, 1, '2027', '02',
                            45.67, 'declaracion_previa', 'F07-2027-01')
                """), {"liquidacion_id": fila.id})
                db.commit()
            db.rollback()
            assert db.execute(text(
                "SELECT count(*) FROM iva_excedentes_164_auditoria"
            )).scalar_one() == 1
            despues = db.execute(text(inventario_sql)).mappings().all()
            assert len(despues) == 1
            assert despues[0]["estado"] == "coincidente"
            assert despues[0]["referencia"] == "F07-2026-12"
            resumen_despues = db.execute(text(resumen_sql)).mappings().one()
            assert resumen_despues["periodos_revisados"] == 1
            assert resumen_despues["saldos_sin_auditoria"] == 0
            assert resumen_despues["coincidentes"] == 1
            # Alteración deliberada en CI: detectar diferencia sin corregirla.
            db.execute(text("""
                UPDATE iva_excedentes_164_auditoria
                SET importe = 45.68
                WHERE liquidacion_id = :id
            """), {"id": fila.id})
            db.commit()
            discrepancia = db.execute(text(inventario_sql)).mappings().all()
            assert len(discrepancia) == 1
            assert discrepancia[0]["estado"] == "importe_discrepante"
            assert discrepancia[0]["saldo_164"] == Decimal("45.67")
            db.execute(text("""
                UPDATE iva_excedentes_164_auditoria
                SET importe = 45.67
                WHERE liquidacion_id = :id
            """), {"id": fila.id})
            db.commit()
            assert db.execute(text(inventario_sql)).mappings().one()["estado"] == "coincidente"
            # La restricción única debe rechazar duplicados en PostgreSQL real.
            db.add(Liquidacion(empresa_id=1, anio="2027", mes="01"))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
            assert db.query(Liquidacion).count() == 1


        # Cerrar la transacción lectora antes de ejecutar ALTER TABLE:
        # PostgreSQL requiere un bloqueo exclusivo para DDL.
        conn.rollback()

    with engine.begin() as conn:
        conn.execute(text("SET search_path TO f07_ci_test"))
        raw2 = conn.connection.driver_connection
        with raw2.cursor() as cursor2:
            cursor2.execute(migration)
            cursor2.execute(unique)
            cursor2.execute(audit)

    with engine.connect() as conn:
        conn.execute(text("SET search_path TO f07_ci_test"))
        with Session(bind=conn) as db:
            assert db.query(Liquidacion).filter_by(
                empresa_id=1, anio="2027", mes="01"
            ).one().excedente_impuesto_anterior == Decimal("45.67")

    engine.dispose()
