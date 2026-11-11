#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 114 — cubo 01 = o113 (eventos + filtro de cámaras) + 2 huecos del validador cerrados (genérico):
  1. un beat que ROMPE o MUEVE algo sin decir QUÉ objeto -> RECHAZO (antes pasaba en silencio y el video no rompía nada);
     aparecer/desaparecer sin objeto ni actor -> RECHAZO.
  2. un personaje ACOPLADO a otro (ej. Imi en el hombro de Kael) cuenta como presente en cada toma donde está su portador:
     el código lo agrega a en_cuadro / personas / por_personaje (marcado «acoplado_a») en vez de solo avisar."""
import copy, json, sys
from pathlib import Path
import cubo01_o113 as C113, cubo01_o109 as C1
NECESITA_OBJETO = ('romper', 'mover')
NECESITA_SUJETO = ('aparecer', 'desaparecer')


def beats_de(obj):
    ev = (obj or {}).get('eventos') or {}
    return ev.get('beats') if isinstance(ev, dict) and isinstance(ev.get('beats'), list) else []


def errores_objeto(beats):
    err = []
    for i, b in enumerate(beats):
        if not isinstance(b, dict): continue
        ac = b.get('accion'); ob = str(b.get('objeto') or '').strip(); efi = str((b.get('efecto') or {}).get('id') or '').strip()
        q = f"eventos.beats[{i}] ({b.get('actor') or '-'} t={b.get('t')})"
        if ac in NECESITA_OBJETO and not ob: err.append(f'{q}: accion «{ac}» sin «objeto» (¿qué se rompe/mueve? no se inventa)')
        if ac in NECESITA_SUJETO and not (ob or efi or b.get('actor')): err.append(f'{q}: accion «{ac}» sin objeto, efecto ni actor')
    return err


def acoples(beats):
    """{actor_acoplado: portador} según los beats (el último acople manda)."""
    m = {}
    for b in beats:
        if isinstance(b, dict) and b.get('actor') and b.get('acoplado_actor'): m[b['actor']] = b['acoplado_actor']
    return m


def completar_en_cuadro(obj):
    ac = acoples(beats_de(obj)); hechos = []
    for t in (obj or {}).get('tomas') or []:
        w = t.get('palabras') if isinstance(t, dict) else None
        if not isinstance(w, dict) or not isinstance(w.get('en_cuadro'), list): continue
        for a, h in ac.items():
            if h in w['en_cuadro'] and a not in w['en_cuadro']:
                w['en_cuadro'].append(a)
                if isinstance(w.get('personas'), int): w['personas'] += 1
                pp = w.get('por_personaje')
                if isinstance(pp, list) and not any(isinstance(x, dict) and x.get('id') == a for x in pp):
                    base = next((x for x in pp if isinstance(x, dict) and x.get('id') == h), None)
                    nx = copy.deepcopy(base) if base else {}; nx['id'] = a; nx['acoplado_a'] = h; pp.append(nx)
                hechos.append(f"toma {t.get('id')}: {a} va acoplado a {h} -> se cuenta en cuadro")
    return hechos


_VAL113 = C1.validar
def validar(K, obj, e, P):
    hechos = completar_en_cuadro(obj)
    C, err = _VAL113(K, obj, e, P)
    err = list(err) + errores_objeto(beats_de(obj))
    if isinstance(C, dict) and hechos: C['avisos_codigo'] = (C.get('avisos_codigo') or []) + hechos
    return C, err
C1.validar = validar


def main(argv):
    r = C113.main(argv)
    if isinstance(r, dict): r['version_validador'] = 'o114'
    return r
if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
