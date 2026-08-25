from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
import csv
import io
from typing import List, Optional

from app.core.dte_parser import parse_compras, parse_ventas_contribuyente, parse_ventas_consumidor
from app.core.database import get_db
from app.models.models import DteProcesado, UsuarioEmpresa

router = APIRouter()

def _validar_dte(dte_json, mes_declaracion, anio_declaracion, empresa_nrc, empresa_nit, tipo_anexo, filename, db: Session):
    ident = dte_json.get("identificacion", {})
    codigo_gen = ident.get("codigoGeneracion", "").replace("-", "").upper()
    fecha_raw = ident.get("fecEmi", "")
    
    # 1. Validar Fechas (Ley MH: No futuros, máximo 3 meses atrás)
    try:
        fecha_dte = datetime.strptime(fecha_raw[:10], '%Y-%m-%d')
        meses_diferencia = (anio_declaracion - fecha_dte.year) * 12 + (mes_declaracion - fecha_dte.month)
        
        if meses_diferencia < 0:
            return False, f"Fecha futura no válida ({fecha_raw[:10]})"
        if meses_diferencia > 3:
            return False, f"DTE vencido, excede 3 meses legales ({fecha_raw[:10]})"
    except Exception:
        return False, "Fallo al parsear fecha del DTE"
        
    # 2. Validar Pertenencia (Propiedad del DTE)
    receptor = dte_json.get("receptor", {})
    emisor = dte_json.get("emisor", {})
    
    if tipo_anexo == 'compras':
        rec_nit = str(receptor.get("nit", "")).replace("-", "")
        rec_nrc = str(receptor.get("nrc", "")).replace("-", "")
        if rec_nrc != empresa_nrc and rec_nit != empresa_nit:
            return False, f"El DTE de compra no pertenece a esta empresa (Receptor difiere)"
    else:
        emi_nit = str(emisor.get("nit", "")).replace("-", "")
        emi_nrc = str(emisor.get("nrc", "")).replace("-", "")
        if emi_nrc != empresa_nrc and emi_nit != empresa_nit:
            return False, f"El DTE de venta no pertenece a esta empresa (Emisor difiere)"
            
    # 3. Validar Duplicados en Base de Datos
    # Nota: Consultar JSON en BD (PostgreSQL) o de forma segura
    existente = db.query(DteProcesado).filter(
        DteProcesado.datos_json.op('->')('identificacion').op('->>')('codigoGeneracion') == ident.get("codigoGeneracion", "")
    ).first()
    
    if existente:
        return False, f"DTE ya declarado anteriormente en el sistema"

    return True, codigo_gen

@router.post("/procesar/compras")
async def procesar_compras(
    files: List[UploadFile] = File(...), 
    mes: int = Form(...),
    anio: int = Form(...),
    usuario_id: int = Form(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo:
        raise HTTPException(status_code=400, detail="Usuario no tiene empresa vinculada")
        
    empresa = vinculo.empresa
    emp_nrc = empresa.nrc.replace("-", "")
    emp_nit = empresa.nit.replace("-", "")

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0
    total_gravado = 0.0
    total_iva = 0.0
    total_general = 0.0
    codigos_vistos = set()
    
    registros_validos = []
    omitidos = []
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'compras', file.filename, db)
            
            if not es_valido:
                omitidos.append({"archivo": file.filename, "motivo": resultado})
                continue
                
            codigo_gen = resultado
            if codigo_gen in codigos_vistos:
                omitidos.append({"archivo": file.filename, "motivo": "Duplicado en este mismo lote de archivos"})
                continue
                
            codigos_vistos.add(codigo_gen)
            row = parse_compras(dte_json)
            
            # Formatear números a 2 decimales seguros para la UI
            row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
            
            writer.writerow(row)
            registros_validos.append(row)
            
            total_docs += 1
            total_gravado += float(row[9]) + float(row[11]) + float(row[12]) # J, L, M
            total_iva += float(row[13]) # N
            total_general += float(row[14]) # O
            
            if periodo_id:
                db.add(DteProcesado(
                    periodo_id=periodo_id,
                    tipo_documento=dte_json.get("identificacion", {}).get("tipoDte", "00"),
                    clasificacion='compra',
                    datos_json=dte_json
                ))
        except json.JSONDecodeError:
            omitidos.append({"archivo": file.filename, "motivo": "Archivo no es un JSON válido"})
        except Exception as e:
            omitidos.append({"archivo": file.filename, "motivo": f"Error estructural: {str(e)}"})
            
    if periodo_id: db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {
            "documentos": total_docs,
            "gravado": total_gravado,
            "iva": total_iva,
            "total": total_general
        },
        "registros": registros_validos,
        "omitidos": omitidos
    })

