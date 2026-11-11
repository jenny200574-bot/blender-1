# -*- coding: utf-8 -*-
"""Detector de faltantes que consulta Star + recetas_aprendidas ANTES de marcar FALTA.
Copia de via_b/faltantes.py con capa aprendida. US$0, sin IA.
Salida: faltantes_con_aprendidas.json (+ resumen). Rehacer esc-habitacion debe dar 0
faltantes a Argon (salvo excluidos como obj-rayo-confundidor)."""
from __future__ import annotations
import json, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
ESC = AQUI.parents[1] / 'escenario'
VIA = ESC / 'via_b'
N8N = Path('/workspace/fabricas/datos_n8n/objetos')
sys.path[:0] = [str(ESC / 'codigo'), str(AQUI)]
from ensamblar import dims_locales
import cargar as LIB

plan = json.loads((ESC / 'datos/plan_esc-habitacion.json').read_text(encoding='utf-8'))
val = json.loads((ESC / 'datos/validacion_star.json').read_text(encoding='utf-8'))
sost = {s['id'] for s in val['sostenidos_no_dibujados']}
r4b = {o['objeto_id']: o for o in json.loads((N8N / 'rama_4b.json').read_text(encoding='utf-8'))}
ADN = {'obj-candados-cofre': 'gdc-candados', 'obj-vocales': 'gdc-vocales', 'obj-papel-numeros': 'gdc-papel-numeros',
       'obj-pincel-magico': 'gdc-pincel-pintor', 'obj-visor-spark': 'gdc-visor', 'obj-cofre-dorado': 'gdc-cofre-abecedario'}
EXCLUIDOS = {'obj-rayo-confundidor': 'es un EFECTO (rayo de la pistola de Don Caos), no un objeto con forma; va por efectos, no por receta'}

def clave(it):
    return it.get('oid') or it['id']

def main(consultar_aprendidas=True):
    star_ids = LIB.ids_star()
    apr_ids = LIB.ids_aprendidas() if consultar_aprendidas else set()
    alias = LIB.alias_n8n() if consultar_aprendidas else {}
    por = {}
    for it in plan['objetos']:
        if it.get('estructura'):
            continue
        por.setdefault(clave(it), []).append(it)

    falt, cubiertos = [], []
    for k, its in por.items():
        it = its[0]
        if k in EXCLUIDOS:
            cubiertos.append({'objeto_id': k, 'capa': 'excluido', 'motivo': EXCLUIDOS[k]})
            continue
        fid = it.get('fid')
        if fid and fid in star_ids:
            cubiertos.append({'objeto_id': k, 'capa': 'star', 'fid': fid, 'aprox': bool(it.get('aprox'))})
            continue
        if consultar_aprendidas and k in alias and alias[k] in apr_ids:
            cubiertos.append({'objeto_id': k, 'capa': 'recetas_aprendidas', 'gid': alias[k]})
            continue
        # sin forma
        d = {'objeto_id': k, 'nombre': it.get('nombre') or k,
             'caja_m': dict(zip(('ancho', 'fondo', 'alto'), [round(v, 4) for v in dims_locales(it)])),
             'instancias': len(its), 'fid_plan': fid}
        falt.append(d)

    out = {
        'escenario': plan['escenario_id'],
        'consultar_aprendidas': consultar_aprendidas,
        'n_star': len(star_ids),
        'n_aprendidas': len(apr_ids),
        'cubiertos': cubiertos,
        'faltantes_para_argon': falt,
        'excluidos': EXCLUIDOS,
        'resumen': {
            'cubiertos_star': sum(1 for c in cubiertos if c['capa'] == 'star'),
            'cubiertos_aprendidas': sum(1 for c in cubiertos if c['capa'] == 'recetas_aprendidas'),
            'excluidos': sum(1 for c in cubiertos if c['capa'] == 'excluido'),
            'faltantes': len(falt),
        },
    }
    dest = AQUI / 'faltantes_con_aprendidas.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['resumen'], ensure_ascii=False))
    return out

if __name__ == '__main__':
    consultar = '--sin-aprendidas' not in sys.argv
    main(consultar_aprendidas=consultar)
