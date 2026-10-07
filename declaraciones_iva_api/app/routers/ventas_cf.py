import csv
from io import StringIO, BytesIO
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import DteVenta, Empresa, DeclaracionEstado, DteAnulado
from app.routers.compras import is_periodo_declarado

router = APIRouter()

@router.get("/estado/{empresa_id}")
def get_estado_declaracion(empresa_id: int, mes: str, anio: str, tipo_libro: str = "ventas_cf", db: Session = Depends(get_db)):
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
def update_numero_declaracion(empresa_id: int, mes: str, anio: str, numero: str, version: int = 1, tipo_libro: str = "ventas_cf", db: Session = Depends(get_db)):
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

@router.post("/declarar/{empresa_id}")
def marcar_como_declarado(empresa_id: int, mes: str, anio: str, version: int = 1, tipo_libro: str = "ventas_cf", db: Session = Depends(get_db)):
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

@router.post("/modificatoria/{empresa_id}")
def crear_modificatoria(empresa_id: int, mes: str, anio: str, numero_original: str, tipo_libro: str = "ventas_cf", db: Session = Depends(get_db)):
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
    
    ventas = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_anio == anio,
        DteVenta.periodo_mes == mes,
        DteVenta.version == ultima_version
    ).all()
    
    for v in ventas:
        nuevo = DteVenta(
            empresa_id=v.empresa_id,
            periodo_mes=v.periodo_mes,
            periodo_anio=v.periodo_anio,
            fecha_emision=v.fecha_emision,
            clase_documento=v.clase_documento,
            tipo_documento=v.tipo_documento,
            numero_resolucion=v.numero_resolucion,
            serie_documento=v.serie_documento,
            numero_control_del=v.numero_control_del,
            numero_control_al=v.numero_control_al,
            codigo_generacion=v.codigo_generacion,
            sello_recepcion=v.sello_recepcion,
            nit_cliente=v.nit_cliente,
            ventas_exentas=v.ventas_exentas,
            ventas_no_sujetas=v.ventas_no_sujetas,
            ventas_gravadas=v.ventas_gravadas,
            exportaciones=v.exportaciones,
            ventas_zona_franca=v.ventas_zona_franca,
            ventas_terceros=v.ventas_terceros,
            total_ventas=v.total_ventas,
            raw_json=v.raw_json,
            version=nueva_version
        )
        db.add(nuevo)
        
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