@router.post("/procesar/ventas-contribuyentes")
async def procesar_ventas(
    files: List[UploadFile] = File(...),
    mes: int = Form(...),
    anio: int = Form(...),
    usuario_id: int = Form(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    empresa = vinculo.empresa
    emp_nrc, emp_nit = empresa.nrc.replace("-", ""), empresa.nit.replace("-", "")

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0; total_gravado = 0.0; total_iva = 0.0; total_general = 0.0
    codigos_vistos = set(); registros_validos = []; omitidos = []
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas', file.filename, db)
            if not es_valido:
                omitidos.append({"archivo": file.filename, "motivo": resultado})
                continue
                
            if resultado in codigos_vistos:
                omitidos.append({"archivo": file.filename, "motivo": "Duplicado en lote"})
                continue
            codigos_vistos.add(resultado)
            
            row = parse_ventas_contribuyente(dte_json)
            row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
            
            writer.writerow(row)
            registros_validos.append(row)
            
            total_docs += 1
            total_gravado += float(row[11])
            total_iva += float(row[12])
            total_general += float(row[15])
            
            if periodo_id:
                db.add(DteProcesado(periodo_id=periodo_id, tipo_documento="03", clasificacion='venta', datos_json=dte_json))
        except Exception as e:
            omitidos.append({"archivo": file.filename, "motivo": str(e)})
            
    if periodo_id: db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {"documentos": total_docs, "gravado": total_gravado, "iva": total_iva, "total": total_general},
        "registros": registros_validos,
        "omitidos": omitidos
    })

@router.post("/procesar/ventas-consumidor")
async def procesar_ventas_consumidor(
    files: List[UploadFile] = File(...),
    mes: int = Form(...),
    anio: int = Form(...),
    usuario_id: int = Form(...),
    periodo_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    empresa = vinculo.empresa
    emp_nrc, emp_nit = empresa.nrc.replace("-", ""), empresa.nit.replace("-", "")

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0; total_gravado = 0.0; total_general = 0.0
    codigos_vistos = set(); registros_validos = []; omitidos = []
    
    for file in files:
        content = await file.read()
        try:
            dte_json = json.loads(content)
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas', file.filename, db)
            if not es_valido:
                omitidos.append({"archivo": file.filename, "motivo": resultado})
                continue
                
            if resultado in codigos_vistos:
                omitidos.append({"archivo": file.filename, "motivo": "Duplicado en lote"})
                continue
            codigos_vistos.add(resultado)
            
            row = parse_ventas_consumidor(dte_json)
            row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
            
            writer.writerow(row)
            registros_validos.append(row)
            
            total_docs += 1
            total_gravado += float(row[13])
            total_general += float(row[19])
            
            if periodo_id:
                db.add(DteProcesado(periodo_id=periodo_id, tipo_documento="01", clasificacion='venta_consumidor', datos_json=dte_json))
        except Exception as e:
            omitidos.append({"archivo": file.filename, "motivo": str(e)})
            
    if periodo_id: db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {"documentos": total_docs, "gravado": total_gravado, "iva": 0.0, "total": total_general},
        "registros": registros_validos,
        "omitidos": omitidos
    })
