#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 113 (t308u) — cubo 01 con eventos (o112) + FILTRO DE CÁMARAS (gratis, genérico).
Antes de pedir a Argon, mide en Blender (camaras_o113_blender.py) qué cámaras del molde ven de verdad la zona de acción con figuras de pie
(en cuadro, no inclinadas fuera, sin objetos que tapen). A Argon SOLO se le ofrecen esas; si ninguna sirve, una cámara nivelada
«auto_o113_*» creada desde la geometría del set (marcada auto_generada). El validador rechaza cualquier otra cámara.
Resultado del filtro: <capítulo>/cubos/01/camaras_o113/<escenario>.json (lo lee también el 02v para crear las cámaras auto)."""
import copy, json, subprocess, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
import cubo01_o112 as C112, cubo01_o109 as C1, paso01_dirigir as DI
_CFG112 = DI._cfg
def _cfg():
    c = dict(_CFG112()); c['prompt'] = 'prompts_01/dirigir_escena_o113.txt'; c['esquema'] = 'prompts_01/dirigir_escena_esquema_o112.json'; return c
DI._cfg = _cfg; C112._cfg = _cfg


def filtrar(K, D, eid, rehacer=False):
    blend = D / 'ramas' / 'moldes' / str(eid) / 'molde.blend'; S = D / 'cubos' / '01' / 'camaras_o113'; S.mkdir(parents=True, exist_ok=True); f = S / f'{eid}.json'
    if f.is_file() and not rehacer: return json.loads(f.read_text(encoding='utf-8'))
    b = K.blender()
    if not b or not blend.is_file(): return None
    p = subprocess.run(['nice', '-n', '15', b, '-b', str(blend), '--factory-startup', '-P', str(AQUI / 'camaras_o113_blender.py'), '--', str(f)], capture_output=True, text=True, timeout=600)
    if not f.is_file(): (S / f'{eid}.log').write_text((p.stdout or '')[-5000:] + (p.stderr or '')[-3000:]); return None
    return json.loads(f.read_text(encoding='utf-8'))


_PEDIDO112 = C1.pedido   # (ya es el de o112)
def pedido(K, D, a, e, cd, PC, guion, avisos):
    eid = e['escenario_id']; M, err = K.molde(D, eid)
    if M and not M.get('_o113'):
        R = filtrar(K, D, eid)
        if R is None: return None, f'escena {e["numero"]}: no se pudo medir qué cámaras ven la escena (no se ofrece ninguna sin medir)'
        M2 = copy.deepcopy(M); ok = set(R['sirven'])
        M2['camaras_molde'] = [c for c in M.get('camaras_molde') or [] if c['nombre'] in ok]
        for x in R.get('auto') or []:
            M2['camaras_molde'].append({'nombre': x['nombre'], 'loc': x['loc'], 'dir': x['dir'], 'arriba': x['arriba'], 'lente_mm': x['lente_mm'],
                                        'sensor_ancho_mm': x['sensor_ancho_mm'], 'escena_molde': '', 'auto_generada': True})
        M2['_o113'] = R; K._CACHE_MOLDE[eid] = (M2, err)
        avisos.append(f"escena {e['numero']}: cámaras ofrecidas a Argon (filtro o113): {R['sirven']}")
    return _PEDIDO112(K, D, a, e, cd, PC, guion, avisos)
C1.pedido = pedido


def main(argv):
    r = C1.main(argv)
    if isinstance(r, dict): r['version_camaras'] = 'o113'
    return r
if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