@router.delete("/limpiar/{empresa_id}")
def limpiar_periodo(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    if is_periodo_declarado(db, empresa_id, anio, mes, tipo_libro="ventas_cf", version=version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio,
        DteVenta.version == version
    ).delete()
    db.commit()
    return {"mensaje": "Período limpiado correctamente"}

@router.post("/upload")
async def upload_dtes_cf(
    empresa_id: int = Form(...),
    periodo_mes: str = Form(...),
    periodo_anio: str = Form(...),
    files: List[UploadFile] = File(...),
    version: int = Form(1),
    db: Session = Depends(get_db)
):
    if is_periodo_declarado(db, empresa_id, periodo_anio, periodo_mes, tipo_libro="ventas_cf", version=version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    procesados = 0
    errores = []

    for file in files:
        fname = file.filename.lower()
        if not (fname.endswith('.json') or fname.endswith('.csv') or fname.endswith('.xlsx') or fname.endswith('.xls')):
            errores.append(f'{file.filename}: Formato no soportado. Debe ser archivo JSON de DTE, o Excel/CSV oficial del Libro de Ventas a Consumidor de Hacienda.')
            continue
            
        content = await file.read()

        def clean_id(val) -> str:
            return str(val or "").replace("-", "").strip().lower()

        emp_nit = clean_id(empresa.nit)
        emp_nrc = clean_id(empresa.nrc)

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
                for encoding in ['utf-8-sig', 'latin-1', 'windows-1252', 'utf-16']:
                    try:
                        decoded_str = content.decode(encoding)
                        reader = csv.reader(StringIO(decoded_str))
                        rows = list(reader)
                        break
                    except Exception:
                        continue

            if not rows:
                errores.append(f"{file.filename}: Archivo vacío o codificación no soportada.")
                continue

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
                if "código de generación" in line_str or "codigo de generacion" in line_str or "número de correlativo" in line_str or "numero de correlativo" in line_str:
                    header_idx = idx

            # Validar pertenencia a la empresa
            if nit_reporte:
                clean_rep_nit = clean_id(nit_reporte).lstrip("0")
                clean_emp_nit = emp_nit.lstrip("0")
                if clean_emp_nit and clean_rep_nit and clean_emp_nit != clean_rep_nit and clean_rep_nit not in clean_emp_nit and clean_emp_nit not in clean_rep_nit:
                    errores.append(f"{file.filename}: El NIT del reporte ({nit_reporte}) no coincide con la empresa seleccionada ({empresa.nit}).")
                    continue

            # Validar período
            if periodo_reporte and "/" in periodo_reporte:
                p_parts = periodo_reporte.strip().split("/")
                if len(p_parts) == 2:
                    p_mes = p_parts[0].zfill(2)
                    p_anio = p_parts[1].strip()
                    if p_mes != periodo_mes or p_anio != periodo_anio:
                        errores.append(f"{file.filename}: El período del reporte ({periodo_reporte}) no coincide con el seleccionado ({periodo_mes}/{periodo_anio}).")
                        continue

            start_row = (header_idx + 2) if header_idx != -1 else 0
            filas_procesadas = 0

            def is_item_num(val):
                s = str(val or "").strip()
                try:
                    f = float(s)
                    return f > 0 and (f == int(f))
                except Exception:
                    return False

            def to_float(val_c):
                try:
                    s = str(val_c).replace("$", "").replace(",", "").strip()
                    return float(s) if s else 0.0
                except Exception:
                    return 0.0

            for r in rows[start_row:]:
                clean_cells = [c.strip() for c in r if c and str(c).strip()]
                if not clean_cells:
                    continue

                try:
                    # Estructura del reporte oficial de Consumidor Final de Hacienda:
                    # [0]="", [1]=No., [2]=Fecha, [3]=Cód Gen Inicial, [4]=Cód Gen Final,
                    # [5]=Correlativo Del, [6]=Correlativo Al, [7]=Venta No Sujeta, [8]=Exportaciones,
                    # [9]=Exentas, [10]=Gravadas, [11]=Débito Fiscal, [12]=Terceros Valor,
                    # [13]=Terceros Débito, [14]=Total Ventas, [15]=Retención
                    shift = 0
                    if len(r) > 1 and r[0].strip() == "" and is_item_num(r[1]):
                        shift = 1
                    elif is_item_num(r[0]):
                        shift = 0
                    else:
                        continue

                    if len(r) <= shift + 9:
                        continue

                    fecha_str = str(r[shift + 1]).strip()
                    if not fecha_str or ("-" not in fecha_str and "/" not in fecha_str):
                        continue

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

                    if mes_row != periodo_mes or anio_row != periodo_anio:
                        continue

                    cg_ini_raw = str(r[shift + 2]).strip()
                    cg_fin_raw = str(r[shift + 3]).strip() if len(r) > shift + 3 else cg_ini_raw
                    ctrl_del = str(r[shift + 4]).strip() if len(r) > shift + 4 else "N/A"
                    ctrl_al = str(r[shift + 5]).strip() if len(r) > shift + 5 else ctrl_del

                    is_anulado = "INV" in cg_ini_raw.upper() or "-INV" in ctrl_del.upper()
                    clean_cg = cg_ini_raw.replace("-INV", "").replace("INV", "").replace("-", "").strip().upper()

                    if is_anulado:
                        # Si es un comprobante invalidado (-INV), registrarlo en anulados para excluirlo del cálculo fiscal
                        anulado_existente = db.query(DteAnulado).filter(
                            DteAnulado.empresa_id == empresa_id,
                            DteAnulado.codigo_generacion == clean_cg,
                            DteAnulado.version == version
                        ).first()
                        if not anulado_existente:
                            nuevo_anulado = DteAnulado(
                                empresa_id=empresa_id,
                                periodo_mes=mes_row,
                                periodo_anio=anio_row,
                                fecha_emision=fecha_emision,
                                tipo_documento="01",
                                codigo_generacion=clean_cg,
                                sello_recepcion=ctrl_del,
                                raw_json={"origen": "reporte_hacienda_excel_inv", "fila": r},
                                version=version
                            )
                            db.add(nuevo_anulado)
                            db.commit()
                        continue

                    no_sujetas = to_float(r[shift + 6]) if len(r) > shift + 6 else 0.0
                    exportaciones = to_float(r[shift + 7]) if len(r) > shift + 7 else 0.0
                    exentas = to_float(r[shift + 8]) if len(r) > shift + 8 else 0.0
                    gravadas = to_float(r[shift + 9]) if len(r) > shift + 9 else 0.0
                    debito_fiscal = to_float(r[shift + 10]) if len(r) > shift + 10 else 0.0
                    ventas_terceros = to_float(r[shift + 11]) if len(r) > shift + 11 else 0.0
                    total_ventas = to_float(r[shift + 13]) if len(r) > shift + 13 else (gravadas + exentas + no_sujetas + exportaciones)

                    # Evitar duplicados
                    existe = db.query(DteVenta).filter(
                        DteVenta.empresa_id == empresa_id,
                        DteVenta.codigo_generacion == clean_cg,
                        DteVenta.version == version
                    ).first()

                    if existe:
                        continue

                    nuevo_dte = DteVenta(
                        empresa_id=empresa_id,
                        periodo_mes=mes_row,
                        periodo_anio=anio_row,
                        fecha_emision=fecha_emision,
                        clase_documento="4",
                        tipo_documento="01",
                        numero_resolucion="N/A",
                        serie_documento="N/A",
                        numero_control_del=ctrl_del,
                        numero_control_al=ctrl_al,
                        codigo_generacion=clean_cg,
                        sello_recepcion=ctrl_del,
                        nit_cliente="Consumidor Final",
                        ventas_exentas=exentas,
                        ventas_no_sujetas=no_sujetas,
                        ventas_gravadas=gravadas,
                        exportaciones=exportaciones,
                        ventas_zona_franca=0.0,
                        ventas_terceros=ventas_terceros,
                        total_ventas=total_ventas,
                        raw_json={"origen": "reporte_hacienda_excel", "fila": r, "debito_fiscal": debito_fiscal},
                        version=version
                    )
                    db.add(nuevo_dte)
                    procesados += 1
                    filas_procesadas += 1

                except Exception as row_err:
                    continue

            db.commit()
            if filas_procesadas == 0 and not errores:
                errores.append(f"{file.filename}: No se encontraron filas de ventas a consumidor final para el período {periodo_mes}/{periodo_anio}.")
            continue

        # CASO 2: Archivo JSON individual de DTE
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
                # Ignorar silenciosamente para permitir subir carpetas mixtas
                continue

            # Filtro por empresa: En ventas, nuestra empresa es el EMISOR
            def clean_id(val) -> str:
                return str(val or "").replace("-", "").strip().lower()

            emp_nit = clean_id(empresa.nit)
            emp_nrc = clean_id(empresa.nrc)
            emisor_data = dte_json.get("emisor", {}) or {}
            emi_nit = clean_id(emisor_data.get("nit"))
            emi_nrc = clean_id(emisor_data.get("nrc"))
            pertenece = False
            if emp_nit and emi_nit and (emp_nit == emi_nit or emp_nit in emi_nit or emi_nit in emp_nit):
                pertenece = True
            elif emp_nrc and emi_nrc and (emp_nrc == emi_nrc or emp_nrc.lstrip("0") == emi_nrc.lstrip("0")):
                pertenece = True

            if not pertenece:
                continue
                
            resumen = dte_json.get("resumen", {})
            receptor = dte_json.get("receptor", {}) or {}
            
            fecha_cruda = identificacion.get("fecEmi", "")
            try:
                fec_clean = str(fecha_cruda).split('T')[0].split(' ')[0].strip()
                fecha_obj = datetime.strptime(fec_clean, "%Y-%m-%d")
                fecha_emision = fecha_obj.strftime("%d/%m/%Y")
                mes_dte = f"{fecha_obj.month:02d}"
                anio_dte = str(fecha_obj.year)
            except Exception:
                errores.append(f'{file.filename}: Fecha de emisión inválida o formato no reconocido ({fecha_cruda}).')
                continue
                
            # VALIDACION ESTRICTA: Las ventas no se pueden diferir de mes por ley de IVA
            if mes_dte != periodo_mes or anio_dte != periodo_anio:
                errores.append(f'{file.filename}: La fecha de emisión ({fecha_cruda}) corresponde al período {mes_dte}/{anio_dte}, no al período seleccionado ({periodo_mes}/{periodo_anio}). Por ley de IVA de El Salvador, las ventas deben declararse obligatoriamente en el mes en que fueron emitidas.')
                continue
                
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
                DteVenta.codigo_generacion == codigo_generacion,
                DteVenta.version == version
            ).first()
            
            if existe:
                errores.append(f"{file.filename}: Ya fue procesado anteriormente en el mes {existe.periodo_mes}/{existe.periodo_anio}.")
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
                periodo_mes=mes_dte,
                periodo_anio=anio_dte,
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
                raw_json=dte_json,
                version=version
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
def get_ventas(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    ventas = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio,
        DteVenta.version == version
    ).order_by(DteVenta.fecha_emision).all()
    
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    
    set_anulados = {a.codigo_generacion for a in anulados}
    
    res = []
    for v in ventas:
        cg_clean = v.codigo_generacion.replace("-", "")
        v_dict = v.__dict__.copy()
        v_dict.pop("_sa_instance_state", None)
        v_dict["anulado"] = cg_clean in set_anulados
        res.append(v_dict)
        
    return res

@router.get("/export_csv/{empresa_id}")
def export_ventas_csv(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    ventas = db.query(DteVenta).filter(
        DteVenta.empresa_id == empresa_id,
        DteVenta.periodo_mes == mes,
        DteVenta.periodo_anio == anio,
        DteVenta.version == version
    ).order_by(DteVenta.fecha_emision, DteVenta.creado_en).all()
    
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    set_anulados = {a.codigo_generacion for a in anulados}
    
    # Agrupar por dia
    from collections import defaultdict
    agrupado = defaultdict(list)
    for v in ventas:
        cg_clean = v.codigo_generacion.replace("-", "")
        if cg_clean not in set_anulados:
            agrupado[v.fecha_emision].append(v)
            
    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")

    for fecha, lista_dia in agrupado.items():
        def fmt(val):
            return f"{val:.2f}"
            
        v_exentas = sum(v.ventas_exentas for v in lista_dia)
        v_no_sujetas = sum(v.ventas_no_sujetas for v in lista_dia)
        v_gravadas = sum(v.ventas_gravadas for v in lista_dia)
        t_ventas = sum(v.total_ventas for v in lista_dia)
        
        # El primero y el ultimo emitido en el dia
        primer_dte = lista_dia[0].codigo_generacion.replace("-", "")
        ultimo_dte = lista_dia[-1].codigo_generacion.replace("-", "")
        
        row = [
            fecha,
            "4", # Clase
            "01", # Tipo
            "N/A", # Resolución
            "N/A", # Serie
            "N/A", # Control Del
            "N/A", # Control Al
            primer_dte, # Documento Del (Código Generación Inicial)
            ultimo_dte, # Documento Al (Código Generación Final)
            "", # Maquina registradora
            fmt(v_exentas),
            "0.00", # Internas exentas no sujetas a proporcionalidad
            fmt(v_no_sujetas),
            fmt(v_gravadas),
            "0.00", # Exp CA
            "0.00", # Exp Fuera CA
            "0.00", # Exp Servicios
            "0.00", # Zonas Francas
            "0.00", # Terceros no domiciliados
            fmt(t_ventas),
            "1", # Tipo Operacion
            "3", # Tipo Ingreso
            "2"  # Numero de Anexo (según F07 v14 es 2 para CF)
        ]
        writer.writerow(row)

    output.seek(0)
    content = output.getvalue().encode("utf-8")

    headers = {
        "Content-Disposition": f"attachment; filename=\"F07_Ventas_CF_{mes}_{anio}_v{version}.csv\""
    }

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers=headers
    )

