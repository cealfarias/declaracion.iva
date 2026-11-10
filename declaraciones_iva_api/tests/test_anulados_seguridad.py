"""Pruebas aisladas de autorización y TLS en documentos invalidados."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.routers.anulados import router as anulados_router
from test_compras_autorizacion import escenario, headers


def cliente_anulados(db):
    app = FastAPI()
    app.include_router(anulados_router, prefix="/api/v1/anulados")
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_anulados_empresa_ajena_rechazada(escenario):
    _, db, ids = escenario
    with cliente_anulados(db) as client:
        r = client.get(
            f"/api/v1/anulados/list/{ids['e2']}?mes=11&anio=2026",
            headers=headers(ids["u1"]),
        )
        assert r.status_code == 403, r.text


def test_anulados_empresa_propia_permitida(escenario):
    _, db, ids = escenario
    with cliente_anulados(db) as client:
        r = client.get(
            f"/api/v1/anulados/list/{ids['e1']}?mes=11&anio=2026",
            headers=headers(ids["u1"]),
        )
        assert r.status_code == 200, r.text


def test_consulta_hacienda_requiere_sesion(escenario):
    _, db, _ = escenario
    with cliente_anulados(db) as client:
        r = client.get("/api/v1/anulados/consultar-mh")
        assert r.status_code in (401, 403), r.text


def test_consulta_hacienda_valida_certificado(monkeypatch):
    import ssl
    from app.routers import anulados

    class Respuesta:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"estadoDoc":"Invalidado"}'

    def urlopen(req, context, timeout):
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
        assert timeout == 6
        return Respuesta()

    monkeypatch.setattr(anulados.urllib.request, "urlopen", urlopen)
    r = anulados.verificar_dte_hacienda("TEST", "2026-11-01")
    assert r["ok"] is True
    assert r["estadoDoc"] == "Invalidado"
