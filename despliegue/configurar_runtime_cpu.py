#!/usr/bin/env python3
"""Comprueba un Python ya instalado y, solo con --aplicar, cambia numeric_python.

No crea symlink, no llama a pip, no toca avance10 ni otras claves del JSON.
La ruta la pasa quien ejecuta. Este programa no elige un intérprete por su cuenta.
"""
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

RUTA_MUERTA = '/workspace/MOTOR_v9_desde_PC/v9_universal_calidad_20261106/entorno_cpu/bin/python'
SONDA = (
    'import json\n'
    'out={"numpy":None,"scipy":None,"sparse":False,"splu":False}\n'
    'try:\n'
    ' import numpy\n'
    ' out["numpy"]=numpy.__version__\n'
    'except Exception as exc:\n'
    ' out["numpy_error"]=type(exc).__name__+": "+str(exc)\n'
    'try:\n'
    ' import scipy\n'
    ' from scipy import sparse\n'
    ' from scipy.sparse.linalg import splu\n'
    ' out["scipy"]=scipy.__version__\n'
    ' out["sparse"]=sparse.__name__=="scipy.sparse"\n'
    ' out["splu"]=callable(splu)\n'
    'except Exception as exc:\n'
    ' out["scipy_error"]=type(exc).__name__+": "+str(exc)\n'
    'print(json.dumps(out))\n'
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def es_regular(path):
    path = Path(path)
    if path.is_symlink():
        return False
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def exigir_config(path):
    path = Path(path).resolve()
    texto = str(path)
    if 'avance10_20261108' in texto or 'v9_universal_calidad' in texto or texto.endswith(RUTA_MUERTA):
        raise SystemExit('Config prohibida: ' + texto)
    if not texto.endswith('config/runtime_cpu.json'):
        raise SystemExit('Solo se edita config/runtime_cpu.json')
    if path.is_symlink() or not es_regular(path):
        raise SystemExit('La config no es un archivo regular')
    return path


def evaluar(interprete):
    path = Path(interprete)
    if str(path) == RUTA_MUERTA or not path.exists():
        return {'ok': False, 'motivo': 'no existe'}
    if path.is_symlink():
        return {'ok': False, 'motivo': 'es symlink; no se guarda un enlace'}
    if not es_regular(path) or not os.access(path, os.X_OK):
        return {'ok': False, 'motivo': 'no es ejecutable regular'}
    try:
        proc = subprocess.run([str(path), '-c', SONDA], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'motivo': type(exc).__name__}
    if proc.returncode != 0:
        return {'ok': False, 'motivo': 'salida ' + str(proc.returncode), 'stderr': proc.stderr[-400:]}
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {'ok': False, 'motivo': 'la sonda no devolvió JSON'}
    ok = isinstance(data.get('numpy'), str) and isinstance(data.get('scipy'), str) and data.get('sparse') is True and data.get('splu') is True
    data['ok'] = ok
    if not ok:
        data['motivo'] = 'falta numpy, scipy, scipy.sparse o splu'
    return data


def jobs_pendientes(etapas):
    if not etapas:
        return None
    data = json.loads(Path(etapas).read_text(encoding='utf-8'))
    for etapa in data:
        if etapa.get('handler') == 'pulida':
            return (etapa.get('artefacto') or {}).get('retarget_jobs_pending')
    return None


def aplicar(config, elegido):
    original = config.read_bytes()
    previo = hashlib.sha256(original).hexdigest()
    data = json.loads(original.decode('utf-8'))
    if not isinstance(data, dict) or 'numeric_python' not in data:
        raise SystemExit('El JSON no tiene numeric_python')
    antes = {k: v for k, v in data.items()}
    data['numeric_python'] = str(elegido)
    if any(data[k] != antes[k] for k in antes if k != 'numeric_python'):
        raise SystemExit('Iba a cambiar otra clave; no se escribió')
    nuevo = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    respaldo = config.with_name('runtime_cpu.json.bak.' + previo[:12])
    if respaldo.exists():
        raise SystemExit('El respaldo ya existe: ' + respaldo.name)
    parcial = config.with_name('runtime_cpu.json.parcial')
    parcial.write_bytes(nuevo)
    os.replace(parcial, config)
    if config.is_symlink() or sha256(config) != hashlib.sha256(nuevo).hexdigest():
        raise SystemExit('La escritura no quedó verificada')
    respaldo.write_bytes(original)
    return previo, hashlib.sha256(nuevo).hexdigest(), respaldo


def main(argv=None):
    parser = argparse.ArgumentParser(description='Elige un Python verificado para runtime_cpu.json del stage')
    parser.add_argument('--config', required=True)
    parser.add_argument('--candidato', action='append', required=True)
    parser.add_argument('--preflight-etapas')
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args(argv)
    config = exigir_config(args.config)
    data = json.loads(config.read_text(encoding='utf-8'))
    actual = data.get('numeric_python')
    informes = []
    elegido = None
    for candidato in args.candidato:
        informe = evaluar(candidato)
        informe['ruta'] = candidato
        informes.append(informe)
        if elegido is None and informe.get('ok'):
            elegido = candidato
    pendientes = jobs_pendientes(args.preflight_etapas) if args.preflight_etapas else None
    print(json.dumps({
        'numeric_python_actual': actual,
        'existe_actual': Path(str(actual)).is_file() if isinstance(actual, str) else False,
        'se_ejecuta_solo_si_hay_job_sin_cache': True,
        'retarget_jobs_pending': pendientes,
        'candidatos': informes,
        'elegido': elegido,
        'production_approved': False,
    }, ensure_ascii=False))
    if elegido is None:
        print('RECHAZADO ningún intérprete pasó numpy+scipy+splu')
        return 2
    if not args.aplicar:
        print('SECO no se cambió la config')
        return 0
    if actual == elegido:
        print('SECO numeric_python ya es el intérprete verificado')
        return 0
    previo, posterior, respaldo = aplicar(config, elegido)
    recibo = {
        'production_approved': False,
        'campo': 'numeric_python',
        'antes': actual,
        'despues': elegido,
        'sha256_antes': previo,
        'sha256_despues': posterior,
        'respaldo': respaldo.name,
        'otras_claves_intactas': True,
        'oro_no_lee_este_archivo': True,
        'preflight_solo_validar_no_lee_este_archivo': True,
    }
    (config.parent / 'runtime_cpu_recibo.json').write_text(json.dumps(recibo, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('APLICADO', posterior)
    return 0


if __name__ == '__main__':
    sys.exit(main())
