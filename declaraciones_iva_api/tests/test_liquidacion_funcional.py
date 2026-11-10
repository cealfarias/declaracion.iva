"""Pruebas funcionales de Liquidación en SQLite en memoria."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.models.models import Liquidacion, UsuarioEmpresa
from app.routers.liquidacion import router as liquidacion_router
from test_compras_autorizacion import escenario, headers


def test_guardar_y_consultar_remanente_propio(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(liquidacion_router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = f"/api/v1/liquidacion/{ids['e1']}"
    with TestClient(app) as client:
        r = client.post(ruta + "/remanente", params={"mes": "11", "anio": "2026", "remanente": 125.50}, headers=headers(ids["u1"]))
        assert r.status_code == 200, r.text
        r = client.get(ruta, params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
        assert r.status_code == 200, r.text
        assert r.json()["remanente_anterior"] == 125.50
        liq = db.query(Liquidacion).filter_by(empresa_id=ids["e1"], mes="11", anio="2026").one()
        assert liq.remanente_anterior == 125.50


def test_ajustes_guardados_solo_para_empresa_propia(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(liquidacion_router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        ruta = f"/api/v1/liquidacion/{ids['e1']}/ajustes"
        r = client.post(ruta, params={"mes": "11", "anio": "2026"}, json={
            "remanente_anterior": 50.0, "retenciones_recibidas": 10.0,
            "percepciones_recibidas": 5.0, "retenciones_efectuadas": 2.0,
            "percepciones_efectuadas": 3.0, "anticipo_cuenta_2": 4.0
        }, headers=headers(ids["u1"]))
        assert r.status_code == 200, r.text
        r = client.get(f"/api/v1/liquidacion/{ids['e1']}", params={"mes": "11", "anio": "2026"}, headers=headers(ids["u1"]))
        assert r.status_code == 200, r.text
        assert r.json()["retenciones_recibidas"] == 10.0
        assert r.json()["percepciones_efectuadas"] == 3.0
        assert db.query(Liquidacion).filter_by(empresa_id=ids["e2"]).count() == 0


def test_ajustes_empresa_ajena_no_modifican_datos(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(liquidacion_router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        r = client.post(f"/api/v1/liquidacion/{ids['e2']}/ajustes",
            params={"mes": "11", "anio": "2026"},
            json={"remanente_anterior": 999.0}, headers=headers(ids["u1"]))
        assert r.status_code == 403, r.text
        assert db.query(Liquidacion).filter_by(empresa_id=ids["e2"]).count() == 0


def test_vinculo_archivado_no_puede_guardar(escenario):
    _, db, ids = escenario
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=ids["u1"], empresa_id=ids["e1"]).one()
    vinculo.archivado = True
    db.commit()
    app = FastAPI()
    app.include_router(liquidacion_router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        r = client.post(f"/api/v1/liquidacion/{ids['e1']}/remanente",
            params={"mes": "11", "anio": "2026", "remanente": 50.0},
            headers=headers(ids["u1"]))
        assert r.status_code == 403, r.text
        assert db.query(Liquidacion).filter_by(empresa_id=ids["e1"]).count() == 0
