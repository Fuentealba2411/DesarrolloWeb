"""Inicia y detiene los nueve servicios locales, incluidos sus procesos hijos."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('PYTHONUTF8', '1')
RUNTIME = Path(os.environ.get('RUNTIME_DIR', ROOT / '.runtime'))
SERVICES = {
    'secrets': ('secrets_service', 8500),
    'auth': ('auth', 8501),
    'clients': ('clients', 8502),
    'inventory': ('inventory', 8503),
    'orders': ('orders', 8504),
    'payments': ('payments', 8505),
    'graphql': ('graphql_gateway', 8506),
    'provider': ('provider', 8507),
    'gateway': ('gateway', 8443),
}


def check_ports():
    for _, port in SERVICES.values():
        with socket.socket() as probe:
            if os.name != 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                raise RuntimeError(f'El puerto {port} está ocupado. Detén la instancia anterior antes de iniciar otra.') from None


def wait_ready(process, port):
    with httpx.Client(verify=str(RUNTIME / 'cert.pem'), trust_env=False, timeout=1) as client:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError(f'El servicio del puerto {port} terminó durante el arranque.')
            try:
                if client.get(f'https://127.0.0.1:{port}/health').status_code == 200:
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.2)
    raise RuntimeError(f'El servicio del puerto {port} no respondió a tiempo.')


def stop_services(processes):
    # En Windows el ejecutable de venv puede crear otro python.exe.
    # taskkill /T alcanza también ese proceso hijo y libera su puerto.
    for process in reversed(processes):
        if os.name == 'nt':
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 5
    while any(process.poll() is None for process in processes) and time.monotonic() < deadline:
        time.sleep(0.1)
    for process in processes:
        if process.poll() is None:
            if os.name == 'nt':
                process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        process.wait()


def main():
    processes = []
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
    try:
        check_ports()
        subprocess.run([sys.executable, 'scripts/configurar.py'], check=True)
        subprocess.run([sys.executable, 'scripts/sembrar.py'], check=True)
        for name, (module, port) in SERVICES.items():
            options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen([
                sys.executable, '-m', 'uvicorn', f'backend.{module}:app',
                '--host', '127.0.0.1', '--port', str(port),
                '--ssl-keyfile', str(RUNTIME / 'key.pem'),
                '--ssl-certfile', str(RUNTIME / 'cert.pem'), '--no-access-log',
            ], env=dict(os.environ, SERVICE=name), **options)
            processes.append(process)
            wait_ready(process, port)
        print('\nMediterráneo: https://localhost:8443\nLos nueve servicios están listos. Ctrl+C detiene el sistema.\n', flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise RuntimeError('Un servicio terminó. Revisa su mensaje anterior.')
    except KeyboardInterrupt:
        print('\nDeteniendo Mediterráneo…', flush=True)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f'No se pudo mantener el sistema en ejecución: {error}', file=sys.stderr)
        return 1
    finally:
        stop_services(processes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
