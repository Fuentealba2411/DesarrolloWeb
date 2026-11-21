from fastapi import FastAPI
import httpx

# Desde esta carpeta: python -m uvicorn gateway_api:app --port 8000
app = FastAPI(title="API Gateway Nikkei Roll")

BACKEND_URL = "http://127.0.0.1:9000"


# El Gateway obtiene los datos del backend; no almacena productos ni pedidos.
@app.get("/api/productos")
async def productos():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/productos")
    return response.json()


@app.get("/api/pedidos")
async def pedidos():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/pedidos")
    return response.json()
