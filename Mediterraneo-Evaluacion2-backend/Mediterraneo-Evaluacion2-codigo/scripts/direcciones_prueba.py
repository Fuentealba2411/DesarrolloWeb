"""Proveedor HTTP de geocodificación controlado, exclusivo de las pruebas."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse


class AddressHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        address = parse_qs(urlparse(self.path).query).get('q', [''])[0]
        status = 200
        features = []
        if address.startswith('Servicio no disponible'):
            status = 503
        elif address.startswith('Calle cercana') or address.startswith('Direccion lejana'):
            coordinates = [-71, -34] if address.startswith('Direccion lejana') else [-70.6506, -33.4372]
            features = [{'geometry': {'coordinates': coordinates},
                         'properties': {'countrycode': 'CL', 'street': address.split(' 123')[0], 'housenumber': '123'}}]
        body = json.dumps({'features': features}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_geocoder():
    server = ThreadingHTTPServer(('127.0.0.1', 0), AddressHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
