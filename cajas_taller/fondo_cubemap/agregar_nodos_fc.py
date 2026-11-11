"""Agrega la rama «FC ·» (fondo cubemap) a la COPIA JTYnu9oItUj6okH9. Clave n8n por entrada estándar. Respaldo antes; se niega si cambió la base."""
import json, sys, uuid, urllib.request, time
WID = 'JTYnu9oItUj6okH9'; API = 'http://127.0.0.1:5678/api/v1/workflows/' + WID
clave =[REDACTED]
H = {'X-N8N-API-KEY': clave, 'Content-Type': 'application/json', 'Accept': 'application/json'}
def req(m='GET', body=None):
    r = urllib.request.Request(API, method=m, headers=H, data=None if body is None else json.dumps(body).encode())
    with urllib.request.urlopen(r, timeout=60) as f: return json.loads(f.read())
w = req(); json.dump(w, open(resp, 'w'), ensure_ascii=False)
if w['updatedAt'] != base: print(json.dumps({'ok': False, 'error': 'la copia cambió desde la base', 'vivo': w['updatedAt']})); sys.exit(2)
if any(n['name'].startswith('FC ·') for n in w['nodes']): print(json.dumps({'ok': False, 'error': 'ya hay nodos FC ·'})); sys.exit(2)
CRED = {'sshPrivateKey': {'id': 'Bq5yySVYqN3VlOi2', 'name': 'SSH taller → staging 213 (n8ntaller, restringido)'}}
X0, Y0 = 11648, 3000
ENT = "$('FC · escena').first().json"
ARGS = f"--canal {{{{ {ENT}.canal }}}} --capitulo {{{{ {ENT}.capitulo }}}} --escena {{{{ {ENT}.escena }}}}"
def nid(): return str(uuid.uuid4())
def ssh(name, accion, x, y, extra=''):
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.ssh', 'typeVersion': 1, 'position': [x, y], 'credentials': CRED,
            'parameters': {'authentication': 'privateKey', 'command': f'=paso00_cadena cubemap {accion} {ARGS}{extra}'}}
def leer(name, etiqueta, x, y, gratis=True):
    js = ("const it=$input.first().json; const txt=String(it.stdout||'').trim().split('\\n').pop();\n"
          f"let r; try{{ r=JSON.parse(txt); }}catch(e){{ throw new Error('FC {etiqueta}: no devolvió JSON. stdout: '+String(it.stdout||'').slice(0,300)+' | stderr: '+String(it.stderr||'').slice(0,300)); }}\n"
          f"if(!r.ok) throw new Error('FC {etiqueta}: '+(r.error||JSON.stringify(r).slice(0,500)));\n"
          + (f"if(r.llamadas_pagas||r.usd_gastado) throw new Error('FC {etiqueta}: no debía gastar');\n" if gratis else '') + "return [{json:r}];")
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [x, y], 'parameters': {'jsCode': js}}
def asig(n, v, t): return {'id': nid(), 'name': n, 'value': v, 'type': t}
dx = 256
N = [
 {'id': nid(), 'name': 'FC · Inicio fondo cubemap (manual)', 'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1, 'position': [X0, Y0], 'parameters': {}},
 {'id': nid(), 'name': 'FC · escena', 'type': 'n8n-nodes-base.set', 'typeVersion': 3.4, 'position': [X0 + dx, Y0],
  'parameters': {'assignments': {'assignments': [asig('canal', 'cn-gnesis-digital-el-de-ed178619', 'string'), asig('capitulo', '1', 'string'),
                 asig('escena', '9', 'string'), asig('tope_usd', 0, 'number')]}, 'options': {}}},
 ssh('FC · 1 cubo gris + molde (gratis)', 'cubo', X0 + 2 * dx, Y0, ' --cuadros 1,93,185'),
 leer('FC · leer cubo', 'cubo', X0 + 3 * dx, Y0),
 ssh('FC · 2 cotizar pintura (gratis)', 'cotizar', X0 + 4 * dx, Y0),
 leer('FC · leer cotización', 'cotizar', X0 + 5 * dx, Y0),
 {'id': nid(), 'name': 'FC · ¿con pago? (tope > 0)', 'type': 'n8n-nodes-base.if', 'typeVersion': 2, 'position': [X0 + 6 * dx, Y0],
  'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose', 'version': 2},
                 'conditions': [{'id': nid(), 'leftValue': f'={{{{ Number({ENT}.tope_usd||0) > 0 }}}}', 'rightValue': '',
                                 'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}], 'combinator': 'and'}, 'options': {}}},
 ssh('FC · ▶ pintar cubemap (pago)', 'pintar', X0 + 7 * dx, Y0 - 120),
 leer('FC · leer pintura', 'pintar', X0 + 8 * dx, Y0 - 120, gratis=False),
 ssh('FC · 3 proyectar por toma (gratis)', 'proyectar', X0 + 9 * dx, Y0),
 leer('FC · leer proyección', 'proyectar', X0 + 10 * dx, Y0),
]
nota = {'id': nid(), 'name': 'Sección · FC · Fondo cubemap universal (2-nov-2026)', 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1,
        'position': [X0 - 48, Y0 - 300], 'parameters': {'width': 2900, 'height': 520, 'content':
 "## FC · Fondo cubemap universal · 2-nov-2026 (Ricardo t401u)\n"
 "Rama aparte (manual). **1 cubo** (US$0): clona la escena de Blender SIN personajes y saca 6 grises F/B/L/R/U/D desde el origen de la cámara + molde con personajes por toma → "
 "**2 cotizar** (US$0, 6 caras una sola vez) → ¿con pago? → tope > 0: **▶ pintar** (pago, SOLO con cajas/HABILITAR_PAGO_FC + ledger) → "
 "**3 proyectar** (US$0): por toma, el cubemap pintado (o el gris = prueba seca) desde la cámara de ESA toma = **Imagen 1 fondo**; **Imagen 2** = molde con personajes.\n"
 "Programa: cajas/fondo_cubemap/cubemap.py (entrada `paso00_cadena cubemap …`). Salida: <capítulo>/cubos/FC/esc_<E>/. Límite: sin paralaje (fondo de entorno)."}}
C = w['connections']
def con(a, b, salida=0):
    m = C.setdefault(a, {}).setdefault('main', [])
    while len(m) <= salida: m.append([])
    m[salida].append({'node': b, 'type': 'main', 'index': 0})
nm = [n['name'] for n in N]
for a, b in zip(nm[:7], nm[1:7]): con(a, b)
con(nm[6], nm[7], 0); con(nm[7], nm[8]); con(nm[8], nm[9]); con(nm[6], nm[9], 1); con(nm[9], nm[10])
w['nodes'] += N + [nota]
SET_OK = ('saveExecutionProgress', 'saveManualExecutions', 'saveDataErrorExecution', 'saveDataSuccessExecution', 'executionTimeout',
          'errorWorkflow', 'timezone', 'executionOrder', 'callerPolicy', 'callerIds', 'timeSavedPerExecution')
body = {'name': w['name'], 'nodes': w['nodes'], 'connections': C, 'settings': {k: v for k, v in (w.get('settings') or {}).items() if k in SET_OK}}
r = req('PUT', body); v = req()
print(json.dumps({'ok': True, 'nodos': len(v['nodes']), 'antes': len(w['nodes']) - len(N) - 1, 'fc': sorted(n['name'] for n in v['nodes'] if n['name'].startswith('FC ·')),
                  'updatedAt': v['updatedAt'], 'activa': v.get('active')}, ensure_ascii=False))
