"""Contrato HTTP provisional F-07: separa saldos de crédito e impuesto.

No certifica la fórmula normativa. Usa SQLite efímero y JWT de prueba.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import Liquidacion
from app.routers.liquidacion import router
from test_compras_autorizacion import escenario, headers


def test_contrato_casillas_provisionales_no_inventa_saldos(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = f"/api/v1/liquidacion/{ids['e1']}?mes=07&anio=2027"
    with TestClient(app) as client:
        respuesta = client.get(ruta, headers=headers(ids["u1"]))
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        casillas = datos["casillas_f07_preliminares"]
        assert set(casillas) == {"110", "155", "164", "167", "168", "203"}
        assert casillas["164"] is None
        assert casillas["167"] is None
        assert casillas["168"] is None
        assert casillas["203"] is None
        assert datos["estado_normativo_f07"]["conciliacion_completa"] is False
        assert set(datos["estado_normativo_f07"]["casillas_pendientes"]) == {164, 167, 168, 203}
        assert casillas["155"] == datos["remanente_credito_fiscal_siguiente"]
        assert datos["remanente_siguiente"] == datos["remanente_credito_fiscal_siguiente"]


def test_contrato_164_guardada_no_habilita_167_168_203(escenario):
    _client, db, ids = escenario
    db.add(Liquidacion(
        empresa_id=ids["e1"], mes="08", anio="2027",
        excedente_impuesto_anterior="45.67",
    ))
    db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        respuesta = client.get(
            f"/api/v1/liquidacion/{ids['e1']}?mes=08&anio=2027",
            headers=headers(ids["u1"]),
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        casillas = datos["casillas_f07_preliminares"]
        assert casillas["164"] == 45.67
        assert all(casillas[clave] is None for clave in ("167", "168", "203"))
        assert datos["estado_normativo_f07"]["casillas_pendientes"] == [167, 168, 203]
        assert datos["estado_normativo_f07"]["conciliacion_completa"] is False
