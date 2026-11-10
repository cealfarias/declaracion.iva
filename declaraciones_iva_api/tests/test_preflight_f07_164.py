"""Contrato de preflight: nunca activar casilla 164 desde SQLite o sin esquema válido."""
import pytest

from app.core.preflight_f07_164 import verificar_preflight_164


class Dialecto:
    name = "sqlite"


class Bind:
    dialect = Dialecto()


class FakeDB:
    def get_bind(self):
        return Bind()

    def execute(self, *_args, **_kwargs):
        raise AssertionError("No se debe consultar ni modificar la base SQLite.")


def test_preflight_rechaza_sqlite_antes_de_ejecutar_sql():
    with pytest.raises(ValueError, match="PostgreSQL"):
        verificar_preflight_164(FakeDB())
