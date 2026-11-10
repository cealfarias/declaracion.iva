from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, field_validator
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.core.database import get_db
from app.core.authorization import autorizar_empresa_tributaria
from app.models.models import Empresa, DteCompra, DteVenta, DteVentaContribuyente, DteAnulado, Liquidacion

router = APIRouter(dependencies=[Depends(autorizar_empresa_tributaria)])

def get_previous_month_year(mes: str, anio: str):
    m = int(mes)
    a = int(anio)
    if m == 1:
        return '12', str(a - 1)
    return str(m - 1).zfill(2), str(a)

def calculate_liquidacion_for_period(db: Session, empresa_id: int, mes: str, anio: str, version: int = 1):
    # 1. Obtener anulados
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    set_anulados = set()
    for a in anulados:
        if a.codigo_generacion:
            set_anulados.add(a.codigo_generacion)
            set_anulados.add(a.codigo_generacion.replace("-", ""))

    # 2. Ventas Consumidor Final (DteVenta)
    ventas_cf = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio,
        DteVenta.version == version
    ).all()
    
    bruto_cf = 0.0
    for v in ventas_cf:
        cg = v.codigo_generacion or ""
        cg_clean = cg.replace("-", "")
        if not (v.omitido or False) and cg not in set_anulados and cg_clean not in set_anulados:
            bruto_cf += (v.ventas_gravadas or 0.0)
    
    neto_cf = round(bruto_cf / 1.13, 2)
    debito_cf = round(bruto_cf - neto_cf, 2)

    # 3. Ventas Contribuyentes (DteVentaContribuyente)
    ventas_ccf = db.query(DteVentaContribuyente).filter(
        DteVentaContribuyente.empresa_id == empresa_id,
        DteVentaContribuyente.periodo_mes == mes,
        DteVentaContribuyente.periodo_anio == anio,
        DteVentaContribuyente.version == version
    ).all()
    
    neto_ccf = 0.0
    debito_ccf = 0.0
    for v in ventas_ccf:
        nd = v.numero_documento or ""
        nr = v.numero_resolucion or ""
        if (not (v.omitido or False) and
            nd not in set_anulados and nd.replace("-", "") not in set_anulados and
            nr not in set_anulados and nr.replace("-", "") not in set_anulados):
            neto_ccf += (v.ventas_gravadas or 0.0)
            debito_ccf += (v.debito_fiscal or 0.0)

    # 4. Compras (DteCompra)
    compras = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio,
        DteCompra.version == version
    ).all()
    
    neto_compras_gravadas = 0.0 # Casilla 80
    credito_compras_gravadas = 0.0 # Casilla 130
    devoluciones_compras_neto = 0.0 # Casilla 81
    devoluciones_compras_credito = 0.0 # Casilla 131

    for c in compras:
        if not (c.omitido or False):
            if c.tipo_documento == "05":
                devoluciones_compras_neto += (c.compras_internas_gravadas or 0.0)
                devoluciones_compras_credito += (c.credito_fiscal or 0.0)
            else:
                neto_compras_gravadas += (c.compras_internas_gravadas or 0.0) + (c.internaciones_gravadas_bienes or 0.0) + (c.importaciones_gravadas_bienes or 0.0) + (c.importaciones_gravadas_servicios or 0.0)
                credito_compras_gravadas += (c.credito_fiscal or 0.0)

    neto_cf = round(neto_cf, 2)
    debito_cf = round(debito_cf, 2)
    neto_ccf = round(neto_ccf, 2)
    debito_ccf = round(debito_ccf, 2)

    neto_compras_gravadas = round(neto_compras_gravadas, 2)
    credito_compras_gravadas = round(credito_compras_gravadas, 2)
    devoluciones_compras_neto = round(devoluciones_compras_neto, 2)
    devoluciones_compras_credito = round(devoluciones_compras_credito, 2)

    neto_compras_total = round(neto_compras_gravadas - devoluciones_compras_neto, 2)
    credito_compras_neto = round(credito_compras_gravadas - devoluciones_compras_credito, 2)

    total_debito = round(debito_cf + debito_ccf, 2)
    total_credito = round(credito_compras_neto, 2)
    diferencia_periodo = round(total_debito - total_credito, 2)

    if diferencia_periodo > 0:
        impuesto_determinado = diferencia_periodo
        excedente_credito = 0.0
    else:
        impuesto_determinado = 0.0
        excedente_credito = round(abs(diferencia_periodo), 2)

    return {
        'ventas_cf': {'neto': neto_cf, 'debito': debito_cf},
        'ventas_ccf': {'neto': neto_ccf, 'debito': debito_ccf},
        'compras': {
            'neto': neto_compras_total,
            'credito': total_credito,
            'neto_gravadas': neto_compras_gravadas,
            'credito_gravadas': credito_compras_gravadas,
            'devoluciones_neto': devoluciones_compras_neto,
            'devoluciones_credito': devoluciones_compras_credito
        },
        'totales': {
            'debito': total_debito,
            'credito': total_credito,
            'diferencia_periodo': diferencia_periodo,
            'impuesto_determinado': impuesto_determinado,
            'excedente_credito': excedente_credito
        }
    }

