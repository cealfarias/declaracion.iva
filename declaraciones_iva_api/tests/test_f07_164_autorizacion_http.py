"""Pruebas HTTP JWT reales del registro auditado F-07 164.

Sin anular autorización ni usuario_actual. Base SQLite temporal, nunca Render.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.models import Liquidacion, Excedente164Auditoria, UsuarioEmpresa
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
        consulta = client.get(
            "/api/v1/liquidacion/{}/excedente-impuesto-anterior-auditoria?mes=01&anio=2027".format(ids["e1"]),
            headers=headers(ids["u1"]),
        )
        assert consulta.status_code == 200, consulta.text
        respaldo = consulta.json()["respaldo"]
        assert consulta.json()["auditoria_disponible"] is True
        assert consulta.json()["consistencia"] == "coincidente"
        assert respaldo["referencia"] == "F07-2026-12"
        assert respaldo["usuario_id"] == ids["u1"]
        assert respaldo["importe"] == 45.67

        consulta_ajena = client.get(
            "/api/v1/liquidacion/{}/excedente-impuesto-anterior-auditoria?mes=01&anio=2027".format(ids["e2"]),
            headers=headers(ids["u1"]),
        )
        assert consulta_ajena.status_code == 403

        sin_respaldo = client.get(
            "/api/v1/liquidacion/{}/excedente-impuesto-anterior-auditoria?mes=02&anio=2027".format(ids["e1"]),
            headers=headers(ids["u1"]),
        )
        assert sin_respaldo.status_code == 200
        assert sin_respaldo.json()["auditoria_disponible"] is False
        assert sin_respaldo.json()["consistencia"] == "sin_registro"
        assert sin_respaldo.json()["respaldo"] is None

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


def test_164_detecta_saldo_historico_sin_respaldo_y_discrepancia(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = f"/api/v1/liquidacion/{ids['e1']}/excedente-impuesto-anterior-auditoria?mes=03&anio=2027"
    db.add(Liquidacion(empresa_id=ids["e1"], anio="2027", mes="03", excedente_impuesto_anterior=12.34))
    db.commit()
    with TestClient(app) as client:
        sin_auditoria = client.get(ruta, headers=headers(ids["u1"]))
        assert sin_auditoria.status_code == 200, sin_auditoria.text
        assert sin_auditoria.json()["consistencia"] == "saldo_sin_auditoria"
        assert sin_auditoria.json()["respaldo"] is None

        # Auditar un período distinto para comprobar una discrepancia real.
        ruta_post = f"/api/v1/liquidacion/{ids['e1']}/excedente-impuesto-anterior-auditado?mes=04&anio=2027"
        payload = {"importe": "15.00", "origen": "conciliacion_manual", "referencia": "ACTA-2027-04"}
        creada = client.post(ruta_post, json=payload, headers=headers(ids["u1"]))
        assert creada.status_code == 200, creada.text
        liq = db.query(Liquidacion).filter_by(empresa_id=ids["e1"], anio="2027", mes="04").one()
        liq.excedente_impuesto_anterior = 16
        db.commit()
        inconsistente = client.get(
            f"/api/v1/liquidacion/{ids['e1']}/excedente-impuesto-anterior-auditoria?mes=04&anio=2027",
            headers=headers(ids["u1"]),
        )
        assert inconsistente.status_code == 409, inconsistente.text


def test_164_consulta_y_escritura_rechazan_vinculo_archivado(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    vinculo = db.query(UsuarioEmpresa).filter_by(
        usuario_id=ids["u1"], empresa_id=ids["e1"]
    ).one()
    vinculo.archivado = True
    db.commit()
    ruta = f"/api/v1/liquidacion/{ids['e1']}"
    with TestClient(app) as client:
        consulta = client.get(
            ruta + "/excedente-impuesto-anterior-auditoria?mes=05&anio=2027",
            headers=headers(ids["u1"]),
        )
        assert consulta.status_code == 403, consulta.text
        escritura = client.post(
            ruta + "/excedente-impuesto-anterior-auditado?mes=05&anio=2027",
            json={"importe": "20.00", "origen": "declaracion_previa", "referencia": "F07-2027-04"},
            headers=headers(ids["u1"]),
        )
        assert escritura.status_code == 403, escritura.text
    assert db.query(Liquidacion).count() == 0
    assert db.query(Excedente164Auditoria).count() == 0


def test_164_consulta_sin_jwt_o_jwt_invalido(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = f"/api/v1/liquidacion/{ids['e1']}/excedente-impuesto-anterior-auditoria?mes=06&anio=2027"
    with TestClient(app) as client:
        assert client.get(ruta).status_code in (401, 403)
        respuesta = client.get(ruta, headers={"Authorization": "Bearer token-invalido"})
        assert respuesta.status_code == 401, respuesta.text


def test_164_detecta_respaldo_con_periodo_inconsistente(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        creada = client.post(
            f"/api/v1/liquidacion/{ids['e1']}/excedente-impuesto-anterior-auditado?mes=09&anio=2027",
            json={"importe": "22.00", "origen": "declaracion_previa", "referencia": "F07-2027-08"},
            headers=headers(ids["u1"]),
        )
        assert creada.status_code == 200, creada.text
        auditoria = db.query(Excedente164Auditoria).one()
        auditoria.mes = "10"
        db.commit()
        respuesta = client.get(
            f"/api/v1/liquidacion/{ids['e1']}/excedente-impuesto-anterior-auditoria?mes=10&anio=2027",
            headers=headers(ids["u1"]),
        )
        assert respuesta.status_code == 409, respuesta.text


def test_conciliacion_devoluciones_dte_05_solo_lectura_y_empresa(escenario):
    _client, db, ids = escenario
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = f"/api/v1/liquidacion/{ids['e1']}/conciliacion-devoluciones?mes=07&anio=2027"
    with TestClient(app) as client:
        assert client.get(ruta).status_code in (401, 403)
        assert client.get(ruta, headers=headers(ids["u2"])).status_code == 403
        respuesta = client.get(ruta, headers=headers(ids["u1"]))
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["devoluciones_dte"] == {"neto": 0.0, "credito": 0.0}
        assert cuerpo["ajuste_manual_persistido"] is None
        assert cuerpo["estado_conciliacion"] == "pendiente_definicion_normativa"
        assert db.query(Liquidacion).count() == 0
        assert db.query(Excedente164Auditoria).count() == 0
        assert client.get(ruta + "&version=0", headers=headers(ids["u1"])).status_code == 422


def test_conciliacion_devoluciones_dte_05_importes_y_versiones(escenario):
    from test_liquidacion_aritmetica import compra

    _client, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "COMPRA-BASE", 200.00, 26.00),
        compra(ids["e1"], "NOTA-05", 50.00, 6.50, tipo="05"),
        compra(ids["e1"], "NOTA-V2", 80.00, 10.40, tipo="05", version=2),
        compra(ids["e1"], "NOTA-OMITIDA", 30.00, 3.90, tipo="05", omitido=True),
        compra(ids["e2"], "NOTA-OTRA-EMPRESA", 99.00, 12.87, tipo="05"),
    ])
    db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[get_db] = lambda: db
    ruta = f"/api/v1/liquidacion/{ids['e1']}/conciliacion-devoluciones?mes=11&anio=2026"
    with TestClient(app) as client:
        respuesta = client.get(ruta, headers=headers(ids["u1"]))
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["devoluciones_dte"] == {"neto": 50.0, "credito": 6.5}
        assert respuesta.json()["ajuste_manual_persistido"] is None
        otra_version = client.get(ruta + "&version=2", headers=headers(ids["u1"]))
        assert otra_version.status_code == 200, otra_version.text
        assert otra_version.json()["devoluciones_dte"] == {"neto": 80.0, "credito": 10.4}
        assert db.query(Liquidacion).count() == 0
        assert db.query(Excedente164Auditoria).count() == 0
