"""Integridad real del modelo de liquidaciones en una base SQLite aislada.

La restricción equivalente debe aplicarse a PostgreSQL mediante migración
controlada; estas pruebas no modifican la base de datos de producción.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import Empresa, Liquidacion


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Empresa.__table__.create(engine)
    Liquidacion.__table__.create(engine)
    with Session(engine) as session:
        session.add(Empresa(id=1, razon_social="Empresa prueba", nit="00000000000000", nrc="0000000"))
        session.add(Empresa(id=2, razon_social="Otra empresa", nit="11111111111111", nrc="1111111"))
        session.commit()
        yield session
    engine.dispose()


def test_164_decimal_se_persiste_y_nulo_es_distinto_de_cero(db):
    db.add_all([
        Liquidacion(empresa_id=1, anio="2026", mes="11", excedente_impuesto_anterior=Decimal("45.67")),
        Liquidacion(empresa_id=1, anio="2026", mes="12"),
        Liquidacion(empresa_id=2, anio="2026", mes="11", excedente_impuesto_anterior=Decimal("0.00")),
    ])
    db.commit()
    db.expire_all()
    saldos = {
        (l.empresa_id, l.mes): l.excedente_impuesto_anterior
        for l in db.query(Liquidacion).all()
    }
    assert saldos[(1, "11")] == Decimal("45.67")
    assert saldos[(1, "12")] is None
    assert saldos[(2, "11")] == Decimal("0.00")


def test_no_permite_dos_liquidaciones_de_la_misma_empresa_y_periodo(db):
    db.add(Liquidacion(empresa_id=1, anio="2026", mes="11"))
    db.commit()
    db.add(Liquidacion(empresa_id=1, anio="2026", mes="11"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_permite_mismo_periodo_en_empresas_distintas(db):
    db.add_all([
        Liquidacion(empresa_id=1, anio="2026", mes="11"),
        Liquidacion(empresa_id=2, anio="2026", mes="11"),
    ])
    db.commit()
    assert db.query(Liquidacion).count() == 2
