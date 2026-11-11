"""t358u — pruebas GRATIS (sin red, sin Argon, ledger de PRUEBA en /tmp). Nada toca el ledger real ni compuertas."""
import os, sys, json, time, threading, tempfile, subprocess, csv
from pathlib import Path
CAJAS = Path('/opt/myia-taller-n8n/cajas'); sys.path.insert(0, str(CAJAS))
TMP = Path(tempfile.mkdtemp(prefix='t358_')); R = {}
import paralelo_cadena as PC

# a) Bolsa: tope atómico
b = PC.Bolsa(1.0); ok = []
ths = [threading.Thread(target=lambda: ok.append(b.reservar(0.1))) for _ in range(50)]
[t.start() for t in ths]; [t.join() for t in ths]
R['a_bolsa'] = {'intentos': 50, 'reservas_ok': sum(ok), 'max_comprometido': round(b.max_comprometido, 4), 'tope': 1.0, 'PASA': sum(ok) == 10 and b.max_comprometido <= 1.0 + 1e-9}

# b) correr_paralelo + ranura entre hilos: 9 tareas de 2 s, máx 3
RAN = TMP / 'ranuras'; vivos = [0]; pico = [0]; lk = threading.Lock()
def tarea(i):
    with PC.ranura('argon', RAN, n=3):
        with lk: vivos[0] += 1; pico[0] = max(pico[0], vivos[0])
        time.sleep(2)
        with lk: vivos[0] -= 1
    return {'estado': 'ok'}
t0 = time.time(); rr = PC.correr_paralelo(list(range(9)), tarea, 9); w = time.time() - t0
R['b_paralelo'] = {'tareas': 9, 'seg_cada_una': 2, 'en_fila_s': 18, 'real_s': round(w, 1), 'pico_a_la_vez': pico[0], 'PASA': pico[0] == 3 and w < 8}

# c) ranura ENTRE PROCESOS (como 4b1 y 4c1 juntos): 2 procesos × 4 tareas de 2 s, máx 3 en total
hijo = TMP / 'hijo.py'
hijo.write_text(f"""import sys,time,json;sys.path.insert(0,'{CAJAS}');import paralelo_cadena as PC
from pathlib import Path
def t(i):
    with PC.ranura('argon', Path('{RAN}'), n=3) as r:
        a=time.time(); time.sleep(2); return {{'estado':'ok','ini':a,'fin':time.time()}}
print(json.dumps([r for _,r,_,_ in PC.correr_paralelo(list(range(4)), t, 4)]))""")
t0 = time.time(); ps = [subprocess.Popen([sys.executable, str(hijo)], stdout=subprocess.PIPE) for _ in range(2)]
iv = [x for p in ps for x in json.loads(p.communicate()[0])]; w = time.time() - t0
ev = sorted([(x['ini'], 1) for x in iv] + [(x['fin'], -1) for x in iv]); c = m = 0
for _, d in ev: c += d; m = max(m, c)
R['c_ranura_entre_procesos'] = {'tareas': 8, 'en_fila_s': 16, 'real_s': round(w, 1), 'pico_a_la_vez': m, 'PASA': m <= 3 and w < 9}

# d) ledger con candado: myia_argon REAL con ledger de prueba + transporte simulado (sin red)
LED = TMP / 'ledger_prueba.csv'
os.environ.update(MYIA_ARGON_LEDGER=str(LED), MYIA_FIJO_PROMPT='0', MYIA_T27F_COTIZACION='0')
sys.path[:0] = ['/opt/myia-staging-arreglos-20261026/repo/web', '/opt/myia-staging-arreglos-20261026/repo']
import myia_argon as AR
def correr_ledger(blindado, n=24):
    if LED.exists(): LED.unlink()
    import importlib; A = importlib.reload(AR)
    if blindado: PC.blindar_ledger(A, LED)
    malos = []
    def transp(prompt, modelo, nivel, max_out, json_out, **k):
        fila = [r for r in A._leer() if r['id'] == prompt]
        if not fila or fila[0]['estado'] != 'enviado': malos.append(prompt)   # la fila DEBE estar escrita antes de llamar
        time.sleep(0.3); return {'texto': '{}', 'tokens_entrada': 1000, 'tokens_salida': 500, 'fin': 'STOP'}
    errs = []
    def uno(i):
        try: A.llamar(f'prueba-t358-{i}', f'prueba-t358-{i}', str(TMP / f's{i}.json'), 0.01, 'prueba t358 sin red', transporte=transp, modelo='gemini-4-argon', nivel='HIGH', ok_usd=0.01)
        except Exception as e: errs.append(f'{type(e).__name__}: {str(e)[:120]}')
    ths = [threading.Thread(target=uno, args=(i,)) for i in range(n)]; [t.start() for t in ths]; [t.join() for t in ths]
    filas = A._leer() if LED.exists() else []
    return {'llamadas': n, 'filas_en_ledger': len(filas), 'filas_ok': sum(1 for r in filas if r['estado'] == 'ok'), 'fila_no_escrita_antes': len(malos), 'errores': errs[:3]}
