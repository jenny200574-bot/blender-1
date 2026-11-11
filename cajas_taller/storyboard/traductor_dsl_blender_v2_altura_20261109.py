#!/usr/bin/env python3
"""TRADUCTOR SB → cámara Blender · v2 altura (9-nov-2026, fase 2 motor, OK Ricardo t987s3315). Gratis, sin red, no toca Blender.
Copia versionada: traductor_dsl_blender.py (v1) NO se tocó y esc_N_camara.json (v1) NO se pisa.
Cambio v2: la ALTURA de cada viñeta sale del ADN oficial (trabajo/biblioteca/<canal>/personajes/personajes.json, altura_m;
id del mapa ch-… → ids_mapa). Si un personaje no tiene altura en el ADN → queda None y el informe dice STOP_FALTA_ALTURA (nunca se inventa).
Blender NO decide la altura: con --comparar-blender solo se mide y se reporta la diferencia (±2%).
Uso: python3 traductor_dsl_blender_v2_altura_20261109.py --canal C --capitulo CAP --escena N [--comparar-blender]
Escribe: trabajo/paso00_cadena/<C>/<CAP>/cubos/SB/blender/esc_N_camara_v2_altura.json"""
import sys, json, argparse
from pathlib import Path
AQUI = Path(__file__).resolve().parent; sys.path.insert(0, str(AQUI)); sys.path.insert(0, str(AQUI.parent))
import sb_comun as S
import traductor_dsl_blender as TR1
TABLA = '/opt/myia-taller-n8n/trabajo/biblioteca/{canal}/personajes/personajes.json'
RAIZ = '/opt/myia-taller-n8n/trabajo/paso00_cadena/{canal}/{cap}'
VERSION = 'sb_dsl_a_blender_v2_altura_20261109'

def altura_adn(canal):
    p = Path(TABLA.format(canal=canal)); t = json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
    idx = {}
    for x in t.get('personajes') or []:
        for k in [x.get('id')] + list(x.get('ids_mapa') or []): idx[k] = x
    def f(pid):
        x = idx.get(pid)
        if not x or x.get('altura_m') is None: return None, None
        return float(x['altura_m']), f"ADN oficial ({p.name}#{x['id']}: {x.get('altura_fuente')})"
    return f

def traducir_v2(sb, canal, blender=None):
    T = TR1.traducir(sb, altura_adn(canal))
    T['version'] = VERSION; T['version_base'] = 'sb_dsl_a_blender_borrador_v1'
    T['altura_regla'] = 'manda el ADN (personajes.json altura_m); Blender solo mide y compara (±2%)'
    T['pista'] = 'v2: altura del ADN oficial; distancias calculadas con esa altura.'
    if blender:
        for v in T['vinetas']:
            try: b, fb = blender(v['objetivo'])
            except Exception as e: b, fb = None, f'no medido: {type(e).__name__}'
            v['altura_blender_m'] = b
            v['altura_diferencia_pct'] = round((b / v['altura_m'] - 1) * 100, 2) if (b and v.get('altura_m')) else None
    T['estado'] = 'OK' if not T['alturas_por_medir'] else 'STOP_FALTA_ALTURA_ADN'
    return T

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True); ap.add_argument('--escena', required=True)
    ap.add_argument('--comparar-blender', action='store_true'); a = ap.parse_args(argv)
    D = Path(RAIZ.format(canal=a.canal, cap=a.capitulo)); f = D / 'cubos' / 'SB' / f'esc_{a.escena}.json'
    sb = S.leer(f)
    if not sb: print(json.dumps({'ok': False, 'error': f'no hay storyboard {f}'})); return 1
    bl = None
    if a.comparar_blender:
        import alturas_blender as AB; bl = lambda pid: AB.altura(a.canal, a.capitulo, a.escena, pid)
    T = traducir_v2(sb, a.canal, bl); out = D / 'cubos' / 'SB' / 'blender' / f'esc_{a.escena}_camara_v2_altura.json'
    S.guardar(out, T)
    n = len(T['vinetas']); llenas = sum(1 for v in T['vinetas'] if v.get('altura_m') is not None)
    print(json.dumps({'ok': T['estado'] == 'OK', 'estado': T['estado'], 'archivo': str(out), 'vinetas': n, 'con_altura': llenas,
                      'alturas_por_medir': T['alturas_por_medir'], 'llamadas_pagas': 0, 'usd_gastado': 0}, ensure_ascii=False))
    return 0 if T['estado'] == 'OK' else 2

if __name__ == '__main__': sys.exit(main())
