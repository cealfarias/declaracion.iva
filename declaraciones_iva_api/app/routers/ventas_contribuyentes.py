import csv
import io
import re
from io import StringIO, BytesIO
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import DteVentaContribuyente, Empresa, DeclaracionEstado, DteAnulado

router = APIRouter()

def is_periodo_declarado(db: Session, empresa_id: int, anio: str, mes: str, tipo_libro: str = 'ventas_contribuyentes', version: int = 1) -> bool:
    estado = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro,
        DeclaracionEstado.version == version
    ).first()
    return estado.declarado if estado else False

@router.get('/estado/{empresa_id}')
def get_estado_declaracion(empresa_id: int, mes: str, anio: str, tipo_libro: str = 'ventas_contribuyentes', db: Session = Depends(get_db)):
    estados = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro
    ).order_by(DeclaracionEstado.version.asc()).all()
    
    if not estados:
        return {'versiones': [{'version': 1, 'declarado': False, 'numero_declaracion': None}]}
        
    res = []
    for e in estados:
        res.append({'version': e.version, 'declarado': e.declarado, 'numero_declaracion': e.numero_declaracion})
    return {'versiones': res}

@router.put('/estado/{empresa_id}/numero')
def update_numero_declaracion(empresa_id: int, mes: str, anio: str, numero: str, version: int = 1, tipo_libro: str = 'ventas_contribuyentes', db: Session = Depends(get_db)):
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
    return {'mensaje': 'Número guardado'}

@router.post('/declarar/{empresa_id}')
def marcar_como_declarado(empresa_id: int, mes: str, anio: str, version: int = 1, tipo_libro: str = 'ventas_contribuyentes', db: Session = Depends(get_db)):
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
    return {'mensaje': 'Período marcado como declarado'}

