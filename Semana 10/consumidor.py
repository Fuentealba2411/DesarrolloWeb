"""Escucha pedidos y confirma o rechaza cada mensaje individualmente."""
import argparse
import json
import time
import xml.etree.ElementTree as ET

import stomp

DESTINO = "/queue/pedidos"


def interpretar(cuerpo, headers):
    formato = headers.get("x-formato", "").lower()
    mime = headers.get("content-type", "").lower()
    if not formato:
        if "application/json" in mime:
            formato = "json"
        elif "application/xml" in mime or "text/xml" in mime:
            formato = "xml"
        else:
            formato = "texto"
    if formato == "texto":
        return formato, cuerpo
    if formato == "fijo":
        if len(cuerpo) != 36:
            raise ValueError("El formato fijo debe tener exactamente 36 caracteres.")
        identificador = cuerpo[:6]
        cliente = cuerpo[6:26].strip()
        monto = cuerpo[26:36]
        if not identificador.isascii() or not identificador.isdigit():
            raise ValueError("ID fijo inválido.")
        if not cliente or not all(c.isalnum() or c == " " for c in cliente):
            raise ValueError("Cliente fijo inválido.")
        if not (monto[:7].isascii() and monto[:7].isdigit() and monto[7] == "."
                and monto[8:].isascii() and monto[8:].isdigit() and float(monto) > 0):
            raise ValueError("Monto fijo inválido.")
        return formato, {"id": identificador, "cliente": cliente, "monto": monto}
    if formato == "json":
        return formato, json.loads(cuerpo)
    if formato == "xml":
        raiz = ET.fromstring(cuerpo)
        if raiz.tag != "pedido":
            raise ValueError("El nodo raíz debe ser pedido.")
        return formato, {elemento.tag: elemento.text for elemento in raiz}
    raise ValueError(f"Formato no soportado: {formato}")


class Escuchador(stomp.ConnectionListener):
    def __init__(self, conexion):
        self.conexion = conexion

    def on_error(self, frame):
        print(f"Error del broker: {frame.body}", flush=True)

    def on_disconnected(self):
        print("Conexión STOMP cerrada.", flush=True)

    def on_message(self, frame):
        ack_id = frame.headers.get("ack")
        if not ack_id:
            print("El mensaje no incluye el identificador ACK de STOMP 1.2.", flush=True)
            return
        try:
            formato, contenido = interpretar(frame.body, frame.headers)
        except (ValueError, ET.ParseError) as error:
            print(f"Mensaje inválido: {error}", flush=True)
            self.conexion.nack(id=ack_id)
            return
        print(f"\nRecibido, formato {formato}:", flush=True)
        if isinstance(contenido, str):
            print(contenido, flush=True)
        else:
            print(json.dumps(contenido, ensure_ascii=False, indent=2), flush=True)
        self.conexion.ack(id=ack_id)


def main():
    parser = argparse.ArgumentParser(description="Consumidor STOMP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    parser.add_argument("--usuario", default="demo")
    parser.add_argument("--clave", default="demo123")
    args = parser.parse_args()
    conexion = stomp.Connection12([(args.host, args.port)])
    conexion.set_listener("pedidos", Escuchador(conexion))
    try:
        conexion.connect(args.usuario, args.clave, wait=True)
        conexion.subscribe(destination=DESTINO, id="lector-pedidos",
                           ack="client-individual", headers={"activemq.prefetchSize": "1"})
        print(f"Escuchando {DESTINO}. Presiona Ctrl+C para salir.", flush=True)
        while conexion.is_connected():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nDeteniendo consumidor...")
    except Exception as error:
        parser.exit(1, f"Error de conexión: {error}\n")
    finally:
        if conexion.is_connected():
            conexion.disconnect()


if __name__ == "__main__":
    main()
