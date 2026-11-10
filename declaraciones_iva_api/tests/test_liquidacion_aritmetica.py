"""Pruebas de aritmética de liquidación con datos ficticios en SQLite."""
from app.models.models import DteCompra, DteVenta, DteVentaContribuyente, DteAnulado
from app.routers.liquidacion import calculate_liquidacion_for_period
from test_compras_autorizacion import escenario


def compra(empresa_id, codigo, neto, credito, tipo="03", version=1, omitido=False):
    return DteCompra(
        empresa_id=empresa_id, periodo_mes="11", periodo_anio="2026",
        fecha_emision="01/11/2026", tipo_documento=tipo,
        numero_resolucion=codigo, serie_documento="SELLO",
        numero_documento=codigo, nit_proveedor="PROVEEDOR",
        nombre_proveedor="Proveedor de prueba",
        compras_internas_gravadas=neto, credito_fiscal=credito,
        version=version, omitido=omitido, raw_json={},
    )


def venta_cf(empresa_id, codigo, bruto, version=1):
    return DteVenta(
        empresa_id=empresa_id, periodo_mes="11", periodo_anio="2026",
        fecha_emision="01/11/2026", numero_resolucion="N/A",
        serie_documento="N/A", numero_control_del="N/A",
        numero_control_al="N/A", codigo_generacion=codigo,
        sello_recepcion="SELLO", ventas_gravadas=bruto,
        total_ventas=bruto, version=version, raw_json={},
    )


def venta_ccf(empresa_id, codigo, neto, debito, version=1):
    return DteVentaContribuyente(
        empresa_id=empresa_id, periodo_mes="11", periodo_anio="2026",
        fecha_emision="01/11/2026", numero_resolucion=codigo,
        serie_documento="SELLO", numero_documento=codigo,
        nombre_cliente="Cliente de prueba", ventas_gravadas=neto,
        debito_fiscal=debito, version=version, raw_json={},
    )


def test_totales_con_resultado_independiente(escenario):
    _, db, ids = escenario
    db.add_all([
        venta_cf(ids["e1"], "CF-UNO", 113.00),
        venta_ccf(ids["e1"], "CCF-UNO", 200.00, 26.00),
        compra(ids["e1"], "COMPRA-UNO", 100.00, 13.00),
    ])
    db.commit()
    r = calculate_liquidacion_for_period(db, ids["e1"], "11", "2026")
    assert r["ventas_cf"] == {"neto": 100.00, "debito": 13.00}
    assert r["ventas_ccf"] == {"neto": 200.00, "debito": 26.00}
    assert r["compras"]["neto"] == 100.00
    assert r["totales"] == {
        "debito": 39.00, "credito": 13.00,
        "diferencia_periodo": 26.00,
        "impuesto_determinado": 26.00, "excedente_credito": 0.00,
    }


def test_nota_credito_y_compra_omitida(escenario):
    _, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "COMPRA-UNO", 200.00, 26.00),
        compra(ids["e1"], "NOTA-UNO", 50.00, 6.50, tipo="05"),
        compra(ids["e1"], "OMITIDA", 999.00, 129.87, omitido=True),
    ])
    db.commit()
    r = calculate_liquidacion_for_period(db, ids["e1"], "11", "2026")
    assert r["compras"]["neto"] == 150.00
    assert r["compras"]["credito"] == 19.50
    assert r["totales"]["excedente_credito"] == 19.50
    assert r["totales"]["impuesto_determinado"] == 0.00


def test_anulacion_y_version_no_contaminan_totales(escenario):
    _, db, ids = escenario
    db.add_all([
        venta_cf(ids["e1"], "CF-ANULADO", 113.00),
        venta_cf(ids["e1"], "CF-VIGENTE", 226.00),
        venta_cf(ids["e1"], "CF-OTRA-VERSION", 1130.00, version=2),
        venta_cf(ids["e2"], "CF-OTRA-EMPRESA", 1130.00),
        DteAnulado(
            empresa_id=ids["e1"], periodo_mes="11", periodo_anio="2026",
            fecha_emision="01/11/2026", tipo_documento="01",
            codigo_generacion="CF-ANULADO", sello_recepcion="SELLO",
            raw_json={},
        ),
    ])
    db.commit()
    r = calculate_liquidacion_for_period(db, ids["e1"], "11", "2026", version=1)
    assert r["ventas_cf"] == {"neto": 200.00, "debito": 26.00}
    assert r["totales"]["debito"] == 26.00
    assert r["totales"]["impuesto_determinado"] == 26.00
