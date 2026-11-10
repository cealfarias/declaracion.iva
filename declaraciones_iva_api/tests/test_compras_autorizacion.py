"""Pruebas de aislamiento del módulo Compras.

Ejecutar desde declaraciones_iva_api:
    .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_compras_autorizacion.py

Utiliza SQLite en memoria; NO toca PostgreSQL.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.models import Empresa, Usuario, UsuarioEmpresa, DteCompra
from app.routers.compras import router as compras_router


@pytest.fixture
def escenario():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        u1 = Usuario(email="prueba1@example.invalid", nombre="Usuario uno", password_hash="prueba")
        u2 = Usuario(email="prueba2@example.invalid", nombre="Usuario dos", password_hash="prueba")
        e1 = Empresa(razon_social="Empresa uno", nit="TEST-UNO", nrc="TEST-UNO")
        e2 = Empresa(razon_social="Empresa dos", nit="TEST-DOS", nrc="TEST-DOS")
        db.add_all([u1, u2, e1, e2])
        db.flush()
        db.add_all([
            UsuarioEmpresa(usuario_id=u1.id, empresa_id=e1.id, rol="admin", archivado=False),
            UsuarioEmpresa(usuario_id=u2.id, empresa_id=e2.id, rol="admin", archivado=False),
        ])
        db.commit()
        ids = {"u1": u1.id, "u2": u2.id, "e1": e1.id, "e2": e2.id}

        app = FastAPI()
        app.include_router(compras_router, prefix="/api/v1/compras")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as client:
            yield client, db, ids
    finally:
        db.close()
        engine.dispose()


def headers(user_id):
    return {"Authorization": f"Bearer {create_access_token({'id': user_id})}"}


def ruta(empresa_id):
    return f"/api/v1/compras/{empresa_id}?mes=11&anio=2026"


def test_sin_token_rechazado(escenario):
    client, _, ids = escenario
    assert client.get(ruta(ids["e1"])).status_code in (401, 403)


def test_usuario_puede_leer_su_empresa(escenario):
    client, _, ids = escenario
    r = client.get(ruta(ids["e1"]), headers=headers(ids["u1"]))
    assert r.status_code == 200, r.text


def test_usuario_no_puede_leer_empresa_ajena(escenario):
    client, _, ids = escenario
    r = client.get(ruta(ids["e2"]), headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text


def test_usuario_no_puede_modificar_empresa_ajena(escenario):
    client, db, ids = escenario
    r = client.put(
        f"/api/v1/compras/estado/{ids['e2']}/numero",
        params={"mes": "11", "anio": "2026", "numero": "INTRUSION"},
        headers=headers(ids["u1"]),
    )
    assert r.status_code == 403, r.text


def test_vinculo_archivado_rechazado(escenario):
    client, db, ids = escenario
    vinculo = db.query(UsuarioEmpresa).filter_by(
        usuario_id=ids["u1"], empresa_id=ids["e1"]
    ).one()
    vinculo.archivado = True
    db.commit()
    r = client.get(ruta(ids["e1"]), headers=headers(ids["u1"]))
    assert r.status_code == 403, r.text


def test_id_de_compra_ajena_rechazado(escenario):
    client, db, ids = escenario
    compra = DteCompra(
        empresa_id=ids["e2"], periodo_mes="11", periodo_anio="2026",
        fecha_emision="01/11/2026", numero_resolucion="PRUEBA",
        serie_documento="PRUEBA", numero_documento="PRUEBA",
        nit_proveedor="PRUEBA", nombre_proveedor="Proveedor ficticio",
        raw_json={},
    )
    db.add(compra)
    db.commit()
    r = client.delete(
        f"/api/v1/compras/item/{compra.id}",
        headers=headers(ids["u1"]),
    )
    assert r.status_code == 403, r.text
    assert db.get(DteCompra, compra.id) is not None