sin = correr_ledger(False); con = correr_ledger(True)
R['d_ledger'] = {'sin_candado': sin, 'con_candado': con, 'PASA': con['filas_en_ledger'] == 24 and con['filas_ok'] == 24 and con['fila_no_escrita_antes'] == 0}

# e) timeout: stream que se cuelga → LlamadaVencida a los 2 s; ledger marca la fila (no queda «enviado»)
import llamada_segura as LS, importlib
A = importlib.reload(AR); PC.blindar_ledger(A, LED)
class _Ch:  # chunk lento
    text = '{'; usage_metadata = None; candidates = None
class _M:
    def generate_content_stream(self, **k):
        while True: time.sleep(0.5); yield _Ch()
class _Cl: models = _M()
A._cliente = lambda: _Cl()
tr = LS.transporte_texto(A, 2); t0 = time.time(); est = None
try: A.llamar('prueba-t358-timeout', 'x', str(TMP / 'to.json'), 0.01, 'prueba timeout', transporte=tr, modelo='gemini-4-argon', nivel='HIGH', ok_usd=0.01); est = 'no cortó'
except Exception as e: est = type(e).__name__; print('EXC', est, str(e)[:300], file=sys.stderr)
print(json.dumps(R, default=str)[:3000], file=sys.stderr); fila = [r for r in A._leer() if r['id'] == 'prueba-t358-timeout'][0]
R['e_timeout'] = {'tope_s': 2, 'corto_a_los_s': round(time.time() - t0, 1), 'excepcion': est, 'es_timeout': LS.es_timeout(LS.LlamadaVencida('x')), 'fila_ledger': fila['estado'],
                  'tope_config_texto_s': LS.tope_s('texto'), 'tope_base_s': PC.timeout_paso('base'), 'tope_objetos_s': PC.timeout_paso('objetos'), 'tope_4b1_s': PC.timeout_paso('inv_obj_historia__obj-x') or LS.tope_s('texto'),
                  'PASA': est == 'LlamadaVencida' and time.time() - t0 < 6 and fila['estado'] != 'enviado' and LS.tope_s('texto') == 360}

# f) prechequeo: esquemas reales del taller (ninguno debe bloquearse) + uno sintético de 250 propiedades (debe bloquearse)
reales = []
for e in sorted((CAJAS / 'FIJOS_TALLER').rglob('esquema.txt')):
    try: reales.append((e.parent.parent.name, PC.prechequeo('x' * 1000, e.read_text())))
    except Exception as exc: reales.append((e.parent.parent.name, [str(exc)]))
grande = {'type': 'object', 'properties': {f'c{i}': {'type': 'string'} for i in range(250)}}
R['f_prechequeo'] = {'esquemas_reales_revisados': len(reales), 'reales_bloqueados': [x for x in reales if x[1]], 'sintetico_250_props': PC.prechequeo('x', grande),
                     'prompt_1M_chars': PC.prechequeo('x' * 1000001, None), 'nota': 'solo deben bloquearse los esquemas 4a1 COMPLETOS (o61/o72, 208-217 props) que Vertex rechazó con 400; hoy se mandan partidos A/B', 'PASA': all(('_4a1_o' in x[0] and not x[0].endswith(('divA','divB'))) for x in reales if x[1]) and bool(PC.prechequeo('x', grande))}

# g) compuerta: 2 procesos a la vez piden 0.6 cada uno contra monto 1.0 → solo uno pasa
RES = TMP / 'reservas.json'; hc = TMP / 'comp.py'
hc.write_text(f"""import sys,time,json;sys.path.insert(0,'{CAJAS}');import paralelo_cadena as PC
time.sleep(max(0, float(sys.argv[1]) - time.time()))
r = PC.reservar_compuerta('{RES}', 1.0, 0.0, 0.6, 'prueba'); print(json.dumps(r)); time.sleep(1.5)""")
go = time.time() + 1; ps = [subprocess.Popen([sys.executable, str(hc), str(go)], stdout=subprocess.PIPE) for _ in range(2)]
outs = [json.loads(p.communicate()[0]) for p in ps]
R['g_compuerta_entre_procesos'] = {'resultados': outs, 'pasaron': sum(1 for o in outs if o is None), 'PASA': sum(1 for o in outs if o is None) == 1}

