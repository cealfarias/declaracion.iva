"""Pruebas HTTP JWT reales del registro auditado F-07 164.

Sin anular autorización ni usuario_actual. Base SQLite temporal, nunca Render.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import Liquidacion, Excedente164Auditoria
from app.routers.liquidacion import router
from test_compras_autorizacion import escenario, headers


def test_164_auditado_jwt_y_aislamiento_empresa(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = "/api/v1/liquidacion/{}/excedente-impuesto-anterior-auditado?mes=01&anio=2027"
    payload = {
        "importe": "45.67",
        "origen": "declaracion_previa",
        "referencia": "F07-2026-12",
    }
    with TestClient(app) as client:
        sin_token = client.post(ruta.format(ids["e1"]), json=payload)
        assert sin_token.status_code in (401, 403), sin_token.text

        token_invalido = client.post(
            ruta.format(ids["e1"]), json=payload,
            headers={"Authorization": "Bearer no-es-jwt"},
        )
        assert token_invalido.status_code == 401, token_invalido.text

        ajena = client.post(
            ruta.format(ids["e2"]), json=payload,
            headers=headers(ids["u1"]),
        )
        assert ajena.status_code == 403, ajena.text
        assert db.query(Liquidacion).count() == 0
        assert db.query(Excedente164Auditoria).count() == 0

        propia = client.post(
            ruta.format(ids["e1"]), json=payload,
            headers=headers(ids["u1"]),
        )
        assert propia.status_code == 200, propia.text
        audit = db.query(Excedente164Auditoria).one()
        assert audit.usuario_id == ids["u1"]
        assert audit.empresa_id == ids["e1"]
        assert db.query(Liquidacion).count() == 1

        duplicada = client.post(
            ruta.format(ids["e1"]), json=payload,
            headers=headers(ids["u1"]),
        )
        assert duplicada.status_code == 409, duplicada.text
        assert db.query(Excedente164Auditoria).count() == 1
