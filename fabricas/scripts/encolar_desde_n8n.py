#!/usr/bin/env python3
"""Inmi, fase A 9-nov-2026 — INSTALADA con OK Ricardo pt946u. Puente n8n → servicio fábricas (127.0.0.1:18750).
Destino propuesto: /opt/myia-fabricas/scripts/encolar_desde_n8n.py  (lo llama entrada_ssh.sh con «fabrica_encolar <tipo> b64.<x>»).
- n8n corre en Docker y NO ve 127.0.0.1:18750 del host; por eso pasa por la puerta SSH restringida (igual que cubo_fijo / sello_pago).
- Revalida los campos obligatorios (sin valores por defecto). Si falta algo: no llama, imprime {"ok":false,"faltan":[...]}.
- escenario sin id + expandir_desde_inventario → lee escenarios[].escenario_id del inventario real y encola uno por escenario.
- Nunca gasta: el servicio tiene argon_enabled=false. Timeout 5 s. Una línea JSON en stdout. Siempre exit 0 (no tumba n8n).
- --seco o FABRICA_ENCOLAR_SECO=1: valida y muestra lo que mandaría, sin llamar al servicio (por defecto: llama)."""
import base64, json, os, re, sys, urllib.request
from pathlib import Path
TIPOS = ('personaje', 'escenario', 'objeto', 'objeto_usuario')
REQ = {'personaje': ['canal', 'id', 'nombre', 'clase', 'version', 'sello_path', 'adn_path'],
       'objeto': ['canal', 'id', 'nombre', 'clase', 'version', 'sello_path', 'adn_path'],
       'objeto_usuario': ['canal', 'id', 'nombre', 'clase', 'version', 'sello_path', 'adn_path'],
       'escenario': ['canal', 'capitulo', 'episodio', 'carpeta', 'inventario_path']}
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{1,79}$')
RAICES_OK = ('/opt/myia-taller-n8n/cajas/cubo_fijo/', '/opt/myia-taller-n8n/trabajo/', '/opt/myia-fabricas/entradas/')   # + entradas: copias solo lectura de datos n8n (10-nov-2026)
URL = 'http://127.0.0.1:18750/v1/jobs/'

def out(d): print(json.dumps(d, ensure_ascii=False)); sys.exit(0)
def vacio(v): return v is None or (isinstance(v, str) and (not v.strip() or v.strip().lower().startswith('desconocid')))

def main(a):
    seco = '--seco' in a or os.environ.get('FABRICA_ENCOLAR_SECO') == '1'; a = [x for x in a if x != '--seco']
    if len(a) != 2 or a[0] not in TIPOS or not a[1].startswith('b64.'): out({'ok': False, 'error': 'uso: <tipo> b64.<payload>'})
    try:
        s = a[1][4:]; p = json.loads(base64.urlsafe_b64decode(s + '=' * (-len(s) % 4)).decode('utf-8'))
    except Exception as e: out({'ok': False, 'error': f'payload ilegible: {type(e).__name__}'})
    tipo = a[0]
    if p.get('tipo') != tipo: out({'ok': False, 'error': f'tipo no coincide: {p.get("tipo")} != {tipo}'})
    faltan = [k for k in REQ[tipo] if vacio(p.get(k))]
    for k in ('sello_path', 'adn_path', 'inventario_path'):
        v = p.get(k)
        if not v: continue
        try: existe = str(v).startswith(RAICES_OK) and Path(v).is_file()
        except PermissionError: faltan.append(f'{k} sin permiso de lectura para este usuario: {v}'); continue
        if not existe: faltan.append(f'{k} no existe o fuera de raíz permitida: {v}')
    if faltan: out({'ok': False, 'tipo': tipo, 'faltan': faltan, 'llamado': False, 'gasto_usd': 0})
    ids = [p['id']] if p.get('id') else []
    if tipo == 'escenario' and not ids and p.get('expandir_desde_inventario'):
        inv = json.loads(Path(p['inventario_path']).read_text(encoding='utf-8'))
        ids = [e.get('escenario_id') or e.get('id') for e in (inv.get('escenarios') or []) if isinstance(e, dict) and (e.get('escenario_id') or e.get('id'))]
    ids = [i for i in ids if ID.match(str(i))]
    if not ids: out({'ok': False, 'tipo': tipo, 'faltan': ['id (ni en el pedido ni en el inventario)'], 'llamado': False, 'gasto_usd': 0})
    res = []
    for i in ids:
        body = dict(p, id=i)
        if tipo == 'escenario':
            parc = Path(p['carpeta']) / 'respuestas' / f'inv_escenarios__{i}.json'
            body['inventario_parcial_path'] = str(parc) if parc.is_file() else None
        if seco: res.append({'id': i, 'seco': True, 'body_campos': sorted(body)}); continue
        try:
            r = urllib.request.Request(URL + tipo, data=json.dumps(body).encode(), method='POST', headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(r, timeout=5) as f: res.append({'id': i, 'http': f.status, **json.loads(f.read())})
        except Exception as e: res.append({'id': i, 'ok': False, 'error': type(e).__name__})
    out({'ok': all(x.get('ok', True) for x in res), 'tipo': tipo, 'n': len(res), 'trabajos': res, 'gasto_usd': 0, 'seco': seco})

if __name__ == '__main__':
    try: main(sys.argv[1:])
    except SystemExit: raise
    except Exception as e: out({'ok': False, 'error': f'fallo interno: {type(e).__name__}', 'llamado': False, 'gasto_usd': 0})