def get_remanente_historico(db: Session, empresa_id: int, target_mes: str, target_anio: str) -> float:
    """Calcula eficientemente el remanente de crédito fiscal que viene del mes anterior."""
    target_key = (int(target_anio), int(target_mes))

    # 1. Obtener todas las liquidaciones guardadas manualmente
    liquidaciones = db.query(Liquidacion).filter(Liquidacion.empresa_id == empresa_id).all()
    manuales = {(l.mes, l.anio): (l.remanente_anterior or 0.0) for l in liquidaciones}

    # Si hay registro específico manual para el período meta con valor > 0
    if manuales.get((target_mes, target_anio), 0.0) > 0:
        return manuales[(target_mes, target_anio)]

    # 2. Agrupar compras por período distinguiendo compras (03) y devoluciones (05)
    compras_grp = db.query(
        DteCompra.periodo_mes,
        DteCompra.periodo_anio,
        DteCompra.tipo_documento,
        func.sum(DteCompra.credito_fiscal)
    ).filter(
        DteCompra.empresa_id == empresa_id,
        or_(DteCompra.omitido == False, DteCompra.omitido.is_(None))
    ).group_by(
        DteCompra.periodo_anio, DteCompra.periodo_mes, DteCompra.tipo_documento
    ).all()
    compras_map = {}
    for r in compras_grp:
        k = (r[0], r[1])
        cred = float(r[3] or 0.0)
        if r[2] == "05":
            compras_map[k] = compras_map.get(k, 0.0) - cred
        else:
            compras_map[k] = compras_map.get(k, 0.0) + cred

    # 3. Anulados para filtrar ventas
    anulados = db.query(DteAnulado.codigo_generacion).filter(DteAnulado.empresa_id == empresa_id).all()
    set_anulados = set()
    for a in anulados:
        if a[0]:
            set_anulados.add(a[0])
            set_anulados.add(a[0].replace("-", ""))

    # 4. Ventas CF
    ventas_cf = db.query(
        DteVenta.periodo_mes,
        DteVenta.periodo_anio,
        DteVenta.codigo_generacion,
        DteVenta.ventas_gravadas
    ).filter(
        DteVenta.empresa_id == empresa_id,
        or_(DteVenta.omitido == False, DteVenta.omitido.is_(None))
    ).all()
    
    ventas_cf_map = {}
    for v in ventas_cf:
        cg = v.codigo_generacion or ""
        if cg not in set_anulados and cg.replace("-", "") not in set_anulados:
            k = (v.periodo_mes, v.periodo_anio)
            ventas_cf_map[k] = ventas_cf_map.get(k, 0.0) + (v.ventas_gravadas or 0.0)
            
    # Convertir bruto CF a débito CF
    debito_cf_map = {}
    for k, bruto in ventas_cf_map.items():
        neto = round(bruto / 1.13, 2)
        debito_cf_map[k] = round(bruto - neto, 2)

    # 5. Ventas CCF
    ventas_ccf = db.query(
        DteVentaContribuyente.periodo_mes,
        DteVentaContribuyente.periodo_anio,
        DteVentaContribuyente.numero_documento,
        DteVentaContribuyente.numero_resolucion,
        DteVentaContribuyente.debito_fiscal
    ).filter(
        DteVentaContribuyente.empresa_id == empresa_id,
        or_(DteVentaContribuyente.omitido == False, DteVentaContribuyente.omitido.is_(None))
    ).all()
    
    debito_ccf_map = {}
    for v in ventas_ccf:
        nd = v.numero_documento or ""
        nr = v.numero_resolucion or ""
        if (nd not in set_anulados and nd.replace("-", "") not in set_anulados and
            nr not in set_anulados and nr.replace("-", "") not in set_anulados):
            k = (v.periodo_mes, v.periodo_anio)
            debito_ccf_map[k] = debito_ccf_map.get(k, 0.0) + (v.debito_fiscal or 0.0)

    # Periodos cronológicos previos al target
    all_periods = set(compras_map.keys()) | set(debito_cf_map.keys()) | set(debito_ccf_map.keys()) | set(manuales.keys())
    past_periods = sorted(
        [p for p in all_periods if (int(p[1]), int(p[0])) < target_key],
        key=lambda x: (int(x[1]), int(x[0]))
    )

    if not past_periods:
        return 0.0

    remanente_acumulado = 0.0
    for p in past_periods:
        if manuales.get(p, 0.0) > 0:
            remanente_acumulado = manuales[p]

        debito = round(debito_cf_map.get(p, 0.0) + debito_ccf_map.get(p, 0.0), 2)
        credito = round(compras_map.get(p, 0.0), 2)
        dif = round(debito - credito, 2)

        if dif > 0:
            imp_det = dif
            rem_aplicado = min(imp_det, remanente_acumulado)
            remanente_acumulado = round(remanente_acumulado - rem_aplicado, 2)
        else:
            excedente = round(abs(dif), 2)
            remanente_acumulado = round(excedente + remanente_acumulado, 2)

    return round(remanente_acumulado, 2)

