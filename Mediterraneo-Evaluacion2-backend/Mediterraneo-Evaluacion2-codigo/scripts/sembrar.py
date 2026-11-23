"""Crea cuentas de personal ficticias; no incluye credenciales en el código."""
import json
import os
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['SERVICE']='auth'
from backend.auth import HASHER
from backend.common import db
accounts=json.loads((Path(os.environ.get('RUNTIME_DIR',ROOT/'.runtime'))/'cuentas-demo.json').read_text())
with db() as c:
    for role,data in accounts.items():
        c.execute('INSERT OR IGNORE INTO users(id,email,hash,role,verified) VALUES(?,?,?,?,1)',(str(uuid.uuid4()),data['correo'],HASHER.hash(data['clave']),role))
print('Cuentas de personal creadas. No se modifican las ya existentes.')
