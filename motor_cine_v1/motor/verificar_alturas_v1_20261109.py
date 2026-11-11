#!/usr/bin/env python3
"""VERIFICAR ALTURAS · v1 (9-nov-2026, fase 2 motor, OK Ricardo t987s3315). GRATIS: no llama a nada, no cambia nada.
Regla: la altura oficial es la del ADN (trabajo/biblioteca/<canal>/personajes/personajes.json, altura_m). Todas las otras
fuentes (copia del cubo fijo, adn_manifest del motor, texto del ADN de Argon, storyboard traducido, molde/Blender) deben coincidir ±2%.
  SI falta la altura oficial de alguien pedido            -> STOP FALTA_DATO   (exit 2)  · no se inventa
  SI alguna fuente numérica difiere > 2% de la oficial    -> STOP CONFLICTO    (exit 3)  · no se escoge una
  SI NO                                                    -> PASS              (exit 0)
Uso: verificar_alturas_v1_20261109.py --canal C [--ids a,b] [--source01 f] [--storyboard f] [--manifiesto f] [--salida informe.json]"""
import sys, json, re, glob, argparse, os
from pathlib import Path
TOL = 0.02
TABLA = '/opt/myia-taller-n8n/trabajo/biblioteca/{canal}/personajes/personajes.json'
CUBO = '/opt/myia-taller-n8n/cajas/cubo_fijo/personajes'
SELLO = '/opt/myia-taller-n8n/trabajo/sello_pago/{canal}'
ADN_SELLADO = '/opt/myia-taller-n8n/cajas/cubo_fijo/adn'
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def num_texto(t):
    m = re.search(r'Estatura en metros\W*:?\W*([0-9]+(?:[.,][0-9]+)?)\s*m\b', t, re.I)
    if m: return float(m.group(1).replace(',', '.')), 'texto ADN (Estatura en metros)'
    m = re.search(r'Estatura[^:\n]*:\**\s*~?\s*([0-9]+(?:[.,][0-9]+)?)\s*(cm|m)\b', t, re.I)
    if m:
        v = float(m.group(1).replace(',', '.')); return (v / 100 if m.group(2).lower() == 'cm' else v), 'texto ADN (Estatura aparente)'
    return None, 'texto ADN sin número'

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--canal', required=True); ap.add_argument('--ids', default='')
    ap.add_argument('--source01'); ap.add_argument('--storyboard'); ap.add_argument('--manifiesto'); ap.add_argument('--salida')
    a = ap.parse_args(argv)
    tp = TABLA.format(canal=a.canal); t = rj(tp)
    por_id, alias = {}, {}
    for x in t.get('personajes') or []:
        por_id[x['id']] = x
        for k in [x['id'], 'gdc-' + x['id']] + list(x.get('ids_mapa') or []): alias[k] = x['id']
    falt = {f['id']: f for f in t.get('faltan_datos') or []}
    pedidos = [i for i in a.ids.split(',') if i]
    if a.source01: pedidos += [p['id'] for p in rj(a.source01).get('personajes') or []]
    sbv = rj(a.storyboard)['vinetas'] if a.storyboard else []
    pedidos += [v['objetivo'] for v in sbv if v.get('objetivo')]
    if not pedidos: pedidos = list(por_id)
    canon = []
    for i in pedidos:
        c = alias.get(i, i)
        if c not in canon: canon.append(c)
    man = {e['id']: e for e in rj(a.manifiesto)} if a.manifiesto else {}
    filas, stop_falta, stop_conf = [], [], []
    for c in canon:
        x = por_id.get(c); of = (x or {}).get('altura_m')
        f = {'id': c, 'oficial_m': of, 'fuente_oficial': f'{tp}#{c}' if x else None, 'otras': [], 'estado': None}
        if of is None:
            f['estado'] = 'STOP_FALTA_DATO'; f['nota'] = (falt.get(c) or {}).get('nota') or 'no está en la tabla de alturas del ADN'
            stop_falta.append(c); filas.append(f); continue
        of = float(of)
        def add(nombre, v, nota=''):
            r = {'fuente': nombre, 'm': v, 'nota': nota}
            if v is not None:
                r['diferencia_pct'] = round((float(v) / of - 1) * 100, 2); r['ok'] = abs(float(v) / of - 1) <= TOL
            f['otras'].append(r)
        for p in glob.glob(f'{CUBO}/*.json'):
            try: e = rj(p)
            except Exception: continue
            if e.get('canal') == a.canal and (e.get('id') == 'gdc-' + c or c in (e.get('ids_canal') or [])):
                add(f'cubo_fijo {os.path.basename(p)} altura_m', e.get('altura_m'))
                if e.get('altura_blender_m') is not None: add(f'cubo_fijo {os.path.basename(p)} altura_blender_m (solo compara)', e['altura_blender_m'])
        for mid in (x.get('ids_mapa') or []):
            if mid in man: add(f'adn_manifest {mid} height_m', man[mid].get('height_m')); v, n = num_texto(man[mid].get('text') or ''); add(f'adn_manifest {mid} texto', v, n)
        ak = Path(f'{ADN_SELLADO}/gdc-{c}_ako.json')
        if ak.is_file(): v, n = num_texto(rj(ak).get('texto') or ''); add(f'ADN sellado {ak.name}', v, n)
        txts = sorted(glob.glob(f"{SELLO.format(canal=a.canal)}/gdc-{c}/adn_personaje_*.txt"))
        if txts:   # salida cruda de Argon (antes de sellar): solo se INFORMA, no detiene (lo que usa el taller es el ADN sellado)
            v, n = num_texto(Path(txts[-1]).read_text(encoding='utf-8'))
            r = {'fuente': f'ADN crudo Argon {os.path.basename(txts[-1])} (solo informa)', 'm': v, 'nota': n}
            if v is not None: r['diferencia_pct'] = round((v / of - 1) * 100, 2); r['aviso'] = abs(v / of - 1) > TOL
            f['otras'].append(r)
        for v in sbv:
            if alias.get(v.get('objetivo')) == c and isinstance(v.get('altura_m'), (int, float)): add(f"storyboard {v['vineta']} altura_m", v['altura_m'])
        malos = [r for r in f['otras'] if r.get('ok') is False]
        f['estado'] = 'STOP_CONFLICTO' if malos else 'OK'
        if malos: stop_conf.append(c)
        filas.append(f)
    estado = 'STOP_FALTA_DATO' if stop_falta else ('STOP_CONFLICTO' if stop_conf else 'PASS')
    avisos = [f"{x['id']}: {o['fuente']} = {o['m']} m ({o['diferencia_pct']:+}%)" for x in filas for o in x['otras'] if o.get('aviso')]
    rep = {'ok': estado == 'PASS', 'avisos': avisos, 'estado': estado, 'regla': 'oficial = ADN personajes.json; otras fuentes ±2%; falta → STOP; conflicto → STOP (no se escoge)',
           'tabla': tp, 'faltan': stop_falta, 'conflictos': stop_conf, 'personajes': filas, 'usd': 0}
    if a.salida: Path(a.salida).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(rep, ensure_ascii=False))
    return {'PASS': 0, 'STOP_FALTA_DATO': 2, 'STOP_CONFLICTO': 3}[estado]

if __name__ == '__main__': sys.exit(main())
