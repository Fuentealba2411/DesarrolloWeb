"""Pruebas HTTP contra los nueve procesos reales, iniciados con scripts/iniciar.py."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
import json
import os
from pathlib import Path
import time
import uuid
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]
R=Path(os.environ.get('RUNTIME_DIR',ROOT/'.runtime'))
BASE='https://127.0.0.1:8443'


def client():return httpx.Client(base_url=BASE,verify=str(R/'cert.pem'),trust_env=False,timeout=30)


def request(c,method,path,data=None,headers=None):
    h={'X-CSRF-Token':c.cookies.get('csrf','')};h.update(headers or {})
    return c.request(method,'/api'+path,json=data,headers=h)


def register(c):
    email='cliente-'+uuid.uuid4().hex+'@example.test'
    payload=dict(correo=email,clave='Prueba-academica-2026',nombre='Cliente Ficticio',run='11111111-1',direccion='Direccion ficticia 123',comuna='Santiago',provincia='Santiago',region='Metropolitana',nacimiento='1990-01-01',sexo='No informar',telefono='+56911111111')
    r=request(c,'POST','/auth/register',payload);assert r.status_code==201,r.text
    return payload,r.json()['id']


def verify_email(c,email):
    with httpx.Client(verify=str(R/'cert.pem'),trust_env=False) as provider:
        mails=provider.get('https://127.0.0.1:8507/operator/mailbox',headers={'X-Service-Key':(R/'operator.token').read_text()}).json()
    code=next(m['body'].split(': ')[-1] for m in mails if m['recipient']==email and m['subject']=='Verifica tu correo')
    r=request(c,'POST','/auth/verify',{'token':code});assert r.status_code==200,r.text
    return code


def login(c,payload):
    r=request(c,'POST','/auth/login',{k:payload[k] for k in ('correo','clave')});assert r.status_code==200,r.text
    assert 'access_token' not in r.json()
    assert 'HttpOnly' in r.headers.get('set-cookie','')


@pytest.fixture
def customer():
    with client() as c:
        p,uid=register(c);verify_email(c,p['correo']);login(c,p);yield c,p,uid


@pytest.fixture
def admin():
    with client() as c:
        login(c,json.loads((R/'cuentas-demo.json').read_text())['admin']);yield c


def order(c,pid=6,qty=1,key=None):
    return request(c,'POST','/orders',dict(items=[{'id':pid,'cantidad':qty}],direccion='Direccion ficticia 123'),headers={'Idempotency-Key':key or str(uuid.uuid4())})


def approve(payment_id):
    with httpx.Client(verify=str(R/'cert.pem'),trust_env=False,timeout=30) as c:
        return c.post('https://127.0.0.1:8507/operator/approve/'+payment_id,headers={'X-Service-Key':(R/'operator.token').read_text()})


def test_catalogo_anonimo_y_datos_publicos():
    with client() as c:
        r=request(c,'GET','/products');assert r.status_code==200 and len(r.json())>=13
        assert not any('correo' in p or 'hash' in p for p in r.json())
        assert request(c,'GET','/orders').status_code==401
        assert request(c,'GET','/internal/session').status_code==404
        assert request(c,'DELETE','/products').status_code==404


def test_registro_validacion_correo_y_sesion():
    with client() as c:
        p,uid=register(c);login(c,p)
        assert order(c).status_code==403
        code=verify_email(c,p['correo'])
        assert request(c,'POST','/auth/verify',{'token':code}).status_code==400
        assert order(c).status_code==201
        assert request(c,'POST','/auth/logout').status_code==200
        assert request(c,'GET','/me').status_code==401


def test_roles_propiedad_y_cabeceras_falsas(customer):
    c,_,_=customer;oid=order(c).json()['id']
    assert request(c,'POST','/admin/products',{}).status_code in (403,422)
    # Un producto válido obliga a comprobar el rol, además de validar el cuerpo.
    p=request(c,'GET','/products').json()[0];p.pop('id');
    assert request(c,'POST','/admin/products',p).status_code==403
    with client() as other:
        data,_=register(other);verify_email(other,data['correo']);login(other,data)
        r=request(other,'GET','/orders/'+oid,headers={'X-User-ID':customer[2],'X-Role':'admin'})
        assert r.status_code==403 and 'Direccion ficticia' not in r.text
        gql=request(other,'POST','/graphql',{'query':'query($id:ID!){resumenPedido(id:$id){id total}}','variables':{'id':oid}})
        assert gql.status_code==200 and gql.json().get('errors') and gql.json()['data']['resumenPedido'] is None


def test_red_privada_y_acl_secretos():
    with httpx.Client(verify=str(R/'cert.pem'),trust_env=False) as c:
        assert c.get('https://127.0.0.1:8503/products').status_code==403
        assert c.get('https://127.0.0.1:8500/v1/secrets/jwt_private',headers={'X-Service-Key':(R/'inventory.token').read_text()}).status_code==403
        assert c.post('https://127.0.0.1:8507/operator/approve/x').status_code==403


def test_pedido_idempotente_precios_y_stock(customer):
    c,_,_=customer;key=str(uuid.uuid4())
    before=request(c,'GET','/products').json();stock=next(p['stock'] for p in before if p['id']==6)
    first=order(c,qty=2,key=key);second=order(c,qty=2,key=key)
    assert first.status_code==second.status_code==201
    assert first.json()['id']==second.json()['id'] and first.json()['total']==19600
    assert next(p['stock'] for p in request(c,'GET','/products').json() if p['id']==6)==stock-2
    bad=request(c,'POST','/orders',dict(items=[{'id':6,'cantidad':1}],direccion='Direccion ficticia 123',lat=-33.4372,lon=-70.6506,total=1),headers={'Idempotency-Key':str(uuid.uuid4())})
    assert bad.status_code==422


def test_stock_concurrente_sin_sobreventa(customer):
    c,_,_=customer
    cookie=dict(c.cookies)
    def attempt(_):
        with client() as other:
            other.cookies.update(cookie)
            return order(other,pid=10,qty=20).status_code
    before=next(p['stock'] for p in request(c,'GET','/products').json() if p['id']==10)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(attempt,range(4)))
    assert results.count(201)==before//20
    assert all(s in (201,409) for s in results)
    after=next(p['stock'] for p in request(c,'GET','/products').json() if p['id']==10)
    assert after==before%20 and after>=0


def test_pago_firmado_duplicados_despacho_y_comprobante(customer,admin):
    c,_,_=customer;oid=order(c).json()['id']
    assert request(admin,'PUT','/orders/'+oid+'/status',{'status':'preparando'}).status_code==409
    p=request(c,'POST','/payments',{'order_id':oid});assert p.status_code==201,p.text
    assert approve(p.json()['id']).status_code==200
    assert approve(p.json()['id']).status_code==200
    assert request(c,'GET','/orders/'+oid).json()['status']=='pagado'
    assert request(c,'GET','/orders/'+oid+'/receipt').json()['total']==9800
    assert request(admin,'POST','/orders/'+oid+'/receipt-email').status_code==200
    assert request(admin,'POST','/orders/'+oid+'/receipt-email').status_code==200
    assert request(admin,'GET','/orders/'+oid+'/dispatch').status_code==200
    for status in ['preparando','despachado','entregado']:
        assert request(admin,'PUT','/orders/'+oid+'/status',{'status':status}).status_code==200
    assert request(c,'POST','/orders/'+oid+'/cancel',{'motivo':'Cambio de planes'}).status_code==409
    (R/'checkpoint.json').write_text(json.dumps({'order_id':oid,'session':c.cookies.get('session')}))


def test_pago_alterado_y_firma_invalida(customer):
    c,_,_=customer;oid=order(c).json()['id']
    assert request(c,'POST','/payments',{'order_id':oid,'total':1}).status_code==422
    with httpx.Client(verify=str(R/'cert.pem'),trust_env=False) as direct:
        r=direct.post('https://127.0.0.1:8505/webhook',json={'order_id':oid,'status':'pagado'},headers={'X-Service-Key':(R/'gateway.token').read_text(),'X-Provider-Timestamp':str(int(time.time())),'X-Provider-Signature':'falsa'})
        assert r.status_code==401
    assert request(c,'GET','/orders/'+oid).json()['status']=='pendiente_pago'


def test_anulacion_reembolso_y_recuperacion_stock(customer):
    c,_,_=customer
    before=next(p['stock'] for p in request(c,'GET','/products').json() if p['id']==5)
    oid=order(c,pid=5).json()['id'];p=request(c,'POST','/payments',{'order_id':oid}).json()
    assert approve(p['id']).status_code==200
    assert request(c,'POST','/orders/'+oid+'/cancel',{'motivo':'Cambio de planes'}).status_code==200
    assert request(c,'POST','/orders/'+oid+'/cancel',{'motivo':'Cambio de planes'}).status_code==200
    assert next(p['stock'] for p in request(c,'GET','/products').json() if p['id']==5)==before
    assert approve(p['id']).status_code==409


def test_graphql_agregacion_limites_y_campos(customer):
    c,_,_=customer;oid=order(c).json()['id']
    r=request(c,'POST','/graphql',{'query':'query($id:ID!){resumenPedido(id:$id){id estado total lineas{nombre descripcionActual cantidad}}}','variables':{'id':oid}})
    assert r.status_code==200 and not r.json().get('errors'),r.text
    assert r.json()['data']['resumenPedido']['lineas'][0]['descripcionActual']
    assert request(c,'POST','/graphql',{'query':'{__schema{types{name}}}'}).status_code==400
    assert request(c,'POST','/graphql',{'query':'{misPedidos(limit:31){id}}'}).json().get('errors')
    assert request(c,'POST','/graphql',{'query':'{'+''.join('a'+str(i)+':misPedidos{id}' for i in range(30))+'}'}).status_code==400
    assert request(c,'POST','/graphql',{'query':'{misPedidos{clave}}'}).status_code==400


def test_csrf_y_sesion_revocada(customer):
    c,p,_=customer;old=c.cookies.get('session')
    r=c.post('/api/auth/logout',json={});assert r.status_code==403
    assert request(c,'POST','/auth/logout',headers={'Origin':'https://sitio-ajeno.test'}).status_code==403
    assert request(c,'POST','/auth/logout').status_code==200
    c.cookies.set('session',old,domain='127.0.0.1',path='/')
    assert request(c,'GET','/orders').status_code==401


def test_contacto_reservas_y_perfil(customer,admin):
    c,_,_=customer
    assert request(c,'POST','/contact',{'nombre':'Cliente Ficticio','correo':'persona@example.test','mensaje':'Consulta de prueba'}).status_code==201
    assert request(c,'GET','/contact').status_code==403
    assert request(admin,'GET','/contact').status_code==200
    assert request(c,'PUT','/me',{'direccion':'Nueva direccion ficticia 234'}).status_code==200
    assert request(c,'PUT','/me',{'role':'admin'}).status_code==422
    future=date.today()+timedelta(days=1)
    while future.weekday()==0:future+=timedelta(days=1)
    data={'nombre':'Cliente Ficticio','correo':'persona@example.test','fecha':str(future),'personas':2,'comentarios':''}
    r=request(c,'POST','/reservations',data);assert r.status_code==201,r.text
    assert request(admin,'PUT','/reservations/'+r.json()['id'],{'status':'confirmada'}).status_code==200
    assert request(c,'PUT','/reservations/'+r.json()['id'],{'status':'cancelada'}).status_code==200
    assert request(c,'POST','/reservations',dict(data,fecha='2000-01-01')).status_code==422


def test_admin_catalogo_roles_reporte(customer,admin):
    p=dict(nombre='Producto de prueba',categoria='Almuerzos',descripcion='Registro ficticio de prueba',precio=7000,imagen='falafel.jpg',stock=10,disponible=True)
    r=request(admin,'POST','/admin/products',p);assert r.status_code==201,r.text
    uid=r.json()['id'];assert request(admin,'PUT','/admin/products/'+str(uid),dict(p,precio=7500)).status_code==200
    assert request(admin,'DELETE','/admin/products/'+str(uid)).status_code==200
    assert request(admin,'GET','/reports/sales').status_code==200
    c,data,cid=customer
    assert request(admin,'PUT','/users/'+cid,{'role':'dispatch','active':True}).status_code==200
    assert request(c,'GET','/orders').status_code==401 # Cambio de perfil revoca sesiones.
    assert request(admin,'POST','/admin/reconcile').status_code==200


def test_radio_delivery(customer):
    c,_,_=customer
    r=request(c,'POST','/orders',{'items':[{'id':6,'cantidad':1}],'direccion':'Direccion lejana 123, Santiago', 'lat':-33.4372,'lon':-70.6506},headers={'Idempotency-Key':str(uuid.uuid4())})
    assert r.status_code==422


def test_admin_clientes_y_proteccion_campo_direccion(customer,admin):
    c,_,cid=customer
    assert request(admin,'PUT','/profiles/'+cid,{'direccion':'Direccion corregida ficticia 234'}).status_code==200
    assert request(c,'GET','/me').json()['direccion']=='Direccion corregida ficticia 234'
    oid=order(c).json()['id']
    with client() as owner_client:
        login(owner_client,json.loads((R/'cuentas-demo.json').read_text())['owner'])
        r=request(owner_client,'POST','/graphql',{'query':'query($id:ID!){resumenPedido(id:$id){id direccion total}}','variables':{'id':oid}})
        assert r.status_code==200 and r.json()['data']['resumenPedido']['direccion'] is None and r.json().get('errors')


def test_promociones_con_fecha_controlada():
    # Prueba de regla de negocio con fecha explícita; no depende del día de ejecución.
    import subprocess,sys
    code='''
from datetime import datetime
from unittest.mock import patch
from backend.orders import price_items
postre={'id':11,'nombre':'Baklava','categoria':'Postres','precio':3900,'cantidad':3}
with patch('backend.orders.datetime') as clock:
    clock.now.return_value=datetime(2026,11,8,13,0)
    assert price_items([postre])[0]==7800
    clock.now.return_value=datetime(2026,11,7,13,0)
    assert price_items([postre])[0]==11700
    clock.now.return_value=datetime(2026,11,3,10,0)
    assert price_items([{'id':1,'nombre':'Shakshuka','categoria':'Desayunos','precio':6500,'cantidad':1}])[0]==5525
'''
    subprocess.run([sys.executable,'-c',code],env=dict(os.environ,SERVICE='orders'),cwd=ROOT,check=True)


def test_direccion_sin_coordenadas_y_sin_confiar_en_navegador(customer):
    c,_,_=customer
    def submit(address, **extras):
        return request(c,'POST','/orders',dict(items=[{'id':6,'cantidad':1}],direccion=address,**extras),headers={'Idempotency-Key':str(uuid.uuid4())})
    before=request(c,'GET','/orders').json()
    assert submit('Domicilio inexistente 987, Santiago').status_code==422
    assert submit('Servicio no disponible 123, Santiago').status_code==503
    assert submit('Direccion lejana 123, Santiago',lat=-33.4372,lon=-70.6506).status_code==422
    assert len(request(c,'GET','/orders').json())==len(before)
    response=submit('Calle cercana 123, Santiago')
    assert response.status_code==201,response.text
    # Un cambio de dirección con la misma clave no crea otro pedido.
    key=str(uuid.uuid4())
    body={'items':[{'id':6,'cantidad':1}],'direccion':'Calle cercana 123, Santiago'}
    first=request(c,'POST','/orders',body,headers={'Idempotency-Key':key})
    assert first.status_code==201,first.text
    body['direccion']='Servicio no disponible 123, Santiago'
    repeated=request(c,'POST','/orders',body,headers={'Idempotency-Key':key})
    assert repeated.status_code==201 and repeated.json()['id']==first.json()['id']
    page=c.get('/pedido.html').text
    assert 'id="lat"' not in page and 'id="lon"' not in page
    assert 'id="direccionPedido"' in page
