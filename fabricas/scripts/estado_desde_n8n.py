#!/usr/bin/env python3
"""estado_desde_n8n.py (10-nov-2026, Ricardo t1027u): estado de trabajos de fábrica para n8n, US$0.
Uso (vía entrada_ssh.sh): «fabrica_estado ID[,ID...]» (ids de 16 hex devueltos por fabrica_encolar).
GET 127.0.0.1:18750/v1/jobs/<id> (solo lectura). Una línea JSON: {ok, en_curso, n, trabajos:[{id, kind, estado, gasto_usd, error?, resumen?}], gasto_usd: 0}."""
import json, sys, re, urllib.request, urllib.error
BASE = 'http://127.0.0.1:18750/v1/jobs/'
EN_CURSO = ('en_cola', 'corriendo')

def corto(v, n=600):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + '…'

def uno(jid):
    try:
        with urllib.request.urlopen(BASE + jid, timeout=5) as f: j = json.loads(f.read())
    except urllib.error.HTTPError as e:
        return {"id": jid, "estado": "no_encontrado" if e.code == 404 else f"http_{e.code}"}
    except Exception as e:
        return {"id": jid, "estado": "servicio_caido", "error": corto(str(e), 200)}
    r = {"id": j.get('id', jid), "kind": j.get('kind'), "estado": j.get('estado'), "gasto_usd": j.get('gasto_usd', 0)}
    if j.get('error'): r['error'] = corto(j['error'], 400)
    for k in ('resultado', 'result', 'salida', 'publicado'):
        if j.get(k) is not None: r['resumen'] = corto(j[k]); break
    lg = j.get('log') or []
    if lg: r['ultimo_log'] = corto(lg[-1], 300)
    return r

def main(a):
    ids = [x for x in (a[0].split(',') if a else []) if x]
    if not ids or len(ids) > 20 or not all(re.fullmatch(r'[a-f0-9]{16}', x) for x in ids):
        print(json.dumps({"ok": False, "error": "uso: fabrica_estado ID[,ID...] (16 hex, máx 20)", "gasto_usd": 0})); return
    T = [uno(x) for x in ids]
    print(json.dumps({"ok": all(t['estado'] not in ('no_encontrado', 'servicio_caido', 'error') and not str(t['estado']).startswith('http_') for t in T),
                      "en_curso": any(t['estado'] in EN_CURSO for t in T), "n": len(T), "trabajos": T, "gasto_usd": 0}, ensure_ascii=False))

if __name__ == '__main__':
    try: main(sys.argv[1:])
    except Exception as e: print(json.dumps({"ok": False, "error": str(e)[:300], "gasto_usd": 0}))
