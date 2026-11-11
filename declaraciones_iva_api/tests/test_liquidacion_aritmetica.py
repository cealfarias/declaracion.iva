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


def test_ventas_omitidas_no_afectan_debito_fiscal(escenario):
    _, db, ids = escenario
    cf = venta_cf(ids["e1"], "CF-OMITIDA", 113.00)
    cf.omitido = True
    ccf = venta_ccf(ids["e1"], "CCF-OMITIDA", 200.00, 26.00)
    ccf.omitido = True
    db.add_all([cf, ccf, venta_cf(ids["e1"], "CF-VIGENTE", 226.00)])
    db.commit()
    r = calculate_liquidacion_for_period(db, ids["e1"], "11", "2026")
    assert r["ventas_cf"] == {"neto": 200.00, "debito": 26.00}
    assert r["ventas_ccf"] == {"neto": 0.00, "debito": 0.00}
    assert r["totales"]["debito"] == 26.00


def test_devoluciones_05_no_se_descontaran_dos_veces_por_version(escenario):
    _, db, ids = escenario
    db.add_all([
        compra(ids["e1"], "COMPRA-V1", 200.00, 26.00, version=1),
        compra(ids["e1"], "NC-V1", 50.00, 6.50, tipo="05", version=1),
        compra(ids["e1"], "NC-V2", 80.00, 10.40, tipo="05", version=2),
        compra(ids["e1"], "NC-OMITIDA", 30.00, 3.90, tipo="05", omitido=True),
        compra(ids["e2"], "NC-AJENA", 100.00, 13.00, tipo="05"),
    ])
    db.commit()
    resultado = calculate_liquidacion_for_period(db, ids["e1"], "11", "2026", version=1)
    compras = resultado["compras"]
    assert compras["neto_gravadas"] == 200.00
    assert compras["credito_gravadas"] == 26.00
    assert compras["devoluciones_neto"] == 50.00
    assert compras["devoluciones_credito"] == 6.50
    assert compras["neto"] == 150.00
    assert compras["credito"] == 19.50


def test_devolucion_05_sin_compra_de_origen_se_muestra_sin_ocultarla(escenario):
    _, db, ids = escenario
    db.add(compra(ids["e1"], "NC-SOLA", 50.00, 6.50, tipo="05"))
    db.commit()
    resultado = calculate_liquidacion_for_period(db, ids["e1"], "11", "2026")
    compras = resultado["compras"]
    assert compras["devoluciones_neto"] == 50.00
    assert compras["devoluciones_credito"] == 6.50
    # Contrato actual: los netos pueden ser negativos; requiere revisión
    # tributaria antes de considerar este período apto para presentación.
    assert compras["neto"] == -50.00
    assert compras["credito"] == -6.50
