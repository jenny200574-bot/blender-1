#!/usr/bin/env python3
"""Prueba de aceptación CPU del constructor con un paquete sintético (sin material de cliente, sin GPU).

  python3 probar_constructor_sintetico.py --blender /opt/blender/actual/blender --salida /tmp/prueba_nueva \
      [--motor-referencia /ruta/motor_instalado]

Pasos: 1) orquestador solo_validar sobre paquetes/fixture_4g_v5 (paquete normalizado y sellado);
2) preflight_constructor; 3) constructor_final completo y validar_salida_constructor;
4) tope MOTOR_CAMARA_LIMITE_S, archivo de cancelación y SIGTERM: cada uno debe acabar BLOQUEADO
con su código, salida != 0 y sin escena.blend; 5) con --motor-referencia, revisión, trazas y
camara_v2.json idénticos a los del motor de referencia.
Límite: el fixture es un ave de 16 cuadros y 2 tomas. No mide el costo ni la geometría de la escena real.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[2]


def constructor(blender, motor, pk, out, extra_env=None, sigterm=False, limite=900):
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, **(extra_env or {}))
    cmd = [blender, '-b', '--disable-autoexec', '-t', '2', '--python-exit-code', '17', '-P', str(Path(motor) / 'motor' / 'constructor_final.py'), '--', str(pk), str(out)]
    with (out.parent / (out.name + '.log')).open('wb') as log:
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(out.parent))
        if sigterm:
            prog = out / 'progreso_worker.json'
            t0 = time.monotonic()
            while time.monotonic() - t0 < limite:
                if prog.is_file() and '"etapa": "' in prog.read_text(encoding='utf-8', errors='replace'):
                    break
                if p.poll() is not None:
                    break
                time.sleep(0.002)
            p.send_signal(signal.SIGTERM)
        try:
            return p.wait(timeout=limite)
        except subprocess.TimeoutExpired:
            p.kill()
            return p.wait()


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--blender', required=True)
    a.add_argument('--salida', required=True)
    a.add_argument('--motor-referencia')
    a = a.parse_args(argv)
    base = Path(a.salida)
    if base.exists():
        print(json.dumps({'error': 'la salida ya existe'}))
        return 2
    base.mkdir(parents=True)
    sys.path.insert(0, str(MOTOR / 'motor'))
    from orquestador import ejecutar
    import preflight_constructor as PF
    import validar_salida_constructor as VS
    res = {'blender': subprocess.run([a.blender, '--version'], capture_output=True, text=True).stdout.splitlines()[:1], 'pasos': {}}
    r = ejecutar(str(MOTOR / 'paquetes' / 'fixture_4g_v5' / 'entrada_escena.json'), str(base / 'validacion'), prueba_cpu=True, solo_validar=True)
    pk = base / 'validacion' / 'paquete_normalizado'
    res['pasos']['orquestador_solo_validar'] = {'estado': r['estado'], 'errores': len(r['errores'])}
    pf = PF.revisar(pk)
    res['pasos']['preflight'] = {'estado': pf['estado'], 'bloqueos': pf['bloqueos']}
    rc = constructor(a.blender, MOTOR, pk, base / 'normal')
    v = VS.validar(base / 'normal', pk)
    res['pasos']['constructor'] = {'rc': rc, 'validacion': v['ok'], 'motivos': v['motivos']}
    casos = {'tope': ({'MOTOR_CAMARA_LIMITE_S': '0.000001'}, False, 'CAMARA_TIEMPO_AGOTADO'),
             'cancelar': ({'MOTOR_CANCELAR_ARCHIVO': str(base / 'CANCELAR')}, False, 'CANCELADO'),
             'sigterm': ({}, True, 'CANCELADO')}
    (base / 'CANCELAR').write_text('', encoding='utf-8')
    for nombre, (env, term, codigo) in casos.items():
        rc = constructor(a.blender, MOTOR, pk, base / nombre, env, term)
        w = json.loads((base / nombre / 'worker_resultado.json').read_text(encoding='utf-8')) if (base / nombre / 'worker_resultado.json').is_file() else {}
        res['pasos'][nombre] = {'rc': rc, 'codigo': w.get('codigo'), 'etapa': w.get('etapa_en_curso'), 'blend': (base / nombre / 'escena.blend').exists(),
                                'ok': rc != 0 and w.get('estado') == 'BLOQUEADO' and w.get('codigo') == codigo and not (base / nombre / 'escena.blend').exists()}
    if a.motor_referencia:
        rc = constructor(a.blender, a.motor_referencia, pk, base / 'referencia')
        iguales = {}
        for f in ('revision_final.json', 'trazas_finales.json', 'auditoria_4g/camara_v2.json'):
            x = json.loads((base / 'normal' / f).read_text(encoding='utf-8'))
            y = json.loads((base / 'referencia' / f).read_text(encoding='utf-8'))
            if isinstance(x, dict):
                x.pop('interruptores', None)
                y.pop('interruptores', None)
            iguales[f] = x == y
        res['pasos']['referencia'] = {'rc': rc, 'iguales': iguales}
    ok = (res['pasos']['orquestador_solo_validar']['estado'] == 'VALIDADO' and pf['estado'] == 'APTO_PARA_CONSTRUIR'
          and res['pasos']['constructor']['rc'] == 0 and res['pasos']['constructor']['validacion']
          and all(res['pasos'][k]['ok'] for k in casos)
          and (not a.motor_referencia or all(res['pasos']['referencia']['iguales'].values())))
    res['ok'] = ok
    res['limite'] = 'fixture sintético de 16 cuadros; no sustituye la escena real ni el oro 23/23'
    (base / 'resultado_prueba.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False))
    shutil.rmtree(base / 'validacion' / 'paquete_normalizado' / '__pycache__', ignore_errors=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
