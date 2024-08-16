import os
from dotenv import load_dotenv

from fastapi import HTTPException

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import requests

from models.Userlogin import UserRegister


load_dotenv()

cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)

async def register_user_firebase(user: UserRegister):
    try:
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )
        return {
            "message": "User created successfully"
            , "user": user_record.uid
        }
    except Exception as e:
        raise HTTPException(
            status_code=400
            , detail="User already exists: {e}"
        )
    
async def login_user_firebase(user: UserRegister):
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
                status_code=400
                , detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )
        
        id_token = response_data["idToken"]
        return {
            "message": "User authenticated successfully"
            , "id_token": id_token
        }
    except Exception as e:
        raise HTTPException(
            status_code=400
            , detail=f"Error al autenticar usuario: {e}"
        )