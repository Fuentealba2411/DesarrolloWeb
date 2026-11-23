"""Genera material local de prueba; nunca se debe subir .runtime a GitHub."""
from datetime import datetime,timedelta,timezone
import ipaddress
import os
import json
from pathlib import Path
import secrets
import sys
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT=Path(__file__).resolve().parents[1]
dest=Path(os.environ.get('RUNTIME_DIR',ROOT/'.runtime'))
if dest.exists() and (dest/'secrets.json').exists():
    print('Configuración existente conservada. No se cambian claves ni datos.');sys.exit(0)
dest.mkdir(mode=0o700,exist_ok=True)
names=['secrets','auth','clients','inventory','orders','payments','graphql','provider','gateway','operator']
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Mediterraneo Desarrollo')])
now=datetime.now(timezone.utc)
cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
      .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=365))
      .add_extension(x509.SubjectAlternativeName([x509.DNSName(n) for n in names+['localhost']]+[x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
      .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256()))
def private(k):return k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
(dest/'key.pem').write_text(private(key));(dest/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
jwtkey=rsa.generate_private_key(public_exponent=65537,key_size=2048)
values={'jwt_private':private(jwtkey),'jwt_public':jwtkey.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode(),'payment_hmac':secrets.token_urlsafe(40)}
tokens={n:secrets.token_urlsafe(40) for n in names}
acl={n:[] for n in names}
for n in ['auth','clients','inventory','orders','payments','graphql','gateway']:acl[n]=['jwt_public']
acl['auth']+=['jwt_private'];acl['payments']+=['payment_hmac'];acl['provider']+=['payment_hmac']
(dest/'secrets.json').write_text(json.dumps({'tokens':tokens,'values':values,'acl':acl}))
for n,t in tokens.items():(dest/f'{n}.token').write_text(t)
accounts={role:{'correo':role+'@example.test','clave':secrets.token_urlsafe(15)} for role in ['admin','owner','cashier','dispatch']}
(dest/'cuentas-demo.json').write_text(json.dumps(accounts,indent=2))
for p in dest.iterdir():p.chmod(0o600)
print('Configuración y certificado local creados. Cuentas de prueba: .runtime/cuentas-demo.json')
