import csv
import io
import re
import json
from io import StringIO
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import DteRetencion, Empresa, Liquidacion, DeclaracionEstado

router = APIRouter()

def is_periodo_declarado(db: Session, empresa_id: int, anio: str, mes: str, version: int = 1) -> bool:
    estado = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == "retenciones",
        DeclaracionEstado.version == version
    ).first()
    return estado.declarado if estado else False

def sync_liquidacion_retenciones(db: Session, empresa_id: int, anio: str, mes: str):
    """Sincroniza la sumatoria de retenciones recibidas con la Casilla 162 de la liquidación."""
    total_ret = db.query(DteRetencion).filter(
        DteRetencion.empresa_id == empresa_id,
        DteRetencion.periodo_anio == anio,
        DteRetencion.periodo_mes == mes,
        DteRetencion.omitido == False
    ).all()
    
    suma_ret = round(sum(r.monto_retencion for r in total_ret), 2)
    
    liq = db.query(Liquidacion).filter(
        Liquidacion.empresa_id == empresa_id,
        Liquidacion.anio == anio,
        Liquidacion.mes == mes
    ).first()
    
    if liq:
        liq.retenciones_recibidas = suma_ret
    else:
        liq = Liquidacion(
            empresa_id=empresa_id,
            anio=anio,
            mes=mes,
            retenciones_recibidas=suma_ret
        )
        db.add(liq)
    db.commit()

