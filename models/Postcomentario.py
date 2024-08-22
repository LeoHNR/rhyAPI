from pydantic import BaseModel

class Comentario(BaseModel):
    usuario_id: int
    contenido: str