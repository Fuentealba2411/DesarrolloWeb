import os
import secrets

from fastapi import FastAPI, Header, HTTPException, Depends

app = FastAPI(
    title="Servicio de Catalogo",
    description="Servicio interno al que solo se accede a traves de la puerta de enlace"
)

CLAVE_INTERNA = os.getenv("CLAVE_INTERNA_PUERTA")

if not CLAVE_INTERNA:
    raise RuntimeError("CLAVE_INTERNA_PUERTA no esta configurada")


def validar_puerta(x_puerta_clave: str = Header(default="")):
    es_valida = secrets.compare_digest(x_puerta_clave, CLAVE_INTERNA)
    if not es_valida:
        raise HTTPException(
            status_code=403,
            detail="Peticion rechazada: no proviene de la puerta de enlace"
        )


def armar_identidad(id_usuario, nombre_usuario, roles):
    return {
        "id_usuario": id_usuario,
        "nombre_usuario": nombre_usuario,
        "roles": roles
    }


@app.get("/estado", dependencies=[Depends(validar_puerta)])
def estado():
    return {"estado": "OK", "servicio": "Servicio de Catalogo"}


@app.get("/articulos", dependencies=[Depends(validar_puerta)])
def articulos(
    x_id_usuario: str | None = Header(default=None),
    x_nombre_usuario: str | None = Header(default=None),
    x_roles_usuario: str | None = Header(default=None),
):
    return {
        "identidad": armar_identidad(x_id_usuario, x_nombre_usuario, x_roles_usuario),
        "articulos": [
            {"id": 1, "nombre": "Portatil", "precio": 900000},
            {"id": 2, "nombre": "Pantalla", "precio": 250000},
        ]
    }


@app.get("/pedidos", dependencies=[Depends(validar_puerta)])
def pedidos(
    x_id_usuario: str | None = Header(default=None),
    x_nombre_usuario: str | None = Header(default=None),
    x_roles_usuario: str | None = Header(default=None),
):
    return {
        "identidad": armar_identidad(x_id_usuario, x_nombre_usuario, x_roles_usuario),
        "pedidos": [
            {"id": 1001, "situacion": "pagado"},
            {"id": 1002, "situacion": "pendiente"}
        ]
    }
