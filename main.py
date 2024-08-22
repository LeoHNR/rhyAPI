from fastapi import FastAPI, Request, Response, Depends, HTTPException

from models.UserRegister import UserRegister
from models.Userlogin import UserLogin
from models.Postcomentario import Comentario

from controllers.o365 import login_o365 , auth_callback_o365
from controllers.firebase import register_user_firebase, login_user_firebase
from controllers.card import fetch_cards
from controllers.album import fetch_album_details, dar_me_gusta_album, cantidad_me_gusta_album, obtener_nombre_artista, canciones_album_con_info, quitar_me_gusta_album, albumes_home
from controllers.cancion import fetch_cancion_details, dar_me_gusta_cancion,  comentarios_cancion, agregar_comentario_cancion, manejar_accion, quitar_me_gusta_cancion

from fastapi.middleware.cors import CORSMiddleware
from utils.security import verify_jwt_token
from datetime import datetime





app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los encabezados
)


@app.get("/")
async def hello():
    return {
        "Hello": "World"
        , "version": "0.1.15"
    }

@app.get("/cards")
async def cards(response: Response):
    return await fetch_cards()

@app.get("/login")
async def login():
    return await login_o365()

@app.get("/auth/callback")
async def authcallback(request: Request):
    return await auth_callback_o365(request)

@app.post("/register")
async def register(user: UserRegister):
    return await register_user_firebase(user)

@app.post("/login/custom")
async def login_custom(user: UserLogin):
    user_data = await login_user_firebase(user)
    if user_data:
        return {
            "access_token": user_data["access_token"],
            "token_type": "bearer",
            "user": user_data
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid email or password")






@app.get("/albumes/{album_id}")
async def albumes(album_id: int):
    album_details = await fetch_album_details(album_id)
    return album_details

@app.get("/canciones/{cancion_id}")
async def get_cancion(cancion_id: int):
    cancion_details = await fetch_cancion_details(cancion_id)
    return cancion_details




@app.post("/albumes/{album_id}/me_gusta")
async def me_gusta_album(album_id: int, token: dict = Depends(verify_jwt_token)):
    usuario_id = token["usuario_id"]
    await dar_me_gusta_album(usuario_id, album_id)
    return {"status": "success", "message": "Me gusta registrado exitosamente"}

@app.post("/albumes/{album_id}/no_me_gusta")
async def no_me_gusta_album(album_id: int, token: dict = Depends(verify_jwt_token)):
    usuario_id = token["usuario_id"]
    await quitar_me_gusta_album(usuario_id, album_id)
    return {"status": "success", "message": "No me gusta registrado exitosamente"}

@app.get("/albumes/{album_id}/me_gusta")
async def cantidad_me_gusta(album_id: int):
    cantidad = await cantidad_me_gusta_album(album_id)
    return {"cantidad": cantidad}


@app.post("/canciones/{cancion_id}/me_gusta")
async def me_gusta_cancion(cancion_id: int, token: dict = Depends(verify_jwt_token)):
    usuario_id = token["usuario_id"]
    await dar_me_gusta_cancion(usuario_id, cancion_id)
    return {"status": "success", "message": "Me gusta registrado exitosamente"}

@app.post("/canciones/{cancion_id}/no_me_gusta")
async def no_me_gusta_cancion(cancion_id: int, token: dict = Depends(verify_jwt_token)):
    usuario_id = token["usuario_id"]
    await quitar_me_gusta_cancion(usuario_id, cancion_id)
    return {"status": "success", "message": "No me gusta registrado exitosamente"}


@app.get("/canciones/{cancion_id}/comentarios")
async def comentarios(cancion_id: int):
    comentarios = await comentarios_cancion(cancion_id)
    return comentarios

@app.post("/canciones/{cancion_id}/comentarios")
async def post_comentario(cancion_id: int, comentario: Comentario, token: dict = Depends(verify_jwt_token)):
    fecha_publicacion = datetime.now()
    return await agregar_comentario_cancion(comentario.usuario_id, cancion_id, comentario.contenido, fecha_publicacion)

@app.get("/canciones/{cancion_id}/accion")
async def accion_cancion(cancion_id: int, token: dict = Depends(verify_jwt_token)):
    return await manejar_accion(cancion_id, token)





@app.get("/albumes/{album_id}/canciones_info")
async def obtener_canciones_album_con_info(album_id: int):
    canciones = await canciones_album_con_info(album_id)
    return canciones


@app.get("/albumes")
async def obtener_albumes_disponibles():
    return await albumes_home()





@app.get("/me")
async def get_me(token: dict = Depends(verify_jwt_token)):
    usuario_info = {
        "usuario_id": token["usuario_id"],
        "nombre": token["nombre"],
        "nombre_usuario": token["nombre_usuario"],
        "correo_electronico": token["correo_electronico"],
        "tipo_usuario_id": token["tipo_usuario_id"]
    }
    return usuario_info

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)