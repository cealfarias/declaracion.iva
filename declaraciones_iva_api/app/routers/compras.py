import csv
from io import StringIO
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import DteCompra, Empresa
import json

router = APIRouter()

@router.post("/upload")
async def upload_dtes(
    empresa_id: int = Form(...),
    periodo_mes: str = Form(...),
    periodo_anio: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    # Validar que la empresa exista
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    procesados = 0
    errores = []

    for file in files:
        if not file.filename.endswith('.json'):
            errores.append(f"{file.filename}: No es un archivo JSON.")
            continue
            
        content = await file.read()
        try:
            dte_json = json.loads(content)
        except json.JSONDecodeError:
            errores.append(f"{file.filename}: JSON inválido.")
            continue
            
        # Extraer campos clave
        try:
            identificacion = dte_json.get("identificacion", {})
            tipo_dte = identificacion.get("tipoDte", "")
            
            if tipo_dte != "03":
                errores.append(f"{file.filename}: No es un Crédito Fiscal (03).")
                continue
                
            emisor = dte_json.get("emisor", {})
            resumen = dte_json.get("resumen", {})
            
            # Fecha (Formato esperado AAAA-MM-DD, cambiar a DD/MM/AAAA)
            fecha_cruda = identificacion.get("fecEmi", "")
            try:
                fecha_obj = datetime.strptime(fecha_cruda, "%Y-%m-%d")
                fecha_emision = fecha_obj.strftime("%d/%m/%Y")
            except:
                fecha_emision = fecha_cruda
                
            # Evitar duplicados (mismo sello/resolucion en mismo periodo para la empresa)
            sello = identificacion.get("selloRecibido", "")
            codigo_generacion = identificacion.get("codigoGeneracion", "")
            
            # El "Número de Documento" para DTE (clase 4) debe ser el código de generación sin guiones
            num_doc = codigo_generacion.replace("-", "") if codigo_generacion else ""
            
            # Comprobar si ya existe
            existe = db.query(DteCompra).filter(
                DteCompra.empresa_id == empresa_id,
                DteCompra.numero_documento == num_doc
            ).first()
            
            if existe:
                errores.append(f"{file.filename}: Ya fue procesado anteriormente.")
                continue

            nit_proveedor = emisor.get("nit", "")
            nombre_proveedor = emisor.get("nombre", "")
            
            # Montos
            tributos = resumen.get("tributos", [])
            iva = 0.0
            for t in tributos:
                if t.get("codigo") == "20":
                    iva += float(t.get("valor", 0.0))
                    
            total_gravada = float(resumen.get("totalGravada", 0.0))
            total_exenta = float(resumen.get("totalExenta", 0.0))
            total_compras = float(resumen.get("totalPagar", 0.0))
            
            nuevo_dte = DteCompra(
                empresa_id=empresa_id,
                periodo_mes=periodo_mes,
                periodo_anio=periodo_anio,
                fecha_emision=fecha_emision,
                clase_documento="4",
                tipo_documento="03",
                numero_resolucion=num_doc, # Para DTEs se usa el código de generación
                serie_documento=sello,
                numero_documento=num_doc,
                nit_proveedor=nit_proveedor.replace("-", ""),
                nombre_proveedor=nombre_proveedor,
                compras_internas_exentas=total_exenta,
                compras_internas_gravadas=total_gravada,
                credito_fiscal=iva,
                total_compras=total_compras,
                raw_json=dte_json
            )
            
            db.add(nuevo_dte)
            procesados += 1
            
        except Exception as e:
            errores.append(f"{file.filename}: Error procesando datos ({str(e)}).")
            
    db.commit()
    
    return {
        "message": f"Archivos procesados: {procesados} correctos, {len(errores)} errores.",
        "errores": errores
    }

@router.get("/{empresa_id}")
def get_compras(empresa_id: int, mes: str, anio: str, db: Session = Depends(get_db)):
    compras = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio
    ).all()
    
    return compras

@router.put("/update_operacion/{dte_id}")
def update_operacion(dte_id: int, tipo_operacion: str, clasificacion: str, sector: str, tipo_costo: str, db: Session = Depends(get_db)):
    dte = db.query(DteCompra).filter(DteCompra.id == dte_id).first()
    if not dte:
        raise HTTPException(status_code=404, detail="DTE no encontrado")
        
    dte.tipo_operacion = tipo_operacion
    dte.clasificacion = clasificacion
    dte.sector = sector
    dte.tipo_costo_gasto = tipo_costo
    db.commit()
    return {"message": "Actualizado"}

@router.get("/{empresa_id}/export")
def export_csv(empresa_id: int, mes: str, anio: str, db: Session = Depends(get_db)):
    compras = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio
    ).all()
    
    # Generar CSV en memoria
    output = StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    for c in compras:
        row = [
            c.fecha_emision,
            c.clase_documento,
            c.tipo_documento,
            c.numero_resolucion,
            c.nit_proveedor,
            c.nombre_proveedor,
            f"{c.compras_internas_exentas:.2f}",
            f"{c.internaciones_exentas:.2f}",
            f"{c.importaciones_exentas:.2f}",
            f"{c.compras_internas_gravadas:.2f}",
            f"{c.internaciones_gravadas_bienes:.2f}",
            f"{c.importaciones_gravadas_bienes:.2f}",
            f"{c.importaciones_gravadas_servicios:.2f}",
            f"{c.credito_fiscal:.2f}",
            f"{c.total_compras:.2f}",
            "", # DUI Proveedor (vacío si hay NIT)
            c.tipo_operacion if c.tipo_operacion else "0",
            c.clasificacion if c.clasificacion else "0",
            c.sector if c.sector else "0",
            c.tipo_costo_gasto if c.tipo_costo_gasto else "0",
            "3" # Número de Anexo (siempre 3 para compras)
        ]
        writer.writerow(row)
        
    output.seek(0)
    filename = f"Compras_{anio}{mes}.csv"
    
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)
