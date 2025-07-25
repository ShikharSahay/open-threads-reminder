import psycopg2
from psycopg2 import sql, OperationalError

DB_HOST = "10.150.3.246"
DB_PORT = 5433
DB_USER = "yugabyte"
DB_PASSWORD = "Threads@123"
TEST_DB_NAME = "test_yb_db"

def connect_to_db(dbname):
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=dbname
    )

def create_test_db():
    try:
        conn = connect_to_db("yugabyte")  # Connect to a default db
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB_NAME)))
        print(f"✅ Database '{TEST_DB_NAME}' created.")

        cur.close()
        conn.close()
    except OperationalError as e:
        print(f"❌ Failed to create database: {e}")

def drop_test_db():
    try:
        conn = connect_to_db("yugabyte")
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(TEST_DB_NAME)))
        print(f"🗑️ Database '{TEST_DB_NAME}' deleted.")

        cur.close()
        conn.close()
    except OperationalError as e:
        print(f"❌ Failed to drop database: {e}")

if __name__ == "__main__":
    create_test_db()

    # Optional: connect and run a test query
    try:
        conn = connect_to_db(TEST_DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_database();")
        print("🔍 Connected to:", cur.fetchone()[0])
        cur.close()
        conn.close()
    except Exception as e:
        print("❌ Error connecting to test DB:", e)

    drop_test_db()
