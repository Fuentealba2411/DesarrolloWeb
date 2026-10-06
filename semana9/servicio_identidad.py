"""Gestiona el inicio, la verificacion y el cierre de sesiones."""

from datetime import datetime, timedelta, timezone
import os
import secrets

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI(
    title="Servicio de Identidad",
    description="Servicio sencillo para iniciar y cerrar sesion"
)

USUARIOS = {
    "lucia": {
        "clave": "1234",
        "id_usuario": "USR-001",
        "roles": ["user"]
    },
    "mateo": {
        "clave": "5678",
        "id_usuario": "USR-002",
        "roles": ["user"]
    },
    "sofia": {
        "clave": "admin123",
        "id_usuario": "USR-003",
        "roles": ["user", "admin"]
    }
}

SESIONES = {}

MINUTOS_DE_VIDA_TOKEN = 15

CLAVE_VERIFICACION = os.getenv(
    "CLAVE_VERIFICACION_IDENTIDAD",
    "clave-demo-verificacion"
)


class PeticionLogin(BaseModel):
    usuario: str
    clave: str


class PeticionToken(BaseModel):
    token: str


def exigir_puerta(clave_recibida: str):
    if not secrets.compare_digest(clave_recibida, CLAVE_VERIFICACION):
        raise HTTPException(status_code=403, detail="Puerta de enlace no autorizada")


def crear_sesion(nombre_usuario: str, registro: dict) -> str:
    token = secrets.token_urlsafe(32)
    vence = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_DE_VIDA_TOKEN)

    # Guardar la identidad y la fecha de vencimiento de la sesion
    SESIONES[token] = {
        "id_usuario": registro["id_usuario"],
        "nombre_usuario": nombre_usuario,
        "roles": registro["roles"],
        "vence": vence
    }
    return token


@app.post("/login")
def login(peticion: PeticionLogin, x_puerta_auth_clave: str = Header(default="")):
    exigir_puerta(x_puerta_auth_clave)

    registro = USUARIOS.get(peticion.usuario)
    if registro is None:
        raise HTTPException(status_code=401, detail="Usuario inexistente")
    if registro["clave"] != peticion.clave:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    token = crear_sesion(peticion.usuario, registro)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": MINUTOS_DE_VIDA_TOKEN * 60
    }


@app.post("/verificar")
def verificar(peticion: PeticionToken, x_puerta_auth_clave: str = Header(default="")):
    exigir_puerta(x_puerta_auth_clave)

    sesion = SESIONES.get(peticion.token)
    if sesion is None:
        return {"activo": False}
    if datetime.now(timezone.utc) > sesion["vence"]:
        SESIONES.pop(peticion.token, None)
        return {"activo": False}
    return {
        "activo": True,
        "id_usuario": sesion["id_usuario"],
        "nombre_usuario": sesion["nombre_usuario"],
        "roles": sesion["roles"],
        "vence": sesion["vence"].isoformat()
    }


@app.post("/logout")
def logout(peticion: PeticionToken, x_puerta_auth_clave: str = Header(default="")):
    exigir_puerta(x_puerta_auth_clave)
    SESIONES.pop(peticion.token, None)
    return {"mensaje": "Sesion cerrada"}


@app.get("/estado")
def estado(x_puerta_auth_clave: str = Header(default="")):
    exigir_puerta(x_puerta_auth_clave)
    return {"estado": "OK", "servicio": "Servicio de Identidad"}
