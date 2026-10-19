import csv
import io
import re
from io import StringIO, BytesIO
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import DteCompra, Empresa, DeclaracionEstado
import json

router = APIRouter()

def is_periodo_declarado(db: Session, empresa_id: int, anio: str, mes: str, tipo_libro: str = "compras", version: int = 1) -> bool:
    estado = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro,
        DeclaracionEstado.version == version
    ).first()
    return estado.declarado if estado else False

@router.get("/estado/{empresa_id}")
def get_estado_declaracion(empresa_id: int, mes: str, anio: str, tipo_libro: str = "compras", db: Session = Depends(get_db)):
    estados = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro
    ).order_by(DeclaracionEstado.version.asc()).all()
    
    if not estados:
        return {"versiones": [{"version": 1, "declarado": False, "numero_declaracion": None}]}
        
    res = []
    for e in estados:
        res.append({"version": e.version, "declarado": e.declarado, "numero_declaracion": e.numero_declaracion})
    return {"versiones": res}

@router.put("/estado/{empresa_id}/numero")
def update_numero_declaracion(empresa_id: int, mes: str, anio: str, numero: str, version: int = 1, tipo_libro: str = "compras", db: Session = Depends(get_db)):
    estado = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro,
        DeclaracionEstado.version == version
    ).first()
    if estado:
        estado.numero_declaracion = numero
        db.commit()
    return {"mensaje": "Número guardado"}

@router.post("/modificatoria/{empresa_id}")
def crear_modificatoria(empresa_id: int, mes: str, anio: str, numero_original: str, tipo_libro: str = "compras", db: Session = Depends(get_db)):
    # Buscar ultima version
    estados = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro
    ).order_by(DeclaracionEstado.version.desc()).all()
    
    ultima_version = estados[0].version if estados else 1
    if ultima_version >= 3:
        raise HTTPException(status_code=400, detail="Se alcanzó el límite de 2 modificatorias.")
        
    nueva_version = ultima_version + 1
    
    # Clonar comprobantes
    compras = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_anio == anio,
        DteCompra.periodo_mes == mes,
        DteCompra.version == ultima_version
    ).all()
    
    for c in compras:
        nuevo = DteCompra(
            empresa_id=c.empresa_id,
            periodo_mes=c.periodo_mes,
            periodo_anio=c.periodo_anio,
            fecha_emision=c.fecha_emision,
            clase_documento=c.clase_documento,
            tipo_documento=c.tipo_documento,
            numero_resolucion=c.numero_resolucion,
            serie_documento=c.serie_documento,
            numero_documento=c.numero_documento,
            nit_proveedor=c.nit_proveedor,
            nombre_proveedor=c.nombre_proveedor,
            compras_internas_exentas=c.compras_internas_exentas,
            internaciones_exentas=c.internaciones_exentas,
            importaciones_exentas=c.importaciones_exentas,
            compras_internas_gravadas=c.compras_internas_gravadas,
            internaciones_gravadas_bienes=c.internaciones_gravadas_bienes,
            importaciones_gravadas_bienes=c.importaciones_gravadas_bienes,
            importaciones_gravadas_servicios=c.importaciones_gravadas_servicios,
            credito_fiscal=c.credito_fiscal,
            total_compras=c.total_compras,
            tipo_operacion=c.tipo_operacion,
            clasificacion=c.clasificacion,
            sector=c.sector,
            tipo_costo_gasto=c.tipo_costo_gasto,
            raw_json=c.raw_json,
            omitido=c.omitido or False,
            version=nueva_version
        )
        db.add(nuevo)
        
    # Crear estado abierto
    estado = DeclaracionEstado(
        empresa_id=empresa_id,
        anio=anio,
        mes=mes,
        tipo_libro=tipo_libro,
        version=nueva_version,
        declarado=False
    )
    db.add(estado)
    db.commit()
    return {"mensaje": "Modificatoria creada", "nueva_version": nueva_version}


@router.post("/declarar/{empresa_id}")
def marcar_como_declarado(empresa_id: int, mes: str, anio: str, version: int = 1, tipo_libro: str = "compras", db: Session = Depends(get_db)):
    estado = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro,
        DeclaracionEstado.version == version
    ).first()
    
    if not estado:
        estado = DeclaracionEstado(
            empresa_id=empresa_id,
            anio=anio,
            mes=mes,
            tipo_libro=tipo_libro,
            version=version,
            declarado=True
        )
        db.add(estado)
    else:
        estado.declarado = True
        
    db.commit()
    return {"mensaje": "Período marcado como declarado"}