@router.get('/{empresa_id}')
def get_liquidacion(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    validar_periodo_fiscal(mes, anio)
    data = calculate_liquidacion_for_period(db, empresa_id, mes, anio, version)
    
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.mes == mes,
        Liquidacion.anio == anio
    ).first()
    
    # 1. Remanente anterior (Casilla 110)
    remanente_anterior = (liq.remanente_anterior or 0.0) if liq else 0.0
    if remanente_anterior == 0.0:
        remanente_anterior = get_remanente_historico(db, empresa_id, mes, anio)
    
    data['remanente_anterior'] = round(remanente_anterior, 2)

    # 2. Ajustes F-07 (Retenciones, Percepciones, Anticipos)
    retenciones_recibidas = round((liq.retenciones_recibidas or 0.0) if liq else 0.0, 2)
    percepciones_recibidas = round((liq.percepciones_recibidas or 0.0) if liq else 0.0, 2)
    retenciones_efectuadas = round((liq.retenciones_efectuadas or 0.0) if liq else 0.0, 2)
    percepciones_efectuadas = round((liq.percepciones_efectuadas or 0.0) if liq else 0.0, 2)
    anticipo_cuenta_2 = round((liq.anticipo_cuenta_2 or 0.0) if liq else 0.0, 2)

    data['retenciones_recibidas'] = retenciones_recibidas
    data['percepciones_recibidas'] = percepciones_recibidas
    data['retenciones_efectuadas'] = retenciones_efectuadas
    data['percepciones_efectuadas'] = percepciones_efectuadas
    data['anticipo_cuenta_2'] = anticipo_cuenta_2

    # 3. Liquidación paso a paso según el Formulario F-07 (Ministerio de Hacienda)
    total_debito = data['totales']['debito']
    total_credito = data['totales']['credito']
    diferencia = data['totales']['diferencia_periodo']

    if diferencia > 0:
        # Débito > Crédito: Hay Impuesto Determinado (Casilla 160)
        impuesto_determinado = diferencia
        excedente_credito = 0.0
        
        # Aplicación del Remanente Anterior (Casilla 110) contra el Impuesto Determinado
        remanente_aplicado = min(impuesto_determinado, remanente_anterior)
        saldo_impuesto_1 = round(impuesto_determinado - remanente_aplicado, 2)
        remanente_no_utilizado = round(remanente_anterior - remanente_aplicado, 2)
    else:
        # Crédito >= Débito: Hay Excedente de Crédito del período (Casilla 155)
        impuesto_determinado = 0.0
        excedente_credito = round(abs(diferencia), 2)
        remanente_aplicado = 0.0
        saldo_impuesto_1 = 0.0
        remanente_no_utilizado = remanente_anterior

    # Deducciones adicionales (Retenciones y Percepciones practicadas a la empresa + Anticipo 2%)
    total_deducciones = round(retenciones_recibidas + percepciones_recibidas + anticipo_cuenta_2, 2)
    if saldo_impuesto_1 > 0:
        deducciones_aplicadas = min(saldo_impuesto_1, total_deducciones)
        impuesto_propio = round(saldo_impuesto_1 - deducciones_aplicadas, 2)
        deducciones_sobrantes = round(total_deducciones - deducciones_aplicadas, 2)
    else:
        deducciones_aplicadas = 0.0
        impuesto_propio = 0.0
        deducciones_sobrantes = total_deducciones

    # Operaciones a enterar de terceros
    total_terceros = round(retenciones_efectuadas + percepciones_efectuadas, 2)
    impuesto_a_pagar = round(impuesto_propio + total_terceros, 2)

    # Separar el crédito fiscal del excedente de deducciones tributarias.
    # No se debe arrastrar el excedente de deducciones como crédito fiscal.
    remanente_credito_fiscal_siguiente = round(excedente_credito + remanente_no_utilizado, 2)
    excedente_deducciones_pendiente = round(deducciones_sobrantes, 2)
    # Alias histórico para consumidores existentes: exclusivamente crédito fiscal.
    remanente_siguiente = remanente_credito_fiscal_siguiente

    # Estructura enriquecida para el frontend
    data['liquidacion'] = {
        'total_debito': total_debito,
        'total_credito': total_credito,
        'diferencia_periodo': diferencia,
        'impuesto_determinado': impuesto_determinado,
        'excedente_credito': excedente_credito,
        'remanente_anterior': remanente_anterior,
        'remanente_aplicado': remanente_aplicado,
        'remanente_no_utilizado': remanente_no_utilizado,
        'total_deducciones': total_deducciones,
        'deducciones_aplicadas': deducciones_aplicadas,
        'deducciones_sobrantes': deducciones_sobrantes,
        'total_terceros': total_terceros,
        'impuesto_propio': impuesto_propio,
        'impuesto_a_pagar': impuesto_a_pagar,
        'remanente_siguiente': remanente_siguiente,
        'remanente_credito_fiscal_siguiente': remanente_credito_fiscal_siguiente,
        'excedente_deducciones_pendiente': excedente_deducciones_pendiente
    }

    # Campos de compatibilidad directa
    data['impuesto_a_pagar'] = impuesto_a_pagar
    data['remanente_siguiente'] = remanente_siguiente
    data['remanente_credito_fiscal_siguiente'] = remanente_credito_fiscal_siguiente
    data['excedente_deducciones_pendiente'] = excedente_deducciones_pendiente
    
    return data

