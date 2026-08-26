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
    tipo_dte = ident.get("tipoDte", "")
    codigo_gen = ident.get("codigoGeneracion", "").replace("-", "").upper()
    fecha_raw = ident.get("fecEmi", "")
    
    if tipo_anexo == 'compras' and tipo_dte not in ["03", "05", "06", "14"]:
        return False, f"Tipo incorrecto para Compras: DTE {tipo_dte} (Se esperan CCF 03, FSE 14, NC/ND)"
    if tipo_anexo == 'ventas_ccf' and tipo_dte not in ["03", "05", "06"]:
        return False, f"Tipo incorrecto para Ventas CCF: DTE {tipo_dte} (Se esperan CCF 03 o NC/ND)"
    if tipo_anexo == 'ventas_consumidor' and tipo_dte not in ["01", "05", "06"]:
        return False, f"Tipo incorrecto para Consumidor: DTE {tipo_dte} (Se esperan Facturas 01 o NC/ND)"
    
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
    elif tipo_anexo in ['ventas_ccf', 'ventas_consumidor']:
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
    empresa_id: int = Form(...),
    db: Session = Depends(get_db)
):
    empresa = db.query(Empresa).filter_by(id=empresa_id).first()
    if not empresa: raise HTTPException(status_code=400, detail="Empresa no encontrada")
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
            
            
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1
            
            total_docs += 1
            total_gravado += factor * (float(row[9]) + float(row[11]) + float(row[12]))
            total_iva += factor * float(row[13])
            total_general += factor * float(row[14])
            
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
    empresa_id: int = Form(...),
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
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas_ccf', file.filename, db)
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
            
            
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1

            total_docs += 1
            total_gravado += factor * float(row[11])
            total_iva += factor * float(row[12])
            total_general += factor * float(row[15])
            
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
    empresa_id: int = Form(...),
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
            es_valido, resultado = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, 'ventas_consumidor', file.filename, db)
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
            
            
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1

            total_docs += 1
            total_gravado += factor * float(row[13])
            total_general += factor * float(row[19])
            
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
    empresa_id: int = Query(...),
    db: Session = Depends(get_db)
):
    periodo = db.query(PeriodoFiscal).filter_by(empresa_id=empresa_id, anio=anio, mes=mes).first()
    if not periodo:
        return JSONResponse({"data": None}) # No data yet for this period
        
    dtes = db.query(DteProcesado).filter_by(periodo_id=periodo.id).all()
    if not dtes:
        return JSONResponse({"data": None})
        
    remanente_anterior = 0.0
    for d in dtes:
        if d.tipo_documento == 'REMANENTE':
            remanente_anterior = d.datos_json.get('remanente_anterior', 0.0)
        
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
                
                tipo = d.datos_json.get("identificacion", {}).get("tipoDte", "")
                factor = -1 if tipo == "05" else 1
                
                resultado["compras"]["gravado"] += factor * (float(row[9]) + float(row[11]) + float(row[12]))
                resultado["compras"]["iva"] += factor * float(row[13])
                resultado["compras"]["total"] += factor * float(row[14])
            elif d.clasificacion == 'venta':
                row = parse_ventas_contribuyente(d.datos_json)
                row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
                w_ccf.writerow(row)
                resultado["ventasContribuyentes"]["registros"].append(row)
                resultado["ventasContribuyentes"]["documentos"] += 1
                tipo = d.datos_json.get("identificacion", {}).get("tipoDte", "")
                factor = -1 if tipo == "05" else 1
                resultado["ventasContribuyentes"]["gravado"] += factor * float(row[11])
                resultado["ventasContribuyentes"]["iva"] += factor * float(row[12])
                resultado["ventasContribuyentes"]["total"] += factor * float(row[15])
            elif d.clasificacion == 'venta_consumidor':
                row = parse_ventas_consumidor(d.datos_json)
                row = [f"{float(x):.2f}" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','',1).isdigit() and '.' in x and len(x)>0 and x.count('.')==1) else x for x in row]
                w_fcf.writerow(row)
                resultado["ventasConsumidor"]["registros"].append(row)
                resultado["ventasConsumidor"]["documentos"] += 1
                tipo = d.datos_json.get("identificacion", {}).get("tipoDte", "")
                factor = -1 if tipo == "05" else 1
                resultado["ventasConsumidor"]["gravado"] += factor * float(row[13])
                resultado["ventasConsumidor"]["total"] += factor * float(row[19])
        except Exception as e:
            import traceback; traceback.print_exc()
            pass
            
    resultado["compras"]["csv"] = out_compras.getvalue()
    resultado["ventasContribuyentes"]["csv"] = out_ccf.getvalue()
    resultado["ventasConsumidor"]["csv"] = out_fcf.getvalue()
    
    # Remove empty ones
    if resultado["compras"]["documentos"] == 0: del resultado["compras"]
    if resultado["ventasContribuyentes"]["documentos"] == 0: del resultado["ventasContribuyentes"]
    if resultado["ventasConsumidor"]["documentos"] == 0: del resultado["ventasConsumidor"]
    
    resultado["remanente_anterior"] = remanente_anterior
    return JSONResponse({"data": resultado if len(resultado) > 0 else None})

from pydantic import BaseModel

class RemanenteRequest(BaseModel):
    mes: int
    anio: int
    usuario_id: int
    remanente_anterior: float

@router.post("/procesar/guardar-remanente")
async def guardar_remanente(req: RemanenteRequest, db: Session = Depends(get_db)):
    vinculo = db.query(UsuarioEmpresa).filter_by(usuario_id=req.usuario_id).first()
    if not vinculo: raise HTTPException(status_code=400, detail="Usuario no vinculado")
    
    periodo = get_or_create_periodo(db, vinculo.empresa_id, req.anio, req.mes)
    
    # Buscar si ya hay un DTE de remanente
    dte_rem = db.query(DteProcesado).filter_by(periodo_id=periodo.id, tipo_documento='REMANENTE').first()
    if dte_rem:
        dte_rem.datos_json = {"remanente_anterior": req.remanente_anterior}
    else:
        dte_rem = DteProcesado(
            periodo_id=periodo.id,
            tipo_documento='REMANENTE',
            clasificacion='ajuste',
            datos_json={"remanente_anterior": req.remanente_anterior}
        )
        db.add(dte_rem)
        
    db.commit()
    return {"message": "Remanente guardado con éxito"}

from app.core.gmail_service import fetch_dtes_from_gmail
from app.models.models import Empresa

@router.post("/procesar/gmail")
async def procesar_gmail(
    access_token: str = Form(...),
    tipo_anexo: str = Form(...), # "compras", "ventas_ccf", "ventas_consumidor"
    mes: int = Form(...),
    anio: int = Form(...),
    empresa_id: int = Form(...),
    db: Session = Depends(get_db)
):
    empresa = db.query(Empresa).filter_by(id=empresa_id).first()
    if not empresa: raise HTTPException(status_code=400, detail="Empresa no encontrada")
        
    emp_nrc, emp_nit = empresa.nrc.replace("-", ""), empresa.nit.replace("-", "")
    periodo = get_or_create_periodo(db, empresa.id, anio, mes)

    try:
        # 1. Fetch DTEs from Gmail
        dtes_json_list = fetch_dtes_from_gmail(access_token, anio, mes, emp_nit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando a Gmail: {str(e)}")
        
    if not dtes_json_list:
        return JSONResponse(status_code=200, content={"message": "No se encontraron DTEs en Gmail para este mes."})

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    total_docs = 0; total_gravado = 0.0; total_iva = 0.0; total_general = 0.0
    codigos_vistos = set(); registros_validos = []; omitidos = []
    
    for dte_json in dtes_json_list:
        es_valido, msg = _validar_dte(dte_json, mes, anio, emp_nrc, emp_nit, tipo_anexo, "gmail_attachment", db)
        
        if not es_valido:
            omitidos.append({"archivo": "gmail_attachment", "razon": msg})
            continue
            
        if msg in codigos_vistos:
            continue
        codigos_vistos.add(msg)

        # Parsear según el tipo
        try:
            if tipo_anexo == 'compras':
                fila = parse_compras(dte_json)
                # Opcional: si quisieras usar combustible_50_porciento en parse_compras tendrías que modificar dte_parser.py, 
                # pero como ahorita toma 1 argumento, le pasamos 1.
                gravado = float(fila[9]) + float(fila[11]) + float(fila[12])
                iva = float(fila[13])
                total = float(fila[14])
            elif tipo_anexo == 'ventas_ccf':
                fila = parse_ventas_contribuyente(dte_json)
                gravado = float(fila[11])
                iva = float(fila[12])
                total = float(fila[15])
            elif tipo_anexo == 'ventas_consumidor':
                fila = parse_ventas_consumidor(dte_json)
                gravado = float(fila[8])
                iva = float(fila[9])
                total = float(fila[12])
            else:
                raise ValueError("Tipo de anexo inválido")
                
            tipo = dte_json.get("identificacion", {}).get("tipoDte", "")
            factor = -1 if tipo == "05" else 1

            registros_validos.append(fila)
            total_gravado += factor * gravado
            total_iva += factor * iva
            total_general += factor * total
            total_docs += 1
            
            db_dte = DteProcesado(
                periodo_id=periodo.id,
                tipo_anexo=tipo_anexo,
                datos_json=dte_json,
                procesado_en=datetime.utcnow()
            )
            db.add(db_dte)
        except Exception as e:
            omitidos.append({"archivo": "gmail_attachment", "razon": f"Error de parseo: {str(e)}"})

    db.commit()

    if tipo_anexo == 'compras':
        registros_validos.sort(key=lambda r: (r[2], r[6]))
    elif tipo_anexo == 'ventas_ccf':
        registros_validos.sort(key=lambda r: (r[2], r[7]))
    elif tipo_anexo == 'ventas_consumidor':
        registros_validos.sort(key=lambda r: (r[2], r[4]))

    for r in registros_validos:
        writer.writerow(r)

    filename = f"anexo_{tipo_anexo}_{mes:02d}_{anio}"

    return JSONResponse(status_code=200, content={
        "documentos": total_docs,
        "csv": output.getvalue(),
        "filename": filename,
        "registros": registros_validos,
        "omitidos": omitidos,
        "totales": {
            "gravado": round(total_gravado, 2),
            "iva": round(total_iva, 2),
            "general": round(total_general, 2)
        }
    })
