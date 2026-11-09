"""Exporta los contratos reales sin abrir documentación en los servicios privados."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
subprocess.run([sys.executable,'scripts/configurar.py'],check=True)
modules={'auth':'auth','clients':'clients','inventory':'inventory','orders':'orders','payments':'payments','graphql':'graphql_gateway'}
for name,module in modules.items():
    code=f"import json;from backend.{module} import app;from pathlib import Path;Path('docs/contratos/{name}.openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding='utf-8')"
    subprocess.run([sys.executable,'-c',code],env=dict(os.environ,SERVICE=name,PYTHONUTF8='1'),check=True)
print('Contratos OpenAPI exportados. El schema GraphQL está en backend/schema.graphql.')
