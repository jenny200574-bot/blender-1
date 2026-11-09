#!/usr/bin/env python3
"""Valida la carpeta de salida de constructor_final.py. Solo lectura.

  python3 motor/validar_salida_constructor.py SALIDA [--paquete PAQUETE]

OK (código 0) solo si están todos: worker_resultado CONSTRUIDO_REVISADO, escena.blend con
cabecera de Blender y el mismo SHA-256 del recibo, revision_final sin errores, las etapas
del worker completas y, con SB_4G, camara_v2.json sin tomas bloqueadas ni faltantes.
Un código de salida 0 de Blender o un log con "OK" no bastan. No aprueba producción.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ETAPAS = ('6', '5', '8', 'anclas', '7', '9', '10', '12', '11', '13')
CABECERAS = (b'BLENDER', b'\x28\xb5\x2f\xfd', b'\x1f\x8b')


def _sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def _json(p, motivos, nombre):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except FileNotFoundError:
        motivos.append('falta ' + nombre)
    except (OSError, ValueError) as exc:
        motivos.append(nombre + ' ilegible: ' + str(exc))
    return None


def validar(salida, paquete=None):
    out = Path(salida)
    motivos = []
    w = _json(out / 'worker_resultado.json', motivos, 'worker_resultado.json')
    if w is not None and w.get('estado') != 'CONSTRUIDO_REVISADO':
        motivos.append('worker_resultado estado=%s codigo=%s etapa=%s: %s' % (w.get('estado'), w.get('codigo'), w.get('etapa_en_curso'), str(w.get('mensaje'))[:300]))
    blend = out / 'escena.blend'
    if not blend.is_file():
        motivos.append('falta escena.blend')
    else:
        with blend.open('rb') as f:
            cab = f.read(7)
        if not any(cab.startswith(c) for c in CABECERAS):
            motivos.append('escena.blend no tiene cabecera de archivo Blender')
        if blend.stat().st_size == 0:
            motivos.append('escena.blend vacío')
        if w is not None and w.get('estado') == 'CONSTRUIDO_REVISADO' and w.get('blend_sha256') != _sha(blend):
            motivos.append('escena.blend no coincide con blend_sha256 del recibo')
    if (out / 'escena_parcial_guardando.blend').exists():
        motivos.append('quedó escena_parcial_guardando.blend: el guardado no terminó')
    r = _json(out / 'revision_final.json', motivos, 'revision_final.json')
    if r is not None and (r.get('all_passed') is not True or r.get('errors')):
        motivos.append('revision_final no pasó: %d errores' % len(r.get('errors') or []))
    e = _json(out / 'etapas_worker.json', motivos, 'etapas_worker.json')
    if e is not None:
        faltan = [k for k in ETAPAS if k not in e]
        if faltan:
            motivos.append('etapas sin recibo: ' + ', '.join(faltan))
    prog = out / 'progreso_worker.json'
    if prog.is_file():
        p = _json(prog, motivos, 'progreso_worker.json')
        if p is not None and p.get('estado') != 'TERMINADO':
            motivos.append('progreso_worker estado=%s en etapa %s' % (p.get('estado'), p.get('etapa')))
    sb4g = None
    if paquete:
        d = _json(Path(paquete) / 'entrada_escena.json', motivos, 'entrada_escena.json del paquete')
        sb4g = bool(d and (d.get('camera') or {}).get('resolver') == 'SB_4G')
    cam = out / 'auditoria_4g' / 'camara_v2.json'
    if sb4g or (sb4g is None and (out / 'auditoria_4g').is_dir()):
        c = _json(cam, motivos, 'auditoria_4g/camara_v2.json')
        if c is not None:
            if (c.get('resumen') or {}).get('bloqueada'):
                motivos.append('tomas de cámara bloqueadas: %s' % c['resumen']['bloqueada'])
            if c.get('faltantes'):
                motivos.append('cámara con %d faltantes' % len(c['faltantes']))
            if c.get('production_approved') is not False:
                motivos.append('camara_v2.json no debe traer aprobación de producción')
    return {'ok': not motivos, 'salida': str(out), 'motivos': motivos, 'production_approved': False,
            'blend_sha256': _sha(blend) if blend.is_file() else None}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('salida')
    p.add_argument('--paquete')
    a = p.parse_args(argv)
    r = validar(a.salida, a.paquete)
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
