"""Pruebas HTTP de validación fiscal sin escrituras a PostgreSQL."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.authorization import autorizar_empresa_tributaria
from app.core.database import get_db
from app.routers.liquidacion import router


class BaseDatosProhibida:
    def query(self, *_args, **_kwargs):
        raise AssertionError("La solicitud inválida no debe consultar PostgreSQL.")

    def commit(self):
        raise AssertionError("La solicitud inválida no debe escribir en PostgreSQL.")


@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/liquidacion")
    app.dependency_overrides[autorizar_empresa_tributaria] = lambda: None
    app.dependency_overrides[get_db] = lambda: BaseDatosProhibida()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize("ruta,metodo,payload", [
    ("/api/v1/liquidacion/1?mes=13&anio=2026", "get", None),
    ("/api/v1/liquidacion/1/remanente?mes=13&anio=2026&remanente=10.00", "post", None),
    ("/api/v1/liquidacion/1/ajustes?mes=13&anio=2026", "post", {"remanente_anterior": "10.00"}),
    ("/api/v1/liquidacion/1/remanente?mes=01&anio=2026&remanente=-1", "post", None),
    ("/api/v1/liquidacion/1/ajustes?mes=01&anio=2026", "post", {"retenciones_recibidas": "12.345"}),
])
def test_solicitud_http_invalida_retorna_422_sin_db(cliente, ruta, metodo, payload):
    if metodo == "get":
        respuesta = cliente.get(ruta)
    else:
        respuesta = cliente.post(ruta, json=payload)
    assert respuesta.status_code == 422
