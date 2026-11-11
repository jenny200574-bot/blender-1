#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 112 (t305u) — cubo 01 con EVENTOS muy detallados (beats) para el video gris 3D (02v). Genérico.
Reusa TODO el 01 o109 (pedido, pago con guarda, validación de palabras/cámaras/parámetros) y le suma: prompt/esquema o112 (eventos +
pose por toma) y la validación de eventos_o112 (palabras conocidas, sin números en palabras, solo latino, puntos dentro del set,
sin teletransportes, cámaras del molde, citas del guion). Contradicción = rechazo. Pago: igual que o109 (HABILITAR_PAGO_01 + --correr --ok --aprobado)."""
import json, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / 'poses_o110'))
import cubo01_o109 as C1, paso01_dirigir as DI, eventos_o112 as EV, palabras_pose as PP
_CFG0 = DI._cfg
def _cfg():
    c = dict(_CFG0()); c['prompt'] = 'prompts_01/dirigir_escena_o112.txt'; c['esquema'] = 'prompts_01/dirigir_escena_esquema_o112.json'; return c
DI._cfg = _cfg
_VAL109 = C1.validar
_GUION = {'txt': None}
def poses_lista(): return sorted(set(PP.palabras().values()))
def validar(K, obj, e, P):
    C, err = _VAL109(K, obj, e, P)
    for t in obj.get('tomas') or []:
        for x in ((t.get('palabras') or {}).get('por_personaje') or []):
            if isinstance(x, dict): err += PP.validar_toma(f"tomas {t.get('id')}", x.get('id'), x)
    L = P['set']['floor_bounds'] or {}
    ctx = {'poses': PP.palabras(), 'camaras': set(P['set'].get('all_camera_names') or []), 'objetos': {o['name'] for o in P['set']['objects']},
           'limites': [L['x'][0], L['x'][1], L['y'][0], L['y'][1]] if L else None, 'margen': float(_cfg()['margen_fuera_m']), 'guion': _GUION['txt']}
    ev, e2, av = EV.validar(obj.get('eventos'), C, ctx)
    err += e2; C['avisos_codigo'] = (C.get('avisos_codigo') or []) + av
    if not _GUION['txt']: C['avisos_codigo'].append('sin guion completo: las citas no se pudieron comprobar')
    C['eventos'] = ev; C['version_eventos'] = 'o112'
    return C, err
C1.validar = validar
_PEDIDO109 = C1.pedido
def pedido(K, D, a, e, cd, PC, guion, avisos):
    _GUION['txt'] = guion
    P, err = _PEDIDO109(K, D, a, e, cd, PC, guion, avisos)
    if P: P['prompt'] += '\n\n=== POSE_LIBRARY ===\n' + json.dumps(poses_lista(), ensure_ascii=False) + '\n=== END POSE_LIBRARY ==='
    return P, err
C1.pedido = pedido
def main(argv):
    r = C1.main(argv)
    if isinstance(r, dict): r['version_eventos'] = 'o112'
    return r
if __name__ == '__main__':
    import paso01_cubos as K; print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
