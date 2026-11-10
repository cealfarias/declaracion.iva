"""Pruebas de remanente histórico: meses, años y aislamiento entre empresas.

Datos ficticios y SQLite en memoria; no accede a producción.
"""
from app.models.models import DteCompra, DteVentaContribuyente
from app.routers.liquidacion import get_remanente_historico, get_previous_month_year
from test_compras_autorizacion import escenario


def compra(empresa_id, mes, anio, codigo, credito):
    return DteCompra(
        empresa_id=empresa_id, periodo_mes=mes, periodo_anio=anio,
        fecha_emision=f"01/{mes}/{anio}", tipo_documento="03",
        numero_resolucion=codigo, serie_documento="SELLO",
        numero_documento=codigo, nit_proveedor="NIT-PRUEBA",
        nombre_proveedor="Proveedor ficticio",
        compras_internas_gravadas=round(credito / 0.13, 2),
        credito_fiscal=credito, raw_json={},
    )


def venta(empresa_id, mes, anio, codigo, debito):
    return DteVentaContribuyente(
        empresa_id=empresa_id, periodo_mes=mes, periodo_anio=anio,
        fecha_emision=f"01/{mes}/{anio}", tipo_documento="03",
        numero_resolucion=codigo, serie_documento="SELLO",
        numero_documento=codigo, nombre_cliente="Cliente ficticio",
        ventas_gravadas=round(debito / 0.13, 2),
        debito_fiscal=debito, raw_json={},
    )


def test_credito_acumulado_y_aplicacion_parcial(escenario):
    _, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "09", "2026", "C-SEPT", 50.00),
        venta(ids["e1"], "10", "2026", "V-OCT", 20.00),
    ])
    db.commit()
    assert get_remanente_historico(db, ids["e1"], "10", "2026") == 50.00
    assert get_remanente_historico(db, ids["e1"], "11", "2026") == 30.00


def test_excedente_de_dos_periodos_se_acumula(escenario):
    _, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "09", "2026", "C-SEPT", 25.00),
        compra(ids["e1"], "10", "2026", "C-OCT", 15.00),
    ])
    db.commit()
    assert get_remanente_historico(db, ids["e1"], "11", "2026") == 40.00


def test_remanente_no_se_mezcla_entre_empresas(escenario):
    _, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "10", "2026", "C-UNO", 35.00),
        compra(ids["e2"], "10", "2026", "C-DOS", 90.00),
    ])
    db.commit()
    assert get_remanente_historico(db, ids["e1"], "11", "2026") == 35.00
    assert get_remanente_historico(db, ids["e2"], "11", "2026") == 90.00


def test_remanente_cruza_de_diciembre_a_enero(escenario):
    _, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "12", "2025", "C-DIC", 70.00),
        venta(ids["e1"], "01", "2026", "V-ENE", 25.00),
    ])
    db.commit()
    assert get_previous_month_year("01", "2026") == ("12", "2025")
    assert get_remanente_historico(db, ids["e1"], "01", "2026") == 70.00
    assert get_remanente_historico(db, ids["e1"], "02", "2026") == 45.00


def test_ventas_omitidas_no_consumen_remanente_historico(escenario):
    _, db, ids = escenario
    vigente = venta(ids["e1"], "10", "2026", "V-VIGENTE", 20.00)
    omitida = venta(ids["e1"], "10", "2026", "V-OMITIDA", 80.00)
    omitida.omitido = True
    db.add_all([
        compra(ids["e1"], "09", "2026", "C-SEPT", 50.00),
        vigente,
        omitida,
    ])
    db.commit()
    assert get_remanente_historico(db, ids["e1"], "11", "2026") == 30.00
