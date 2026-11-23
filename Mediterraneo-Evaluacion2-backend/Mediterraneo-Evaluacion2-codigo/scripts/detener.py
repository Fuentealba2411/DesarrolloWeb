"""Detiene únicamente los procesos de esta carpeta de Mediterráneo."""
import os
from pathlib import Path
import subprocess
import sys

import psutil

ROOT = Path(__file__).resolve().parents[1]


def project_process(process):
    try:
        if not process.name().lower().startswith('python'):
            return False
        arguments = [argument.replace('\\', '/').lower() for argument in process.cmdline()]
        same_directory = Path(process.cwd()).resolve() == ROOT
        launcher = any(argument == 'scripts/iniciar.py' or argument.endswith('/scripts/iniciar.py') for argument in arguments)
        server = any(arguments[index:index + 2] == ['-m', 'uvicorn']
                     and index + 2 < len(arguments) and arguments[index + 2].startswith('backend.')
                     for index in range(len(arguments)))
        own_command = launcher or server
        return process.pid != os.getpid() and same_directory and own_command
    except (psutil.Error, OSError):
        return False


def main():
    processes = [process for process in psutil.process_iter() if project_process(process)]
    if not processes:
        print('Mediterráneo ya está detenido en esta carpeta.')
        return
    if os.name == 'nt':
        for process in processes:
            if process.is_running():
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        for process in processes:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(processes, timeout=8)
        for process in alive:
            process.kill()
    print('Procesos de Mediterráneo detenidos. Los datos se conservan.')


if __name__ == '__main__':
    main()