@router.delete('/limpiar/{empresa_id}')
def limpiar_periodo(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    if is_periodo_declarado(db, empresa_id, anio, mes, tipo_libro='ventas_contribuyentes', version=version):
        raise HTTPException(status_code=403, detail='El período está declarado y no puede ser modificado.')
        
    db.query(DteVentaContribuyente).filter(
        DteVentaContribuyente.empresa_id == empresa_id,
        DteVentaContribuyente.periodo_mes == mes,
        DteVentaContribuyente.periodo_anio == anio,
        DteVentaContribuyente.version == version
    ).delete()
    db.commit()
    return {'mensaje': 'Período limpiado correctamente'}

@router.post('/modificatoria/{empresa_id}')
def crear_modificatoria(empresa_id: int, mes: str, anio: str, numero_original: str, tipo_libro: str = 'ventas_contribuyentes', db: Session = Depends(get_db)):
    estados = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro
    ).order_by(DeclaracionEstado.version.desc()).all()
    
    ultima_version = estados[0].version if estados else 1
    if ultima_version >= 3:
        raise HTTPException(status_code=400, detail='Se alcanzó el límite de 2 modificatorias.')
        
    nueva_version = ultima_version + 1
    
    ventas = db.query(DteVentaContribuyente).filter(
        DteVentaContribuyente.empresa_id == empresa_id,
        DteVentaContribuyente.periodo_anio == anio,
        DteVentaContribuyente.periodo_mes == mes,
        DteVentaContribuyente.version == ultima_version
    ).all()
    
    for v in ventas:
        nuevo = DteVentaContribuyente(
            empresa_id=v.empresa_id,
            periodo_mes=v.periodo_mes,
            periodo_anio=v.periodo_anio,
            fecha_emision=v.fecha_emision,
            clase_documento=v.clase_documento,
            tipo_documento=v.tipo_documento,
            numero_resolucion=v.numero_resolucion,
            serie_documento=v.serie_documento,
            numero_documento=v.numero_documento,
            numero_control_interno=v.numero_control_interno,
            nit_nrc_cliente=v.nit_nrc_cliente,
            nombre_cliente=v.nombre_cliente,
            ventas_exentas=v.ventas_exentas,
            ventas_no_sujetas=v.ventas_no_sujetas,
            ventas_gravadas=v.ventas_gravadas,
            debito_fiscal=v.debito_fiscal,
            ventas_terceros=v.ventas_terceros,
            debito_terceros=v.debito_terceros,
            total_ventas=v.total_ventas,
            dui_cliente=v.dui_cliente,
            tipo_operacion=v.tipo_operacion,
            tipo_ingreso=v.tipo_ingreso,
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
    return {'mensaje': 'Modificatoria creada', 'nueva_version': nueva_version}

@router.post('/upload')
async def upload_dtes(
    empresa_id: int = Form(...),
    periodo_mes: str = Form(...),
    periodo_anio: str = Form(...),
    files: List[UploadFile] = File(...),
    version: int = Form(1),
    db: Session = Depends(get_db)
):
    if is_periodo_declarado(db, empresa_id, periodo_anio, periodo_mes, tipo_libro='ventas_contribuyentes', version=version):
        raise HTTPException(status_code=403, detail='El período está declarado y no puede ser modificado.')

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail='Empresa no encontrada')

    procesados = 0
    errores = []

    for file in files:
        fname = file.filename.lower()
        if not (fname.endswith('.json') or fname.endswith('.csv') or fname.endswith('.xlsx') or fname.endswith('.xls')):
            errores.append(f'{file.filename}: Formato no soportado. Debe ser archivo JSON de DTE, o Excel/CSV oficial del Libro de Ventas de Hacienda.')
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
                if "fecha de emision" in line_str or "fecha de emisión" in line_str:
                    header_idx = idx

            # Validar pertenencia a la empresa
            if nit_reporte:
                clean_rep_nit = clean_id(nit_reporte)
                if emp_nit and clean_rep_nit and clean_rep_nit not in emp_nit and emp_nit not in clean_rep_nit:
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

            for r in rows[start_row:]:
                clean_cells = [c.strip() for c in r if c and str(c).strip()]
                if not clean_cells:
                    continue

                try:
                    # Estructura del reporte oficial de ventas de Hacienda:
                    # [0]="", [1]=No., [2]=Fecha de Emisión, [3]=No. de Doc., [4]=Nombre del Cliente, [5]=NRC,
                    # [6]=Exentas, [7]=Ventas no Sujetas, [8]=Gravadas, [9]=Débito Fiscal,
                    # [10]=Valor Ventas Terceros, [11]=Débito Fiscal Terceros, [12]=FOVIAL, [13]=COTRANS,
                    # [14]=Total, [15]=IVA Percibido, [16]=IVA Retenido
                    shift = 1 if (len(r) > 1 and r[0].strip() == "" and r[1].strip().isdigit()) else 0
                    if len(r) <= shift + 8:
                        continue

                    val_item = str(r[shift]).strip()
                    if not val_item.isdigit():
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

                    no_doc_raw = str(r[shift + 2]).strip()
                    num_doc_clean = no_doc_raw.replace("-", "").upper() if no_doc_raw else ""

                    nombre_cliente = str(r[shift + 3]).strip() if len(r) > shift + 3 else "SIN NOMBRE"
                    nrc_cliente = str(r[shift + 4]).strip() if len(r) > shift + 4 else ""
                    nit_nrc_clean = nrc_cliente.replace("-", "").strip()

                    def to_float(val_c):
                        try:
                            s = str(val_c).replace("$", "").replace(",", "").strip()
                            return float(s) if s else 0.0
                        except Exception:
                            return 0.0

                    exentas = to_float(r[shift + 5]) if len(r) > shift + 5 else 0.0
                    no_sujetas = to_float(r[shift + 6]) if len(r) > shift + 6 else 0.0
                    gravadas = to_float(r[shift + 7]) if len(r) > shift + 7 else 0.0
                    debito_fiscal = to_float(r[shift + 8]) if len(r) > shift + 8 else 0.0
                    if debito_fiscal == 0.0 and gravadas > 0:
                        debito_fiscal = round(gravadas * 0.13, 2)

                    ventas_terceros = to_float(r[shift + 9]) if len(r) > shift + 9 else 0.0
                    debito_terceros = to_float(r[shift + 10]) if len(r) > shift + 10 else 0.0
                    total_ventas = to_float(r[shift + 13]) if len(r) > shift + 13 else (gravadas + debito_fiscal + exentas + no_sujetas)

                    # Evitar duplicados
                    existe = db.query(DteVentaContribuyente).filter(
                        DteVentaContribuyente.empresa_id == empresa_id,
                        DteVentaContribuyente.numero_documento == num_doc_clean,
                        DteVentaContribuyente.version == version
                    ).first()

                    if existe:
                        continue

                    nuevo_dte = DteVentaContribuyente(
                        empresa_id=empresa_id,
                        periodo_mes=mes_row,
                        periodo_anio=anio_row,
                        fecha_emision=fecha_emision,
                        clase_documento='4',
                        tipo_documento='03', # Comprobante de Crédito Fiscal
                        numero_resolucion=num_doc_clean,
                        serie_documento='',
                        numero_documento=num_doc_clean,
                        numero_control_interno='',
                        nit_nrc_cliente=nit_nrc_clean,
                        nombre_cliente=nombre_cliente,
                        ventas_exentas=exentas,
                        ventas_no_sujetas=no_sujetas,
                        ventas_gravadas=gravadas,
                        debito_fiscal=debito_fiscal,
                        ventas_terceros=ventas_terceros,
                        debito_terceros=debito_terceros,
                        total_ventas=total_ventas,
                        dui_cliente='',
                        tipo_operacion='1',
                        tipo_ingreso='2',
                        raw_json={"origen": "reporte_hacienda_excel", "fila": r},
                        version=version
                    )
                    db.add(nuevo_dte)
                    procesados += 1
                    filas_procesadas += 1

                except Exception as row_err:
                    continue

            db.commit()
            if filas_procesadas == 0 and not errores:
                errores.append(f"{file.filename}: No se encontraron filas de ventas válidas para el período {periodo_mes}/{periodo_anio}.")
            continue

        # CASO 2: Archivo JSON individual de DTE
        decoded_content = None
        dte_json = None
        
        for encoding in ['utf-8-sig', 'latin-1', 'windows-1252', 'utf-16']:
            try:
                decoded_content = content.decode(encoding).strip()
                dte_json = json.loads(decoded_content)
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
                
        if dte_json is None:
            errores.append(f'{file.filename}: No es un JSON válido o tiene codificación incorrecta.')
            continue
            
        try:
            if 'dteJson' in dte_json and isinstance(dte_json['dteJson'], dict):
                dte_json = dte_json['dteJson']
                
            identificacion = dte_json.get('identificacion', {})
            tipo_dte = identificacion.get('tipoDte', '')
            
            if tipo_dte not in ['03', '05', '06', '11']:
                # Ignorar silenciosamente para permitir subir carpetas mixtas
                continue

            # Filtro por empresa: En ventas a contribuyentes, nuestra empresa es el EMISOR
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
                
            resumen = dte_json.get('resumen', {})
            receptor = dte_json.get('receptor', {}) or {}
            
            fecha_cruda = identificacion.get('fecEmi', '')
            try:
                fec_clean = str(fecha_cruda).split('T')[0].split(' ')[0].strip()
                fecha_obj = datetime.strptime(fec_clean, '%Y-%m-%d')
                fecha_emision = fecha_obj.strftime('%d/%m/%Y')
                mes_dte = f"{fecha_obj.month:02d}"
                anio_dte = str(fecha_obj.year)
            except Exception:
                errores.append(f'{file.filename}: Fecha de emisión inválida o formato no reconocido ({fecha_cruda}).')
                continue
                
            # VALIDACION ESTRICTA: Las ventas no se pueden diferir de mes por ley de IVA
            if mes_dte != periodo_mes or anio_dte != periodo_anio:
                errores.append(f'{file.filename}: La fecha de emisión ({fecha_cruda}) corresponde al período {mes_dte}/{anio_dte}, no al período seleccionado ({periodo_mes}/{periodo_anio}). Por ley de IVA de El Salvador, las ventas deben declararse obligatoriamente en el mes en que fueron emitidas.')
                continue
                
            codigo_generacion = identificacion.get('codigoGeneracion', '')
            sello = identificacion.get('selloRecibido', '')
            if not sello:
                sello = dte_json.get('selloRecibido', '')
            if not sello:
                sello = dte_json.get('selloRecepcion', '')
            if not sello:
                sello = identificacion.get('numeroControl', '')
                
            num_doc_clean = codigo_generacion.replace('-', '')
            
            existe = db.query(DteVentaContribuyente).filter(
                DteVentaContribuyente.empresa_id == empresa_id,
                DteVentaContribuyente.numero_documento == num_doc_clean,
                DteVentaContribuyente.version == version
            ).first()
            
            if existe:
                errores.append(f'{file.filename}: Ya fue procesado anteriormente en el mes {existe.periodo_mes}/{existe.periodo_anio}.')
                continue

            nit = receptor.get('nit', '')
            nrc = receptor.get('nrc', '')
            nit_nrc = nrc if nrc else nit
            nit_nrc_clean = nit_nrc.replace('-', '') if nit_nrc else ''
            
            nombre_cliente = receptor.get('nombre', receptor.get('nombreComercial', 'SIN NOMBRE'))
            
            total_exenta = float(resumen.get('totalExenta', 0.0))
            total_no_suj = float(resumen.get('totalNoSuj', 0.0))
            total_gravada = float(resumen.get('totalGravada', 0.0))
            iva = float(resumen.get('tributos', [{}])[0].get('valor', 0.0)) if 'tributos' in resumen and len(resumen['tributos']) > 0 else 0.0
            
            if iva == 0.0 and total_gravada > 0:
                iva = round(total_gravada * 0.13, 2)
                
            total_pagar = float(resumen.get('totalPagar', 0.0))

            nuevo_dte = DteVentaContribuyente(
                empresa_id=empresa_id,
                periodo_mes=mes_dte,
                periodo_anio=anio_dte,
                fecha_emision=fecha_emision,
                clase_documento='4',
                tipo_documento=tipo_dte,
                numero_resolucion=identificacion.get('numeroControl', '').replace('-', ''),
                serie_documento=sello,
                numero_documento=num_doc_clean,
                numero_control_interno='',
                nit_nrc_cliente=nit_nrc_clean,
                nombre_cliente=nombre_cliente,
                ventas_exentas=total_exenta,
                ventas_no_sujetas=total_no_suj,
                ventas_gravadas=total_gravada,
                debito_fiscal=iva,
                ventas_terceros=0.0,
                debito_terceros=0.0,
                total_ventas=total_pagar,
                dui_cliente='',
                tipo_operacion='1',
                tipo_ingreso='2',
                raw_json=dte_json,
                version=version
            )
            db.add(nuevo_dte)
            db.commit()
            procesados += 1
            
        except Exception as e:
            db.rollback()
            errores.append(f'{file.filename}: Error interno ({str(e)}).')

    return {
        'procesados': procesados,
        'errores': errores
    }

