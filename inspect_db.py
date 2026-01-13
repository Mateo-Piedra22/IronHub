
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env vars from webapp-api .env
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, 'apps', 'webapp-api', '.env')
load_dotenv(env_path)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_engine(dbname):
    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{dbname}"
    return create_engine(url)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_db = sys.argv[1]
        print(f"Inspecting database: {target_db}...")
        try:
            engine = get_engine(target_db)
            with engine.connect() as conn:
                print(f"Connected to {target_db}")
                
                # List all tables
                # print("\nListing all tables...")
                result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"))
                tables = [row[0] for row in result]
                # print(tables)
                
                # Check for specific tables
                target_tables = ['numeracion_comprobantes', 'comprobantes_pago', 'ejercicios', 'recibos']
                
                print("\nChecking detailed schema for target tables:")
                for t in tables:
                    if t in target_tables or 'comprobante' in t:
                        print(f"\n  TABLE: {t}")
                        cols = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{t}';"))
                        print(f"    Columns:")
                        for c in cols:
                            print(f"      - {c[0]} ({c[1]})")
                            
        except Exception as e:
            print(f"Error connecting to {target_db}: {e}")

    else:
        # Connect to default postgres DB to list databases
        print("No database specified. Listing available databases...")
        try:
            engine = get_engine("postgres")
            with engine.connect() as conn:
                result = conn.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false;"))
                bs = [row[0] for row in result]
                print("Available Databases:", bs)
                print("\nRun: python inspect_db.py <dbname> to inspect a specific database.")
        except Exception as e:
            print(f"Error listing databases: {e}")
