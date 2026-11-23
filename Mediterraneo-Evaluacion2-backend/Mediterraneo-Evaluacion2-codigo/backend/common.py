"""Utilidades de transporte, identidad y persistencia de cada servicio."""
import contextvars
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import ssl
import time
import uuid

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('RUNTIME_DIR', ROOT / '.runtime'))
SERVICE = os.environ.get('SERVICE', 'gateway')
PORTS = dict(secrets=8500, auth=8501, clients=8502, inventory=8503,
             orders=8504, payments=8505, graphql=8506, provider=8507, gateway=8443)
CORRELATION = contextvars.ContextVar('correlation', default='')
SSL = ssl.create_default_context(cafile=str(RUNTIME / 'cert.pem'))
CLIENT = httpx.AsyncClient(verify=SSL, timeout=8, trust_env=False)
BOOTSTRAP = (RUNTIME / f'{SERVICE}.token').read_text().strip()


def url(target):
    override = os.environ.get(target.upper() + '_URL')
    if override:
        return override
    host = target if os.getenv('CONTAINER_MODE') else '127.0.0.1'
    return f'https://{host}:{PORTS[target]}'


@contextmanager
def db():
    # Cada proceso utiliza exclusivamente su archivo; ninguna consulta cruza bases.
    directory = Path(os.getenv('DATA_DIR', RUNTIME / 'data'))
    directory.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(directory / f'{SERVICE}.sqlite', timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init(sql):
    with db() as c:
        c.executescript(sql)


def row(c, sql, params=()):
    r = c.execute(sql, params).fetchone()
    return dict(r) if r else None


def fail(code, message):
    raise HTTPException(code, message)


async def manager(path, payload=None):
    try:
        r = await CLIENT.request('POST' if payload is not None else 'GET',
                                 url('secrets') + path,
                                 headers={'X-Service-Key': BOOTSTRAP}, json=payload)
    except httpx.RequestError:
        fail(503, 'Administrador de secretos no disponible.')
    if r.status_code != 200:
        fail(503, 'No se pudo validar la identidad o la referencia de secreto.')
    return r.json()


async def secret(name):
    return (await manager('/v1/secrets/' + name))['value']


async def peer(request, allowed):
    key = request.headers.get('x-service-key', '')
    if not key:
        fail(403, 'Acceso privado: falta identidad de servicio.')
    identity = (await manager('/v1/identity', {'token': key}))['service']
    if identity not in allowed:
        fail(403, 'El servicio no tiene permiso para esta operación.')
    return identity


async def call(target, method, path, payload=None, token=None, headers=None):
    h = {'X-Service-Key': BOOTSTRAP, 'X-Correlation-ID': CORRELATION.get()}
    if token:
        h['Authorization'] = 'Bearer ' + token
    h.update(headers or {})
    try:
        r = await CLIENT.request(method, url(target) + path, json=payload, headers=h)
    except httpx.RequestError:
        fail(503, f'Dependencia {target} no disponible; vuelve a intentarlo.')
    if r.status_code >= 400:
        try:
            message = r.json().get('detail', 'Operación rechazada.')
        except ValueError:
            message = 'Dependencia devolvió un error.'
        fail(r.status_code if r.status_code < 500 else 503, message)
    return r.json()


def bearer(request):
    return request.headers.get('authorization', '').removeprefix('Bearer ')


async def user(request, roles=None, verified=True):
    token = bearer(request)
    if not token:
        fail(401, 'Inicia sesión para continuar.')
    try:
        claims = jwt.decode(token, await secret('jwt_public'), algorithms=['RS256'],
                            audience='mediterraneo', issuer='mediterraneo-auth',
                            options={'require': ['exp', 'iat', 'sub', 'jti', 'role']})
    except jwt.PyJWTError:
        fail(401, 'Sesión inválida o vencida.')
    if SERVICE == 'auth':
        with db() as c:
            valid = row(c, 'SELECT id,verified,role FROM users WHERE id=? AND active=1', (claims['sub'],))
            session = row(c, 'SELECT jti FROM sessions WHERE jti=? AND revoked=0', (claims['jti'],))
        if not valid or not session:
            fail(401, 'Sesión revocada.')
        claims['verified'] = bool(valid['verified'])
        claims['role'] = valid['role']
    else:
        claims = await call('auth', 'POST', '/internal/session', token=token)
    if verified and not claims.get('verified'):
        fail(403, 'Debes verificar tu correo antes de comprar.')
    if roles and claims['role'] not in roles:
        fail(403, 'Tu perfil no tiene permiso para esta operación.')
    return claims


def owner(resource, claims):
    if resource['client_id'] != claims['sub'] and claims['role'] not in ('admin', 'owner', 'cashier', 'dispatch'):
        fail(403, 'No tienes acceso a este pedido.')


def app_base(title):
    app = FastAPI(title=title, version='1.0.0', docs_url=None, redoc_url=None, openapi_url=None)
    limits = {}

    @app.middleware('http')
    async def controls(request, next_call):
        cid = request.headers.get('x-correlation-id', '')
        # No registrar rutas con IDs de clientes, cuerpos, cabeceras o errores de validación.
        if not cid or len(cid) > 64 or not all(x.isalnum() or x == '-' for x in cid):
            cid = str(uuid.uuid4())
        marker = CORRELATION.set(cid)
        try:
            if SERVICE == 'gateway' and request.url.path.startswith('/api/'):
                address = request.client.host
                now = time.monotonic()
                times = [t for t in limits.get(address, []) if now - t < 60]
                # Límite de demostración; la carga de prueba se mantiene bajo este umbral.
                if len(times) >= 600:
                    return JSONResponse({'detail': 'Demasiadas solicitudes. Intenta en un minuto.'}, status_code=429)
                limits[address] = times + [now]
            if len(await request.body()) > 65536:
                return JSONResponse({'detail': 'Solicitud demasiado grande.'}, status_code=413)
            response = await next_call(request)
            response.headers.update({'X-Correlation-ID': cid, 'X-Content-Type-Options': 'nosniff',
                                     'Referrer-Policy': 'same-origin', 'Cache-Control': 'no-store'})
            if SERVICE == 'gateway':
                response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
            logging.getLogger('mediterraneo').warning('service=%s correlation=%s method=%s status=%s', SERVICE, cid, request.method, response.status_code)
            return response
        finally:
            CORRELATION.reset(marker)

    @app.get('/health')
    async def health():
        return {'status': 'ok', 'service': SERVICE}

    return app
