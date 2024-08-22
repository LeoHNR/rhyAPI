import json
from utils.database import fetch_query_as_json, get_db_connection
from fastapi import HTTPException
from datetime import datetime
from typing import List, Dict
import pyodbc

async def fetch_album_details(album_id: int):
    query = f"""
        SELECT a.*, ar.nombre_artistico
        FROM Albumes a
        JOIN Artistas ar ON a.artista_id = ar.artista_id
        WHERE a.album_id = {album_id}
    """
    album_details_json = await fetch_query_as_json(query)
    album_details = json.loads(album_details_json)
    
    if album_details:
        return album_details[0]  # Retornar el primer resultado ya que album_id es único
    else:
        raise HTTPException(status_code=404, detail="Album not found")
    
async def albumes_home():
    query = """
        SELECT album_id,nombre, fecha_lanzamiento
        FROM Albumes
    """
    try:
        albumes_json = await fetch_query_as_json(query)
        albumes = json.loads(albumes_json)
        return albumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
async def dar_me_gusta_album(usuario_id: int, album_id: int):
    conn = await get_db_connection()
    cursor = conn.cursor()
    fecha_megusta = datetime.now()
    
    try:
        query = """
        INSERT INTO MeGusta_Album (usuario_id, album_id, fecha_megusta)
        VALUES (?, ?, ?)
        """
        cursor.execute(query, (usuario_id, album_id, fecha_megusta))
        conn.commit()
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=400, detail="El usuario ya ha dado 'me gusta' a este álbum")
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        cursor.close()
        conn.close()
        
async def quitar_me_gusta_album(usuario_id: int, album_id: int):
    conn = await get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
        DELETE FROM MeGusta_Album
        WHERE usuario_id = ? AND album_id = ?
        """
        cursor.execute(query, (usuario_id, album_id))
        conn.commit()
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    finally:
        cursor.close()
        conn.close()

        
async def cantidad_me_gusta_album(album_id: int):
    query = f"SELECT COUNT(*) AS cantidad FROM MeGusta_Album WHERE album_id = {album_id}"
    cantidad_json = await fetch_query_as_json(query)
    cantidad = json.loads(cantidad_json)
    return cantidad[0] if cantidad else 0

async def canciones_album(album_id: int) -> List[Dict[str, str]]:
    conn = await get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT cancion_id, nombre
    FROM Canciones
    WHERE album_id = ?
    """
    cursor.execute(query, (album_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    canciones = [{"cancion_id": row[0], "nombre": row[1]} for row in rows]
    return canciones

async def obtener_nombre_artista(artista_id: int) -> str:
    conn = await get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT nombre_artistico
    FROM Artistas
    WHERE artista_id = ?
    """
    cursor.execute(query, (artista_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row:
        return row[0]
    else:
        raise HTTPException(status_code=404, detail="Artista no encontrado")
    
    

async def canciones_album_con_info(album_id: int) -> List[Dict[str, str]]:
    conn = await get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT 
        c.cancion_id,
        c.nombre AS nombre_cancion,
        g.nombre AS genero,
        c.duracion,
        COUNT(mg.usuario_id) AS cantidad_megusta
    FROM 
        Canciones c
    LEFT JOIN 
        CancionGenero cg ON c.cancion_id = cg.cancion_id
    LEFT JOIN 
        Genero g ON cg.genero_id = g.genero_id
    LEFT JOIN 
        MeGusta_Cancion mg ON c.cancion_id = mg.cancion_id
    WHERE 
        c.album_id = ?
    GROUP BY 
        c.cancion_id, c.nombre, g.nombre, c.duracion
    """
    cursor.execute(query, (album_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    canciones = [
        {
            "cancion_id": row[0],
            "nombre_cancion": row[1],
            "genero": row[2],
            "duracion": row[3],
            "cantidad_megusta": row[4]
        }
        for row in rows
    ]
    return canciones