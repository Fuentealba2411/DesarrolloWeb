"""Inyecta fallos reales de conexión en procesos privados adicionales de prueba."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import httpx
ROOT=Path(__file__).resolve().parents[1];R=Path(os.environ.get('RUNTIME_DIR',ROOT/'.runtime'))
key=(R/'gateway.token').read_text();token=json.loads((R/'checkpoint.json').read_text())['session']
headers={'X-Service-Key':key,'Authorization':'Bearer '+token}
results=[]

def alternative(service,module,port,extra,fn):
    env=dict(os.environ,SERVICE=service,**extra)
    with open(R/(service+'-fault.log'),'w') as log:
        p=subprocess.Popen([sys.executable,'-m','uvicorn','backend.'+module+':app','--host','127.0.0.1','--port',str(port),'--ssl-keyfile',str(R/'key.pem'),'--ssl-certfile',str(R/'cert.pem'),'--no-access-log'],env=env,stdout=log,stderr=log)
        try:
            with httpx.Client(verify=str(R/'cert.pem'),trust_env=False,timeout=20,headers=headers) as c:
                for _ in range(50):
                    try:
                        if c.get(f'https://127.0.0.1:{port}/health').status_code==200:break
                    except httpx.RequestError:time.sleep(.1)
                fn(c,f'https://127.0.0.1:{port}')
        finally:p.terminate();p.wait(timeout=10)

def graphql_failure(c,base):
    oid=json.loads((R/'checkpoint.json').read_text())['order_id']
    r=c.post(base+'/graphql',json={'query':'query($id:ID!){resumenPedido(id:$id){id total aviso lineas{nombre descripcionActual}}}','variables':{'id':oid}})
    assert r.status_code==200,r.text
    d=r.json()['data']['resumenPedido'];assert d['aviso'] and d['total']==9800 and d['lineas'][0]['descripcionActual'] is None
    results.append({'prueba':'inventory inaccesible durante agregación','resultado':'detalle histórico conservado, descripción actual nula y aviso explícito'})

def secrets_failure(c,base):
    r=c.get(base+'/products');assert r.status_code==503
    results.append({'prueba':'administrador de secretos inaccesible','resultado':'503; acceso cerrado, sin secretos de respaldo incrustados'})

alternative('graphql','graphql_gateway',8606,{'INVENTORY_URL':'https://127.0.0.1:1'},graphql_failure)
alternative('inventory','inventory',8603,{'SECRETS_URL':'https://127.0.0.1:1'},secrets_failure)
with httpx.Client(verify=str(R/'cert.pem'),trust_env=False,timeout=20) as browser:
    browser.cookies.set('session',token,domain='127.0.0.1',path='/');browser.cookies.set('csrf','prueba',domain='127.0.0.1',path='/')
    stock=next(p['stock'] for p in browser.get('https://127.0.0.1:8443/api/products').json() if p['id']==9)
    r=browser.post('https://127.0.0.1:8443/api/orders',json={'items':[{'id':9,'cantidad':1}],'direccion':'Direccion ficticia 123','lat':-33.4372,'lon':-70.6506},headers={'X-CSRF-Token':'prueba','Idempotency-Key':str(uuid.uuid4())});assert r.status_code==201,r.text
    oid=r.json()['id']
    def cancellation_failure(c,base):
        r=c.post(base+'/orders/'+oid+'/cancel',json={'motivo':'Prueba de recuperación'});assert r.status_code==503,r.text
    alternative('orders','orders',8604,{'PAYMENTS_URL':'https://127.0.0.1:1'},cancellation_failure)
    assert browser.get('https://127.0.0.1:8443/api/orders/'+oid).json()['status']=='cancelando'
    account=json.loads((R/'cuentas-demo.json').read_text())['admin']
    browser.post('https://127.0.0.1:8443/api/auth/login',json=account,headers={'X-CSRF-Token':'prueba'}).raise_for_status()
    csrf=browser.cookies.get('csrf')
    r=browser.post('https://127.0.0.1:8443/api/admin/reconcile',headers={'X-CSRF-Token':csrf});assert r.status_code==200,r.text
    assert browser.get('https://127.0.0.1:8443/api/orders/'+oid).json()['status']=='cancelado'
    assert next(p['stock'] for p in browser.get('https://127.0.0.1:8443/api/products').json() if p['id']==9)==stock
    results.append({'prueba':'payments caído durante anulación','resultado':'estado cancelando persistente; reconciliación completa anulación y devuelve stock sin duplicarlo'})
(ROOT/'docs/resultados-resiliencia.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('Resiliencia: tres fallos de dependencias verificados.')
