"""entrada_n8n — puerta del motor unificado v1 para n8n (COPIA FABRICAS d2Bwmk2j4ijX28eK), vía SSH restringido n8ntaller
(entrada_ssh.sh -> sudo -n /opt/myia-motor-unificado/v1_20261110/entrada_motor.sh). Siempre responde UNA línea JSON.
  preparar --canal C --capitulo N --escena E     -> moldes + traductor + inventario + A*+RVO2 (CPU 213, US$0, ~20 s)
  correr   --canal C --capitulo N --escena E     -> lanza en segundo plano el trabajo GPU (RunPod; topes del motor) y responde ya
  estado   --canal C --capitulo N --escena E [--id ID] -> estado.json de la última corrida (o de ID)
Interruptor: /opt/myia-motor-unificado/v1_20261110/entrada_n8n.off (si existe, no corre nada)."""
import sys, json, re, subprocess, os
from pathlib import Path
from datetime import datetime
V = Path('/opt/myia-motor-unificado/v1_20261110'); CAD = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
def out(**d): print(json.dumps(d, ensure_ascii=False)); sys.exit(0)
a = sys.argv[1:]
if not a or a[0] not in ('preparar', 'correr', 'estado'): out(ok=False, error='acción no permitida')
acc = a[0]; kv = {}
for i in range(1, len(a) - 1, 2):
    if a[i] not in ('--canal', '--capitulo', '--escena', '--id') or not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', a[i + 1]) or '..' in a[i + 1]: out(ok=False, error=f'argumento no permitido {a[i]}')
    kv[a[i][2:]] = a[i + 1]
for k in ('canal', 'capitulo', 'escena'):
    if k not in kv: out(ok=False, error=f'falta --{k}')
cap = kv['capitulo']; capd = None
base = CAD / kv['canal']
if re.fullmatch(r'\d+', cap):
    c = sorted(base.glob(f'cap{int(cap):02d}_*')); capd = c[0] if c else None
elif (base / cap).is_dir(): capd = base / cap
if not capd: out(ok=False, error='capítulo no encontrado en paso00_cadena', canal=kv['canal'], capitulo=cap)
if acc == 'estado':
    cs = sorted((V / 'corridas').glob(f"n8n_{kv['canal'][:20]}_{capd.name[:12]}_esc{kv['escena']}_*")) if 'id' not in kv else [V / 'corridas' / kv['id']]
    if not cs or not (cs[-1] / 'estado.json').exists():
        out(ok=True, estado='sin_corridas' if not cs else 'en_curso', id=cs[-1].name if cs else None)
    e = json.load(open(cs[-1] / 'estado.json'))
    vids = sorted(str(p) for p in (cs[-1] / 'salida' / 'out').glob('*.mp4')) if (cs[-1] / 'salida').exists() else []
    out(ok=True, id=cs[-1].name, estado=e.get('estado'), revision_ok=e.get('revision_ok'), videos=vids, gpu=e.get('gpu', {}), pasos=e.get('pasos'))
cid = f"n8n_{kv['canal'][:20]}_{capd.name[:12]}_esc{kv['escena']}_{datetime.now():%Y%m%d_%H%M%S}" + ('_prep' if acc == 'preparar' else '')
cmd = ['/usr/bin/python3', str(V / 'motor' / 'correr_escena.py'), '--cadena', str(capd), '--escena', kv['escena'], '--id', cid]
if acc == 'preparar':
    r = subprocess.run(cmd + ['--solo_cpu'], capture_output=True, text=True, timeout=900)
    try: e = json.load(open(V / 'corridas' / cid / 'estado.json'))
    except Exception: out(ok=False, error='preparar sin estado', tail=(r.stdout + r.stderr)[-600:])
    E = json.load(open(V / 'corridas' / cid / 'entrada_motor.json')) if (V / 'corridas' / cid / 'entrada_motor.json').exists() else {}
    out(ok=e.get('estado') == 'OK_sin_gpu', id=cid, estado=e.get('estado'), faltantes=E.get('faltantes', []), avisos=E.get('avisos', []),
        personajes=[p['id'] for p in E.get('personajes', [])], escenario=(E.get('escenario') or {}).get('fuente'), pasos=e.get('pasos'), gasto_usd=0)
# correr: en segundo plano (el trabajo GPU dura ~30-45 min); n8n consulta con «estado»
log = open(V / 'corridas' / f'{cid}.lanzamiento.log', 'w')
p = subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
out(ok=True, estado='lanzado', id=cid, pid=p.pid, consultar=f"motor_unificado estado --canal {kv['canal']} --capitulo {cap} --escena {kv['escena']} --id {cid}",
    topes={"por_trabajo_usd": json.load(open(V / 'config_motor.json'))['gpu']['tope_por_trabajo_usd'], "motor_total_usd": json.load(open(V / 'config_motor.json'))['gpu']['tope_motor_total_usd']})
