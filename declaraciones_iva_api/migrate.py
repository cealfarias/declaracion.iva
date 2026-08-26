from sqlalchemy import create_engine
import sqlite3

conn = sqlite3.connect('iva_database.db')
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE iva_periodos_fiscales ADD COLUMN remanente_anterior FLOAT DEFAULT 0.0")
except Exception as e:
    print(f"Col already exists? {e}")

try:
    cursor.execute("ALTER TABLE iva_periodos_fiscales ADD COLUMN remanente_siguiente FLOAT DEFAULT 0.0")
except Exception as e:
    print(f"Col already exists? {e}")

conn.commit()
conn.close()
print("Migration done")
