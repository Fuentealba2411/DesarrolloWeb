"""Gestor de secretos local para la entrega: ACL por identidad y referencias."""
import hmac
import json
from fastapi import Request
from backend.common import RUNTIME, app_base, fail

CONFIG = json.loads((RUNTIME / 'secrets.json').read_text())
app = app_base('Administrador privado de secretos')


def identify(token):
    for name, value in CONFIG['tokens'].items():
        if hmac.compare_digest(token, value):
            return name
    fail(403, 'Identidad no autorizada.')


@app.get('/v1/secrets/{name}')
async def get_secret(name: str, request: Request):
    caller = identify(request.headers.get('x-service-key', ''))
    if name not in CONFIG['acl'].get(caller, []):
        fail(403, 'Referencia fuera del alcance de la identidad.')
    return {'value': CONFIG['values'][name]}


@app.post('/v1/identity')
async def identity(request: Request):
    identify(request.headers.get('x-service-key', ''))
    payload = await request.json()
    return {'service': identify(str(payload.get('token', '')))}
