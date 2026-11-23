import os
import secrets

from fastapi import (
    FastAPI,  # Levanta el servicio de API
    Header,  # Recibe el token
    HTTPException,  # Problemas de conexion
    Depends,  # Cada vez que se llame al backend se tiene que validar el token
)

app = FastAPI(
    title="Backend API juegos",
    description="API ubicada en localhost enrutada por API Gateway",
)

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET")

if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError("INTERNAL_GATEWAY_SECRET NO ESTA CONFIGURADO")




def verify_gateway(x_gateway_secret: str = Header(default="")):
    valid = secrets.compare_digest(
        x_gateway_secret.encode("utf-8"),
        INTERNAL_GATEWAY_SECRET.encode("utf-8"),
    )
    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Solicitud no autorizada desde gateway",
        )


@app.get("/health", dependencies=[Depends(verify_gateway)])
def health():
    return {
        "status": "OK",
        "service": "Backend API Juegos",
    }


@app.get("/productos", dependencies=[Depends(verify_gateway)])
def productos():
    return {
        "products": [
            {
                "id": 1,
                "nombre": "Minecraft",
                "desarrollador": "Mojang Studios",
                "editor": "Xbox Game Studios",
                "fecha": "18-11-2011",
                "precio": 24990,
            },
            {
                "id": 2,
                "nombre": "Geometry Dash",
                "desarrollador": "RobTop Games",
                "editor": "RobTop Games",
                "fecha": "22-08-2013",
                "precio": 3990,
            },
            {
                "id": 3,
                "nombre": "osu!",
                "desarrollador": "ppy Pty Ltd",
                "editor": "ppy Pty Ltd",
                "fecha": "16-09-2007",
                "precio": 0,
            },
            {
                "id": 4,
                "nombre": "Fortnite",
                "desarrollador": "Epic Games",
                "editor": "Epic Games",
                "fecha": "25-07-2017",
                "precio": 0,
            },
            {
                "id": 5,
                "nombre": "PUBG: Battlegrounds",
                "desarrollador": "PUBG Studio",
                "editor": "KRAFTON",
                "fecha": "21-12-2017",
                "precio": 0,
            },
            {
                "id": 6,
                "nombre": "Call of Duty: Black Ops III",
                "desarrollador": "Treyarch",
                "editor": "Activision",
                "fecha": "06-11-2015",
                "precio": 29990,
            },
            {
                "id": 7,
                "nombre": "Grand Theft Auto V",
                "desarrollador": "Rockstar North",
                "editor": "Rockstar Games",
                "fecha": "17-09-2013",
                "precio": 19990,
            },
            {
                "id": 8,
                "nombre": "Doki Doki Literature Club!",
                "desarrollador": "Team Salvato",
                "editor": "Team Salvato",
                "fecha": "22-09-2017",
                "precio": 0,
            },
        ]
    }



@app.get("/pedidos", dependencies=[Depends(verify_gateway)])
def pedidos():
    return {
        "pedidos": [
            {"id": 1001, "status": "paid"},
            {"id": 1002, "status": "pending"},
        ]
    }
