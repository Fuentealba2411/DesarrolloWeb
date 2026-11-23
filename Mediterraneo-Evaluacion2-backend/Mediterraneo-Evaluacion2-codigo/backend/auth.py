"""Registro, hash Argon2, verificación de correo y sesiones JWT revocables."""
from datetime import date
import hashlib
import json
import re
import secrets
import time
import uuid
import sqlite3

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
import jwt
from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field
from backend.common import app_base, init, db, row, fail, peer, call, secret, user

app = app_base('Autenticación')
init('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE,hash TEXT,
role TEXT,verified INTEGER DEFAULT 0,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS sessions(jti TEXT PRIMARY KEY,user_id TEXT,expires INTEGER,revoked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS verification(token_hash TEXT PRIMARY KEY,user_id TEXT,expires INTEGER,used INTEGER DEFAULT 0);
''')
HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    correo: str = Field(min_length=5, max_length=254)
    clave: str = Field(min_length=10, max_length=128)


class Register(Login):
    nombre: str = Field(min_length=2, max_length=100)
    run: str = Field(min_length=3, max_length=12)
    direccion: str = Field(min_length=5, max_length=200)
    comuna: str = Field(min_length=2, max_length=80)
    provincia: str = Field(min_length=2, max_length=80)
    region: str = Field(min_length=2, max_length=80)
    nacimiento: date
    sexo: str = Field(pattern='^(F|M|Otro|No informar)$')
    telefono: str = Field(pattern=r'^\+?[0-9 ]{8,16}$')


def validate_email(value):
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        fail(422, 'Correo inválido.')


def validate_run(value):
    value = value.replace('.', '').replace('-', '').upper()
    if len(value) < 2 or not value[:-1].isdigit():
        fail(422, 'RUN inválido.')
    total = sum(int(n) * (i % 6 + 2) for i, n in enumerate(reversed(value[:-1])))
    digit = 11 - total % 11
    expected = '0' if digit == 11 else 'K' if digit == 10 else str(digit)
    if value[-1] != expected:
        fail(422, 'Dígito verificador del RUN inválido.')


async def send_verification(uid, email):
    token = secrets.token_urlsafe(32)
    with db() as c:
        c.execute('DELETE FROM verification WHERE user_id=?', (uid,))
        c.execute('INSERT INTO verification VALUES(?,?,?,0)',
                  (hashlib.sha256(token.encode()).hexdigest(), uid, int(time.time()) + 1800))
    await call('provider', 'POST', '/internal/mail', {
        'recipient': email, 'subject': 'Verifica tu correo',
        'body': f'Código de verificación de Mediterráneo (30 minutos): {token}'})


@app.post('/register', status_code=201)
async def register(data: Register, request: Request):
    await peer(request, ['gateway'])
    validate_email(data.correo)
    validate_run(data.run)
    if data.nacimiento > date.today():
        fail(422, 'La fecha de nacimiento no puede estar en el futuro.')
    uid = str(uuid.uuid4())
    try:
        with db() as c:
            c.execute('INSERT INTO users(id,email,hash,role) VALUES(?,?,?,?)',
                      (uid, data.correo.lower(), HASHER.hash(data.clave), 'client'))
    except sqlite3.IntegrityError:
        fail(409, 'El correo ya está registrado.')
    try:
        profile = data.model_dump(mode='json', exclude={'clave'})
        await call('clients', 'POST', '/internal/profiles', {'id': uid, **profile})
    except Exception:
        with db() as c:
            c.execute('DELETE FROM users WHERE id=?', (uid,))
        raise
    try:
        await send_verification(uid, data.correo.lower())
        notice = 'Registro creado. Revisa tu correo para verificar la cuenta.'
    except Exception:
        notice = 'Registro creado; correo pendiente. Inicia sesión y solicita reenviar el código.'
    return {'id': uid, 'message': notice}


@app.post('/login')
async def login(data: Login, request: Request):
    await peer(request, ['gateway'])
    with db() as c:
        u = row(c, 'SELECT * FROM users WHERE email=? AND active=1', (data.correo.lower(),))
    try:
        HASHER.verify(u['hash'] if u else HASHER.hash('clave-inexistente'), data.clave)
    except VerificationError:
        fail(401, 'Correo o contraseña incorrectos.')
    if not u:
        fail(401, 'Correo o contraseña incorrectos.')
    now = int(time.time())
    claims = dict(sub=u['id'], role=u['role'], verified=bool(u['verified']),
                  iat=now, exp=now + 1800, jti=str(uuid.uuid4()),
                  iss='mediterraneo-auth', aud='mediterraneo')
    token = jwt.encode(claims, await secret('jwt_private'), algorithm='RS256')
    with db() as c:
        c.execute('INSERT INTO sessions(jti,user_id,expires) VALUES(?,?,?)',
                  (claims['jti'], u['id'], claims['exp']))
    return {'access_token': token, 'user': {k: claims[k] for k in ('sub','role','verified')}, 'expires_in':1800}


@app.post('/verify')
async def verify(request: Request):
    await peer(request, ['gateway'])
    data = await request.json()
    code = hashlib.sha256(str(data.get('token', '')).encode()).hexdigest()
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        v = row(c, 'SELECT * FROM verification WHERE token_hash=? AND used=0 AND expires>?', (code, int(time.time())))
        if not v:
            fail(400, 'Código inválido, utilizado o vencido.')
        c.execute('UPDATE verification SET used=1 WHERE token_hash=?', (code,))
        c.execute('UPDATE users SET verified=1 WHERE id=?', (v['user_id'],))
    return {'message':'Correo verificado. Ya puedes comprar.'}


@app.post('/resend')
async def resend(request: Request):
    await peer(request, ['gateway'])
    u = await user(request, verified=False)
    with db() as c:
        account = row(c, 'SELECT email FROM users WHERE id=?', (u['sub'],))
    await send_verification(u['sub'], account['email'])
    return {'message':'Código reenviado.'}


@app.post('/logout')
async def logout(request: Request):
    await peer(request, ['gateway'])
    u = await user(request, verified=False)
    with db() as c:
        c.execute('UPDATE sessions SET revoked=1 WHERE jti=?', (u['jti'],))
    return {'message':'Sesión cerrada.'}


@app.post('/internal/session')
async def session(request: Request):
    await peer(request, ['gateway','clients','orders','payments','inventory','graphql'])
    return await user(request, verified=False)


@app.get('/users')
async def users(request: Request):
    await peer(request, ['gateway'])
    await user(request, ['admin'])
    with db() as c:
        return [dict(r) for r in c.execute('SELECT id,email,role,verified,active FROM users')]


@app.put('/users/{uid}')
async def update_user(uid: str, request: Request):
    await peer(request, ['gateway'])
    current = await user(request, ['admin'])
    data = await request.json()
    if data.get('role') not in ('admin','owner','client','cashier','dispatch'):
        fail(422, 'Perfil inválido.')
    if uid == current['sub']:
        fail(409, 'No puedes cambiar tu propia cuenta administrativa.')
    with db() as c:
        if not row(c,'SELECT id FROM users WHERE id=?',(uid,)): fail(404,'Usuario no encontrado.')
        c.execute('UPDATE users SET role=?,active=? WHERE id=?',(data['role'],int(bool(data.get('active',True))),uid))
        c.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
    return {'message':'Usuario actualizado; sesiones revocadas.'}


@app.get('/internal/email/{uid}')
async def internal_email(uid:str,request:Request):
    await peer(request,['provider'])
    with db() as c:r=row(c,'SELECT email FROM users WHERE id=?',(uid,))
    if not r:fail(404,'Cuenta no encontrada.')
    return {'email':r['email']}
