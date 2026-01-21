import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection parameters
DB_USER = "postgres"
DB_PASSWORD = "Nakaye0@#"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "apf_portal"

try:
    # Connect to PostgreSQL server
    conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database="postgres"  # Connect to default database first
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cursor.fetchone()
    
    if exists:
        print(f"Database '{DB_NAME}' already exists!")
    else:
        # Create database
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        print(f"Database '{DB_NAME}' created successfully!")
    
    cursor.close()
    conn.close()
    
except psycopg2.Error as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
