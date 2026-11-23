"""Simula la consola independiente de los proveedores, fuera de la aplicación."""
import argparse,json
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Proveedor de prueba: sin pagos ni correos reales')
p.add_argument('accion',choices=['correos','aprobar']);p.add_argument('payment_id',nargs='?');a=p.parse_args()
with httpx.Client(verify=str(ROOT/'.runtime/cert.pem'),trust_env=False,headers={'X-Service-Key':(ROOT/'.runtime/operator.token').read_text()}) as c:
    if a.accion=='correos':r=c.get('https://127.0.0.1:8507/operator/mailbox')
    else:
        if not a.payment_id:p.error('Indica payment_id')
        r=c.post('https://127.0.0.1:8507/operator/approve/'+a.payment_id)
    print(json.dumps(r.json(),ensure_ascii=False,indent=2))
    r.raise_for_status()
