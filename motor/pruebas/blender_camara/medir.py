"""Lanza correr_etapa11_sintetica.py con tope de tiempo y mide memoria pico (CPU, sin GPU).

  python3 medir.py --blender /ruta/blender --motor /ruta/motor --salida /tmp/x --cuadros 48 --tomas 1 [--cortes 2] [--animado] [--limite-s 900]

Imprime una línea JSON con código de salida, segundos, RSS pico (MB) y el resumen de medidas.json.
Código 0 solo si Blender salió 0 y medidas.json dice TERMINADO.
"""
import argparse
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--blender', required=True)
    p.add_argument('--motor', required=True)
    p.add_argument('--salida', required=True)
    p.add_argument('--cuadros', type=int, required=True)
    p.add_argument('--tomas', type=int, default=1)
    p.add_argument('--cortes', type=int, default=2)
    p.add_argument('--limite-s', type=float, default=900)
    p.add_argument('--animado', action='store_true')
    a = p.parse_args(argv)
    out = Path(a.salida)
    if out.exists():
        print(json.dumps({'error': 'la salida ya existe; no se reutiliza', 'salida': str(out)}))
        return 2
    out.mkdir(parents=True)
    cmd = [a.blender, '-b', '--factory-startup', '-t', '2', '--python-exit-code', '17', '-P', str(AQUI / 'correr_etapa11_sintetica.py'),
           '--', a.motor, str(out), str(a.cuadros), str(a.tomas), str(a.cortes), '1' if a.animado else '0']
    t0 = time.monotonic()
    with (out / 'blender.log').open('wb') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            rc = proc.wait(timeout=a.limite_s)
            agotado = False
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait()
            agotado = True
    seg = round(time.monotonic() - t0, 2)
    rss_mb = round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1)
    med = out / ('medidas.json' if (out / 'medidas.json').is_file() else 'medidas_parcial.json')
    datos = json.loads(med.read_text(encoding='utf-8')) if med.is_file() else {}
    rep = datos.pop('reporte', {}) or {}
    res = {'rc': rc, 'tiempo_agotado': agotado, 'segundos': seg, 'rss_pico_mb': rss_mb, 'medidas': datos,
           'tomas': [{k: v for k, v in t.items() if k not in ('recorrido', 'camara')} for t in rep.get('tomas', [])]}
    print(json.dumps(res, ensure_ascii=False))
    return 0 if rc == 0 and not agotado and datos.get('estado') == 'TERMINADO' else 1


if __name__ == '__main__':
    sys.exit(main())
