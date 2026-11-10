"""Pruebas de escritura HTTP sobre SQL real aislado (SQLite, no producción)."""
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.authorization import autorizar_empresa_tributaria
from app.core.database import get_db
from app.models.models import Empresa, Liquidacion
from app.routers.liquidacion import router


def test_registro_164_actualiza_null_y_rechaza_segunda_escritura():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Empresa.__table__.create(engine)
    Liquidacion.__table__.create(engine)
    with Session(engine) as db:
        db.add(Empresa(id=1, razon_social="Empresa", nit="001", nrc="001"))
        db.add(Liquidacion(empresa_id=1, anio="2027", mes="01"))
        db.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/liquidacion")
        app.dependency_overrides[autorizar_empresa_tributaria] = lambda: None
        app.dependency_overrides[get_db] = lambda: db
        ruta = "/api/v1/liquidacion/1/excedente-impuesto-anterior?mes=01&anio=2027"
        with TestClient(app) as cliente:
            primera = cliente.post(ruta, json={"importe": "45.67"})
            segunda = cliente.post(ruta, json={"importe": "99.99"})
        assert primera.status_code == 200
        assert segunda.status_code == 409
        db.expire_all()
        saldo = db.query(Liquidacion).filter_by(
            empresa_id=1, anio="2027", mes="01"
        ).one().excedente_impuesto_anterior
        assert saldo == Decimal("45.67")
    engine.dispose()


def test_registro_164_no_crea_duplicado_de_periodo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Empresa.__table__.create(engine)
    Liquidacion.__table__.create(engine)
    with Session(engine) as db:
        db.add(Empresa(id=1, razon_social="Empresa", nit="002", nrc="002"))
        db.commit()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/liquidacion")
        app.dependency_overrides[autorizar_empresa_tributaria] = lambda: None
        app.dependency_overrides[get_db] = lambda: db
        ruta = "/api/v1/liquidacion/1/excedente-impuesto-anterior?mes=02&anio=2027"
        with TestClient(app) as cliente:
            primera = cliente.post(ruta, json={"importe": "0.00"})
            segunda = cliente.post(ruta, json={"importe": "5.00"})
        assert primera.status_code == 200
        assert segunda.status_code == 409
        assert db.query(Liquidacion).filter_by(
            empresa_id=1, anio="2027", mes="02"
        ).count() == 1
    engine.dispose()
