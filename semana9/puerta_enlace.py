"""Valida al cliente y envia sus peticiones al catalogo interno."""

import os
import httpx

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="Puerta de Enlace Local")

esquema_bearer = HTTPBearer(auto_error=False)

URL_IDENTIDAD = os.getenv("URL_SERVICIO_IDENTIDAD", "http://127.0.0.1:8100")
DIRECCION_VAULT = os.getenv("DIRECCION_VAULT", "http://localhost:8200")
TOKEN_VAULT = os.getenv("TOKEN_VAULT")

if not TOKEN_VAULT:
    raise RuntimeError("TOKEN_VAULT no esta configurado")

URL_CATALOGO = "http://localhost:9000"


async def obtener_configuracion_secreta():
    url = f"{DIRECCION_VAULT}/v1/secret/data/gateway"
    cabeceras = {"X-Vault-Token": TOKEN_VAULT}
    async with httpx.AsyncClient(timeout=5.0) as cliente:
        respuesta = await cliente.get(url, headers=cabeceras)
    if respuesta.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo consultar Vault: {respuesta.status_code}"
        )
    return respuesta.json()["data"]["data"]


async def validar_token_cliente(
    credenciales: HTTPAuthorizationCredentials = Depends(esquema_bearer)
):
    if credenciales is None:
        raise HTTPException(status_code=401, detail="Se requiere token Bearer")

    secretos = await obtener_configuracion_secreta()
    clave_verificacion = secretos["clave_verificacion_identidad"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as cliente:
            respuesta = await cliente.post(
                f"{URL_IDENTIDAD}/verificar",
                json={"token": credenciales.credentials},
                headers={"X-Puerta-Auth-Clave": clave_verificacion}
            )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Servicio de Identidad no disponible")

    if respuesta.status_code != 200:
        raise HTTPException(status_code=502, detail="Fallo al consultar el Servicio de Identidad")

    identidad = respuesta.json()
    if not identidad.get("activo", False):
        raise HTTPException(status_code=401, detail="Token invalido o vencido")

    return {
        "id_usuario": identidad["id_usuario"],
        "nombre_usuario": identidad["nombre_usuario"],
        "roles": identidad["roles"],
        "clave_catalogo": secretos["clave_compartida_catalogo"]
    }


def construir_cabeceras(auth: dict, tipo_contenido: str | None) -> dict:
    cabeceras_internas = {
        "X-Puerta-Clave": auth["clave_catalogo"],
        "X-Id-Usuario": auth["id_usuario"],
        "X-Nombre-Usuario": auth["nombre_usuario"],
        "X-Roles-Usuario": ",".join(auth["roles"]),
    }
    if tipo_contenido:
        cabeceras_internas["content-type"] = tipo_contenido

    return cabeceras_internas


@app.api_route(
    "/api/{ruta:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def reenviar(
    ruta: str,
    peticion: Request,
    auth=Depends(validar_token_cliente)
):
    destino = f"{URL_CATALOGO}/{ruta}"
    cuerpo = await peticion.body()

    cabeceras_internas = construir_cabeceras(
        auth, peticion.headers.get("content-type")
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as cliente:
            respuesta_interna = await cliente.request(
                method=peticion.method,
                url=destino,
                params=peticion.query_params,
                content=cuerpo,
                headers=cabeceras_internas
            )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Catalogo no disponible")

    cabeceras_salida = {}
    if "content-type" in respuesta_interna.headers:
        cabeceras_salida["content-type"] = respuesta_interna.headers["content-type"]

    return Response(
        content=respuesta_interna.content,
        status_code=respuesta_interna.status_code,
        headers=cabeceras_salida
    )
