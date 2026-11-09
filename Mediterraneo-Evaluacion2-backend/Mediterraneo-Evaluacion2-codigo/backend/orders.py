"""Pedidos, precios oficiales, estados, despacho, comprobantes y reportes."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import math
import time
import uuid
from fastapi import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ConfigDict
from backend.common import app_base, init, db, row, fail, peer, user, owner, call, bearer

app=app_base('Pedidos')
init('''CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,client_id TEXT,status TEXT,total INTEGER,
items TEXT,address TEXT,created INTEGER,reason TEXT DEFAULT '',receipt_sent INTEGER DEFAULT 0,
request_key TEXT, UNIQUE(client_id,request_key));
''')


class Item(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:int=Field(ge=1)
    cantidad:int=Field(ge=1,le=20)


class Order(BaseModel):
    model_config=ConfigDict(extra='forbid')
    items:list[Item]=Field(min_length=1,max_length=30)
    direccion:str=Field(min_length=5,max_length=200)
    # Compatibilidad con clientes anteriores. La cobertura siempre se resuelve en el servidor.
    lat:float | None=Field(default=None,ge=-90,le=90)
    lon:float | None=Field(default=None,ge=-180,le=180)


def read_order(uid):
    with db() as c:r=row(c,'SELECT * FROM orders WHERE id=?',(uid,))
    if not r:fail(404,'Pedido no encontrado.')
    r['items']=json.loads(r['items']);return r


def distance(lat,lon):
    # Punto ficticio de demostración en Santiago, configurable al definir el local real.
    lat0,lon0=-33.4372,-70.6506
    a=math.sin(math.radians(lat-lat0)/2)**2+math.cos(math.radians(lat0))*math.cos(math.radians(lat))*math.sin(math.radians(lon-lon0)/2)**2
    return 6371*2*math.atan2(math.sqrt(a),math.sqrt(max(0,1-a)))


def price_items(items):
    now=datetime.now(ZoneInfo('America/Santiago'))
    total=0;result=[]
    for item in items:
        unit=item['precio'];qty=item['cantidad'];discount=0
        if item['id']==14 and not (1<=now.weekday()<=4 and (12,30)<=(now.hour,now.minute)<=(15,30)):
            fail(409,'El menú del día solo está disponible de martes a viernes, 12:30 a 15:30.')
        if item['categoria']=='Desayunos' and (now.hour,now.minute)<=(11,30):discount=round(unit*qty*0.15)
        elif item['categoria']=='Postres' and now.weekday()==6:discount=unit*(qty//2)
        subtotal=unit*qty-discount;total+=subtotal
        result.append({'id':item['id'],'nombre':item['nombre'],'precio':unit,'cantidad':qty,'descuento':discount,'subtotal':subtotal})
    return total,result


@app.post('/orders',status_code=201)
async def create(data:Order,request:Request):
    await peer(request,['gateway'])
    u=await user(request)
    key=request.headers.get('idempotency-key','')
    if not 8<=len(key)<=100:fail(422,'Incluye Idempotency-Key de 8 a 100 caracteres.')
    if len({i.id for i in data.items})!=len(data.items):fail(422,'Agrupa las cantidades del mismo producto.')
    with db() as c:
        existing=row(c,'SELECT id FROM orders WHERE client_id=? AND request_key=?',(u['sub'],key))
        if existing:return read_order(existing['id'])
    location=await call('provider','POST','/internal/geocode',{'direccion':data.direccion})
    if distance(location['lat'],location['lon'])>3:
        fail(422,'La dirección está fuera de nuestra cobertura de delivery de 3 km.')
    with db() as c:
        uid=str(uuid.uuid4())
        try:c.execute('INSERT INTO orders(id,client_id,status,total,items,address,created,request_key) VALUES(?,?,?,?,?,?,?,?)',
                      (uid,u['sub'],'reservando',0,'[]',data.direccion,int(time.time()),key))
        except Exception:fail(409,'Solicitud en proceso. Consulta tus pedidos.')
    try:
        reserved=await call('inventory','POST','/internal/reserve',{'order_id':uid,'items':[i.model_dump() for i in data.items]})
        total,items=price_items(reserved['items'])
        with db() as c:c.execute("UPDATE orders SET status='pendiente_pago',total=?,items=? WHERE id=?",(total,json.dumps(items),uid))
    except Exception:
        with db() as c:c.execute("UPDATE orders SET status='cancelando',reason='Fallo al reservar o calcular' WHERE id=?",(uid,))
        try:
            await call('inventory','POST','/internal/release/'+uid)
            with db() as c:c.execute("UPDATE orders SET status='cancelado' WHERE id=?",(uid,))
        except Exception:pass  # reconciliación reintenta; no se oculta como pedido confirmado.
        raise
    return read_order(uid)


@app.get('/orders')
async def list_orders(request:Request,limit:int=20,offset:int=0):
    await peer(request,['gateway','graphql'])
    u=await user(request)
    if not 1<=limit<=100 or offset<0:fail(422,'Paginación inválida.')
    with db() as c:
        sql='SELECT id FROM orders';params=[]
        if u['role']=='client':sql+=' WHERE client_id=?';params=[u['sub']]
        ids=c.execute(sql+' ORDER BY created DESC LIMIT ? OFFSET ?',params+[limit,offset]).fetchall()
    result=[read_order(r['id']) for r in ids]
    for r in result:
        if u['role']=='owner':r.pop('address',None);r.pop('client_id',None)
    return result


@app.get('/orders/{uid}')
async def get_order(uid:str,request:Request):
    await peer(request,['gateway','graphql'])
    u=await user(request);r=read_order(uid);owner(r,u)
    if u['role']=='owner':r.pop('address',None);r.pop('client_id',None)
    return r


@app.get('/internal/orders/{uid}')
async def quote(uid:str,request:Request):
    await peer(request,['payments'])
    r=read_order(uid)
    return {k:r[k] for k in ('id','client_id','total','status')}


@app.post('/internal/paid/{uid}')
async def paid(uid:str,request:Request):
    await peer(request,['payments'])
    with db() as c:
        c.execute('BEGIN IMMEDIATE');r=row(c,'SELECT status FROM orders WHERE id=?',(uid,))
        if not r:fail(404,'Pedido no encontrado.')
        if r['status'] in ('pagado','preparando','despachado','entregado'):return {'message':'Pago ya aplicado.'}
        if r['status']!='pendiente_pago':fail(409,'El pedido no admite pago.')
        c.execute("UPDATE orders SET status='pagado' WHERE id=?",(uid,))
    return {'message':'Pago confirmado; se habilitó preparación.'}


@app.post('/orders/{uid}/cancel')
async def cancel(uid:str,request:Request):
    await peer(request,['gateway'])
    u=await user(request);r=read_order(uid)
    if u['role'] not in ('client','admin'):fail(403,'Solo cliente propietario o administrador.')
    owner(r,u);data=await request.json();reason=data.get('motivo','')
    if not isinstance(reason,str) or not 5<=len(reason.strip())<=300:fail(422,'Indica un motivo de 5 a 300 caracteres.')
    with db() as c:
        c.execute('BEGIN IMMEDIATE');r=row(c,'SELECT * FROM orders WHERE id=?',(uid,))
        if r['status']=='cancelado':return {'message':'Pedido ya cancelado.'}
        if r['status'] not in ('pendiente_pago','pagado','cancelando'):fail(409,'Solo se anula antes de iniciar preparación.')
        c.execute("UPDATE orders SET status='cancelando',reason=? WHERE id=?",(reason,uid))
    await finish_cancel(uid)
    return read_order(uid)


async def finish_cancel(uid):
    await call('payments','POST','/internal/refund/'+uid)
    await call('inventory','POST','/internal/release/'+uid)
    with db() as c:c.execute("UPDATE orders SET status='cancelado' WHERE id=? AND status='cancelando'",(uid,))


@app.put('/orders/{uid}/status')
async def update_status(uid:str,request:Request):
    await peer(request,['gateway'])
    u=await user(request,['admin','cashier','dispatch'])
    d=await request.json();target=d.get('status')
    transitions={'pagado':'preparando','preparando':'despachado','despachado':'entregado'}
    with db() as c:
        c.execute('BEGIN IMMEDIATE');r=row(c,'SELECT * FROM orders WHERE id=?',(uid,))
        if not r:fail(404,'Pedido no encontrado.')
        if transitions.get(r['status'])!=target:fail(409,'Transición no permitida; confirma primero el pago.')
        c.execute('UPDATE orders SET status=? WHERE id=?',(target,uid))
    return read_order(uid)


@app.get('/orders/{uid}/receipt')
async def receipt(uid:str,request:Request):
    await peer(request,['gateway'])
    u=await user(request);r=read_order(uid);owner(r,u)
    if r['status'] not in ('pagado','preparando','despachado','entregado'):fail(409,'Comprobante disponible después del pago.')
    return {'numero':'DEMO-'+uid,'tipo':'Comprobante académico no tributario','total':r['total'],'items':r['items'],'moneda':'CLP'}


@app.post('/orders/{uid}/receipt-email')
async def receipt_email(uid:str,request:Request):
    await peer(request,['gateway'])
    await user(request,['admin','cashier'])
    r=read_order(uid)
    if r['status'] not in ('pagado','preparando','despachado','entregado'):fail(409,'Primero confirma el pago.')
    # Auth posee correo de cuenta; entrega a proveedor sin exponerlo al cajero.
    await call('provider','POST','/internal/receipt',{'client_id':r['client_id'],'order_id':uid,'total':r['total'],'items':r['items']})
    with db() as c:c.execute('UPDATE orders SET receipt_sent=1 WHERE id=?',(uid,))
    return {'message':'Comprobante enviado al buzón de prueba.'}


@app.get('/orders/{uid}/dispatch')
async def dispatch(uid:str,request:Request):
    await peer(request,['gateway'])
    await user(request,['admin','dispatch','cashier']);r=read_order(uid)
    if r['status'] not in ('pagado','preparando','despachado','entregado'):fail(409,'Orden de despacho requiere pago confirmado.')
    return {'orden':uid,'direccion':r['address'],'items':r['items'],'created':r['created']}


@app.get('/reports/sales')
async def reports(request:Request,desde:int=0,hasta:int=4102444800):
    await peer(request,['gateway'])
    await user(request,['admin','owner'])
    if desde<0 or hasta<desde:fail(422,'Período inválido.')
    with db() as c:
        r=row(c,"SELECT COUNT(*) ventas,COALESCE(SUM(total),0) total FROM orders WHERE status IN ('pagado','preparando','despachado','entregado') AND created BETWEEN ? AND ?",(desde,hasta))
    return dict(r,moneda='CLP',desde=desde,hasta=hasta)


@app.post('/admin/reconcile')
async def reconcile(request:Request):
    await peer(request,['gateway'])
    await user(request,['admin'])
    with db() as c:
        # Recupera pasos interrumpidos y expira reservas impagas después de 15 minutos.
        c.execute("UPDATE orders SET status='cancelando',reason='Reserva vencida o ejecución interrumpida' WHERE status IN ('reservando','pendiente_pago') AND created<?",(int(time.time())-900,))
        ids=[r['id'] for r in c.execute("SELECT id FROM orders WHERE status='cancelando'")]
    for uid in ids:await finish_cancel(uid)
    return {'recuperados':len(ids)}
