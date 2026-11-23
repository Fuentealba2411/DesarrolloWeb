"""Perfiles, contacto y reservas persistentes."""
from datetime import date
import json
import uuid
from fastapi import Request
from pydantic import BaseModel, Field, ConfigDict
from backend.common import app_base, init, db, row, fail, peer, user

app = app_base('Clientes y atención')
init('''CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,data TEXT);
CREATE TABLE IF NOT EXISTS contacts(id TEXT PRIMARY KEY,data TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS reservations(id TEXT PRIMARY KEY,client_id TEXT,fecha TEXT,personas INTEGER,data TEXT,status TEXT);
''')


class Contact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nombre: str = Field(min_length=2,max_length=100)
    correo: str = Field(pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$',max_length=254)
    mensaje: str = Field(min_length=5,max_length=2000)


class Reservation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nombre: str = Field(min_length=2,max_length=100)
    correo: str = Field(pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$',max_length=254)
    fecha: date
    personas: int = Field(ge=2,le=12)
    comentarios: str = Field(default='',max_length=500)


@app.post('/internal/profiles', status_code=201)
async def create_profile(request: Request):
    await peer(request, ['auth'])
    data = await request.json()
    with db() as c:
        c.execute('INSERT INTO profiles VALUES(?,?)',(data['id'],json.dumps(data)))
    return {'id':data['id']}


@app.get('/me')
async def me(request: Request):
    await peer(request, ['gateway','graphql'])
    u = await user(request,verified=False)
    with db() as c: p=row(c,'SELECT data FROM profiles WHERE id=?',(u['sub'],))
    if not p: fail(404,'Perfil no encontrado.')
    return json.loads(p['data'])


@app.put('/me')
async def edit_me(request: Request):
    await peer(request, ['gateway'])
    u = await user(request)
    data = await request.json()
    allowed={'nombre','direccion','comuna','provincia','region','telefono'}
    if not data or set(data)-allowed: fail(422,'Solo puedes modificar los campos de contacto permitidos.')
    if any(not isinstance(v,str) or not 2 <= len(v.strip()) <= 200 for v in data.values()): fail(422,'Datos de perfil inválidos.')
    with db() as c:
        p=row(c,'SELECT data FROM profiles WHERE id=?',(u['sub'],))
        if not p:fail(404,'Perfil no encontrado.')
        profile=json.loads(p['data']);profile.update(data)
        c.execute('UPDATE profiles SET data=? WHERE id=?',(json.dumps(profile),u['sub']))
    return profile


@app.get('/profiles')
async def profiles(request: Request):
    await peer(request,['gateway'])
    await user(request,['admin'])
    with db() as c:return [json.loads(r['data']) for r in c.execute('SELECT data FROM profiles')]


@app.post('/contact', status_code=201)
async def contact(data: Contact, request: Request):
    await peer(request,['gateway'])
    uid=str(uuid.uuid4())
    with db() as c:c.execute('INSERT INTO contacts(id,data) VALUES(?,?)',(uid,data.model_dump_json()))
    return {'id':uid,'message':'Mensaje recibido. Te responderemos al correo.'}


@app.get('/contact')
async def list_contact(request: Request):
    await peer(request,['gateway'])
    await user(request,['admin'])
    with db() as c:return [dict(r) | {'data':json.loads(r['data'])} for r in c.execute('SELECT * FROM contacts ORDER BY created DESC LIMIT 100')]


@app.post('/reservations', status_code=201)
async def reservation(data: Reservation, request: Request):
    await peer(request,['gateway'])
    u=await user(request)
    if data.fecha < date.today():fail(422,'No se admiten fechas pasadas.')
    if data.fecha.weekday()==0:fail(422,'El restaurante cierra los lunes.')
    uid=str(uuid.uuid4())
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        # Capacidad propuesta de 24 plazas por jornada; reservas sujetas a confirmación.
        used=c.execute("SELECT COALESCE(SUM(personas),0) FROM reservations WHERE fecha=? AND status!='cancelada'",(str(data.fecha),)).fetchone()[0]
        if used+data.personas>24:fail(409,'No quedan plazas para ese día.')
        c.execute('INSERT INTO reservations VALUES(?,?,?,?,?,?)',(uid,u['sub'],str(data.fecha),data.personas,data.model_dump_json(),'solicitada'))
    return {'id':uid,'message':'Reserva recibida y guardada; pendiente de confirmación.'}


@app.get('/reservations')
async def reservations(request: Request):
    await peer(request,['gateway'])
    u=await user(request)
    with db() as c:
        result=c.execute('SELECT * FROM reservations' + ('' if u['role']=='admin' else ' WHERE client_id=?'), () if u['role']=='admin' else (u['sub'],))
        return [dict(r) | {'data':json.loads(r['data'])} for r in result]


@app.put('/reservations/{uid}')
async def update_reservation(uid:str,request:Request):
    await peer(request,['gateway'])
    u=await user(request)
    data=await request.json();status=data.get('status')
    if status not in ('confirmada','cancelada'):fail(422,'Estado inválido.')
    with db() as c:
        r=row(c,'SELECT * FROM reservations WHERE id=?',(uid,))
        if not r:fail(404,'Reserva no encontrada.')
        if u['role']!='admin' and (r['client_id']!=u['sub'] or status!='cancelada'):fail(403,'Operación no permitida.')
        c.execute('UPDATE reservations SET status=? WHERE id=?',(status,uid))
    return {'message':'Reserva actualizada.'}


@app.put('/profiles/{uid}')
async def admin_edit_profile(uid:str,request:Request):
    await peer(request,['gateway']);await user(request,['admin'])
    data=await request.json();allowed={'nombre','direccion','comuna','provincia','region','telefono'}
    if not data or set(data)-allowed or any(not isinstance(v,str) or not 2<=len(v.strip())<=200 for v in data.values()):
        fail(422,'Campos o valores de perfil inválidos.')
    with db() as c:
        r=row(c,'SELECT data FROM profiles WHERE id=?',(uid,))
        if not r:fail(404,'Cliente no encontrado.')
        profile=json.loads(r['data']);profile.update(data)
        c.execute('UPDATE profiles SET data=? WHERE id=?',(json.dumps(profile),uid))
    return profile
