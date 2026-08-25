from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.database import get_db
from app.models.models import PeriodoFiscal, Empresa

router = APIRouter()

class PeriodoCreate(BaseModel):
    empresa_id: int
    anio: int
    mes: int

@router.post("/periodos")
def create_periodo(periodo: PeriodoCreate, db: Session = Depends(get_db)):
    # Validar que la empresa exista
    empresa = db.query(Empresa).filter(Empresa.id == periodo.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
    # Verificar si ya existe el periodo
    db_periodo = db.query(PeriodoFiscal).filter(
        PeriodoFiscal.empresa_id == periodo.empresa_id,
        PeriodoFiscal.anio == periodo.anio,
        PeriodoFiscal.mes == periodo.mes
    ).first()
    
    if db_periodo:
        return {"message": "El periodo ya existe", "periodo_id": db_periodo.id}
        
    nuevo_periodo = PeriodoFiscal(
        empresa_id=periodo.empresa_id,
        anio=periodo.anio,
        mes=periodo.mes,
        estado="abierto"
    )
    db.add(nuevo_periodo)
    db.commit()
    db.refresh(nuevo_periodo)
    
    return {"message": "Periodo creado", "periodo_id": nuevo_periodo.id}

@router.get("/periodos/empresa/{empresa_id}")
def get_periodos(empresa_id: int, db: Session = Depends(get_db)):
    periodos = db.query(PeriodoFiscal).filter(PeriodoFiscal.empresa_id == empresa_id).all()
    return [
        {
            "id": p.id,
            "anio": p.anio,
            "mes": p.mes,
            "estado": p.estado
        } for p in periodos
    ]
