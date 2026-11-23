"""Única entrada externa. Lista de rutas permitidas y cookie segura de sesión."""
import hmac
import re
import secrets
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.common import ROOT,app_base,fail,call,CLIENT,url,BOOTSTRAP,CORRELATION

app=app_base('API Gateway Mediterráneo')
# Método, ruta externa, sistema, ruta interna, autenticación requerida.
ROUTES=[
 ('POST',r'/auth/(register|login|verify)','auth',None,False),
 ('POST',r'/auth/(logout|resend)','auth',None,True),
 ('GET',r'/users','auth','/users',True),('PUT',r'/users/[^/]+','auth',None,True),
 ('GET',r'/products','inventory','/products',False),
 ('GET',r'/admin/products','inventory',None,True),
 ('POST',r'/admin/products','inventory',None,True),
 ('PUT',r'/admin/products/[0-9]+','inventory',None,True),
 ('DELETE',r'/admin/products/[0-9]+','inventory',None,True),
 ('GET',r'/me','clients',None,True),('PUT',r'/me','clients',None,True),
 ('GET',r'/profiles','clients',None,True),('PUT',r'/profiles/[^/]+','clients',None,True),
 ('POST',r'/contact','clients',None,False),('GET',r'/contact','clients',None,True),
 ('GET',r'/reservations','clients',None,True),('POST',r'/reservations','clients',None,True),
 ('PUT',r'/reservations/[^/]+','clients',None,True),
 ('POST',r'/orders','orders',None,True),('GET',r'/orders','orders',None,True),
 ('GET',r'/orders/[^/]+','orders',None,True),
 ('GET',r'/orders/[^/]+/(receipt|dispatch)','orders',None,True),
 ('POST',r'/orders/[^/]+/(cancel|receipt-email)','orders',None,True),
 ('PUT',r'/orders/[^/]+/status','orders',None,True),
 ('GET',r'/reports/sales','orders',None,True),('POST',r'/admin/reconcile','orders',None,True),
 ('POST',r'/payments','payments',None,True),
 ('POST',r'/graphql','graphql',None,True),
]


@app.api_route('/api/{path:path}',methods=['GET','POST','PUT','DELETE','PATCH'])
async def proxy(path:str,request:Request):
    path='/'+path
    match=next((r for r in ROUTES if r[0]==request.method and re.fullmatch(r[1],path)),None)
    if not match:fail(404,'Ruta o verbo no permitido.')
    token=request.cookies.get('session','')
    if match[4] and not token:fail(401,'Inicia sesión para continuar.')
    if request.method!='GET':
        origin=request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            fail(403,'Origen no autorizado.')
        if token:
            csrf=request.cookies.get('csrf','')
            if not csrf or not hmac.compare_digest(csrf,request.headers.get('x-csrf-token','')):
                fail(403,'Protección CSRF: recarga la página e inténtalo de nuevo.')
    internal=match[3] or (path.removeprefix('/auth') if path.startswith('/auth/') else path)
    headers={'X-Service-Key':BOOTSTRAP,'X-Correlation-ID':CORRELATION.get(),'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    if 'idempotency-key' in request.headers:headers['Idempotency-Key']=request.headers['idempotency-key']
    # No se propagan X-User, X-Role, Authorization ni destinos aportados por el navegador.
    query=str(request.url.query)
    try:r=await CLIENT.request(request.method,url(match[2])+internal+('?' + query if query else ''),content=await request.body(),headers=headers)
    except Exception:fail(503,'Servicio no disponible. Puedes reintentar sin perder el carrito.')
    try:data=r.json()
    except ValueError:data={'detail':'Respuesta de servicio inválida.'}
    # Pydantic puede incluir input en sus errores: no reflejar contraseñas ni otros datos.
    if r.status_code==422 and not isinstance(data.get('detail'),str):
        data={'detail':'Datos inválidos. Revisa los campos y sus límites.'}
    if r.status_code>=500:data={'detail':'Dependencia no disponible o fallo interno; reintenta.'}
    if path=='/auth/login' and r.status_code==200:
        access=data.pop('access_token')
        response=JSONResponse(data,status_code=r.status_code)
        response.set_cookie('session',access,httponly=True,secure=True,samesite='strict',max_age=1800)
        response.set_cookie('csrf',secrets.token_urlsafe(32),secure=True,samesite='strict',max_age=1800)
    else:response=JSONResponse(data,status_code=r.status_code)
    if path=='/auth/logout' and r.status_code==200:
        response.delete_cookie('session');response.delete_cookie('csrf')
    return response


app.mount('/',StaticFiles(directory=ROOT/'frontend',html=True),name='frontend')