class AjustesLiquidacionRequest(BaseModel):
    remanente_anterior: Optional[Decimal] = Decimal("0.00")
    retenciones_recibidas: Optional[Decimal] = Decimal("0.00")
    percepciones_recibidas: Optional[Decimal] = Decimal("0.00")
    retenciones_efectuadas: Optional[Decimal] = Decimal("0.00")
    percepciones_efectuadas: Optional[Decimal] = Decimal("0.00")
    anticipo_cuenta_2: Optional[Decimal] = Decimal("0.00")

    @field_validator(
        "remanente_anterior", "retenciones_recibidas", "percepciones_recibidas",
        "retenciones_efectuadas", "percepciones_efectuadas", "anticipo_cuenta_2",
        mode="before",
    )
    @classmethod
    def validar_importe(cls, value):
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("El importe debe ser numérico.")
        try:
            importe = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("El importe debe ser numérico.")
        if not importe.is_finite() or importe < 0:
            raise ValueError("El importe debe ser finito y no negativo.")
        if importe.as_tuple().exponent < -2:
            raise ValueError("El importe admite como máximo dos decimales.")
        return importe

def validar_periodo_fiscal(mes: str, anio: str) -> None:
    """Rechaza períodos mal formados antes de acceder a PostgreSQL."""
    if mes not in {f"{numero:02d}" for numero in range(1, 13)}:
        raise HTTPException(status_code=422, detail="El mes debe estar entre 01 y 12.")
    if len(anio) != 4 or not anio.isascii() or not anio.isdecimal() or anio == "0000":
        raise HTTPException(status_code=422, detail="El año debe contener cuatro dígitos válidos.")


