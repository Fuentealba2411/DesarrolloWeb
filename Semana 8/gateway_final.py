"""API Gateway del proyecto Fortnite.

Valida al cliente con un token almacenado en Vault y reenvía la solicitud al
backend, que solo acepta llamadas con el secreto compartido del gateway.
"""

import os
import secrets

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


app = FastAPI(
    title="Fortnite Gateway",
    description="Punto de entrada protegido para la API del proyecto Fortnite",
)
bearer = HTTPBearer(auto_error=False)

VAULT_URL = os.getenv("VAULT_ADDR", "http://localhost:8200").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:9000").rstrip("/")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

if not VAULT_TOKEN:
    raise RuntimeError("Configura VAULT_TOKEN antes de iniciar el gateway")


async def read_credentials_from_vault() -> dict:
    """Obtiene los dos secretos necesarios para validar y reenviar solicitudes."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await client.get(
                f"{VAULT_URL}/v1/secret/data/gateway",
                headers={"X-Vault-Token": VAULT_TOKEN},
            )
            result.raise_for_status()
            values = result.json()["data"]["data"]
            return {
                "client_token": values["client_token"],
                "backend_secret": values["backend_shared_secret"],
            }
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail="No se pudieron obtener las credenciales de Vault"
        ) from exc


async def authorize_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Se requiere un token Bearer")

    stored = await read_credentials_from_vault()
    if not secrets.compare_digest(credentials.credentials, stored["client_token"]):
        raise HTTPException(status_code=401, detail="Token de cliente inválido")

    return stored["backend_secret"]


@app.get("/gateway/health")
def gateway_health():
    """Permite comprobar que el gateway está levantado, sin consultar Vault."""
    return {"status": "OK", "service": "Fortnite Gateway"}


@app.api_route(
    "/api/{resource:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def forward_request(
    resource: str,
    request: Request,
    backend_secret: str = Depends(authorize_client),
):
    """Conserva método, parámetros, cuerpo, estado y tipo de contenido."""
    outgoing_headers = {
        "X-Gateway-Secret": backend_secret,
        "X-Authenticated-Client": "fortnite-client",
    }
    content_type = request.headers.get("content-type")
    if content_type:
        outgoing_headers["Content-Type"] = content_type

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            backend_response = await client.request(
                method=request.method,
                url=f"{BACKEND_URL}/{resource}",
                params=request.query_params,
                content=await request.body(),
                headers=outgoing_headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Backend no disponible") from exc

    response_headers = {}
    if "content-type" in backend_response.headers:
        response_headers["content-type"] = backend_response.headers["content-type"]

    return Response(
        content=backend_response.content,
        status_code=backend_response.status_code,
        headers=response_headers,
    )
