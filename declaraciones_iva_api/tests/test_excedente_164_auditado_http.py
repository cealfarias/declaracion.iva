"""Registro auditado 164 sobre base aislada; nunca utiliza Render."""
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.authorization import autorizar_empresa_tributaria
from app.core.database import get_db
from app.models.models import Empresa, Liquidacion, Usuario, Excedente164Auditoria
from app.routers.empresas import usuario_actual
from app.routers.liquidacion import router


def test_164_auditado_persiste_saldo_y_autor_en_misma_transaccion():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Usuario.__table__.create(engine)
    Empresa.__table__.create(engine)
    Liquidacion.__table__.create(engine)
    Excedente164Auditoria.__table__.create(engine)
    with Session(engine) as db:
        usuario = Usuario(id=1, email="ci@example.invalid", password_hash="no-login", nombre="CI")
        db.add_all([usuario, Empresa(id=1, razon_social="Empresa CI", nit="CI-1", nrc="CI-1")])
        db.commit()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/liquidacion")
        app.dependency_overrides[autorizar_empresa_tributaria] = lambda: None
        app.dependency_overrides[usuario_actual] = lambda: usuario
        app.dependency_overrides[get_db] = lambda: db
        ruta = "/api/v1/liquidacion/1/excedente-impuesto-anterior-auditado?mes=01&anio=2027"
        payload = {"importe": "45.67", "origen": "declaracion_previa", "referencia": "F07-2026-12"}
        with TestClient(app) as client:
            assert client.post(ruta, json=payload).status_code == 200
            assert client.post(ruta, json=payload).status_code == 409
            assert client.post(ruta, json={**payload, "referencia": ""}).status_code == 422
        db.expire_all()
        liq = db.query(Liquidacion).one()
        audit = db.query(Excedente164Auditoria).one()
        assert liq.excedente_impuesto_anterior == Decimal("45.67")
        assert audit.importe == Decimal("45.67")
        assert audit.liquidacion_id == liq.id
        assert audit.usuario_id == 1
        assert audit.referencia == "F07-2026-12"
    engine.dispose()
