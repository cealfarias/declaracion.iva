from app.core.gmail_service import fetch_dtes_from_gmail

code_to_add = '''
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
    writer = csv.writer(output, delimiter=';', lineterminator='\\n')
    
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
                fila, gravado, iva, total = parse_compras(dte_json, empresa.combustible_50_porciento)
            elif tipo_anexo == 'ventas_ccf':
                fila, gravado, iva, total = parse_ventas_contribuyente(dte_json)
            elif tipo_anexo == 'ventas_consumidor':
                fila, gravado, iva, total = parse_ventas_consumidor(dte_json)
            else:
                raise ValueError("Tipo de anexo inválido")
                
            registros_validos.append(fila)
            total_gravado += gravado
            total_iva += iva
            total_general += total
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
'''

with open('app/routers/procesamiento.py', 'a', encoding='utf-8') as f:
    f.write(code_to_add)
