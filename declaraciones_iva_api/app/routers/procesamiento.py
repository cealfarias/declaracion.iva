from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
import csv
import io
from typing import List, Optional

from app.core.dte_parser import parse_compras, parse_ventas_contribuyente, parse_ventas_consumidor
from app.core.database import get_db
from app.models.models import DteProcesado, UsuarioEmpresa, PeriodoFiscal

router = APIRouter()

def get_or_create_periodo(db: Session, empresa_id: int, anio: int, mes: int):
    periodo = db.query(PeriodoFiscal).filter_by(empresa_id=empresa_id, anio=anio, mes=mes).first()
    if not periodo:
        periodo = PeriodoFiscal(empresa_id=empresa_id, anio=anio, mes=mes, estado="borrador")
        db.add(periodo)
        db.commit()
        db.refresh(periodo)
    return periodo

def _validar_dte(dte_json, mes_declaracion, anio_declaracion, empresa_nrc, empresa_nit, tipo_anexo, filename, db: Session):
    ident = dte_json.get("identificacion", {})
    codigo_gen = ident.get("codigoGeneracion", "").replace("-", "").upper()
    fecha_raw = ident.get("fecEmi", "")
    
    try:
        fecha_dte = datetime.strptime(fecha_raw[:10], '%Y-%m-%d')
        meses_diferencia = (anio_declaracion - fecha_dte.year) * 12 + (mes_declaracion - fecha_dte.month)
        
        if meses_diferencia < 0:
            return False, f"Fecha futura no válida ({fecha_raw[:10]})"
        if meses_diferencia > 3:
            return False, f"DTE vencido, excede 3 meses legales ({fecha_raw[:10]})"
    except Exception:
        return False, "Fallo al parsear fecha del DTE"
        
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
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no tiene empresa vinculada")
        
    empresa = vinculo.empresa
    emp_nrc, emp_nit = empresa.nrc.replace("-", ""), empresa.nit.replace("-", "")
    periodo = get_or_create_periodo(db, empresa.id, anio, mes)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0; total_gravado = 0.0; total_iva = 0.0; total_general = 0.0
    codigos_vistos = set(); registros_validos = []; omitidos = []
    
    for file in files:
        content = await file.read()
        try:
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            dte_json = json.loads(text)
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'compras', file.filename, db)
            
            if not es_valido:
                if "ya declarado" not in resultado.lower():
                    omitidos.append({"archivo": file.filename, "motivo": resultado, "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})
                continue
                
            codigo_gen = resultado
            if codigo_gen in codigos_vistos:
                continue
                
            codigos_vistos.add(codigo_gen)
            row = parse_compras(dte_json)
            row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
            
            writer.writerow(row)
            registros_validos.append(row)
            
            total_docs += 1
            total_gravado += float(row[9]) + float(row[11]) + float(row[12]) # J, L, M
            total_iva += float(row[13]) # N
            total_general += float(row[14]) # O
            
            db.add(DteProcesado(
                periodo_id=periodo.id,
                tipo_documento=dte_json.get("identificacion", {}).get("tipoDte", "00"),
                clasificacion='compra',
                datos_json=dte_json
            ))
        except json.JSONDecodeError:
            omitidos.append({"archivo": file.filename, "motivo": "Archivo no es un JSON válido", "contenido": content.decode("utf-8", errors="ignore")})
        except Exception as e:
            omitidos.append({"archivo": file.filename, "motivo": f"Error estructural: {str(e)}", "contenido": content.decode("utf-8", errors="ignore")})
            
    db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {"documentos": total_docs, "gravado": total_gravado, "iva": total_iva, "total": total_general},
        "registros": registros_validos,
        "omitidos": omitidos
    })

