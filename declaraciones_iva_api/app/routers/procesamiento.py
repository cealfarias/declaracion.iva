from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import json
import csv
import io
from typing import List, Optional

from app.core.dte_parser import parse_compras, parse_ventas_contribuyente, parse_ventas_consumidor
from app.core.database import get_db
from app.models.models import DteProcesado

router = APIRouter()

@router.post("/procesar/compras")
async def procesar_compras(
    files: List[UploadFile] = File(...), 
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0
    total_gravado = 0.0
    total_iva = 0.0
    total_general = 0.0
    codigos_vistos = set()
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            codigo_gen = dte_json.get("identificacion", {}).get("codigoGeneracion", "").replace("-", "").upper()
            
            if codigo_gen in codigos_vistos:
                continue # Skip duplicated
            codigos_vistos.add(codigo_gen)
            
            row = parse_compras(dte_json)
            writer.writerow(row)
            
            total_docs += 1
            total_gravado += float(row[9]) + float(row[11]) + float(row[12]) # J, L, M
            total_iva += float(row[13]) # N
            total_general += float(row[14]) # O
            
            if periodo_id:
                db_dte = DteProcesado(
                    periodo_id=periodo_id,
                    tipo_documento=dte_json.get("identificacion", {}).get("tipoDte", "00"),
                    clasificacion='compra',
                    datos_json=dte_json
                )
                db.add(db_dte)
        except Exception as e:
            print(f"Error parseando {file.filename}: {e}")
            
    if periodo_id:
        db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {
            "documentos": total_docs,
            "gravado": total_gravado,
            "iva": total_iva,
            "total": total_general
        }
    })

@router.post("/procesar/ventas-contribuyentes")
async def procesar_ventas(
    files: List[UploadFile] = File(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0
    total_gravado = 0.0
    total_iva = 0.0
    total_general = 0.0
    codigos_vistos = set()
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            codigo_gen = dte_json.get("identificacion", {}).get("codigoGeneracion", "").replace("-", "").upper()
            if codigo_gen in codigos_vistos: continue
            codigos_vistos.add(codigo_gen)
            
            row = parse_ventas_contribuyente(dte_json)
            writer.writerow(row)
            
            total_docs += 1
            total_gravado += float(row[11]) # L (Gravadas)
            total_iva += float(row[12]) # M (Debito Fiscal)
            total_general += float(row[15]) # P (Total)
            
            if periodo_id:
                db_dte = DteProcesado(
                    periodo_id=periodo_id,
                    tipo_documento=dte_json.get("identificacion", {}).get("tipoDte", "03"),
                    clasificacion='venta',
                    datos_json=dte_json
                )
                db.add(db_dte)
        except Exception as e:
            print(f"Error parseando {file.filename}: {e}")
            
    if periodo_id:
        db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {
            "documentos": total_docs,
            "gravado": total_gravado,
            "iva": total_iva,
            "total": total_general
        }
    })

@router.post("/procesar/ventas-consumidor")
async def procesar_ventas_consumidor(
    files: List[UploadFile] = File(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0
    total_gravado = 0.0
    total_iva = 0.0
    total_general = 0.0
    codigos_vistos = set()
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            codigo_gen = dte_json.get("identificacion", {}).get("codigoGeneracion", "").replace("-", "").upper()
            if codigo_gen in codigos_vistos: continue
            codigos_vistos.add(codigo_gen)
            
            row = parse_ventas_consumidor(dte_json)
            writer.writerow(row)
            
            total_docs += 1
            total_gravado += float(row[13]) # N (Ventas Gravadas Locales)
            # FCF IVA is typically included in Gravadas but we can extract it or leave 0
            # F07 Anexo 2 doesn't have an explicit IVA column like Anexo 1
            total_general += float(row[19]) # T (Total)
            
            if periodo_id:
                db_dte = DteProcesado(
                    periodo_id=periodo_id,
                    tipo_documento=dte_json.get("identificacion", {}).get("tipoDte", "01"),
                    clasificacion='venta_consumidor',
                    datos_json=dte_json
                )
                db.add(db_dte)
        except Exception as e:
            print(f"Error parseando {file.filename}: {e}")
            
    if periodo_id:
        db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {
            "documentos": total_docs,
            "gravado": total_gravado,
            "iva": 0.0, # Anexo 2 usually has IVA included in the total
            "total": total_general
        }
    })
