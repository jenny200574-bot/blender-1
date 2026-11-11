#!/usr/bin/env python3
"""PISTA INMI (2026-10-29) orden 98 noche: cubos 11/12 nuevos para n8n (GRATIS, sin red, sin ledger).
Lo llama paso00_cadena.py:  ver o98 texto   --tramo L13L14_o98 --lamina L14   -> arma el texto de pintura POR CODIGO desde las medidas
                                                                                 de Blender + plan ARGON C y corre el chequeo previo (R1-R6)
                            ver o98 revisar --tramo L13L14_o98 --lamina L14   -> resultado del cubo 12 (vision + codigo) del ultimo intento
                            ver o98 tramos                                    -> lista de tramos probados y su estado
Programas: trabajo/o98/programas (copias). No paga nada: pintar sigue con su guarda y --ok."""
import argparse, glob, json, os, subprocess, sys
O98 = '/opt/myia-taller-n8n/trabajo/o98'; PR = O98 + '/programas'; TR = O98 + '/tramos'
def main(argv):
    ap = argparse.ArgumentParser(prog='ver o98'); ap.add_argument('accion', choices=['texto', 'revisar', 'tramos'])
    ap.add_argument('--tramo'); ap.add_argument('--lamina'); a = ap.parse_args(argv)
    if a.accion == 'tramos':
        return {'ok': True, 'tramos': {os.path.basename(d): (json.load(open(d + '/resultado.json')) if os.path.exists(d + '/resultado.json') else None) for d in sorted(glob.glob(TR + '/*'))}}
    if not (a.tramo and a.lamina) or not a.tramo.replace('_', '').isalnum() or not a.lamina.isalnum(): return {'ok': False, 'error': 'falta --tramo/--lamina validos'}
    T = f'{TR}/{a.tramo}'
    if a.accion == 'texto':
        ids = ','.join(f'{a.lamina}_{i}' for i in range(1, 5)); out = f'{T}/prompt_{a.lamina}_n8n.txt'
        r = subprocess.run([sys.executable, PR + '/cubo11/armar_prompt_o98.py', PR + '/cubo11/canal_genesis.json', T + '/medidas.json', T + '/plan_argon.json', ids, out], capture_output=True, text=True)
        try: chq = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception: return {'ok': False, 'error': (r.stderr or r.stdout)[-400:]}
        return {'ok': chq['ok'], 'texto': out, 'chequeo': chq, 'texto_inicio': open(out).read()[:600]}
    vs = sorted(glob.glob(f'{T}/vision_{a.lamina}_i*.json'))
    if not vs: return {'ok': False, 'error': 'sin revision para esa lamina'}
    v = json.load(open(vs[-1])); return {'ok': not v.get('fallan'), 'archivo': vs[-1], 'fallan': v.get('fallan'), 'paneles': {k: x.get('fallas') for k, x in (v.get('paneles') or {}).items()}}
if __name__ == '__main__': print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
