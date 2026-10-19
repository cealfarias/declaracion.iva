import sys
sys.path.append('.')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import PeriodoFiscal, DteProcesado
from app.core.dte_parser import parse_compras, parse_ventas_contribuyente, parse_ventas_consumidor

engine = create_engine('sqlite:///./iva.db')
Session = sessionmaker(bind=engine)
db = Session()

periodo = db.query(PeriodoFiscal).filter_by(mes=4, anio=2026).first()
if not periodo:
    print('No periodo found')
    sys.exit(0)

dtes = db.query(DteProcesado).filter_by(periodo_id=periodo.id).all()
print(f'Found {len(dtes)} dtes')
for d in dtes:
    if d.tipo_documento == 'REMANENTE': continue
    try:
        if d.clasificacion == 'compra':
            parse_compras(d.datos_json)
        elif d.clasificacion == 'venta':
            parse_ventas_contribuyente(d.datos_json)
        elif d.clasificacion == 'venta_consumidor':
            parse_ventas_consumidor(d.datos_json)
    except Exception as e:
        import traceback
        print(f'Error on dte {d.id} {d.clasificacion}')
        traceback.print_exc()

