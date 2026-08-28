import csv
from io import StringIO
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import DteAnulado, Empresa, DeclaracionEstado

router = APIRouter()

def is_periodo_declarado(db: Session, empresa_id: int, anio: str, mes: str, tipo_libro: str = "anulados", version: int = 1) -> bool:
    estado = db.query(DeclaracionEstado).filter(
        DeclaracionEstado.empresa_id == empresa_id,
        DeclaracionEstado.anio == anio,
        DeclaracionEstado.mes == mes,
        DeclaracionEstado.tipo_libro == tipo_libro,
        DeclaracionEstado.version == version
    ).first()
    return estado.declarado if estado else False

@router.get("/estado/{empresa_id}")
def get_estado_declaracion(empresa_id: int, mes: str, anio: str, tipo_libro: str = "anulados", db: Session = Depends(get_db)):
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
def update_numero_declaracion(empresa_id: int, mes: str, anio: str, numero: str, version: int = 1, tipo_libro: str = "anulados", db: Session = Depends(get_db)):
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
def marcar_como_declarado(empresa_id: int, mes: str, anio: str, version: int = 1, tipo_libro: str = "anulados", db: Session = Depends(get_db)):
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
    if is_periodo_declarado(db, empresa_id, anio, mes, tipo_libro="anulados", version=version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")
        
    db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).delete()
    db.commit()
    return {"mensaje": "Período limpiado correctamente"}

@router.post("/modificatoria/{empresa_id}")
def crear_modificatoria(empresa_id: int, mes: str, anio: str, numero_original: str, tipo_libro: str = "anulados", db: Session = Depends(get_db)):
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
    
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_anio == anio,
        DteAnulado.periodo_mes == mes,
        DteAnulado.version == ultima_version
    ).all()
    
    for a in anulados:
        nuevo = DteAnulado(
            empresa_id=a.empresa_id,
            periodo_mes=a.periodo_mes,
            periodo_anio=a.periodo_anio,
            fecha_emision=a.fecha_emision,
            tipo_documento=a.tipo_documento,
            codigo_generacion=a.codigo_generacion,
            sello_recepcion=a.sello_recepcion,
            raw_json=a.raw_json,
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

@router.post("/upload")
async def upload_anulados(
    empresa_id: int = Form(...),
    periodo_mes: str = Form(...),
    periodo_anio: str = Form(...),
    files: List[UploadFile] = File(...),
    version: int = Form(1),
    db: Session = Depends(get_db)
):
    if is_periodo_declarado(db, empresa_id, periodo_anio, periodo_mes, tipo_libro="anulados", version=version):
        raise HTTPException(status_code=403, detail="El período está declarado y no puede ser modificado.")

    procesados = 0
    errores = []

    for file in files:
        if not file.filename.lower().endswith(".json"):
            errores.append(f"{file.filename}: No es un archivo JSON.")
            continue
            
        content = await file.read()
        decoded_content = None
        dte_json = None
        for encoding in ["utf-8-sig", "latin-1", "windows-1252", "utf-16"]:
            try:
                decoded_content = content.decode(encoding).strip()
                dte_json = json.loads(decoded_content)
                break
            except:
                continue
                
        if dte_json is None:
            errores.append(f"{file.filename}: No es un JSON válido o codificación incorrecta.")
            continue
            
        try:
            # Los JSON de invalidacion suelen tener la estructura:
            # { "identificacion": { "codigoGeneracion": "...", "tipoDte": "..." } }
            # o pueden venir envueltos.
            
            data = dte_json.get("dteJson", dte_json)
            identificacion = data.get("identificacion", {})
            motivo = data.get("motivo", {})
            
            # El codigoGeneracion que se esta invalidando
            codigo_generacion = identificacion.get("codigoGeneracion", "")
            
            if not codigo_generacion:
                # Intenta buscar en documento asociado
                doc_asoc = data.get("documentoAsociado", {})
                codigo_generacion = doc_asoc.get("codigoGeneracion", "")
            
            if not codigo_generacion:
                errores.append(f"{file.filename}: No contiene codigoGeneracion del documento original.")
                continue
                
            # Sello de recepcion de la invalidacion, si existe, o del documento
            sello_recepcion = data.get("selloRecepcion", identificacion.get("selloRecibido", "N/A"))
            
            tipo_dte = identificacion.get("tipoDte", "")
            
            fecha_cruda = identificacion.get("fecEmi", "")
            try:
                fecha_obj = datetime.strptime(fecha_cruda, "%Y-%m-%d")
                fecha_emision = fecha_obj.strftime("%d/%m/%Y")
            except:
                fecha_emision = fecha_cruda
                
            # Verificar si ya existe en esta version
            num_doc = codigo_generacion.replace("-", "")
            existe = db.query(DteAnulado).filter(
                DteAnulado.empresa_id == empresa_id,
                DteAnulado.codigo_generacion == num_doc,
                DteAnulado.version == version
            ).first()
            
            if existe:
                errores.append(f"{file.filename}: Ya fue procesado.")
                continue
                
            nuevo_dte = DteAnulado(
                empresa_id=empresa_id,
                periodo_mes=periodo_mes,
                periodo_anio=periodo_anio,
                fecha_emision=fecha_emision,
                tipo_documento=tipo_dte,
                codigo_generacion=num_doc,
                sello_recepcion=sello_recepcion,
                raw_json=dte_json,
                version=version
            )
            
            db.add(nuevo_dte)
            procesados += 1
            
        except Exception as e:
            errores.append(f"{file.filename}: Error procesando datos ({str(e)}).")
            
    db.commit()
    
    return {
        "procesados": procesados,
        "errores": errores
    }

@router.get("/list/{empresa_id}")
def get_anulados(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    
    res = []
    for a in anulados:
        res.append({
            "id": a.id,
            "fecha_emision": a.fecha_emision,
            "codigo_generacion": a.codigo_generacion,
            "tipo_documento": a.tipo_documento,
            "sello_recepcion": a.sello_recepcion
        })
    return res

@router.get("/export_csv/{empresa_id}")
def export_anulados_csv(empresa_id: int, mes: str, anio: str, version: int = 1, db: Session = Depends(get_db)):
    anulados = db.query(DteAnulado).filter(
        DteAnulado.empresa_id == empresa_id,
        DteAnulado.periodo_mes == mes,
        DteAnulado.periodo_anio == anio,
        DteAnulado.version == version
    ).all()
    
    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    
    for a in anulados:
        # A. Número de Resolución (0)
        # B. Clase (4)
        # C. Desde (0)
        # D. Hasta (0)
        # E. Tipo Documento (01, 03, etc)
        # F. Tipo Anulación (D)
        # G. Serie (Sello Recepción)
        # H. Desde Control (0)
        # I. Hasta Control (0)
        # J. Código Generación
        row = [
            "0",
            "4",
            "0",
            "0",
            a.tipo_documento or "01",
            "D",
            a.sello_recepcion,
            "0",
            "0",
            a.codigo_generacion
        ]
        writer.writerow(row)
        
    content = output.getvalue().encode("utf-8")
    headers = {
        "Content-Disposition": f"attachment; filename="F07_Anulados_{mes}_{anio}_v{version}.csv""
    }
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers=headers
    )