@router.get("/{empresa_id}")
def get_retenciones(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
    retenciones = db.query(DteRetencion).filter(
        DteRetencion.empresa_id == empresa_id,
        DteRetencion.periodo_mes == mes,
        DteRetencion.periodo_anio == anio,
        DteRetencion.version == version
    ).order_by(DteRetencion.fecha_emision.asc()).all()
    
    validos = [r for r in retenciones if not r.omitido]
    omitidos = [r for r in retenciones if r.omitido]
    
    tot_sujeto = round(sum(r.monto_sujeto for r in validos), 2)
    tot_ret = round(sum(r.monto_retencion for r in validos), 2)
    
    return {
        "empresa": {"id": empresa.id, "razon_social": empresa.razon_social, "nit": empresa.nit},
        "periodo": {"mes": mes, "anio": anio, "version": version},
        "totales": {
            "total_documentos": len(validos),
            "total_monto_sujeto": tot_sujeto,
            "total_retencion": tot_ret
        },
        "documentos": [
            {
                "id": r.id,
                "nit_agente": r.nit_agente,
                "fecha_emision": r.fecha_emision,
                "tipo_documento": r.tipo_documento,
                "serie_documento": r.serie_documento,
                "numero_documento": r.numero_documento,
                "monto_sujeto": r.monto_sujeto,
                "monto_retencion": r.monto_retencion,
                "dui_agente": r.dui_agente,
                "numero_anexo": r.numero_anexo,
                "nombre_agente": r.nombre_agente,
                "omitido": r.omitido
            }
            for r in validos
        ],
        "omitidos": [
            {
                "id": r.id,
                "numero_documento": r.numero_documento,
                "nombre_agente": r.nombre_agente,
                "monto_retencion": r.monto_retencion
            }
            for r in omitidos
        ]
    }

@router.post("/upload/{empresa_id}")
async def upload_retenciones(
    empresa_id: int,
    mes: str = Form(...),
    anio: str = Form(...),
    version: int = Form(1),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
    if is_periodo_declarado(db, empresa_id, anio, mes, version):
        raise HTTPException(status_code=400, detail="El período ya ha sido declarado.")
        
    # Obtener documentos existentes para evitar duplicados en este período
    existentes = set(
        db.query(DteRetencion.numero_documento).filter(
            DteRetencion.empresa_id == empresa_id,
            DteRetencion.periodo_mes == mes,
            DteRetencion.periodo_anio == anio,
            DteRetencion.version == version
        ).all()
    )
    codigos_vistos = {e[0] for e in existentes}
    
    procesados = 0
    ignorados = 0
    errores = []
    
    target_year = int(anio)
    target_month = int(mes)
    
    for f in files:
        if not f.filename.lower().endswith('.json'):
            continue
        try:
            content = await f.read()
            data = json.loads(content.decode('utf-8', errors='ignore'))
            
            ident = data.get('identificacion', {}) or {}
            emisor = data.get('emisor', {}) or {}
            resumen = data.get('resumen', {}) or {}
            
            tipo_dte = str(ident.get('tipoDte', '')).strip()
            if tipo_dte != '07':
                ignorados += 1
                continue
                
            codigo_gen = ident.get('codigoGeneracion', '')
            codigo_gen_limpio = str(codigo_gen).replace('-', '').strip().upper() if codigo_gen else ''
            if not codigo_gen_limpio:
                errores.append(f"{f.filename}: Código de generación vacío")
                continue
                
            if codigo_gen_limpio in codigos_vistos:
                continue
                
            fecha_raw = ident.get('fecEmi', '')
            try:
                fecha_dt = datetime.strptime(fecha_raw[:10], '%Y-%m-%d')
            except Exception:
                errores.append(f"{f.filename}: Fecha inválida ({fecha_raw})")
                continue
                
            diff_meses = (target_year - fecha_dt.year) * 12 + (target_month - fecha_dt.month)
            if diff_meses < 0 or diff_meses > 3:
                errores.append(f"{f.filename}: Fuera de rango permitido ({fecha_raw[:10]})")
                continue
                
            sello = (
                data.get('selloRecibido') or 
                data.get('respuestaMH', {}).get('selloRecibido') or 
                ident.get('selloRecibido') or 
                ''
            )
            sello_limpio = str(sello).strip()
            
            nit_raw = str(emisor.get('nit', '') or '').strip()
            nit_limpio = re.sub(r'[^0-9]', '', nit_raw)
            dui_raw = str(emisor.get('dui', '') or '').strip()
            dui_limpio = re.sub(r'[^0-9]', '', dui_raw)
            
            if nit_limpio:
                nit_agente = nit_limpio.zfill(14)[-14:] if len(nit_limpio) <= 14 else nit_limpio
                dui_agente = ""
            elif dui_limpio:
                nit_agente = ""
                dui_agente = dui_limpio.zfill(9)[-9:] if len(dui_limpio) <= 9 else dui_limpio
            else:
                nit_agente = ""
                dui_agente = ""
                
            monto_sujeto = float(resumen.get('totalSujetoRetencion', 0.0) or 0.0)
            monto_retencion = float(resumen.get('totalIVAretenido', 0.0) or 0.0)
            
            registro = DteRetencion(
                empresa_id=empresa_id,
                periodo_mes=mes,
                periodo_anio=anio,
                nit_agente=nit_agente,
                fecha_emision=fecha_dt.strftime('%d/%m/%Y'),
                tipo_documento="07",
                serie_documento=sello_limpio,
                numero_documento=codigo_gen_limpio,
                monto_sujeto=round(monto_sujeto, 2),
                monto_retencion=round(monto_retencion, 2),
                dui_agente=dui_agente,
                numero_anexo="7", # Oficial F-07 Casilla 162
                nombre_agente=emisor.get('nombre', 'Agente Retenedor'),
                raw_json=data,
                version=version,
                omitido=False
            )
            db.add(registro)
            codigos_vistos.add(codigo_gen_limpio)
            procesados += 1
            
        except Exception as e:
            errores.append(f"{f.filename}: Error {str(e)}")
            
    db.commit()
    sync_liquidacion_retenciones(db, empresa_id, anio, mes)
    
    return {
        "status": "success",
        "procesados": procesados,
        "ignorados_no_07": ignorados,
        "errores": errores
    }

@router.get("/exportar-csv/{empresa_id}")
def exportar_csv_retenciones(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    """
    Genera el archivo CSV oficial para el Ministerio de Hacienda (F-07 V14, Pág. 35):
    - 9 columnas delimitadas por punto y coma (;)
    - A: NIT Agente (14)
    - B: Fecha Emisión (10, DD/MM/AAAA)
    - C: Tipo Documento (2, 07)
    - D: Serie (hasta 100, Sello de Recepción)
    - E: Número Documento (hasta 100, Código de Generación)
    - F: Monto Sujeto (10, 2 decimales)
    - G: Monto Retención 1% (10, 2 decimales)
    - H: DUI Agente (9)
    - I: Número de Anexo (1, '7')
    - Sin encabezados ni títulos
    """
    retenciones = db.query(DteRetencion).filter(
        DteRetencion.empresa_id == empresa_id,
        DteRetencion.periodo_mes == mes,
        DteRetencion.periodo_anio == anio,
        DteRetencion.version == version,
        DteRetencion.omitido == False
    ).order_by(DteRetencion.fecha_emision.asc()).all()
    
    if not retenciones:
        raise HTTPException(status_code=404, detail="No hay retenciones válidas registradas para este período.")
        
    output = StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\r\n')
    
    for r in retenciones:
        writer.writerow([
            r.nit_agente or '',
            r.fecha_emision,
            r.tipo_documento,
            r.serie_documento or '',
            r.numero_documento,
            f"{r.monto_sujeto:.2f}",
            f"{r.monto_retencion:.2f}",
            r.dui_agente or '',
            r.numero_anexo or '7'
        ])
        
    output.seek(0)
    filename = f"Anexo7_Retencion1_Casilla162_{anio}_{mes}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.delete("/{empresa_id}")
def clear_retenciones(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    if is_periodo_declarado(db, empresa_id, anio, mes, version):
        raise HTTPException(status_code=400, detail="El período ya ha sido declarado.")
        
    db.query(DteRetencion).filter(
        DteRetencion.empresa_id == empresa_id,
        DteRetencion.periodo_mes == mes,
        DteRetencion.periodo_anio == anio,
        DteRetencion.version == version
    ).delete()
    
    db.commit()
    sync_liquidacion_retenciones(db, empresa_id, anio, mes)
    return {"message": "Retenciones del período eliminadas correctamente"}