@router.get('/list/{empresa_id}')
def get_ventas_contribuyentes(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    ventas = db.query(DteVentaContribuyente).filter(
        DteVentaContribuyente.empresa_id == empresa_id,
        DteVentaContribuyente.periodo_mes == mes,
        DteVentaContribuyente.periodo_anio == anio,
        DteVentaContribuyente.version == version
    ).order_by(DteVentaContribuyente.fecha_emision).all()
    
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    
    set_anulados = {a.codigo_generacion for a in anulados}
    
    res = []
    for v in ventas:
        cg_clean = v.numero_documento
        v_dict = v.__dict__.copy()
        v_dict.pop('_sa_instance_state', None)
        v_dict['anulado'] = cg_clean in set_anulados
        res.append(v_dict)
        
    return res

@router.get('/export_csv/{empresa_id}')
def export_ventas_contribuyentes_csv(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    ventas = db.query(DteVentaContribuyente).filter(
        DteVentaContribuyente.empresa_id == empresa_id,
        DteVentaContribuyente.periodo_mes == mes,
        DteVentaContribuyente.periodo_anio == anio,
        DteVentaContribuyente.version == version
    ).order_by(DteVentaContribuyente.fecha_emision).all()
    
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    set_anulados = {a.codigo_generacion for a in anulados}

    output = StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\r\n')

    for v in ventas:
        if v.numero_documento in set_anulados:
            continue
            
        def fmt(val):
            return f'{val:.2f}'
            
        row = [
            v.fecha_emision,
            v.clase_documento,
            v.tipo_documento,
            v.numero_resolucion.replace('-', ''),
            v.serie_documento,
            v.numero_documento,
            '',
            v.nit_nrc_cliente,
            v.nombre_cliente,
            fmt(v.ventas_exentas),
            fmt(v.ventas_no_sujetas),
            fmt(v.ventas_gravadas),
            fmt(v.debito_fiscal),
            fmt(v.ventas_terceros),
            fmt(v.debito_terceros),
            fmt(v.total_ventas),
            v.dui_cliente or '',
            v.tipo_operacion or '1',
            v.tipo_ingreso or '2',
            '1'
        ]
        writer.writerow(row)

    output.seek(0)
    content = output.getvalue().encode('utf-8')

    headers = {
        'Content-Disposition': f'attachment; filename=\"F07_Ventas_Contribuyentes_{mes}_{anio}_v{version}.csv\"'
    }

    return StreamingResponse(
        iter([content]),
        media_type='text/csv',
        headers=headers
    )

@router.put('/update_operacion/{id}')
def update_operacion(id: int, tipo_operacion: str, tipo_ingreso: str, db: Session = Depends(get_db)):
    dte = db.query(DteVentaContribuyente).filter(DteVentaContribuyente.id == id).first()
    if not dte:
        raise HTTPException(status_code=404, detail='Documento no encontrado')
        
    dte.tipo_operacion = tipo_operacion
    dte.tipo_ingreso = tipo_ingreso
    db.commit()
    return {'mensaje': 'Actualizado correctamente'}
