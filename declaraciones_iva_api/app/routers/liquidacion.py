from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import calendar

from app.core.database import get_db
from app.models.models import Empresa, DteCompra, DteVenta, DteVentaContribuyente, DteAnulado, Liquidacion

router = APIRouter()

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
    set_anulados = {a.codigo_generacion for a in anulados}

    # 2. Ventas Consumidor Final (DteVenta)
    ventas_cf = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio,
        DteVenta.version == version
    ).all()
    
    bruto_cf = 0.0
    for v in ventas_cf:
        if v.codigo_generacion not in set_anulados:
            bruto_cf += v.ventas_gravadas
    
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
        if v.numero_documento not in set_anulados:
            neto_ccf += v.ventas_gravadas
            debito_ccf += v.debito_fiscal

    # 4. Compras (DteCompra)
    compras = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio,
        DteCompra.version == version
    ).all()
    
    neto_compras = 0.0
    credito_compras = 0.0
    for c in compras:
        # Simplificacion: sumamos todo el credito fiscal
        neto_compras += c.compras_internas_gravadas + c.internaciones_gravadas_bienes + c.importaciones_gravadas_bienes + c.importaciones_gravadas_servicios
        credito_compras += c.credito_fiscal

    neto_ccf = round(neto_ccf, 2)
    debito_ccf = round(debito_ccf, 2)
    neto_compras = round(neto_compras, 2)
    credito_compras = round(credito_compras, 2)

    total_debito = round(debito_cf + debito_ccf, 2)
    total_credito = round(credito_compras, 2)

    return {
        'ventas_cf': {'neto': neto_cf, 'debito': debito_cf},
        'ventas_ccf': {'neto': neto_ccf, 'debito': debito_ccf},
        'compras': {'neto': neto_compras, 'credito': total_credito},
        'totales': {
            'debito': total_debito,
            'credito': total_credito
        }
    }

def get_remanente_recursivo(db: Session, empresa_id: int, mes: str, anio: str, max_depth: int = 12):
    if max_depth == 0:
        return 0.0
        
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.mes == mes,
        Liquidacion.anio == anio
    ).first()
    
    if liq and liq.remanente_anterior > 0: # Si hay uno manual forzado
        # Calculamos el resultado de ese mes
        data = calculate_liquidacion_for_period(db, empresa_id, mes, anio)
        impuesto = data['totales']['debito'] - data['totales']['credito'] - liq.remanente_anterior
        return abs(impuesto) if impuesto < 0 else 0.0
        
    # Si no, calculamos recursivamente el de este mes
    prev_m, prev_a = get_previous_month_year(mes, anio)
    rem_ant = get_remanente_recursivo(db, empresa_id, prev_m, prev_a, max_depth - 1)
    
    data = calculate_liquidacion_for_period(db, empresa_id, mes, anio)
    if data['totales']['debito'] == 0 and data['totales']['credito'] == 0 and rem_ant == 0:
        return 0.0 # Mes vacio
        
    impuesto = data['totales']['debito'] - data['totales']['credito'] - rem_ant
    return abs(impuesto) if impuesto < 0 else 0.0

@router.get('/{empresa_id}')
def get_liquidacion(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    data = calculate_liquidacion_for_period(db, empresa_id, mes, anio, version)
    
    # Obtener el registro de liquidacion actual si existe
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.mes == mes,
        Liquidacion.anio == anio
    ).first()
    
    # Si tiene remanente manual, lo usamos. Si no, o si es 0, intentamos calcular el del mes anterior
    remanente_anterior = liq.remanente_anterior if liq else 0.0
    
    if remanente_anterior == 0.0:
        prev_m, prev_a = get_previous_month_year(mes, anio)
        remanente_anterior = round(get_remanente_recursivo(db, empresa_id, prev_m, prev_a), 2)
    
    data['remanente_anterior'] = remanente_anterior
    
    # Resultado
    resultado = data['totales']['debito'] - data['totales']['credito'] - remanente_anterior
    data['impuesto_a_pagar'] = round(resultado if resultado > 0 else 0.0, 2)
    data['remanente_siguiente'] = round(abs(resultado) if resultado < 0 else 0.0, 2)
    
    return data

@router.post('/{empresa_id}/remanente')
def update_remanente(empresa_id: int, mes: str, anio: str, remanente: float, db: Session = Depends(get_db)):
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.mes == mes,
        Liquidacion.anio == anio
    ).first()
    
    if not liq:
        liq = Liquidacion(empresa_id=empresa_id, mes=mes, anio=anio, remanente_anterior=remanente)
        db.add(liq)
    else:
        liq.remanente_anterior = remanente
        
    db.commit()
    return {'mensaje': 'Remanente actualizado correctamente', 'remanente': remanente}
