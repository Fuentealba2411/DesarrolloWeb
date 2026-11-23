"""Catálogo y reservas de stock atómicas e idempotentes."""
import json
from pathlib import Path
from fastapi import Request
from pydantic import BaseModel, Field, ConfigDict
from backend.common import app_base, init, db, row, fail, peer, user

app=app_base('Inventario')
init('''CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,data TEXT,stock INTEGER,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS reservations(order_id TEXT PRIMARY KEY,items TEXT,status TEXT);
''')
with db() as c:
    if not c.execute('SELECT COUNT(*) FROM products').fetchone()[0]:
        for p in json.loads(Path(__file__).with_name('catalogo.json').read_text()):
            c.execute('INSERT INTO products(id,data,stock) VALUES(?,?,?)',(p['id'],json.dumps(p),p['stock']))


class Product(BaseModel):
    model_config=ConfigDict(extra='forbid')
    nombre:str=Field(min_length=2,max_length=100)
    categoria:str=Field(pattern='^(Desayunos|Almuerzos|Postres)$')
    descripcion:str=Field(min_length=5,max_length=500)
    precio:int=Field(ge=1,le=1000000)
    imagen:str=Field(pattern=r'^[a-z0-9-]+\.jpg$')
    stock:int=Field(ge=0,le=10000)
    disponible:bool=True


def product(r):
    p=json.loads(r['data']);p.update(id=r['id'],stock=r['stock'],disponible=bool(r['active']))
    return p


@app.get('/products')
async def products(request:Request,limit:int=30,offset:int=0):
    await peer(request,['gateway','orders','graphql'])
    if not 1<=limit<=100 or offset<0:fail(422,'Paginación inválida.')
    with db() as c:return [product(r) for r in c.execute('SELECT * FROM products WHERE active=1 ORDER BY id LIMIT ? OFFSET ?',(limit,offset))]


@app.post('/internal/batch')
async def batch(request:Request):
    await peer(request,['orders','graphql'])
    data=await request.json();ids=data.get('ids',[])
    if len(ids)>100:fail(422,'Máximo 100 productos por lote.')
    with db() as c:
        return [product(r) for r in c.execute('SELECT * FROM products WHERE id IN ('+','.join('?' for _ in ids)+')',ids)] if ids else []


@app.get('/admin/products')
async def all_products(request:Request):
    await peer(request,['gateway'])
    await user(request,['admin','owner'])
    with db() as c:return [product(r) for r in c.execute('SELECT * FROM products')]


@app.post('/admin/products',status_code=201)
async def add_product(data:Product,request:Request):
    await peer(request,['gateway']);await user(request,['admin','owner'])
    with db() as c:
        cur=c.execute('INSERT INTO products(data,stock,active) VALUES(?,?,?)',(data.model_dump_json(),data.stock,int(data.disponible)))
        uid=cur.lastrowid
    return {'id':uid}


@app.put('/admin/products/{uid}')
async def edit_product(uid:int,data:Product,request:Request):
    await peer(request,['gateway']);await user(request,['admin','owner'])
    with db() as c:
        if not row(c,'SELECT id FROM products WHERE id=?',(uid,)):fail(404,'Producto no encontrado.')
        c.execute('UPDATE products SET data=?,stock=?,active=? WHERE id=?',(data.model_dump_json(),data.stock,int(data.disponible),uid))
    return {'id':uid,'message':'Producto actualizado.'}


@app.delete('/admin/products/{uid}')
async def disable_product(uid:int,request:Request):
    await peer(request,['gateway']);await user(request,['admin','owner'])
    with db() as c:
        if not row(c,'SELECT id FROM products WHERE id=?',(uid,)):fail(404,'Producto no encontrado.')
        c.execute('UPDATE products SET active=0 WHERE id=?',(uid,))
    return {'message':'Producto desactivado; historial conservado.'}


@app.post('/internal/reserve')
async def reserve(request:Request):
    await peer(request,['orders'])
    d=await request.json()
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        existing=row(c,'SELECT * FROM reservations WHERE order_id=?',(d['order_id'],))
        if existing:
            if existing['status']!='reserved':fail(409,'Reserva ya liberada.')
            return {'items':json.loads(existing['items'])}
        result=[]
        for item in d['items']:
            p=row(c,'SELECT * FROM products WHERE id=? AND active=1',(item['id'],))
            if not p or p['stock']<item['cantidad']:fail(409,'Producto sin disponibilidad suficiente.')
            c.execute('UPDATE products SET stock=stock-? WHERE id=?',(item['cantidad'],item['id']))
            result.append({**product(p),'cantidad':item['cantidad']})
        c.execute('INSERT INTO reservations VALUES(?,?,?)',(d['order_id'],json.dumps(result),'reserved'))
    return {'items':result}


@app.post('/internal/release/{uid}')
async def release(uid:str,request:Request):
    await peer(request,['orders'])
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        r=row(c,'SELECT * FROM reservations WHERE order_id=?',(uid,))
        if r and r['status']=='reserved':
            for item in json.loads(r['items']):
                c.execute('UPDATE products SET stock=stock+? WHERE id=?',(item['cantidad'],item['id']))
            c.execute("UPDATE reservations SET status='released' WHERE order_id=?",(uid,))
    return {'message':'Stock liberado o ya liberado.'}