# h) par_inv real de paso00_cadena con llamar_uno simulado: 5 pedidos de 2 s, máx 3, tope atómico, para si uno falla
os.environ['TALLER_DATOS'] = str(TMP)
import paso00_cadena as C
C.TRABAJO = TMP; llam = []
def falso(a, X, x, tope, limite=None, **k):
    llam.append((x['paso'], limite)); time.sleep(2)
    return {'paso': x['paso'], 'estado': 'error' if x['paso'] == 'malo' else 'ok', 'usd_real': round(x['peor_caso_usd'] * 0.6, 4)}
C.llamar_uno = falso; C.registrar_taller = lambda *a, **k: None
class A_: ok = 1.0; repetir = False; caja = 'investigar_objetos_historia'
D = TMP / 'cap'; (D / 'resultados').mkdir(parents=True)
X = {'D': D, 'FP': None, 'F': None}
pasos = [{'paso': f'inv_obj_historia__o{i}', 'ya_hecho': False, 'peor_caso_usd': 0.19, '_fijo': {}} for i in range(5)]
t0 = time.time(); res = C.par_inv(A_, X, pasos, 0.5, 3); w = time.time() - t0
pl = json.loads((D / 'resultados' / 'investigar_objetos_historia_paralelo.json').read_text())
pasos2 = [{'paso': n, 'ya_hecho': False, 'peor_caso_usd': 0.3, '_fijo': {}} for n in ('malo', 'b', 'c', 'd', 'e')]
res2 = C.par_inv(A_, X, pasos2, 0.5, 1)
pasos3 = [{'paso': f'x{i}', 'ya_hecho': False, 'peor_caso_usd': 0.3, '_fijo': {}} for i in range(4)]   # 1.2 > ok 1.0
res3 = C.par_inv(A_, X, pasos3, 0.5, 3)
R['h_par_inv'] = {'pedidos': 5, 'en_fila_s': 10, 'real_s': round(w, 1), 'estados': [r['estado'] for r in res], 'limite_por_pedido': sorted({l for _, l in llam[:5]}),
                  'max_comprometido_usd': pl['max_comprometido_usd'], 'ok_usd': 1.0,
                  'si_falla_uno_en_fila': [r['estado'] for r in res2], 'si_pasa_lo_aprobado': [r['estado'] for r in res3],
                  'PASA': w < 5 and all(r['estado'] == 'ok' for r in res) and pl['max_comprometido_usd'] <= 1.0 and res2[1]['estado'] == 'no_llamado' and all(r['estado'] == 'no_llamado' for r in res3)}

# i) Blender a la vez con un «blender» falso (no renderiza): 3 escenarios de 2 s, máx 2
import paso00_ramas as RA
fb = TMP / 'blender_falso.py'
fb.write_text("""#!/usr/bin/env python3
import sys, time, json, os
from pathlib import Path
d = Path(sys.argv[-1]); time.sleep(2)
(d / 'cam_1.png').write_bytes(b'x'); (d / 'molde.json').write_text(json.dumps({'ok': True, 'renders': ['cam_1.png'], 'hilos': os.environ.get('MOLDE_HILOS')}))
print('MOLDE_OK')""")
fb.chmod(0o755); DB = TMP / 'capb'
t0 = time.time(); rb = RA.moldes_blender(DB, [{'id': f'esc-{i}'} for i in range(3)], str(fb)); w = time.time() - t0
R['i_blender'] = {'escenarios': 3, 'en_fila_s': 6, 'real_s': round(w, 1), 'a_la_vez': rb.get('blender_a_la_vez'), 'hilos_por_blender': rb.get('hilos_por_blender'), 'ok': rb.get('ok'), 'PASA': rb.get('ok') and w < 5.5}

# j) juntos: solo validación (ok 0 → se salta; caja no permitida → error). No llama a nada.
j1 = C.cmd_juntos(['investigar_objetos_historia:0,investigar_objetos_lugar:0', '--canal', 'prueba', '--aprobado', 'prueba-t358'])
j2 = C.cmd_juntos(['base:0.5', '--canal', 'prueba', '--aprobado', 'prueba-t358'])
R['j_juntos'] = {'ok_cero': {k: j1.get(k) for k in ('ok', 'saltadas', 'cajas')}, 'no_permitida': j2.get('error'), 'PASA': j1.get('ok') and j1.get('saltadas') and 'no permitida' in (j2.get('error') or '')}

R['TODAS_PASAN'] = all(v.get('PASA') for v in R.values() if isinstance(v, dict))
R['carpeta_prueba'] = str(TMP); R['usd'] = 0; R['hora'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
