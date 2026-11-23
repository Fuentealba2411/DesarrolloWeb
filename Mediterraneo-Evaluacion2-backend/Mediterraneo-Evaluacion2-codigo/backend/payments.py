"""Pagos: importe desde orders; avisos HMAC, idempotencia y reembolso."""
import hashlib
import hmac
import json
import time
import uuid
from fastapi import Request
from backend.common import app_base,init,db,row,fail,peer,user,call,secret

app=app_base('Pagos')
init('''CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY,order_id TEXT UNIQUE,client_id TEXT,total INTEGER,status TEXT);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,payment_id TEXT);
''')


@app.post('/payments',status_code=201)
async def start(request:Request):
    await peer(request,['gateway']);u=await user(request)
    d=await request.json()
    if set(d)!={'order_id'}:fail(422,'Solo se admite order_id; el servidor determina el importe.')
    order=await call('orders','GET','/internal/orders/'+str(d['order_id']))
    if order['client_id']!=u['sub']:fail(403,'El pedido no te pertenece.')
    if order['status']!='pendiente_pago':fail(409,'El pedido no admite iniciar pago.')
    with db() as c:
        existing=row(c,'SELECT * FROM payments WHERE order_id=?',(order['id'],))
        if existing:
            p=existing
        else:
            uid=str(uuid.uuid4());p=dict(id=uid,order_id=order['id'],client_id=u['sub'],total=order['total'],status='pendiente')
            c.execute('INSERT INTO payments VALUES(?,?,?,?,?)',tuple(p.values()))
    await call('provider','POST','/internal/checkout',p)
    return p


@app.post('/webhook')
async def webhook(request:Request):
    await peer(request,['gateway','provider'])
    raw=await request.body();timestamp=request.headers.get('x-provider-timestamp','')
    try:
        if abs(time.time()-int(timestamp))>300:fail(401,'Aviso vencido.')
    except ValueError:fail(401,'Fecha de aviso inválida.')
    expected=hmac.new((await secret('payment_hmac')).encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,request.headers.get('x-provider-signature','')):fail(401,'Firma de pago inválida.')
    d=json.loads(raw)
    with db() as c:
        if row(c,'SELECT id FROM events WHERE id=?',(d['event_id'],)):return {'message':'Evento ya procesado.'}
        p=row(c,'SELECT * FROM payments WHERE id=?',(d['payment_id'],))
    if not p or p['total']!=d['total'] or d['status']!='pagado':fail(409,'Pago no coincide con el contrato.')
    if p['status']=='reembolsado':fail(409,'Pago ya reembolsado.')
    await call('orders','POST','/internal/paid/'+p['order_id'])
    with db() as c:
        c.execute("UPDATE payments SET status='pagado' WHERE id=? AND status!='reembolsado'",(p['id'],))
        c.execute('INSERT OR IGNORE INTO events VALUES(?,?)',(d['event_id'],p['id']))
    return {'message':'Pago validado.'}


@app.post('/internal/refund/{uid}')
async def refund(uid:str,request:Request):
    await peer(request,['orders'])
    with db() as c:p=row(c,'SELECT * FROM payments WHERE order_id=?',(uid,))
    if p and p['status']!='reembolsado':
        await call('provider','POST','/internal/refund',{'payment_id':p['id']})
        with db() as c:c.execute("UPDATE payments SET status='reembolsado' WHERE id=?",(p['id'],))
    return {'message':'Pago cancelado o reembolsado.'}
