"""Adaptador privado de proveedor de pagos y correo para pruebas académicas.
No mueve dinero ni envía correo a Internet. Conserva identidad y contratos.
"""
import hashlib
import asyncio
import hmac
import json
import time
import uuid
import os
import math
import re
import unicodedata
import httpx
from fastapi import Request
from backend.common import app_base,init,db,row,fail,peer,call,secret,CLIENT,url,BOOTSTRAP

app=app_base('Proveedor sandbox privado')
init('''CREATE TABLE IF NOT EXISTS mailbox(id TEXT PRIMARY KEY,recipient TEXT,subject TEXT,body TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS checkout(id TEXT PRIMARY KEY,data TEXT,status TEXT);
CREATE TABLE IF NOT EXISTS receipts(order_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS geocoding(address TEXT PRIMARY KEY,data TEXT,created INTEGER);
''')

GEOCODER_URL=os.environ.get('GEOCODER_URL','https://photon.komoot.io/api/')
geocoding_lock=asyncio.Lock()
last_lookup=0.0


def normalize_address(address):
    value=unicodedata.normalize('NFKD',address.casefold())
    return ' '.join(re.sub(r'[^a-z0-9 ]',' ',''.join(c for c in value if not unicodedata.combining(c))).split())


def parse_location(payload,address):
    """Solo acepta un domicilio numerado de Chile; no usa el centro de una comuna."""
    locations={}
    address_tokens=set(normalize_address(address).split())
    for feature in payload.get('features',[]):
        properties=feature.get('properties',{})
        coordinates=feature.get('geometry',{}).get('coordinates',[])
        if properties.get('countrycode','').upper()!='CL' or not properties.get('street') or not properties.get('housenumber'):
            continue
        street_tokens=set(normalize_address(str(properties['street'])).split())-{'calle','avenida','av','pasaje','pje'}
        number_tokens=set(normalize_address(str(properties['housenumber'])).split())
        if not street_tokens or not street_tokens.issubset(address_tokens) or not number_tokens.issubset(address_tokens):
            continue
        if len(coordinates)!=2:
            continue
        lon,lat=map(float,coordinates)
        if math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180:
            locations[(round(lat,5),round(lon,5))]={'lat':lat,'lon':lon,'source':'Photon / OpenStreetMap'}
    if not locations:
        fail(422,'No encontramos ese domicilio. Escribe calle, número, comuna y ciudad. Puedes usar Dirección de prueba 123, Santiago para la demostración.')
    if len(locations)!=1:
        fail(422,'La dirección tiene varias coincidencias. Agrega comuna y ciudad para identificarla.')
    return next(iter(locations.values()))


@app.post('/internal/geocode')
async def geocode(request:Request):
    global last_lookup
    await peer(request,['orders'])
    data=await request.json()
    address=data.get('direccion','')
    if not isinstance(address,str) or not 5<=len(address.strip())<=200:
        fail(422,'Escribe una dirección de entrega de 5 a 200 caracteres.')
    normalized=normalize_address(address)
    # Domicilio ficticio explícito para la evaluación, disponible sin Internet.
    if normalized in ('direccion de prueba 123 santiago','direccion ficticia 123'):
        return {'lat':-33.4372,'lon':-70.6506,'source':'Domicilio ficticio de demostración'}
    async with geocoding_lock:
        with db() as c:
            cached=row(c,'SELECT data FROM geocoding WHERE address=? AND created>?',(normalized,int(time.time())-86400))
        if cached:
            return json.loads(cached['data'])
        await asyncio.sleep(max(0,1-(time.monotonic()-last_lookup)))
        last_lookup=time.monotonic()
        try:
            # Solo viaja la dirección; no se envían identidad, correo ni datos del pedido.
            async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
                response=await client.get(GEOCODER_URL,params={'q':address,'limit':5},headers={'User-Agent':'Mediterraneo-Academico/1.1','Accept':'application/json'})
                response.raise_for_status()
                location=parse_location(response.json(),address)
        except (httpx.HTTPError,ValueError,TypeError,KeyError,AttributeError):
            fail(503,'El servicio de direcciones no está disponible. Inténtalo más tarde o utiliza la dirección ficticia indicada para la demostración.')
        with db() as c:
            c.execute('DELETE FROM geocoding WHERE created<?',(int(time.time())-86400,))
            c.execute('INSERT OR REPLACE INTO geocoding VALUES(?,?,?)',(normalized,json.dumps(location),int(time.time())))
        return location


@app.post('/internal/mail',status_code=201)
async def mail(request:Request):
    await peer(request,['auth'])
    d=await request.json();uid=str(uuid.uuid4())
    with db() as c:c.execute('INSERT INTO mailbox VALUES(?,?,?,?,?)',(uid,d['recipient'],d['subject'],d['body'],int(time.time())))
    return {'id':uid,'accepted':True}


@app.post('/internal/receipt')
async def receipt(request:Request):
    await peer(request,['orders']);d=await request.json()
    email=(await call('auth','GET','/internal/email/'+d['client_id']))['email']
    # Entrega al buzón sandbox de ese correo; no contacta personas reales.
    with db() as c:
        if row(c,'SELECT order_id FROM receipts WHERE order_id=?',(d['order_id'],)):return {'accepted':True}
        c.execute('INSERT INTO receipts VALUES(?)',(d['order_id'],))
        c.execute('INSERT INTO mailbox VALUES(?,?,?,?,?)',(str(uuid.uuid4()),email,'Comprobante académico no tributario',json.dumps(d),int(time.time())))
    return {'accepted':True}


@app.post('/internal/checkout')
async def checkout(request:Request):
    await peer(request,['payments']);d=await request.json()
    with db() as c:c.execute('INSERT OR IGNORE INTO checkout VALUES(?,?,?)',(d['id'],json.dumps(d),'pendiente'))
    return {'checkout_id':d['id']}


@app.post('/internal/refund')
async def refund(request:Request):
    await peer(request,['payments']);d=await request.json()
    with db() as c:c.execute("UPDATE checkout SET status='reembolsado' WHERE id=?",(d['payment_id'],))
    return {'accepted':True}


@app.get('/operator/mailbox')
async def mailbox(request:Request):
    await peer(request,['operator'])
    with db() as c:return [dict(r) for r in c.execute('SELECT * FROM mailbox ORDER BY created DESC')]


@app.post('/operator/approve/{uid}')
async def approve(uid:str,request:Request):
    await peer(request,['operator'])
    with db() as c:p=row(c,'SELECT * FROM checkout WHERE id=?',(uid,))
    if not p:fail(404,'Checkout no encontrado.')
    if p['status']=='reembolsado':fail(409,'Checkout reembolsado.')
    d=json.loads(p['data'])
    event={'event_id':'aprobacion-'+uid,'payment_id':uid,'total':d['total'],'status':'pagado'}
    raw=json.dumps(event,separators=(',',':')).encode();timestamp=str(int(time.time()))
    signature=hmac.new((await secret('payment_hmac')).encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    r=await CLIENT.post(url('payments')+'/webhook',content=raw,headers={
        'X-Service-Key':BOOTSTRAP,'Content-Type':'application/json',
        'X-Provider-Timestamp':timestamp,'X-Provider-Signature':signature})
    if r.status_code!=200:fail(r.status_code,'No se pudo confirmar el aviso; se puede reintentar.')
    with db() as c:c.execute("UPDATE checkout SET status='pagado' WHERE id=?",(uid,))
    return {'message':'Pago de prueba aprobado.', 'resultado':r.json()}
