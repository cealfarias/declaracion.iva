"""Integridad de importaciones JSON de retenciones; SQLite en memoria."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import DteRetencion
from app.routers.retenciones import router as retenciones_router
from test_compras_autorizacion import escenario, headers


@pytest.fixture
def cliente_importacion(escenario):
    _, db, ids = escenario
    app = FastAPI()
    app.include_router(retenciones_router, prefix="/api/v1/retenciones")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, db, ids


def enviar(client, empresa_id, usuario_id, archivos, mes="11", anio="2026"):
    return client.post(
        f"/api/v1/retenciones/upload/{empresa_id}",
        data={"mes": mes, "anio": anio},
        files=[("files", (nombre, contenido, "application/json")) for nombre, contenido in archivos],
        headers=headers(usuario_id),
    )


def dte(codigo="RET-PRUEBA-001", fecha="2026-11-01", tipo="07"):
    return json.dumps({
        "identificacion": {"tipoDte": tipo, "codigoGeneracion": codigo, "fecEmi": fecha},
        "emisor": {"nit": "06140000000000", "nombre": "Agente ficticio"},
        "resumen": {"totalSujetoRetencion": 100.0, "totalIvaRetenido": 1.0},
        "cuerpoDocumento": [],
    }).encode("utf-8")


def test_json_malformado_no_crea_retencion(cliente_importacion):
    client, db, ids = cliente_importacion
    r = enviar(client, ids["e1"], ids["u1"], [("roto.json", b'{"identificacion":')])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0
    assert r.json()["errores"]
    assert db.query(DteRetencion).count() == 0


def test_documento_de_tipo_incorrecto_ignorado(cliente_importacion):
    client, db, ids = cliente_importacion
    r = enviar(client, ids["e1"], ids["u1"], [("otro.json", dte(tipo="01"))])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0
    assert r.json()["ignorados_no_07"] == 1
    assert db.query(DteRetencion).count() == 0


def test_periodo_futuro_no_aceptado(cliente_importacion):
    client, db, ids = cliente_importacion
    r = enviar(client, ids["e1"], ids["u1"], [("futuro.json", dte(fecha="2026-12-01"))])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0
    assert r.json()["errores"]
    assert db.query(DteRetencion).count() == 0


def test_documento_fuera_de_ventana_no_aceptado(cliente_importacion):
    client, db, ids = cliente_importacion
    r = enviar(client, ids["e1"], ids["u1"], [("antiguo.json", dte(fecha="2026-01-01"))])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0
    assert r.json()["errores"]
    assert db.query(DteRetencion).count() == 0


def test_duplicados_en_misma_carga_y_reenvio(cliente_importacion):
    client, db, ids = cliente_importacion
    archivo = dte()
    r = enviar(client, ids["e1"], ids["u1"], [
        ("primero.json", archivo), ("segundo.json", archivo)
    ])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 1, r.text
    assert db.query(DteRetencion).filter_by(empresa_id=ids["e1"]).count() == 1
    r = enviar(client, ids["e1"], ids["u1"], [("repetido.json", archivo)])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 0, r.text
    assert db.query(DteRetencion).filter_by(empresa_id=ids["e1"]).count() == 1


def test_archivo_valido_se_guarda_en_empresa_correcta(cliente_importacion):
    client, db, ids = cliente_importacion
    r = enviar(client, ids["e1"], ids["u1"], [("valido.json", dte())])
    assert r.status_code == 200, r.text
    assert r.json()["procesados"] == 1, r.text
    registros = db.query(DteRetencion).all()
    assert len(registros) == 1
    assert registros[0].empresa_id == ids["e1"]
    assert registros[0].monto_retencion == 1.0
