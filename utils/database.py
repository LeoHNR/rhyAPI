from dotenv import load_dotenv
import os
import pyodbc
import logging
import json
from datetime import datetime
from decimal import Decimal

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

driver = os.getenv('SQL_DRIVER')
server = os.getenv('SQL_SERVER')
database = os.getenv('SQL_DATABASE')
username = os.getenv('SQL_USERNAME')
password = os.getenv('SQL_PASSWORD')

connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"

async def get_db_connection():
    try:
        logger.info(f"Intentando conectar a la base de datos con la cadena de conexión: {connection_string}")
        conn = pyodbc.connect(connection_string, timeout=10)
        logger.info("Conexión exitosa a la base de datos.")
        return conn
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise Exception(f"Database connection error: {str(e)}")

def convert_special_types(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, datetime):
                obj[key] = value.isoformat()
            elif isinstance(value, Decimal):
                obj[key] = float(value)
    return obj

async def fetch_query_as_json(query, is_procedure=False):
    conn = await get_db_connection()
    cursor = conn.cursor()
    logger.info(f"Ejecutando query: {query}")
    try:
        cursor.execute(query)

        if is_procedure and cursor.description is None:
            conn.commit()
            return json.dumps([{"status": 200, "message": "Procedure executed successfully"}])

        columns = [column[0] for column in cursor.description]
        results = []
        logger.info(f"Columns: {columns}")
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            result = convert_special_types(result)
            results.append(result)

        return json.dumps(results)

    except pyodbc.Error as e:
        raise Exception(f"Error ejecutando el query: {str(e)}")
    finally:
        cursor.close()
        conn.close()