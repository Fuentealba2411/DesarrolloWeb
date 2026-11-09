"""Agregación privada orders + inventory sin acceso a sus bases de datos."""
import asyncio
from pathlib import Path
from graphql import build_schema, parse, validate, graphql, GraphQLError
from graphql.language.ast import FieldNode, OperationDefinitionNode
from fastapi import Request
from backend.common import app_base,fail,peer,user,bearer,call

app=app_base('GraphQL Gateway privado')
schema=build_schema(Path(__file__).with_name('schema.graphql').read_text())


def limits(document):
    count=0
    roots=0
    def walk(selection,depth):
        nonlocal count,roots
        if depth>4:fail(400,'Profundidad GraphQL máxima: 4.')
        for node in selection.selections:
            if not isinstance(node,FieldNode):fail(400,'Este contrato no admite fragments.')
            count+=1
            if depth==1:roots+=1
            if node.name.value.startswith('__'):fail(400,'Introspección no habilitada en este contrato.')
            if node.selection_set:walk(node.selection_set,depth+1)
    if len(document.definitions)!=1:fail(400,'Envía una sola operación.')
    for definition in document.definitions:
        if not isinstance(definition,OperationDefinitionNode):fail(400,'Operación inválida.')
        walk(definition.selection_set,1)
    if count>50 or roots>2:fail(400,'Costo GraphQL máximo: 50 campos y dos selecciones raíz.')


async def aggregate(orders,token):
    ids=list({item['id'] for o in orders for item in o['items']})
    warning=None
    try:
        products=await call('inventory','POST','/internal/batch',{'ids':ids})
        lookup={p['id']:p for p in products}
    except Exception:
        lookup={};warning='Inventario temporalmente no disponible. Se conserva el detalle histórico.'
    return [dict(id=o['id'],estado=o['status'],total=o['total'],direccion=o.get('address'),
                 lineas=[dict(item,descripcionActual=lookup.get(item['id'],{}).get('descripcion')) for item in o['items']],aviso=warning)
            for o in orders]


async def resumen(_root,info,id):
    request=info.context['request']
    o=await call('orders','GET','/orders/'+id,token=bearer(request))
    return (await aggregate([o],bearer(request)))[0]


async def mine(_root,info,limit=20,offset=0):
    if not 1<=limit<=30 or offset<0:raise GraphQLError('Paginación: limit de 1 a 30, offset no negativo.')
    request=info.context['request']
    orders=await call('orders','GET',f'/orders?limit={limit}&offset={offset}',token=bearer(request))
    return await aggregate(orders,bearer(request))


def address(source,info):
    if info.context['user']['role'] not in ('client','admin','dispatch','cashier'):
        raise GraphQLError('El perfil no puede consultar direcciones.')
    return source.get('direccion')


schema.get_type('Query').fields['resumenPedido'].resolve=resumen
schema.get_type('Query').fields['misPedidos'].resolve=mine
schema.get_type('ResumenPedido').fields['direccion'].resolve=address


@app.post('/graphql')
async def endpoint(request:Request):
    await peer(request,['gateway']);u=await user(request)
    d=await request.json();query=d.get('query','')
    if not isinstance(query,str) or len(query)>6000:fail(400,'Consulta demasiado extensa.')
    try:document=parse(query)
    except GraphQLError:fail(400,'Sintaxis GraphQL inválida.')
    limits(document)
    errors=validate(schema,document)
    if errors:fail(400,'Consulta no válida para el schema.')
    try:
        result=await asyncio.wait_for(graphql(schema,query,variable_values=d.get('variables'),
                     operation_name=d.get('operationName'),context_value={'request':request,'user':u}),timeout=10)
    except asyncio.TimeoutError:fail(504,'Se agotó el plazo de la consulta.')
    output={'data':result.data}
    if result.errors:output['errors']=[{'message':e.message if not e.original_error else 'Acceso denegado o dependencia no disponible.'} for e in result.errors]
    return output
