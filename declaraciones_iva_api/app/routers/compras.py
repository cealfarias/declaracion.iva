import csv
from io import StringIO
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
        if not file.filename.lower().endswith('.json'):
            errores.append(f"{file.filename}: No es un archivo JSON.")
            continue
            
        content = await file.read()
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

            if mes_dte != periodo_mes or anio_dte != periodo_anio:
                # El comprobante corresponde a otro período
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
        elif len(doc_clean) <= 9 and doc_clean:
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

