from typing import Optional

class EmpresaUpdate(BaseModel):
    razon_social: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    combustible_50_porciento: Optional[bool] = None

@router.put("/empresas/{empresa_id}")
def update_empresa(empresa_id: int, empresa_data: EmpresaUpdate, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter_by(id=empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    if empresa_data.razon_social is not None:
        empresa.razon_social = empresa_data.razon_social
    if empresa_data.nit is not None:
        empresa.nit = empresa_data.nit
    if empresa_data.nrc is not None:
        empresa.nrc = empresa_data.nrc
    if empresa_data.combustible_50_porciento is not None:
        empresa.combustible_50_porciento = empresa_data.combustible_50_porciento
        
    db.commit()
    return {"message": "Empresa actualizada correctamente"}
