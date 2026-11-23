"""Arranca un entorno temporal, ejecuta pruebas reales y lo detiene sin tocar tus datos."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import httpx
from direcciones_prueba import start_geocoder
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
with tempfile.TemporaryDirectory(prefix='mediterraneo-test-') as temp:
    geocoder=start_geocoder()
    env=dict(os.environ,RUNTIME_DIR=temp,GEOCODER_URL=f'http://127.0.0.1:{geocoder.server_port}/api/')
    log=open(ROOT/'docs/ejecucion-pruebas.log','w')
    process=subprocess.Popen([sys.executable,'scripts/iniciar.py'],env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
    try:
        for _ in range(80):
            if process.poll() is not None:raise RuntimeError('No pudo iniciar. Revisa docs/ejecucion-pruebas.log')
            try:
                with httpx.Client(verify=False,trust_env=False) as c:
                    if c.get('https://127.0.0.1:8443/health').status_code==200:break
            except httpx.RequestError:pass
            time.sleep(0.25)
        else:raise RuntimeError('No respondió el gateway.')
        result=subprocess.run([sys.executable,'-m','pytest','-q','tests','--junitxml=docs/resultados-pruebas.xml'],env=env)
        if result.returncode:
            sys.exit(result.returncode)
        subprocess.run([sys.executable,'scripts/prueba_resiliencia.py'],env=env,check=True)
        if '--navegador' in sys.argv:
            subprocess.run(['node','scripts/prueba_navegador.cjs'],env=env,check=True)
        subprocess.run([sys.executable,'scripts/carga.py'],env=env,check=True)
        # Reinicio real de los nueve procesos, conservando los mismos archivos de datos.
        process.send_signal(signal.CTRL_BREAK_EVENT if os.name=='nt' else signal.SIGINT)
        process.wait(timeout=15)
        process=subprocess.Popen([sys.executable,'scripts/iniciar.py'],env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
        for _ in range(80):
            if process.poll() is not None:raise RuntimeError('El reinicio falló. Revisa docs/ejecucion-pruebas.log')
            try:
                with httpx.Client(verify=False,trust_env=False) as c:
                    if c.get('https://127.0.0.1:8443/health').status_code==200:break
            except httpx.RequestError:pass
            time.sleep(.25)
        else:raise RuntimeError('El gateway no respondió después del reinicio.')
        import json
        checkpoint=json.loads((Path(temp)/'checkpoint.json').read_text())
        with httpx.Client(verify=str(Path(temp)/'cert.pem'),trust_env=False) as c:
            c.cookies.set('session',checkpoint['session'],domain='127.0.0.1',path='/')
            r=c.get('https://127.0.0.1:8443/api/orders/'+checkpoint['order_id'])
            assert r.status_code==200 and r.json()['status']=='entregado'
        (ROOT/'docs/resultados-persistencia.json').write_text(json.dumps({'reinicio':'nueve procesos detenidos y reiniciados','pedido_entregado_conservado':True,'sesion_conservada_hasta_expiracion':True},indent=2))
        print('Persistencia verificada después del reinicio completo.')
        sys.exit(0)
    finally:
        process.send_signal(signal.CTRL_BREAK_EVENT if os.name=='nt' else signal.SIGINT)
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill()
        log.close()
        geocoder.shutdown()
        geocoder.server_close()