def validar_remanente_query(valor: str) -> Decimal:
    """Valida el importe recibido en la ruta de remanente antes de consultar o escribir."""
    try:
        importe = Decimal(valor)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Remanente no numérico.")
    if not importe.is_finite() or importe < 0 or importe.as_tuple().exponent < -2:
        raise HTTPException(
            status_code=422,
            detail="El remanente debe ser finito, no negativo y tener máximo dos decimales.",
        )
    return importe


@router.post('/{empresa_id}/remanente')
def update_remanente(empresa_id: int, mes: str, anio: str, remanente: str, db: Session = Depends(get_db)):
    validar_periodo_fiscal(mes, anio)
    importe = validar_remanente_query(remanente)
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.mes == mes,
        Liquidacion.anio == anio
    ).first()
    
    if not liq:
        liq = Liquidacion(empresa_id=empresa_id, mes=mes, anio=anio, remanente_anterior=importe)
        db.add(liq)
    else:
        liq.remanente_anterior = importe
        
    db.commit()
    return {'mensaje': 'Remanente actualizado correctamente', 'remanente': float(importe)}

@router.post('/{empresa_id}/ajustes')
def update_ajustes(empresa_id: int, mes: str, anio: str, req: AjustesLiquidacionRequest, db: Session = Depends(get_db)):
    validar_periodo_fiscal(mes, anio)
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.mes == mes,
        Liquidacion.anio == anio
    ).first()
    
    if not liq:
        liq = Liquidacion(
            empresa_id=empresa_id,
            mes=mes,
            anio=anio,
            remanente_anterior=req.remanente_anterior or 0.0,
            retenciones_recibidas=req.retenciones_recibidas or 0.0,
            percepciones_recibidas=req.percepciones_recibidas or 0.0,
            retenciones_efectuadas=req.retenciones_efectuadas or 0.0,
            percepciones_efectuadas=req.percepciones_efectuadas or 0.0,
            anticipo_cuenta_2=req.anticipo_cuenta_2 or 0.0
        )
        db.add(liq)
    else:
        if req.remanente_anterior is not None:
            liq.remanente_anterior = req.remanente_anterior
        if req.retenciones_recibidas is not None:
            liq.retenciones_recibidas = req.retenciones_recibidas
        if req.percepciones_recibidas is not None:
            liq.percepciones_recibidas = req.percepciones_recibidas
        if req.retenciones_efectuadas is not None:
            liq.retenciones_efectuadas = req.retenciones_efectuadas
        if req.percepciones_efectuadas is not None:
            liq.percepciones_efectuadas = req.percepciones_efectuadas
        if req.anticipo_cuenta_2 is not None:
            liq.anticipo_cuenta_2 = req.anticipo_cuenta_2
            
    db.commit()
    return {'mensaje': 'Ajustes de liquidación guardados correctamente'}