@router.post("/procesar/ventas-contribuyentes")
async def procesar_ventas(
    files: List[UploadFile] = File(...),
    mes: int = Form(...),
    anio: int = Form(...),
    usuario_id: int = Form(...),
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    empresa = vinculo.empresa
    emp_nrc, emp_nit = empresa.nrc.replace("-", ""), empresa.nit.replace("-", "")
    periodo = get_or_create_periodo(db, empresa.id, anio, mes)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0; total_gravado = 0.0; total_iva = 0.0; total_general = 0.0
    codigos_vistos = set(); registros_validos = []; omitidos = []
    
    for file in files:
        content = await file.read()
        try:
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            dte_json = json.loads(text)
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas', file.filename, db)
            if not es_valido:
                if "ya declarado" not in resultado.lower():
                    omitidos.append({"archivo": file.filename, "motivo": resultado, "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})
                continue
                
            if resultado in codigos_vistos:
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
            
            db.add(DteProcesado(periodo_id=periodo.id, tipo_documento="03", clasificacion='venta', datos_json=dte_json))
        except Exception as e:
            omitidos.append({"archivo": file.filename, "motivo": str(e), "contenido": content.decode("utf-8", errors="ignore")})
            
    db.commit()
            
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
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    empresa = vinculo.empresa
    emp_nrc, emp_nit = empresa.nrc.replace("-", ""), empresa.nit.replace("-", "")
    periodo = get_or_create_periodo(db, empresa.id, anio, mes)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0; total_gravado = 0.0; total_general = 0.0
    codigos_vistos = set(); registros_validos = []; omitidos = []
    
    for file in files:
        content = await file.read()
        try:
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            dte_json = json.loads(text)
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas', file.filename, db)
            if not es_valido:
                if "ya declarado" not in resultado.lower():
                    omitidos.append({"archivo": file.filename, "motivo": resultado, "contenido": json.dumps(dte_json, indent=2, ensure_ascii=False)})
                continue
                
            if resultado in codigos_vistos:
                continue
            codigos_vistos.add(resultado)
            
            row = parse_ventas_consumidor(dte_json)
            row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
            
            writer.writerow(row)
            registros_validos.append(row)
            
            total_docs += 1
            total_gravado += float(row[13])
            total_general += float(row[19])
            
            db.add(DteProcesado(periodo_id=periodo.id, tipo_documento="01", clasificacion='venta_consumidor', datos_json=dte_json))
        except Exception as e:
            omitidos.append({"archivo": file.filename, "motivo": str(e), "contenido": content.decode("utf-8", errors="ignore")})
            
    db.commit()
            
    return JSONResponse({
        "csv": output.getvalue(),
        "resumen": {"documentos": total_docs, "gravado": total_gravado, "iva": 0.0, "total": total_general},
        "registros": registros_validos,
        "omitidos": omitidos
    })

@router.get("/procesar/consultar")
async def consultar_periodo(
    mes: int = Query(...),
    anio: int = Query(...),
    usuario_id: int = Query(...),
    db: Session = Depends(get_db)
):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    
    periodo = db.query(PeriodoFiscal).filter_by(empresa_id=vinculo.empresa_id, anio=anio, mes=mes).first()
    if not periodo:
        return JSONResponse({"data": None}) # No data yet for this period
        
    dtes = db.query(DteProcesado).filter_by(periodo_id=periodo.id).all()
    if not dtes:
        return JSONResponse({"data": None})
        
    # Agrupar los resultados para retornarlos
    resultado = {
        "compras": {"filename": "F07_Anexo_Compras_BD", "documentos": 0, "gravado": 0.0, "iva": 0.0, "total": 0.0, "registros": [], "csv": ""},
        "ventasContribuyentes": {"filename": "F07_Anexo_Ventas_CCF_BD", "documentos": 0, "gravado": 0.0, "iva": 0.0, "total": 0.0, "registros": [], "csv": ""},
        "ventasConsumidor": {"filename": "F07_Anexo_Ventas_FCF_BD", "documentos": 0, "gravado": 0.0, "iva": 0.0, "total": 0.0, "registros": [], "csv": ""}
    }
    
    # We also need to recreate the CSVs if they want to download them again
    out_compras = io.StringIO(); w_compras = csv.writer(out_compras, delimiter=';', lineterminator='\n')
    out_ccf = io.StringIO(); w_ccf = csv.writer(out_ccf, delimiter=';', lineterminator='\n')
    out_fcf = io.StringIO(); w_fcf = csv.writer(out_fcf, delimiter=';', lineterminator='\n')
    
    for d in dtes:
        try:
            if d.clasificacion == 'compra':
                row = parse_compras(d.datos_json)
                row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
                w_compras.writerow(row)
                resultado["compras"]["registros"].append(row)
                resultado["compras"]["documentos"] += 1
                resultado["compras"]["gravado"] += float(row[9]) + float(row[11]) + float(row[12])
                resultado["compras"]["iva"] += float(row[13])
                resultado["compras"]["total"] += float(row[14])
            elif d.clasificacion == 'venta':
                row = parse_ventas_contribuyente(d.datos_json)
                row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
                w_ccf.writerow(row)
                resultado["ventasContribuyentes"]["registros"].append(row)
                resultado["ventasContribuyentes"]["documentos"] += 1
                resultado["ventasContribuyentes"]["gravado"] += float(row[11])
                resultado["ventasContribuyentes"]["iva"] += float(row[12])
                resultado["ventasContribuyentes"]["total"] += float(row[15])
            elif d.clasificacion == 'venta_consumidor':
                row = parse_ventas_consumidor(d.datos_json)
                row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
                w_fcf.writerow(row)
                resultado["ventasConsumidor"]["registros"].append(row)
                resultado["ventasConsumidor"]["documentos"] += 1
                resultado["ventasConsumidor"]["gravado"] += float(row[13])
                resultado["ventasConsumidor"]["total"] += float(row[19])
        except Exception:
            pass # ignore corrupt DB entries if any
            
    resultado["compras"]["csv"] = out_compras.getvalue()
    resultado["ventasContribuyentes"]["csv"] = out_ccf.getvalue()
    resultado["ventasConsumidor"]["csv"] = out_fcf.getvalue()
    
    # Remove empty ones
    if resultado["compras"]["documentos"] == 0: del resultado["compras"]
    if resultado["ventasContribuyentes"]["documentos"] == 0: del resultado["ventasContribuyentes"]
    if resultado["ventasConsumidor"]["documentos"] == 0: del resultado["ventasConsumidor"]
    
    return JSONResponse({"data": resultado if len(resultado) > 0 else None})
