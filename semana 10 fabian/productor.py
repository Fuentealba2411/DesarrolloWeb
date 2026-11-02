"""Envía un mensaje a ActiveMQ mediante STOMP 1.2."""
import argparse
import json
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET

import stomp

DESTINO = "/queue/pedidos"


def construir_mensaje(formato, pedido, texto):
    if formato == "texto":
        return texto, "text/plain; charset=utf-8"
    if formato == "fijo":
        identificador = str(pedido["id"])
        cliente = pedido["cliente"]
        monto = Decimal(pedido["monto"])
        if not identificador.isascii() or not identificador.isdigit() or len(identificador) > 6:
            raise ValueError("El ID debe tener entre 1 y 6 dígitos.")
        if not cliente.strip() or len(cliente) > 20:
            raise ValueError("El cliente debe tener entre 1 y 20 caracteres.")
        if not all(c.isalnum() or c == " " for c in cliente):
            raise ValueError("El cliente solo admite letras, números y espacios en formato fijo.")
        if not monto.is_finite() or monto <= 0 or monto >= Decimal("10000000"):
            raise ValueError("El monto fijo debe ser positivo y caber en 10 caracteres.")
        campo_monto = f"{monto:010.2f}"
        if len(campo_monto) != 10:
            raise ValueError("El monto redondeado supera los 10 caracteres.")
        return identificador.zfill(6) + cliente.ljust(20) + campo_monto, "text/plain; charset=utf-8"
    if formato == "json":
        return json.dumps(pedido, ensure_ascii=False), "application/json"
    if formato == "xml":
        raiz = ET.Element("pedido")
        for nombre, valor in pedido.items():
            ET.SubElement(raiz, nombre).text = str(valor)
        return ET.tostring(raiz, encoding="unicode"), "application/xml"
    raise ValueError("Formato no soportado.")


def main():
    parser = argparse.ArgumentParser(description="Productor STOMP")
    parser.add_argument("--formato", choices=["texto", "fijo", "json", "xml"], required=True)
    parser.add_argument("--mensaje", default="Hola desde el productor STOMP")
    parser.add_argument("--id", default="123")
    parser.add_argument("--cliente", default="Ernesto Banco")
    parser.add_argument("--monto", default="123.45")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    parser.add_argument("--usuario", default="demo")
    parser.add_argument("--clave", default="demo123")
    args = parser.parse_args()
    try:
        monto = Decimal(args.monto)
        if not monto.is_finite():
            raise ValueError("El monto debe ser un número finito.")
        pedido = {"id": args.id, "cliente": args.cliente, "monto": str(monto)}
        cuerpo, mime = construir_mensaje(args.formato, pedido, args.mensaje)
    except (ValueError, InvalidOperation) as error:
        parser.error(f"Datos inválidos: {error}")

    conexion = stomp.Connection12([(args.host, args.port)], timeout=10)
    try:
        conexion.connect(args.usuario, args.clave, wait=True)
        conexion.send(destination=DESTINO, body=cuerpo, headers={
            "content-type": mime, "x-formato": args.formato, "persistent": "true"
        })
        print(f"Mensaje enviado a {DESTINO}, formato {args.formato}:")
        print(cuerpo)
    except Exception as error:
        parser.exit(1, f"No se pudo enviar el mensaje: {error}\n")
    finally:
        if conexion.is_connected():
            conexion.disconnect()


if __name__ == "__main__":
    main()
