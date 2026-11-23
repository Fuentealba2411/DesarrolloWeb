from fastapi import FastAPI

# Desde esta carpeta: python -m uvicorn backend_api:app --port 9000
app = FastAPI(
    title="Backend API Nikkei Roll",
    description="Productos y pedidos de ejemplo para consultar desde el API Gateway"
)


@app.get("/health")
def health():
    return {"status": "OK", "service": "Backend API Nikkei Roll"}


# Datos y precios ficticios en CLP. No se utiliza base de datos en este avance.
@app.get("/productos")
def productos():
    return {
        "productos": [
            {
                "id": 1,
                "nombre": "Roll acevichado",
                "descripcion": "Roll de camaron y palta con salsa acevichada, 10 piezas",
                "categoria": "Rolls",
                "precio": 7990
            },
            {
                "id": 2,
                "nombre": "Tabla Nikkei",
                "descripcion": "Seleccion de 30 piezas para compartir",
                "categoria": "Tablas y combos",
                "precio": 19990
            },
            {
                "id": 3,
                "nombre": "Gyozas de pollo",
                "descripcion": "Cinco empanaditas rellenas de pollo",
                "categoria": "Entradas",
                "precio": 4990
            },
            {
                "id": 4,
                "nombre": "Limonada",
                "descripcion": "Limonada de 500 ml",
                "categoria": "Bebidas",
                "precio": 2490
            }
        ]
    }


# Solo se consultan estados de ejemplo; no se procesan pagos ni pedidos reales.
@app.get("/pedidos")
def pedidos():
    return {
        "pedidos": [
            {"id": 1001, "estado": "pagado"},
            {"id": 1002, "estado": "pendiente"}
        ]
    }
