import os
import secrets
import hashlib
import base64
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException,Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv


load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def generate_pkce_verifier():
    return secrets.token_urlsafe(32)

def generate_pkce_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')

def create_jwt_token(data: dict, expires_in: int = 60):
    expire = datetime.utcnow() + timedelta(minutes=expires_in)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")