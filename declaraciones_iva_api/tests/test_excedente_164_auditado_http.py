"""Registro auditado 164 sobre base aislada; nunca utiliza Render."""
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
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
            assert client.post(ruta, json={**payload, "origen": "desconocido"}).status_code == 422
        db.expire_all()
        liq = db.query(Liquidacion).one()
        audit = db.query(Excedente164Auditoria).one()
        assert liq.excedente_impuesto_anterior == Decimal("45.67")
        assert audit.importe == Decimal("45.67")
        assert audit.liquidacion_id == liq.id
        assert audit.usuario_id == 1
        assert audit.referencia == "F07-2026-12"
    engine.dispose()


def test_164_auditado_revierte_saldo_si_falla_auditoria():
    """La inserción de auditoría falla y no puede dejar un saldo huérfano."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Usuario.__table__.create(engine)
    Empresa.__table__.create(engine)
    Liquidacion.__table__.create(engine)
    Excedente164Auditoria.__table__.create(engine)
    with Session(engine) as db:
        usuario = Usuario(id=1, email="ci2@example.invalid", password_hash="no-login", nombre="CI")
        db.add_all([usuario, Empresa(id=1, razon_social="Empresa CI", nit="CI-2", nrc="CI-2")])
        db.commit()
        # Simula un rechazo de la base en la tabla de auditoría.
        @event.listens_for(engine, "before_cursor_execute")
        def bloquear_auditoria(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith("INSERT INTO IVA_EXCEDENTES_164_AUDITORIA"):
                from sqlalchemy.exc import IntegrityError
                raise IntegrityError(statement, _parameters, Exception("rechazo simulado"))

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/liquidacion")
        app.dependency_overrides[autorizar_empresa_tributaria] = lambda: None
        app.dependency_overrides[usuario_actual] = lambda: usuario
        app.dependency_overrides[get_db] = lambda: db
        ruta = "/api/v1/liquidacion/1/excedente-impuesto-anterior-auditado?mes=01&anio=2027"
        with TestClient(app) as client:
            response = client.post(ruta, json={
                "importe": "45.67", "origen": "declaracion_previa", "referencia": "F07-2026-12"
            })
        assert response.status_code == 409
        assert db.query(Liquidacion).count() == 0
        assert db.query(Excedente164Auditoria).count() == 0
    engine.dispose()
