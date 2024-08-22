import os
import json
import traceback
from dotenv import load_dotenv

from fastapi import HTTPException
import requests

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from models.UserRegister import UserRegister
from models.Userlogin import UserLogin
from utils.database import get_db_connection, fetch_query_as_json
from utils.security import create_jwt_token

cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)

async def register_user_firebase(user: UserRegister):
    try:
        user = UserRegister(
            email=user.email,
            password=user.password,
            nombre=user.nombre,
            username=user.username,
            user_type_id=1
        )

        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )
        
        conn = await get_db_connection()
        cursor = conn.cursor()
        
        # Insertar datos del usuario en la tabla Usuarios
        cursor.execute('''
            INSERT INTO Usuarios (nombre, nombre_usuario, correo_electronico, fecha_registro, tipo_usuario_id)
            VALUES (?, ?, ?, GETDATE(), ?)
        ''', user.nombre, user.username, user.email, user.user_type_id)
        
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "message": "User created successfully",
            "user": user_record.uid
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"User already exists: {e}"
        )
    
async def login_user_firebase(user: UserLogin):
    try:
        api_key = os.getenv("FIREBASE_API_KEY")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=payload)
        response_data = response.json()

        if "error" in response_data:
            raise HTTPException(
                status_code=400,
                detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )

        query_user = f"""
            SELECT usuario_id, nombre, nombre_usuario, correo_electronico, fecha_registro, tipo_usuario_id
            FROM Usuarios
            WHERE correo_electronico = '{user.email}'
        """

        try:
            result_json = await fetch_query_as_json(query_user)
            result_dict = json.loads(result_json)
            if not result_dict:
                raise HTTPException(
                    status_code=404,
                    detail="Usuario no encontrado"
                )
            user_data = result_dict[0]

            query_canciones = f"""
                SELECT cancion_id
                FROM MeGusta_Cancion
                WHERE usuario_id = {user_data['usuario_id']}
            """
            result_canciones_json = await fetch_query_as_json(query_canciones)
            canciones_megusta = [row['cancion_id'] for row in json.loads(result_canciones_json)]

            query_albumes = f"""
                SELECT album_id
                FROM MeGusta_Album
                WHERE usuario_id = {user_data['usuario_id']}
            """
            result_albumes_json = await fetch_query_as_json(query_albumes)
            albumes_megusta = [row['album_id'] for row in json.loads(result_albumes_json)]

            token_data = {
                "usuario_id": user_data["usuario_id"],
                "nombre": user_data["nombre"],
                "nombre_usuario": user_data["nombre_usuario"],
                "correo_electronico": user_data["correo_electronico"],
                "tipo_usuario_id": user_data["tipo_usuario_id"]
            }
            return {
                "message": "Usuario autenticado exitosamente",
                "access_token": create_jwt_token(token_data),
                "token_type": "bearer",
                "usuario_id": user_data["usuario_id"],
                "canciones_megusta": canciones_megusta,
                "albumes_megusta": albumes_megusta
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        error_detail = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(
            status_code=400,
            detail=f"Error al autenticar usuario: {error_detail}"
        )

