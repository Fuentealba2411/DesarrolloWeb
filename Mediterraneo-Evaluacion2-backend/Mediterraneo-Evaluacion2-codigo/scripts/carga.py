"""Carga reproducible de lectura de catálogo y reportes; no es una proyección medida de producción."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import statistics
import time
import httpx
import psutil
ROOT=Path(__file__).resolve().parents[1]
R=Path(os.environ.get('RUNTIME_DIR',ROOT/'.runtime'))
base='https://127.0.0.1:8443'
accounts=json.loads((R/'cuentas-demo.json').read_text())
with httpx.Client(verify=str(R/'cert.pem'),trust_env=False) as c:
    r=c.post(base+'/api/auth/login',json=accounts['owner']);r.raise_for_status();cookies=dict(c.cookies)
processes=[]
for p in psutil.process_iter(['cmdline']):
    cmd=' '.join(p.info['cmdline'] or [])
    if 'uvicorn' in cmd and 'backend.' in cmd:
        try:
            if p.environ().get('RUNTIME_DIR')==str(R):
                p.cpu_percent();processes.append(p)
        except psutil.Error:pass
results=[]
def run(worker):
    records=[]
    with httpx.Client(verify=str(R/'cert.pem'),trust_env=False,timeout=30,cookies=cookies) as c:
        for i in range(20):
            route='/api/products' if i%2==0 else '/api/reports/sales'
            start=time.perf_counter()
            r=c.get(base+route)
            records.append({'ms':(time.perf_counter()-start)*1000,'status':r.status_code,'route':route})
    return records
start=time.perf_counter()
with ThreadPoolExecutor(max_workers=5) as pool:
    for records in pool.map(run,range(5)):results.extend(records)
duration=time.perf_counter()-start
memory=0;cpu=0
for p in processes:
    try:memory+=p.memory_info().rss;cpu+=p.cpu_percent()
    except psutil.Error:pass
lat=sorted(r['ms'] for r in results)
report={'tipo':'medición local de prueba, no tráfico real del restaurante','entorno':{'python':platform.python_version(),'plataforma':platform.system(),'cpu_logicas':psutil.cpu_count()},'concurrencia':5,'solicitudes':len(results),'duracion_s':round(duration,3),'p95_ms':round(lat[int(len(lat)*.95)-1],2),'throughput_rps':round(len(results)/duration,2),'errores':sum(r['status']!=200 for r in results),'rss_servicios_mib':round(memory/1024**2,2),'cpu_porcentaje_suma_procesos':round(cpu,2),'objetivo_de_equipo':{'p95_ms':1000,'errores':0},'advertencia':'CPU es promedio observado al final del intervalo; RSS es instantánea, no máximo. Incluye HTTPS. Datos ficticios del entorno temporal de integración.'}
(ROOT/'docs/resultados-carga.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print(json.dumps(report,indent=2,ensure_ascii=False))
assert report['errores']==0 and report['p95_ms']<1000
