import csv
from io import StringIO
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import DteVenta, Empresa, DeclaracionEstado
from app.routers.compras import is_periodo_declarado

router = APIRouter()

@router.delete("/limpiar/{empresa_id}")
def limpiar_periodo(empresa_id: int, mes: str, anio: str, db: Session = Depends(get_db)):
    if is_periodo_declarado(db, empresa_id, anio, mes):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio
    ).delete()
    db.commit()
    return {"mensaje": "Período limpiado correctamente"}

@router.post("/upload")
async def upload_dtes_cf(
    empresa_id: int = Form(...),
    periodo_mes: str = Form(...),
    periodo_anio: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if is_periodo_declarado(db, empresa_id, periodo_anio, periodo_mes):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    procesados = 0
    errores = []

    for file in files:
        if not file.filename.lower().endswith(".json"):
            errores.append(f"{file.filename}: No es un archivo JSON.")
            continue
            
        content = await file.read()
        decoded_content = None
        dte_json = None
        
        for encoding in ["utf-8-sig", "latin-1", "windows-1252", "utf-16"]:
            try:
                decoded_content = content.decode(encoding).strip()
                dte_json = json.loads(decoded_content)
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
                
        if dte_json is None:
            errores.append(f"{file.filename}: No es un JSON válido o tiene codificación incorrecta.")
            continue
            
        try:
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
                
            identificacion = dte_json.get("identificacion", {})
            tipo_dte = identificacion.get("tipoDte", "")
            
            if tipo_dte != "01": # 01 es Factura, 11 es Exportacion
                errores.append(f"{file.filename}: No es una Factura de Consumidor Final (01). Encontrado: {tipo_dte}")
                continue
                
            resumen = dte_json.get("resumen", {})
            receptor = dte_json.get("receptor", {}) or {}
            
            fecha_cruda = identificacion.get("fecEmi", "")
            try:
                fecha_obj = datetime.strptime(fecha_cruda, "%Y-%m-%d")
                fecha_emision = fecha_obj.strftime("%d/%m/%Y")
            except:
                fecha_emision = fecha_cruda
                
            codigo_generacion = identificacion.get("codigoGeneracion", "")
            sello = identificacion.get("selloRecibido", "")
            if not sello:
                sello = dte_json.get("selloRecibido", "")
            if not sello:
                sello = dte_json.get("selloRecepcion", "")
            if not sello:
                sello = identificacion.get("numeroControl", "")
            
            existe = db.query(DteVenta).filter(
                DteVenta.empresa_id == empresa_id,
                DteVenta.codigo_generacion == codigo_generacion
            ).first()
            
            if existe:
                errores.append(f"{file.filename}: Ya fue procesado anteriormente.")
                continue

            nit_cliente = receptor.get("nit", receptor.get("nrc", receptor.get("numDocumento", "")))
            if nit_cliente:
                nit_cliente = nit_cliente.replace("-", "")

            total_exenta = float(resumen.get("totalExenta", 0.0))
            total_no_suj = float(resumen.get("totalNoSuj", 0.0))
            total_pagar = float(resumen.get("totalPagar", 0.0))
            ventas_gravadas = total_pagar - total_exenta - total_no_suj

            nuevo_dte = DteVenta(
                empresa_id=empresa_id,
                periodo_mes=periodo_mes,
                periodo_anio=periodo_anio,
                fecha_emision=fecha_emision,
                clase_documento="4",
                tipo_documento=tipo_dte,
                numero_resolucion="N/A",
                serie_documento="N/A",
                numero_control_del="N/A",
                numero_control_al="N/A",
                codigo_generacion=codigo_generacion,
                sello_recepcion=sello,
                nit_cliente=nit_cliente,
                ventas_exentas=total_exenta,
                ventas_no_sujetas=total_no_suj,
                ventas_gravadas=ventas_gravadas,
                exportaciones=0.0,
                ventas_zona_franca=0.0,
                ventas_terceros=0.0,
                total_ventas=total_pagar,
                raw_json=dte_json
            )
            db.add(nuevo_dte)
            db.commit()
            procesados += 1
            
        except Exception as e:
            db.rollback()
            errores.append(f"{file.filename}: Error interno ({str(e)}).")

    return {
        "procesados": procesados,
        "errores": errores
    }

@router.get("/list/{empresa_id}")
def get_ventas(empresa_id: int, mes: str, anio: str, db: Session = Depends(get_db)):
    ventas = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio
    ).all()
    return ventas

@router.get("/export_csv/{empresa_id}")
def export_ventas_csv(empresa_id: int, mes: str, anio: str, db: Session = Depends(get_db)):
    ventas = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio
    ).order_by(DteVenta.fecha_emision).all()

    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="
")

    for v in ventas:
        def fmt(val):
            return f"{val:.0f}" if val.is_integer() else str(val)
            
        row = [
            v.fecha_emision,
            v.clase_documento,
            v.tipo_documento,
            v.numero_resolucion,
            v.serie_documento,
            v.numero_control_del,
            v.numero_control_al,
            v.codigo_generacion,
            v.sello_recepcion,
            v.nit_cliente or "",
            fmt(v.ventas_exentas),
            fmt(v.ventas_no_sujetas),
            "0", # Ventas No Sujetas Exportaciones
            fmt(v.ventas_gravadas), 
            "0", # Ventas Zona Franca
            "0", # Exportaciones Fuera CA
            "0", # Exportaciones CA
            "0", # Ventas a Terceros
            "0", # IVA Retenido?
            fmt(v.total_ventas),
            "1", # Tipo Operacion / Anexo
            "3", # Ingreso
            "2"  # ???
        ]
        writer.writerow(row)

    output.seek(0)
    content = output.getvalue().encode("utf-8")

    headers = {
        "Content-Disposition": f"attachment; filename="F07_Ventas_CF_{mes}_{anio}.csv""
    }

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers=headers
    )
