"""Rotación local con servicios detenidos. Conserva datos y cuentas demo."""
import json
import os
from pathlib import Path
import secrets
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
ROOT=Path(__file__).resolve().parents[1]
r=Path(os.environ.get('RUNTIME_DIR',ROOT/'.runtime'))
try:
    httpx.get('https://127.0.0.1:8500/health',verify=False,trust_env=False,timeout=1)
except httpx.RequestError:pass
else:raise SystemExit('Detén primero los servicios con Ctrl+C.')
p=r/'secrets.json';config=json.loads(p.read_text())
for service in config['tokens']:
    value=secrets.token_urlsafe(40);config['tokens'][service]=value;(r/(service+'.token')).write_text(value)
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
config['values']['jwt_private']=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
config['values']['jwt_public']=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
config['values']['payment_hmac']=secrets.token_urlsafe(40)
p.write_text(json.dumps(config))
for f in r.glob('*.token'):f.chmod(0o600)
p.chmod(0o600)
print('Identidades, firma JWT y firma de pagos rotadas. Las sesiones anteriores dejan de ser válidas. Reinicia el sistema.')
