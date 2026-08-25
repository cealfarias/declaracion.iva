from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import Response
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
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            row = parse_compras(dte_json)
            writer.writerow(row)
            
            # Persistencia en BD
            if periodo_id:
                ident = dte_json.get("identificacion", {})
                db_dte = DteProcesado(
                    periodo_id=periodo_id,
                    tipo_anexo='compras',
                    json_original=dte_json,
                    fecha_emision=ident.get("fecEmi", ""),
                    numero_control=ident.get("numeroControl", ""),
                    codigo_generacion=ident.get("codigoGeneracion", ""),
                    monto_total=str(dte_json.get("resumen", {}).get("montoTotalOperacion", 0))
                )
                db.add(db_dte)
        except Exception as e:
            print(f"Error parseando {file.filename}: {e}")
            
    if periodo_id:
        db.commit()
            
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anexo3_compras.csv"}
    )

@router.post("/procesar/ventas-contribuyentes")
async def procesar_ventas(
    files: List[UploadFile] = File(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            row = parse_ventas_contribuyente(dte_json)
            writer.writerow(row)
            
            # Persistencia en BD
            if periodo_id:
                ident = dte_json.get("identificacion", {})
                db_dte = DteProcesado(
                    periodo_id=periodo_id,
                    tipo_anexo='ventas_contribuyente',
                    json_original=dte_json,
                    fecha_emision=ident.get("fecEmi", ""),
                    numero_control=ident.get("numeroControl", ""),
                    codigo_generacion=ident.get("codigoGeneracion", ""),
                    monto_total=str(dte_json.get("resumen", {}).get("montoTotalOperacion", 0))
                )
                db.add(db_dte)
        except Exception as e:
            print(f"Error parseando {file.filename}: {e}")
            
    if periodo_id:
        db.commit()
            
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anexo1_ventas_contribuyentes.csv"}
    )

@router.post("/procesar/ventas-consumidor")
async def procesar_ventas_consumidor(
    files: List[UploadFile] = File(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            row = parse_ventas_consumidor(dte_json)
            writer.writerow(row)
            
            # Persistencia en BD
            if periodo_id:
                ident = dte_json.get("identificacion", {})
                db_dte = DteProcesado(
                    periodo_id=periodo_id,
                    tipo_anexo='ventas_consumidor',
                    json_original=dte_json,
                    fecha_emision=ident.get("fecEmi", ""),
                    numero_control=ident.get("numeroControl", ""),
                    codigo_generacion=ident.get("codigoGeneracion", ""),
                    monto_total=str(dte_json.get("resumen", {}).get("montoTotalOperacion", 0))
                )
                db.add(db_dte)
        except Exception as e:
            print(f"Error parseando {file.filename}: {e}")
            
    if periodo_id:
        db.commit()
            
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anexo2_ventas_consumidor.csv"}
    )