@router.delete("/limpiar/{empresa_id}")
def limpiar_periodo(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    if is_periodo_declarado(db, empresa_id, anio, mes, version=version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio,
        DteCompra.version == version
    ).delete()
    
    db.commit()
    return {"mensaje": "Período limpiado correctamente"}

@router.post("/upload")
async def upload_dtes(
    empresa_id: int = Form(...),
    periodo_mes: str = Form(...),
    periodo_anio: str = Form(...),
    files: List[UploadFile] = File(...),
    version: int = Form(1),
    db: Session = Depends(get_db)
):
    # Verificar si está bloqueado
    if is_periodo_declarado(db, empresa_id, periodo_anio, periodo_mes, version=version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")

    # Validar que la empresa exista
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    procesados = 0
    errores = []
    descartados_otra_empresa = 0
    descartados_otro_periodo = 0

    def clean_id(val) -> str:
        if not val:
            return ""
        return str(val).replace("-", "").strip().lower()

    emp_nit = clean_id(empresa.nit)
    emp_nrc = clean_id(empresa.nrc)

    for file in files:
        fname = file.filename.lower()
        if not (fname.endswith('.json') or fname.endswith('.csv') or fname.endswith('.xlsx') or fname.endswith('.xls')):
            errores.append(f"{file.filename}: Formato no soportado. Debe ser archivo JSON de DTE, o Excel/CSV oficial del Libro de Compras de Hacienda.")
            continue
            
        content = await file.read()

        # CASO 1: Archivo Excel (.xlsx / .xls) o CSV de Reporte oficial de Hacienda
        if fname.endswith(('.xlsx', '.xls', '.csv')):
            rows = []
            if fname.endswith(('.xlsx', '.xls')):
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
                    sheet = wb.active
                    for row in sheet.iter_rows(values_only=True):
                        rows.append([str(c) if c is not None else "" for c in row])
                except Exception as e:
                    errores.append(f"{file.filename}: Error leyendo Excel ({str(e)}).")
                    continue
            else:
                for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']:
                    try:
                        decoded_str = content.decode(encoding)
                        # Detectar delimitador (; o ,)
                        chunk = decoded_str[:4096]
                        delim = ';' if chunk.count(';') > chunk.count(',') else ','
                        reader = csv.reader(StringIO(decoded_str), delimiter=delim)
                        rows = list(reader)
                        break
                    except Exception:
                        continue

            if not rows:
                errores.append(f"{file.filename}: Archivo vacío o codificación no soportada.")
                continue

            # Buscar encabezados y metadatos de empresa / periodo
            header_idx = -1
            nit_reporte = None
            periodo_reporte = None
            for idx, r in enumerate(rows[:25]):
                line_str = " ".join(r).lower()
                if "nit:" in line_str:
                    for cell_idx, c in enumerate(r):
                        if "nit:" in str(c).lower() and cell_idx + 1 < len(r):
                            val = str(r[cell_idx + 1]).strip()
                            if not val and cell_idx + 2 < len(r):
                                val = str(r[cell_idx + 2]).strip()
                            nit_reporte = val
                if "periodo" in line_str:
                    for cell_idx, c in enumerate(r):
                        if "periodo" in str(c).lower() and cell_idx + 1 < len(r):
                            val = str(r[cell_idx + 1]).strip()
                            if not val and cell_idx + 2 < len(r):
                                val = str(r[cell_idx + 2]).strip()
                            periodo_reporte = val
                if "fecha de emision" in line_str or "fecha de emisión" in line_str:
                    header_idx = idx

            # Validar si el archivo pertenece a la empresa si trae NIT en el encabezado
            if nit_reporte:
                clean_rep_nit = clean_id(nit_reporte)
                if emp_nit and clean_rep_nit and clean_rep_nit not in emp_nit and emp_nit not in clean_rep_nit:
                    descartados_otra_empresa += 1
                    errores.append(f"{file.filename}: El NIT del reporte ({nit_reporte}) no coincide con la empresa seleccionada ({empresa.nit}).")
                    continue

            # Validar si el período coincide si viene en el encabezado (ej: 09/2026)
            if periodo_reporte and "/" in periodo_reporte:
                p_parts = periodo_reporte.strip().split("/")
                if len(p_parts) == 2:
                    p_mes = p_parts[0].zfill(2)
                    p_anio = p_parts[1].strip()
                    # Ley de IVA Art. 63: se permiten reportes del período o de hasta 3 períodos tributarios anteriores
                    diff_rep = (int(periodo_anio) - int(p_anio)) * 12 + (int(periodo_mes) - int(p_mes))
                    if diff_rep < 0 or diff_rep > 3:
                        descartados_otro_periodo += 1
                        errores.append(f"{file.filename}: El período del reporte ({periodo_reporte}) excede el plazo legal de 3 meses anteriores al seleccionado ({periodo_mes}/{periodo_anio}).")
                        continue

            # DETECCIÓN DE FORMATO: ¿Es un CSV oficial Anexo 3 (21 columnas)?
            es_anexo3_csv = False
            if rows and len(rows[0]) >= 18:
                col0 = rows[0][0].strip()
                if ("/" in col0 and len(col0.split("/")) == 3) or ("-" in col0 and len(col0.split("-")) == 3):
                    es_anexo3_csv = True

            if es_anexo3_csv:
                filas_procesadas = 0
                filas_ya_existentes = 0
                for r in rows:
                    if len(r) < 15:
                        continue
                    fecha_str = r[0].strip()
                    try:
                        if "/" in fecha_str:
                            p = fecha_str.split("/")
                            if len(p[2]) == 4:
                                f_obj = datetime(int(p[2]), int(p[1]), int(p[0]))
                            else:
                                f_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
                        elif "-" in fecha_str:
                            p = fecha_str.split("-")
                            if len(p[0]) == 4:
                                f_obj = datetime(int(p[0]), int(p[1]), int(p[2]))
                            else:
                                f_obj = datetime.strptime(fecha_str, "%d-%m-%Y")
                        else:
                            continue
                        fecha_emision = f_obj.strftime("%d/%m/%Y")
                        mes_row = f"{f_obj.month:02d}"
                        anio_row = str(f_obj.year)
                    except Exception:
                        continue

                    # Validar Art. 63 (hasta 3 períodos anteriores)
                    diff_meses = (int(periodo_anio) - int(anio_row)) * 12 + (int(periodo_mes) - int(mes_row))
                    if diff_meses < 0 or diff_meses > 3:
                        descartados_otro_periodo += 1
                        continue

                    clase_doc = r[1].strip() if len(r) > 1 else "4"
                    tipo_doc = r[2].strip() if len(r) > 2 else "03"
                    num_doc = r[3].strip().replace("-", "").upper() if len(r) > 3 else ""
                    if not num_doc:
                        continue

                    nit_prov = r[4].strip() if len(r) > 4 else ""
                    nombre_prov = r[5].strip() if len(r) > 5 else ""

                    def to_f(v):
                        try:
                            return float(str(v).replace("$", "").replace(",", "").strip())
                        except:
                            return 0.0

                    exenta_int = to_f(r[6]) if len(r) > 6 else 0.0
                    exenta_imp = to_f(r[7]) if len(r) > 7 else 0.0
                    exenta_rec = to_f(r[8]) if len(r) > 8 else 0.0
                    gravada_int = to_f(r[9]) if len(r) > 9 else 0.0
                    gravada_imp = to_f(r[10]) if len(r) > 10 else 0.0
                    iva = to_f(r[13]) if len(r) > 13 else 0.0
                    total = to_f(r[14]) if len(r) > 14 else 0.0

                    # Evitar duplicados
                    existe = db.query(DteCompra).filter(
                        DteCompra.empresa_id == empresa_id,
                        DteCompra.numero_documento == num_doc,
                        DteCompra.version == version
                    ).first()

                    if existe:
                        filas_ya_existentes += 1
                        continue

                    nuevo_dte = DteCompra(
                        empresa_id=empresa_id,
                        periodo_mes=periodo_mes,
                        periodo_anio=periodo_anio,
                        fecha_emision=fecha_emision,
                        clase_documento=clase_doc,
                        tipo_documento=tipo_doc,
                        numero_resolucion=num_doc,
                        serie_documento="",
                        numero_documento=num_doc,
                        nit_proveedor=nit_prov,
                        nombre_proveedor=nombre_prov,
                        compras_internas_exentas=exenta_int + exenta_imp + exenta_rec,
                        compras_internas_gravadas=gravada_int + gravada_imp,
                        credito_fiscal=iva,
                        total_compras=total,
                        tipo_operacion=r[16].strip() if len(r) > 16 else "1",
                        clasificacion=r[17].strip() if len(r) > 17 else "1",
                        sector=r[18].strip() if len(r) > 18 else "2",
                        tipo_costo_gasto=r[19].strip() if len(r) > 19 else "5",
                        raw_json={"origen": "anexo3_csv", "fila": r},
                        omitido=False,
                        version=version
                    )
                    db.add(nuevo_dte)
                    procesados += 1
                    filas_procesadas += 1

                if filas_procesadas == 0 and not errores:
                    if filas_ya_existentes > 0:
                        errores.append(f"{file.filename}: Las {filas_ya_existentes} compras de este archivo ya estaban previamente registradas.")
                    else:
                        errores.append(f"{file.filename}: No se encontraron filas de compras válidas para el período {periodo_mes}/{periodo_anio}.")
                continue

            start_row = (header_idx + 2) if header_idx != -1 else 0
            filas_procesadas = 0
            filas_ya_existentes = 0

            def is_item_num(val):
                s = str(val or "").strip()
                try:
                    f = float(s)
                    return f > 0 and (f == int(f))
                except Exception:
                    return False

            for r in rows[start_row:]:
                clean_cells = [c.strip() for c in r if c and str(c).strip()]
                if not clean_cells:
                    continue

                # Identificar si es una fila de datos (primer valor no vacío suele ser el número de ítem)
                # Formato del MH:
                # [0]="", [1]=No., [2]=Fecha de Emision, [3]=No. de Doc., [4]=NRC, [5]=NIT o DUI Sujeto Excluido,
                # [6]=Nombre Proveedor, [7]=No Sujetas, [8]=Exentas, [9]=Import/Intern Exentas,
                # [10]=Gravadas Internas, [11]=Import/Intern Gravadas, [12]=Credito Fiscal,
                # [13]=Anticipo IVA, [14]=IVA Retenido, [15]=Total Compras, [16]=Compras a Sujetos Excluidos
                try:
                    # Ajustar desplazamiento si la primera columna está vacía
                    shift = 0
                    if len(r) > 1 and r[0].strip() == "" and is_item_num(r[1]):
                        shift = 1
                    elif is_item_num(r[0]):
                        shift = 0
                    else:
                        continue

                    if len(r) <= shift + 10:
                        continue

                    fecha_str = str(r[shift + 1]).strip() # YYYY-MM-DD o DD/MM/YYYY
                    if not fecha_str or "-" not in fecha_str and "/" not in fecha_str:
                        continue

                    # Parsear fecha
                    try:
                        if "-" in fecha_str:
                            f_obj = datetime.strptime(fecha_str.split("T")[0].split(" ")[0], "%Y-%m-%d")
                        else:
                            f_obj = datetime.strptime(fecha_str.split("T")[0].split(" ")[0], "%d/%m/%Y")
                        fecha_emision = f_obj.strftime("%d/%m/%Y")
                        mes_row = f"{f_obj.month:02d}"
                        anio_row = str(f_obj.year)
                    except Exception:
                        continue

                    # Ley de IVA Art. 63: se permiten compras del período y de hasta 3 períodos tributarios anteriores
                    diff_meses = (int(periodo_anio) - int(anio_row)) * 12 + (int(periodo_mes) - int(mes_row))
                    if diff_meses < 0 or diff_meses > 3:
                        descartados_otro_periodo += 1
                        continue

                    no_doc_raw = str(r[shift + 2]).strip()
                    num_doc = no_doc_raw.replace("-", "").upper() if no_doc_raw else ""

                    nrc_prov = str(r[shift + 3]).strip()
                    nit_dui_excluido = str(r[shift + 4]).strip() if len(r) > shift + 4 else ""
                    nombre_prov = str(r[shift + 5]).strip() if len(r) > shift + 5 else ""

                    def to_float(val_c):
                        try:
                            s = str(val_c).replace("$", "").replace(",", "").strip()
                            return float(s) if s else 0.0
                        except Exception:
                            return 0.0

                    no_sujetas = to_float(r[shift + 6]) if len(r) > shift + 6 else 0.0
                    exentas = to_float(r[shift + 7]) if len(r) > shift + 7 else 0.0
                    import_exentas = to_float(r[shift + 8]) if len(r) > shift + 8 else 0.0
                    gravadas_int = to_float(r[shift + 9]) if len(r) > shift + 9 else 0.0
                    import_gravadas = to_float(r[shift + 10]) if len(r) > shift + 10 else 0.0
                    credito_fiscal = to_float(r[shift + 11]) if len(r) > shift + 11 else 0.0
                    anticipo_iva = to_float(r[shift + 12]) if len(r) > shift + 12 else 0.0
                    iva_retenido = to_float(r[shift + 13]) if len(r) > shift + 13 else 0.0
                    total_compras = to_float(r[shift + 14]) if len(r) > shift + 14 else (gravadas_int + credito_fiscal + exentas)
                    sujetos_excluidos = to_float(r[shift + 15]) if len(r) > shift + 15 else 0.0

                    # Si es Sujeto Excluido reportado en el Excel
                    es_sujeto_excluido = False
                    if sujetos_excluidos > 0 or (nit_dui_excluido and not nrc_prov):
                        es_sujeto_excluido = True
                        tipo_dte = "14"
                        nit_proveedor = nit_dui_excluido.replace("-", "").strip()
                        tipo_op_default = "2"
                        total_exenta = sujetos_excluidos if sujetos_excluidos > 0 else (exentas or total_compras)
                        total_gravada = 0.0
                        iva = 0.0
                    else:
                        tipo_dte = "03" # Comprobante de Crédito Fiscal
                        nit_proveedor = nrc_prov.replace("-", "").strip() or clean_id(nit_reporte)
                        tipo_op_default = "1"
                        total_exenta = exentas + no_sujetas + import_exentas
                        total_gravada = gravadas_int + import_gravadas
                        iva = credito_fiscal

                    # Evitar duplicados
                    existe = db.query(DteCompra).filter(
                        DteCompra.empresa_id == empresa_id,
                        DteCompra.numero_documento == num_doc,
                        DteCompra.version == version
                    ).first()

                    if existe:
                        filas_ya_existentes += 1
                        continue

                    nuevo_dte = DteCompra(
                        empresa_id=empresa_id,
                        periodo_mes=periodo_mes,
                        periodo_anio=periodo_anio,
                        fecha_emision=fecha_emision,
                        clase_documento="4",
                        tipo_documento=tipo_dte,
                        numero_resolucion=num_doc,
                        serie_documento="",
                        numero_documento=num_doc,
                        nit_proveedor=nit_proveedor,
                        nombre_proveedor=nombre_prov,
                        compras_internas_exentas=total_exenta,
                        compras_internas_gravadas=total_gravada,
                        credito_fiscal=iva,
                        total_compras=total_compras,
                        tipo_operacion=tipo_op_default,
                        clasificacion="1",
                        sector="2",
                        tipo_costo_gasto="5",
                        raw_json={"origen": "reporte_hacienda_excel", "fila": r},
                        omitido=False,
                        version=version
                    )
                    db.add(nuevo_dte)
                    procesados += 1
                    filas_procesadas += 1

                except Exception as row_err:
                    continue

            if filas_procesadas == 0 and not errores:
                if filas_ya_existentes > 0:
                    errores.append(f"{file.filename}: Las {filas_ya_existentes} compras de este reporte ya estaban registradas previamente en la declaración.")
                else:
                    errores.append(f"{file.filename}: No se encontraron filas de compras válidas para el período {periodo_mes}/{periodo_anio}.")
            continue

        # CASO 2: Archivo JSON individual de DTE
        # Intentar múltiples codificaciones
        decoded_content = None
        dte_json = None
        for encoding in ['utf-8-sig', 'latin-1', 'windows-1252', 'utf-16']:
            try:
                decoded_content = content.decode(encoding).strip()
                dte_json = json.loads(decoded_content)
                break # Si tiene éxito, salir del bucle
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
                
        if dte_json is None:
            errores.append(f"{file.filename}: No es un JSON válido o tiene codificación incorrecta.")
            continue
            
        # Extraer campos clave
        try:
            # Algunos sistemas devuelven el DTE envuelto en la llave 'dteJson'
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
                
            identificacion = dte_json.get("identificacion", {})
            tipo_dte = identificacion.get("tipoDte", "")
            
            if tipo_dte not in ["03", "05", "14"]:
                # Ignorar silenciosamente otros tipos para permitir subir carpetas mixtas
                continue
                
            emisor = dte_json.get("emisor", {})
            receptor = dte_json.get("receptor", {})
            resumen = dte_json.get("resumen", {})
            
            # 1. FILTRO ESTRICTO POR EMPRESA (NIT / NRC)
            pertenece = False
            if tipo_dte in ["03", "05"]:
                # En compras (CCF y NC), nuestra empresa debe ser el RECEPTOR (comprador)
                rec_nit = clean_id(receptor.get("nit") or receptor.get("numDocumento"))
                rec_nrc = clean_id(receptor.get("nrc"))
                
                if emp_nit and rec_nit and (emp_nit == rec_nit or emp_nit in rec_nit or rec_nit in emp_nit):
                    pertenece = True
                elif emp_nrc and rec_nrc and (emp_nrc == rec_nrc or emp_nrc.lstrip("0") == rec_nrc.lstrip("0")):
                    pertenece = True
            elif tipo_dte == "14":
                # En Factura de Sujeto Excluido, nuestra empresa es el EMISOR (adquirente)
                emi_nit = clean_id(emisor.get("nit"))
                emi_nrc = clean_id(emisor.get("nrc"))
                
                if emp_nit and emi_nit and (emp_nit == emi_nit or emp_nit in emi_nit or emi_nit in emp_nit):
                    pertenece = True
                elif emp_nrc and emi_nrc and (emp_nrc == emi_nrc or emp_nrc.lstrip("0") == emi_nrc.lstrip("0")):
                    pertenece = True

            if not pertenece:
                # Comprobante pertenece a otra empresa o persona
                descartados_otra_empresa += 1
                continue

            # 2. FILTRO ESTRICTO POR PERÍODO (MES Y AÑO)
            fecha_cruda = identificacion.get("fecEmi", "")
            try:
                fec_clean = str(fecha_cruda).split('T')[0].split(' ')[0].strip()
                fecha_obj = datetime.strptime(fec_clean, "%Y-%m-%d")
                fecha_emision = fecha_obj.strftime("%d/%m/%Y")
                mes_dte = f"{fecha_obj.month:02d}"
                anio_dte = str(fecha_obj.year)
            except Exception:
                errores.append(f"{file.filename}: Fecha de emisión inválida o formato no reconocido ({fecha_cruda}).")
                continue

            # 2. FILTRO POR PERÍODO (MES Y AÑO) - Art. 63 Ley de IVA (hasta 3 períodos tributarios anteriores)
            diff_meses = (int(periodo_anio) - int(anio_dte)) * 12 + (int(periodo_mes) - int(mes_dte))
            if diff_meses < 0 or diff_meses > 3:
                # El comprobante excede los 3 meses legales o tiene fecha futura
                descartados_otro_periodo += 1
                continue
                
            # Evitar duplicados (mismo sello/resolucion en mismo periodo para la empresa)
            sello = (
                identificacion.get("selloRecibido")
                or dte_json.get("selloRecibido")
                or dte_json.get("selloRecepcion")
                or dte_json.get("SelloRecepcion")
                or identificacion.get("selloRecepcion")
                or identificacion.get("SelloRecepcion")
                or ""
            )
                
            codigo_generacion = identificacion.get("codigoGeneracion", "")
            
            # El "Número de Documento" para DTE (clase 4) debe ser el código de generación sin guiones
            num_doc = codigo_generacion.replace("-", "").upper() if codigo_generacion else ""
            
            # Comprobar si ya existe
            existe = db.query(DteCompra).filter(
                DteCompra.empresa_id == empresa_id,
                DteCompra.numero_documento == num_doc,
                DteCompra.version == version
            ).first()
            
            if existe:
                estado_extra = " (omitido)" if existe.omitido else ""
                errores.append(f"{file.filename}: Ya fue procesado anteriormente en el mes {existe.periodo_mes}/{existe.periodo_anio}{estado_extra}.")
                continue

            if tipo_dte == "14":
                # En DTE 14 (Factura de Sujeto Excluido), el emisor es la empresa adquirente
                # y el receptor es el proveedor Sujeto Excluido que vendió el bien o prestó el servicio.
                receptor = dte_json.get("receptor", {})
                nombre_proveedor = receptor.get("nombre", "")
                nit_proveedor = str(receptor.get("numDocumento", "")).replace("-", "").strip()
                
                # Montos en Sujeto Excluido:
                # No genera Crédito Fiscal de IVA (0.00).
                # Se reporta como Compra Interna Exenta / No Sujeta en el Libro de Compras.
                monto_compra = float(resumen.get("totalCompra") or resumen.get("subTotal") or 0.0)
                total_gravada = 0.0
                total_exenta = monto_compra
                iva = 0.0
                total_compras = monto_compra
                tipo_op_default = "2" # 2: No Gravada o Exenta
            else:
                nit_proveedor = str(emisor.get("nit", "")).replace("-", "").strip()
                nombre_proveedor = emisor.get("nombre", "")
                
                # Montos
                tributos = resumen.get("tributos", [])
                if not isinstance(tributos, list):
                    tributos = []
                    
                iva = 0.0
                for t in tributos:
                    if t.get("codigo") == "20":
                        iva += float(t.get("valor", 0.0))
                        
                if iva == 0.0 and resumen.get("totalIva"):
                    iva = float(resumen.get("totalIva", 0.0))
                    
                total_gravada = float(resumen.get("totalGravada", 0.0))
                if iva == 0.0 and total_gravada > 0:
                    iva = round(total_gravada * 0.13, 2)
                    
                total_exenta = float(resumen.get("totalExenta", 0.0))
                total_compras = float(resumen.get("totalPagar", total_gravada + iva))
                tipo_op_default = "1"
            
            nuevo_dte = DteCompra(
                empresa_id=empresa_id,
                periodo_mes=periodo_mes,
                periodo_anio=periodo_anio,
                fecha_emision=fecha_emision,
                clase_documento="4",
                tipo_documento=tipo_dte,
                numero_resolucion=num_doc, # Para DTEs se usa el código de generación
                serie_documento=sello,
                numero_documento=num_doc,
                nit_proveedor=nit_proveedor,
                nombre_proveedor=nombre_proveedor,
                compras_internas_exentas=total_exenta,
                compras_internas_gravadas=total_gravada,
                credito_fiscal=iva,
                total_compras=total_compras,
                tipo_operacion=tipo_op_default,
                clasificacion="1",
                sector="2",
                tipo_costo_gasto="5",
                raw_json=dte_json,
                omitido=False,
                version=version
            )
            
            db.add(nuevo_dte)
            procesados += 1
            
        except Exception as e:
            errores.append(f"{file.filename}: Error procesando datos ({str(e)}).")
            
    db.commit()
    
    return {
        "message": f"Archivos procesados: {procesados} correctos, {len(errores)} errores.",
        "procesados": procesados,
        "descartados_otra_empresa": descartados_otra_empresa,
        "descartados_otro_periodo": descartados_otro_periodo,
        "errores": errores
    }

@router.get("/{empresa_id}")
def get_compras(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    compras = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio,
        DteCompra.version == version
    ).order_by(DteCompra.fecha_emision.asc()).all()
    
    return compras

@router.put("/toggle_omitir/{dte_id}")
def toggle_omitir(dte_id: int, db: Session = Depends(get_db)):
    dte = db.query(DteCompra).filter(DteCompra.id == dte_id).first()
    if not dte:
        raise HTTPException(status_code=404, detail="DTE no encontrado")
        
    if is_periodo_declarado(db, dte.empresa_id, dte.periodo_anio, dte.periodo_mes, version=dte.version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    dte.omitido = not (dte.omitido or False)
    db.commit()
    estado_str = "omitido" if dte.omitido else "incluido"
    return {"message": f"Documento {estado_str} exitosamente", "omitido": dte.omitido}

@router.delete("/item/{dte_id}")
def delete_compra_item(dte_id: int, db: Session = Depends(get_db)):
    dte = db.query(DteCompra).filter(DteCompra.id == dte_id).first()
    if not dte:
        raise HTTPException(status_code=404, detail="DTE no encontrado")
        
    if is_periodo_declarado(db, dte.empresa_id, dte.periodo_anio, dte.periodo_mes, version=dte.version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    db.delete(dte)
    db.commit()
    return {"message": "Documento eliminado correctamente"}

@router.put("/update_operacion/{dte_id}")
def update_operacion(dte_id: int, tipo_operacion: str, clasificacion: str, sector: str, tipo_costo: str, db: Session = Depends(get_db)):
    dte = db.query(DteCompra).filter(DteCompra.id == dte_id).first()
    if not dte:
        raise HTTPException(status_code=404, detail="DTE no encontrado")
        
    if is_periodo_declarado(db, dte.empresa_id, dte.periodo_anio, dte.periodo_mes):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    dte.tipo_operacion = tipo_operacion
    dte.clasificacion = clasificacion
    dte.sector = sector
    dte.tipo_costo_gasto = tipo_costo
    db.commit()
    return {"message": "Actualizado"}

@router.get("/{empresa_id}/export")
def export_csv(empresa_id: int, mes: str, anio: str, version: int = 1, omitidos: Optional[str] = None, db: Session = Depends(get_db)):
    # Filtrar solo compras que NO estén omitidas
    query = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio,
        DteCompra.version == version,
        DteCompra.tipo_documento != "14",
        (DteCompra.omitido == False) | (DteCompra.omitido == None)
    )
    
    if omitidos:
        try:
            ids_to_exclude = [int(x.strip()) for x in omitidos.split(",") if x.strip().isdigit()]
            if ids_to_exclude:
                query = query.filter(~DteCompra.id.in_(ids_to_exclude))
        except Exception:
            pass

    compras = query.order_by(DteCompra.fecha_emision.asc()).all()
    
    # Generar CSV en memoria
    output = StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    def format_money(val):
        return f"{val or 0.0:.2f}"

    def get_valid(val, default_val):
        return default_val if not val else val
        
    for c in compras:
        doc_clean = (c.nit_proveedor or "").replace("-", "").strip()
        # En El Salvador: DUI tiene 9 dígitos o 10 con guión (ej: 016812897)
        # NIT tradicional tiene 14 dígitos.
        is_dui = False
        if c.tipo_documento == "14":
            rec = (c.raw_json or {}).get("receptor", {}) if isinstance(c.raw_json, dict) else {}
            tipo_doc_rec = rec.get("tipoDocumento", "")
            if tipo_doc_rec == "36" or len(doc_clean) <= 10:
                is_dui = True

        nit_export = "" if is_dui else doc_clean
        dui_export = doc_clean if is_dui else ""

        row = [
            c.fecha_emision,
            c.clase_documento,
            c.tipo_documento,
            c.numero_resolucion,
            nit_export,
            c.nombre_proveedor,
            format_money(c.compras_internas_exentas),
            format_money(c.internaciones_exentas),
            format_money(c.importaciones_exentas),
            format_money(c.compras_internas_gravadas),
            format_money(c.internaciones_gravadas_bienes),
            format_money(c.importaciones_gravadas_bienes),
            format_money(c.importaciones_gravadas_servicios),
            f"{c.credito_fiscal:.2f}",
            f"{c.total_compras:.2f}",
            dui_export, # DUI Proveedor (vacío si hay NIT)
            get_valid(c.tipo_operacion, "2" if c.tipo_documento == "14" else "1"),
            get_valid(c.clasificacion, "1"),  
            get_valid(c.sector, "2"),
            get_valid(c.tipo_costo_gasto, "5"),
            "3" # Número de Anexo (siempre 3 para compras)
        ]
        writer.writerow(row)
        
    output.seek(0)
    filename = f"Compras_{anio}{mes}.csv"
    
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)

@router.get("/{empresa_id}/export_anexo5")
def export_csv_anexo5(empresa_id: int, mes: str, anio: str, version: int = 1, omitidos: Optional[str] = None, db: Session = Depends(get_db)):
    """Exporta el Anexo 5 (Compras a Sujetos Excluidos - Casilla 66 de F-07) según normativa oficial del Ministerio de Hacienda."""
    query = db.query(DteCompra).filter(
        DteCompra.empresa_id == empresa_id,
        DteCompra.periodo_mes == mes,
        DteCompra.periodo_anio == anio,
        DteCompra.version == version,
        DteCompra.tipo_documento == "14",
        (DteCompra.omitido == False) | (DteCompra.omitido == None)
    )
    
    if omitidos:
        try:
            ids_to_exclude = [int(x.strip()) for x in omitidos.split(",") if x.strip().isdigit()]
            if ids_to_exclude:
                query = query.filter(~DteCompra.id.in_(ids_to_exclude))
        except Exception:
            pass

    compras = query.order_by(DteCompra.fecha_emision.asc()).all()
    
    output = StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    
    def format_money(val):
        return f"{val or 0.0:.2f}"

    def get_valid(val, default_val):
        return default_val if not val else val
        
    for c in compras:
        doc_clean = (c.nit_proveedor or "").replace("-", "").strip()
        rec = (c.raw_json or {}).get("receptor", {}) if isinstance(c.raw_json, dict) else {}
        tipo_doc_rec = rec.get("tipoDocumento", "")
        
        # Tipo documento identificación: 1=NIT, 2=DUI, 3=Otro
        if tipo_doc_rec == "36" or len(doc_clean) <= 10:
            tipo_id = "2"
        elif tipo_doc_rec == "13" or len(doc_clean) == 14:
            tipo_id = "1"
        else:
            tipo_id = "3"

        row = [
            tipo_id,                             # Col A: Tipo de Documento (1=NIT, 2=DUI, 3=Otro)
            doc_clean,                           # Col B: Número de Identificación
            c.nombre_proveedor,                  # Col C: Nombre o Razón Social
            c.fecha_emision,                     # Col D: Fecha de Emisión (DD/MM/AAAA)
            c.serie_documento,                   # Col E: Serie del Documento (Sello de recepción)
            c.numero_documento,                  # Col F: Número de Documento (Código de generación sin guiones)
            format_money(c.total_compras),       # Col G: Monto de la Operación
            "0.00",                              # Col H: Monto Retención IVA 13%
            get_valid(c.tipo_operacion, "2"),    # Col I: Tipo de Operación (2=No Gravada)
            get_valid(c.clasificacion, "1"),     # Col J: Clasificación (1=Costo, 2=Gasto)
            get_valid(c.sector, "2"),            # Col K: Sector
            get_valid(c.tipo_costo_gasto, "5"),  # Col L: Tipo de Costo/Gasto
            "5"                                  # Col M: Número de Anexo (5=Sujetos Excluidos)
        ]
        writer.writerow(row)
        
    output.seek(0)
    filename = f"SujetosExcluidos_{anio}{mes}.csv"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)

