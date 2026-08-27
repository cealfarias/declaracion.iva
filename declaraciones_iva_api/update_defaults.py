import os
from sqlalchemy import create_engine, update
from app.models.models import DteCompra
from app.core.database import Base

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "render.com" in SQLALCHEMY_DATABASE_URL and "sslmode=require" not in SQLALCHEMY_DATABASE_URL:
    join_char = "&" if "?" in SQLALCHEMY_DATABASE_URL else "?"
    SQLALCHEMY_DATABASE_URL += f"{join_char}sslmode=require"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def run():
    with engine.begin() as conn:
        conn.execute(
            update(DteCompra).values(
                tipo_operacion="1",
                clasificacion="1",
                sector="2",
                tipo_costo_gasto="1"
            )
        )
    print("Base de datos actualizada con los valores por defecto 1, 1, 2, 1.")

if __name__ == "__main__":
    run()
