"""Las solicitudes con períodos inválidos no deben tocar la base de datos."""
import pytest
from fastapi import HTTPException

from app.routers.liquidacion import (
    AjustesLiquidacionRequest,
    get_liquidacion,
    update_ajustes,
    update_remanente,
)


class BaseDatosProhibida:
    def query(self, *_args, **_kwargs):
        raise AssertionError("No debe consultar PostgreSQL con un período inválido.")

    def commit(self):
        raise AssertionError("No debe escribir en PostgreSQL con un período inválido.")


@pytest.mark.parametrize("operacion", ["consulta", "remanente", "ajustes"])
def test_periodo_invalido_no_accede_base_de_datos(operacion):
    db = BaseDatosProhibida()
    with pytest.raises(HTTPException) as exc:
        if operacion == "consulta":
            get_liquidacion(empresa_id=1, mes="13", anio="2026", db=db)
        elif operacion == "remanente":
            update_remanente(empresa_id=1, mes="13", anio="2026", remanente="10.00", db=db)
        else:
            update_ajustes(
                empresa_id=1, mes="13", anio="2026",
                req=AjustesLiquidacionRequest(retenciones_recibidas="10.00"), db=db,
            )
    assert exc.value.status_code == 422
