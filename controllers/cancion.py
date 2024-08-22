import os
import json
from utils.database import fetch_query_as_json, get_db_connection
from utils.security import verify_jwt_token
from fastapi import HTTPException, Depends
from datetime import datetime, timedelta
from typing import List, Dict
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import pyodbc

async def fetch_cancion_details(cancion_id: int):
    query = f"""
    SELECT 
        c.cancion_id, c.album_id, c.nombre, c.duracion, c.URLarchivo_audio, c.precio,
        COUNT(m.usuario_id) AS cantidad_likes,
        g.nombre AS genero,
        a.nombre_artistico AS nombre_artista
    FROM Canciones c
    LEFT JOIN MeGusta_Cancion m ON c.cancion_id = m.cancion_id
    LEFT JOIN CancionGenero cg ON c.cancion_id = cg.cancion_id
    LEFT JOIN Genero g ON cg.genero_id = g.genero_id
    LEFT JOIN Artistas a ON c.album_id = a.usuario_id  -- Asumiendo que album_id se refiere al artista
    WHERE c.cancion_id = {cancion_id}
    GROUP BY c.cancion_id, c.album_id, c.nombre, c.duracion, c.URLarchivo_audio, c.precio, g.nombre, a.nombre_artistico
    """
    cancion_details_json = await fetch_query_as_json(query)
    cancion_details = json.loads(cancion_details_json)
    
    if cancion_details:
        return cancion_details[0]  # Retornar el primer resultado ya que cancion_id es único
    else:
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    
async def dar_me_gusta_cancion(usuario_id: int, cancion_id: int):
    conn = await get_db_connection()
    cursor = conn.cursor()
    fecha_megusta = datetime.now()
    
    try:
        query = """
        INSERT INTO MeGusta_Cancion (usuario_id, cancion_id, fecha_megusta)
        VALUES (?, ?, ?)
        """
        cursor.execute(query, (usuario_id, cancion_id, fecha_megusta))
        conn.commit()
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=400, detail="El usuario ya ha dado 'me gusta' a esta cancion")
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        cursor.close()
        conn.close()
        
async def quitar_me_gusta_cancion(usuario_id: int, cancion_id: int):
    conn = await get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
        DELETE FROM MeGusta_Cancion
        WHERE usuario_id = ? AND cancion_id = ?
        """
        cursor.execute(query, (usuario_id, cancion_id))
        conn.commit()
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        cursor.close()
        conn.close()
        
async def cantidad_me_gusta_cancion(cancion_id: int):
    query = f"SELECT COUNT(*) AS cantidad FROM MeGusta_Cancion WHERE cancion_id = {cancion_id}"
    cantidad_json = await fetch_query_as_json(query)
    cantidad = json.loads(cantidad_json)
    return cantidad[0] if cantidad else 0

async def comentarios_cancion(cancion_id: int):
    query = f"SELECT * FROM Comentarios WHERE cancion_id = {cancion_id}"
    comentarios_json = await fetch_query_as_json(query)
    comentarios = json.loads(comentarios_json)
    return comentarios

async def agregar_comentario_cancion(usuario_id: int, cancion_id: int, contenido: str):
    conn = await get_db_connection()
    cursor = conn.cursor()
    fecha_publicacion = datetime.now()
    
    try:
        query = """
        INSERT INTO Comentarios (usuario_id, cancion_id, contenido, fecha_publicacion)
        VALUES (?, ?, ?, ?)
        """
        cursor.execute(query, (usuario_id, cancion_id, contenido, fecha_publicacion))
        conn.commit()
        return {"status": "success", "message": "Comentario agregado exitosamente"}
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        cursor.close()
        conn.close()
        
        
async def manejar_accion(cancion_id: int, token: dict = Depends(verify_jwt_token)) -> Dict[str, str]:
    if not token:
        return {"redirect": "/login"}

    usuario_id = token["usuario_id"]

    conn = await get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar si el usuario ha comprado la canción
        query = """
        SELECT dp.detail_id
        FROM DetailPurchases dp
        JOIN Purchases p ON dp.purchase_id = p.purchase_id
        WHERE p.usuario_id = ? AND dp.cancion_id = ?
        """
        cursor.execute(query, (usuario_id, cancion_id))
        result = cursor.fetchone()

        if result:
            # Generar el enlace de descarga temporal
            enlace_descarga = await generar_enlace_descarga(cancion_id)
            return {"action": "download", "enlace": enlace_descarga["enlace"]}
        else:
            return {"redirect": "/"}
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        cursor.close()
        conn.close()

async def generos_canciones(cancion_id: int) -> List[Dict[str, str]]:
    conn = await get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT g.nombre
    FROM Genero g
    JOIN CancionGenero cg ON g.genero_id = cg.genero_id
    WHERE cg.cancion_id = ?
    """
    cursor.execute(query, (cancion_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    generos = [{"nombre": row[0]} for row in rows]
    return generos


async def comentarios_cancion(cancion_id: int) -> List[Dict[str, str]]:
    conn = await get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT c.contenido, u.nombre, c.fecha_publicacion
    FROM Comentarios c
    JOIN Usuarios u ON c.usuario_id = u.usuario_id
    WHERE c.cancion_id = ?
    """
    cursor.execute(query, (cancion_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    comentarios = [{"contenido": row[0], "nombre_usuario": row[1], "fecha_publicacion": row[2].strftime('%Y-%m-%d %H:%M:%S')} for row in rows]
    return comentarios

async def agregar_comentario_cancion(usuario_id: int, cancion_id: int, contenido: str, fecha_publicacion: datetime) -> Dict[str, str]:
    fecha_publicacion = datetime.now()

    try:
        conn = await get_db_connection()
        with conn.cursor() as cursor:
            query = """
            INSERT INTO Comentarios (usuario_id, cancion_id, contenido, fecha_publicacion)
            VALUES (?, ?, ?, ?)
            """
            cursor.execute(query, (usuario_id, cancion_id, contenido, fecha_publicacion))
            conn.commit()
        return {"status": "success", "message": "Comentario agregado exitosamente"}
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        conn.close()
        
        
async def generar_enlace_descarga(cancion_id: int) -> Dict[str, str]:
    try:
        # Obtener la URL del archivo de la base de datos
        conn = await get_db_connection()
        with conn.cursor() as cursor:
            query = "SELECT URLarchivo_audio FROM Canciones WHERE cancion_id = ?"
            cursor.execute(query, (cancion_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Canción no encontrada")
            blob_name = result.URLarchivo_audio
            
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise HTTPException(status_code=500, detail="Cadena de conexión no encontrada en las variables de entorno")

        # Configurar el cliente de Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "musiccontainer"

        # Obtener la clave de la cuenta desde la cadena de conexión
        account_key = connection_string.split("AccountKey=")[1].split(";")[0]

        # Generar el SAS token
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=10),  # Enlace válido por 10 minutos
            account_key=account_key  # Proporcionar la clave de la cuenta
        )

        # Generar la URL de descarga
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

        return {"status": "success", "enlace": blob_url}
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        conn.close()