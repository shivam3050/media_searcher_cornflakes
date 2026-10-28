import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

with open("schema.sql", encoding="utf-8") as f:
    sql = f.read()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute(sql)

print("schema ready")