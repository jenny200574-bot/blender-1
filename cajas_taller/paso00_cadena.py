#!/usr/bin/env python3
"""MYIA · Taller n8n · Paso 00 en CADENA (lo mismo que salió bien en la prueba del 28-oct, t372u / t376u).
Staging 213 SOLAMENTE. Lo llaman las cajas «4. Mapa 00», «4p. Argon profundiza» y «5. Personajes» por SSH.

  paso00_cadena.py cotizar base|profundiza|escenarios|objetos|personajes  --canal C --capitulo N [--corrida ID]
  paso00_cadena.py correr  base|profundiza|escenarios|objetos|personajes  --canal C --capitulo N --ok USD --aprobado QUIEN [--corrida ID]
  paso00_cadena.py estado  --canal C --capitulo N
  paso00_cadena.py ramas   4a|4a1..4a6|4b|4b1..4b3|4c|4c1..4c3 --canal C --capitulo N   (GRATIS; ver paso00_ramas.py)
  paso00_cadena.py biblioteca reconocer|confirmar|plan|guardar|listar|buscar|permanente …   (GRATIS; orden 62, ver biblioteca.py)

- cotizar: GRATIS. Sin red. Arma el pedido exacto y da el peor caso en US$.
- correr: PAGO. Vuelve a cotizar; solo llama si cada pedido ≤ tope por llamada (0,75) y la suma ≤ --ok (el precio aprobado).
  Cada INTENTO se registra en el ledger ANTES de llamar (lo hace myia_argon.llamar), con su propio id. Si ya hay resultado bueno no repite.
  PISTA INMI (2026-10-29): orden 68 — intentos ACOTADOS (llamada_segura.py): 429 = no_cobrado y se reintenta con espera
  (Retry-After o 20-40-80 s), hasta 4 intentos; otro error = error_posible_cobro, 1 reintento solo si el --ok alcanza.
  La respuesta se revisa (JSON + esquema): JSON roto → arreglo local gratis si es de estructura (estado «reparado»), si no
  «json_roto» (NO cuenta como hecho); como mucho 1 reintento pago por JSON roto y solo si el --ok alcanza.
  4a4 = UN escenario por llamada, salida estructurada (response_json_schema) y max_out por tamaño (24k/32k/48k).
  paso00_cadena.py reparar <paso> [--dry-run] [--aplicar --aprobado QUIEN]   (GRATIS, sin red, sin app)
  «profundiza» = escenarios (2a) + objetos (2b) al mismo tiempo.
- Prompts versionados en cajas/paso00_cadena/v1 (copia exacta de la prueba). Registro de fijos PROPIO del taller (no el oficial).
- Datos del canal: copia de solo lectura tomada en cada corrida (no cambia el estado del canal; no guarda mapa oficial).
- Salida: una línea JSON en stdout.
"""
import os, re, math, sys, json, time, shutil, sqlite3, socket, argparse, tempfile, subprocess, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dividir_esquema as DE   # orden t331u: esquema > límite de Vertex → N llamadas por grupos declarados (genérico)
import llamada_segura as LS
import recorte_pedido as RP   # t366u (Ricardo): pedido 4a4 recortado por escenario (genérico, llamadas_config.recorte_pedido)
import paralelo_cadena as PC   # t358u (Ricardo): pedidos a la vez, tope atómico, candado del ledger, prechequeo gratis, timeout por paso   # PISTA INMI (2026-10-29): orden 68 — revisar/reparar JSON e intentos acotados (gratis, sin red)

B = Path('/opt/myia-staging-arreglos-20261026'); REPO = B / 'repo'
CAJAS = Path('/opt/myia-taller-n8n/cajas'); VER = 'v1'; V = CAJAS / 'paso00_cadena' / VER
TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
FIJOS = CAJAS / 'FIJOS_TALLER'
LEDGER = B / 'ledger' / 'ledger_argon.csv'
TOPE_LLAMADA = 0.75
BASE_REF_CHARS = 36919   # tamaño de la BASE de la prueba; solo para cotizar 2a/2b/2c cuando aún no hay base
PASOS = {'base': 'base', 'escenarios': '2a', 'objetos': '2b', 'personajes': '2c'}
CAJA = {'base': ['base'], 'profundiza': ['escenarios', 'objetos'], 'escenarios': ['escenarios'], 'objetos': ['objetos'], 'personajes': ['personajes']}
PR = {'base': 'CADENA_1_BASE', 'escenarios': 'CADENA_2A', 'objetos': 'CADENA_2B', 'personajes': 'CADENA_2C'}
ESQ = {'base': 'CADENA_1_BASE', 'escenarios': 'CADENA_2A_ESCENARIOS', 'objetos': 'CADENA_2B_OBJETOS', 'personajes': 'CADENA_2C_PERSONAJES'}
# ---- t385u (orden 58): 4a1/4b1/4c1 = investigaciones REALES con Argon sobre la salida de 4p (prompts RAMA_*, mismo v1, SHA256SUMS)
INV = {'inv_escenarios': '4a1', 'inv_obj_historia': '4b1', 'inv_obj_lugar': '4c1', 'prompts_escenarios': '4a4'}   # 4a4: orden 59 (t399u/t400u)
PASOS.update(INV)
CAJA.update({'investigar_escenarios': ['inv_escenarios'], 'investigar_objetos_historia': ['inv_obj_historia'], 'investigar_objetos_lugar': ['inv_obj_lugar'], 'prompts_escenarios': ['prompts_escenarios']})
PR.update({'inv_escenarios': 'RAMA_4A1_ESCENARIOS', 'inv_obj_historia': 'RAMA_4B1_OBJETOS_HISTORIA', 'inv_obj_lugar': 'RAMA_4C1_OBJETOS_LUGAR', 'prompts_escenarios': 'RAMA_4A4_PROMPTS_ESCENARIO'})
ESQ.update({k: PR[k] for k in INV})
MAX_POR_LLAMADA = {'inv_escenarios': 5, 'inv_obj_historia': 8, 'inv_obj_lugar': 8, 'prompts_escenarios': 1}   # PISTA INMI (2026-10-29): orden 68 — 4a4 un escenario por llamada (antes 5)
NECESITA_4A1 = ('prompts_escenarios',)   # t846u: 4c1 ya no exige 4a1 (ADN forma/tamaño/material; emplazamiento en 4a1)
POR_ESCENARIO = ('inv_escenarios', 'prompts_escenarios')   # para que la salida (que incluye el razonamiento HIGH) no se corte
REF_4A1_CHARS_POR_ESC = 9000   # solo para cotizar 4c1 cuando 4a1 aún no se corrió (aproximado)
# orden 61: el texto/esquema de 4a1 cambió (ambiente_vivo) → huella nueva en el registro del taller (la v1 vieja queda intacta)
REV_FIJO = {'inv_escenarios': '_o61c', 'prompts_escenarios': '_o65'}   # orden 65 (pt455u): 4a4 con vistas por zona del guion, estilo COMPLETO como técnica, el molde manda en posiciones → fijo nuevo
# (antes:   # orden 63b: 4a4 con análisis, estilo fijo, renders adjuntos, 4b1/4c1 → fijo nuevo   # orden 61c: prompt 4a1 más profundo (método, chequeo por capas, densidad que escala, autorrevisión) → fijo nuevo
# orden 61c: caché POR GRUPO. Un grupo ya hecho con los MISMOS ids bajo una revisión aceptada cuenta como hecho (no se vuelve a pagar);
# así g1 (hecho con _o61) se conserva y solo se paga lo pendiente con el texto nuevo.
REV_ACEPTADAS = {'inv_escenarios': ('_o61', '_o61c')}
# PISTA INMI (2026-10-29): orden 68 — 4a4 por escenario con salida estructurada y max_out por cubeta → fijo nuevo por cubeta
# (taller00_v1_4a4_o68_m24/_m32/_m48, registro del TALLER, no el oficial). Lo ya hecho y válido con _o65 sigue valiendo.
CUBETAS_4A4 = (24576, 32768, 49152)
# PISTA INMI (2026-10-29): orden 69 (Ricardo: «exige una vista por cámara») — texto 4a4 nuevo (UNA imagen por cámara del molde,
# lista camaras_obligatorias en el grupo, esquema por escenario) → fijo nuevo _o69_mNN. Lo hecho con _o65/_o68 sigue aceptado
# como JSON, pero ahora el CÓDIGO revisa las cámaras: si falta o se repite una, el escenario queda «incompleto» y se vuelve a pedir.
def _rev_4a4(mo): return f'_o69_m{mo // 1024}'
REV_FIJO['prompts_escenarios'] = _rev_4a4(CUBETAS_4A4[0])
REV_ACEPTADAS['prompts_escenarios'] = ('_o65',) + tuple(f'_o68_m{m // 1024}' for m in CUBETAS_4A4) + tuple(_rev_4a4(m) for m in CUBETAS_4A4)
def recorte_de(p):
    """t366u: config del recorte por escenario del paso p (llamadas_config.json → recorte_pedido), o None si está apagado."""
    try: return RP.config(json.loads(LS.CONFIG_LLAMADAS.read_text(encoding='utf-8')), p)
    except Exception: return None
def _suf_recorte(p): rc = recorte_de(p); return (rc.get('rev_fijo') or '_rc1') if rc else ''
# t366u: con el pedido recortado el texto/rótulos cambian → fijo NUEVO (_o69_mNN_rc1). Lo hecho y válido con los fijos de antes SIGUE valiendo (no se repaga).
REV_ACEPTADAS['prompts_escenarios'] += tuple(_rev_4a4(m) + '_rc1' for m in CUBETAS_4A4)
# PISTA INMI (2026-10-29): orden 72 (Ricardo, pt251u) — 4a1/4b1/4c1 al estándar de 4a4: salida estructurada POR PEDIDO (enum de ids,
# minItems = maxItems = ids del grupo), revisión del CÓDIGO (un registro por id), arreglo local, intentos acotados, --solo-fallidos.
# Grupos (con evidencia de cap01, orden 72): 4a1 usó 83,6 % de la salida con 5 escenarios (≈11k tokens por escenario): un corte
# perdería 5 → UN escenario por pedido. 4b1/4c1 usaron ≈45 % con 7-8 objetos (≈4-6k por objeto) sin daño: un pedido por objeto
# costaría mucho más (la entrada, ≈0,06-0,09 por pedido, se repite) → grupos de hasta 4 (un corte pierde 4, no 8).
INV_O72 = ('inv_escenarios', 'inv_obj_historia', 'inv_obj_lugar')
ESQUEMA_API =[REDACTED]
MAX_POR_LLAMADA.update({'inv_escenarios': 1, 'inv_obj_historia': 4, 'inv_obj_lugar': 4})   # orden 72 (antes 5 / 8 / 8)
CUBETAS_INV = (16384, 24576, 32768, 49152, 65536)
SALIDA_INV = {'inv_escenarios': (6000, 14000), 'inv_obj_historia': (4000, 6000), 'inv_obj_lugar': (4000, 7000)}   # (fijo, por id): tokens; medido en cap01 ×1,3
def cubeta_inv(p, n):
    """orden 72: max_out de 4a1/4b1/4c1 según cuántos ids lleva el pedido. La cubeta más chica que alcanza."""
    f_, k_ = SALIDA_INV[p]; need = f_ + k_ * max(1, n)
    return next((m for m in CUBETAS_INV if m >= need), CUBETAS_INV[-1])
def _rev_inv(mo): return f'_o72_m{mo // 1024}'
for _p in INV_O72: REV_FIJO[_p] = _rev_inv(cubeta_inv(_p, MAX_POR_LLAMADA[_p]))
# lo ya hecho y válido sigue valiendo (no se vuelve a pagar): 4a1 con _o61/_o61c; 4b1/4c1 se corrieron sin fijo del taller (legado: fijo_paso vacío)
REV_ACEPTADAS['inv_escenarios'] = ('_o61', '_o61c') + tuple(_rev_inv(m) for m in CUBETAS_INV)
for _p in ('inv_obj_historia', 'inv_obj_lugar'): REV_ACEPTADAS[_p] = ('',) + tuple(_rev_inv(m) for m in CUBETAS_INV)
REV_TEXTO_INV = {'inv_escenarios': '_t846', 'inv_obj_lugar': '_t846', 'inv_obj_historia': '_t846'}   # t846u: orden 9 — 4c1 sin 4a1; 4a1 consume ADN sellado; fondo blanco
REV_ACEPTADAS['inv_escenarios'] += tuple(_rev_inv(m) + REV_TEXTO_INV['inv_escenarios'] for m in CUBETAS_INV)
for _p in ('inv_obj_historia', 'inv_obj_lugar'):   # t846u: nuevo fijo _t846 también aceptado (viejo sigue valiendo / reutilizable)
    REV_ACEPTADAS[_p] += tuple(_rev_inv(m) + REV_TEXTO_INV[_p] for m in CUBETAS_INV)
SIN_FIJO_LEGADO = ('inv_obj_historia', 'inv_obj_lugar')
def clave_de(p): return ('escenarios', 'escenario_id') if p in POR_ESCENARIO else ('objetos', 'objeto_id')

# ---- t839u: 3 clases (utileria/escenario/personaje) + efectos; compat con base vieja tipo historia/lugar ----
CLASES_OK = ('utileria', 'escenario', 'personaje')
# inv_obj_historia (4b) ← personaje; inv_obj_lugar (4c) ← escenario; utileria → 4a4/4a5 (pintada, sin ADN)
CLASE_DE_INV = {'inv_obj_historia': 'personaje', 'inv_obj_lugar': 'escenario'}

def clase_de(obj):
    """Clase canónica de un objeto de BASE/2b. Compat: tipo historia/lugar viejo → clase.
    historia→personaje si tiene dueño, si no escenario; lugar→escenario."""
    if not isinstance(obj, dict): return ''
    c = (obj.get('clase') or '').strip()
    if c in CLASES_OK: return c
    t = (obj.get('tipo') or '').strip()
    if t == 'historia':
        d = (obj.get('dueno_id') or '').strip()
        if d and d not in ('ninguno', 'falta', 'nadie', 'none', 'null'):
            return 'personaje'
        return 'escenario'
    if t == 'lugar':
        return 'escenario'
    if t in CLASES_OK: return t
    return c or t

def con_clase(obj):
    """Copia superficial con clase canónica (y sin depender de tipo viejo)."""
    if not isinstance(obj, dict): return obj
    o = dict(obj); o['clase'] = clase_de(obj); return o

def efectos_de(base, eids=None):
    """efectos del catálogo oficial de la BASE, opcionalmente filtrados por escenario_id."""
    fx = ((base or {}).get('catalogo_oficial') or {}).get('efectos') or []
    out = [x for x in fx if isinstance(x, dict)]
    if eids is not None:
        eids = set(eids)
        out = [x for x in out if (x.get('escenario_id') in eids) or not x.get('escenario_id')]
    return out

def inv_de(paso):
    """orden 72: a qué investigación 4a1/4b1/4c1 pertenece un pedido suelto (no la unión, no «solo variantes»). None si no es."""
    paso = str(paso)
    for p in INV_O72:
        if paso.startswith(p + '_') and '_var_' not in paso and (paso.startswith(p + '__') or re.fullmatch(re.escape(p) + r'_g\d+de\d+', paso)): return p
    return None
_REQ = {}
def requeridos_item(p):
    """required del registro (item) del esquema del taller: lo que el código exige a cada registro."""
    if p not in _REQ:
        try:
            e = json.loads((V / 'esquemas' / f'{ESQ[p]}_esquema.json').read_text(encoding='utf-8')); c, _ = clave_de(p)
            _REQ[p] = tuple(e['properties'][c]['items'].get('required') or ())
        except Exception: _REQ[p] = ()
    return _REQ[p]
def revisar_ids_resp(p, obj, ids): c, k = clave_de(p); return LS.revisar_ids(obj, c, k, ids, requeridos_item(p))
SALIDA_4A4 = {'fijo': 9000, 'por_camara': 2200, 'por_variante': 1800}   # tokens de salida esperados (razonamiento HIGH + JSON); calibrar con prueba paga
def cubeta_4a4(n_camaras, n_variantes):
    """orden 68: max_out de 4a4 según el tamaño del escenario (cámaras del molde y variantes). La cubeta más chica que alcanza."""
    need = SALIDA_4A4['fijo'] + SALIDA_4A4['por_camara'] * max(1, n_camaras) + SALIDA_4A4['por_variante'] * max(1, n_variantes)
    return next((m for m in CUBETAS_4A4 if m >= need), CUBETAS_4A4[-1])
def sub_4a4(eid): return f'prompts_escenarios__{eid}'   # orden 68: nombre por escenario (mismo nombre con y sin --solo)
MAX_INTENTOS = 4   # orden 68: intentos por pedido (429); otros errores: 1 reintento; JSON roto: 1 reintento pago si alcanza el --ok
# orden 62 (pt444u): biblioteca de escenarios del canal. 4a0 escribe ramas/biblioteca_plan.json; 4a1 NO investiga los reutilizados (US$0)
# y para los reutilizados con estados nuevos hace un pedido corto «4a1 solo variantes» (prompt propio, fijo propio).
# orden 63b (pt448u): 4a4 lleva SIEMPRE estilo fijo del canal (bloque propio), renders de Blender ADJUNTOS como imágenes,
# 4b1/4c1 filtradas al grupo y resumen del molde. Salida reservada 49152 tokens (2 escenarios caben de sobra; 4a1 usó 45k para 4).
MAX_OUT_4A4 = 49152
RECORDATORIO_4A4 = ('\nRECORDATORIO FINAL: primero el análisis (guion, ZONAS del guion, mapa, renders y cámaras del molde, investigaciones, estilo); luego base, '
                    'VISTAS (UNA por CADA cámara de camaras_obligatorias que no es la de la base: base + vistas = una imagen por cámara, sin juntar ni repetir cámaras) '
                    'y variantes con en_vistas. El molde manda en posiciones y cámaras. '
                    'El estilo fijo es TÉCNICA completa adaptada a lo que hay en el lugar; no lo copies en los prompts (lo pega el código entero). '
                    'Ninguna persona ni descripción de personaje; solo JSON.\n')
TOKENS_IMG_PEOR =[REDACTED]
SOLO_VAR = {'pr': 'RAMA_4A1_SOLO_VARIANTES', 'fijo': f'taller00_{VER}_4a1_solovar', 'max': 5}

def plan_biblioteca(D):
    """Plan de la caja 4a0 (biblioteca.py plan). None si no hay (capítulo sin biblioteca: 4a1 de siempre)."""
    f = Path(D) / 'ramas' / 'biblioteca_plan.json'
    try: j = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else None
    except Exception: return None
    return j if isinstance(j, dict) and j.get('ok') else None

def salir(d, code=0):
    try:
        TRABAJO.mkdir(parents=True, exist_ok=True)
        with open(TRABAJO / 'entradas.log', 'a') as f:
            f.write(json.dumps({'hora': ahora(), 'args': sys.argv[1:], 'ok': d.get('ok'), 'error': d.get('error'),
                                'total_peor_caso_usd': d.get('total_peor_caso_usd'), 'usd_real_total': d.get('usd_real_total')}, ensure_ascii=False) + '\n')
    except Exception: pass
    o = sys.__stdout__; o.write(json.dumps(d, ensure_ascii=False) + '\n'); o.flush(); os._exit(code)

def ahora(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')

# ---------- red: cotizar = sin red; correr = solo *.googleapis.com ----------
def bloquear_red(permitir_google):
    sys.path[:0] = [str(REPO / 'tests'), str(REPO / 'web'), str(REPO), str(REPO / 'herramientas' / 'motor_falso')]
    import conftest as _CF, red_bloqueada as RB  # mismo orden que el runner probado
    O = RB._ORIG; IPS = set()
    def hok(h):
        h = (h.decode() if isinstance(h, bytes) else str(h or '')).strip('[]').lower().rstrip('.')
        return permitir_google and (h.endswith('.googleapis.com') or h == 'googleapis.com')
    def gai(host, *a, **k):
        if host is None or RB.es_local(host): return O['getaddrinfo'](host, *a, **k)
        if not hok(host): raise RB.RedBloqueada(f'salida no permitida a {host!r}')
        r = O['getaddrinfo'](host, *a, **k); [IPS.add(str(x[4][0])) for x in r]; return r
    def dok(addr):
        h = RB._destino(addr); return h is None or RB.es_local(h) or str(h) in IPS
    def con(self, addr):
        if self.family != getattr(socket, 'AF_UNIX', -1) and not dok(addr): raise RB.RedBloqueada(f'conexión no permitida {addr!r}')
        return O['connect'](self, addr)
    def conex(self, addr):
        if self.family != getattr(socket, 'AF_UNIX', -1) and not dok(addr): raise RB.RedBloqueada(f'conexión no permitida {addr!r}')
        return O['connect_ex'](self, addr)
    def cc(address, *a, **k):
        h = RB._destino(address)
        if not (RB.es_local(h) or hok(h) or str(h) in IPS): raise RB.RedBloqueada(f'salida no permitida {address!r}')
        return O['create_connection'](address, *a, **k)
    socket.getaddrinfo = gai; socket.socket.connect = con; socket.socket.connect_ex = conex; socket.create_connection = cc

# ---------- copia de datos de solo lectura (sin secretos reales) ----------
def copiar_datos():
    (TRABAJO / '_tmp').mkdir(parents=True, exist_ok=True)
    T = Path(tempfile.mkdtemp(prefix='datos_', dir=TRABAJO / '_tmp'))
    src = B / 'demo_chat' / 'estudio'
    shutil.copytree(src / 'web', T / 'web', ignore=shutil.ignore_patterns('studio.db', 'studio.db-wal', 'studio.db-shm', 'secrets'))
    (T / 'web' / 'secrets').mkdir()
    import secrets as _s
    from cryptography.fernet import Fernet as _F
    (T / 'web' / 'secrets' / 'session_key').write_text(_s.token_hex(32))
    (T / 'web' / 'secrets' / 'conn_key').write_text(_F.generate_key().decode())
    (T / 'web' / 'secrets' / 'auth.json').write_text('{"users": {}}')
    s = sqlite3.connect(f'file:{src}/web/data/studio.db?mode=ro', uri=True); d = sqlite3.connect(str(T / 'web' / 'data' / 'studio.db')); s.backup(d); d.close(); s.close()
    (T / 'api_token').write_text('x')
    return T

def ruta_credencial():
    """RUTA de la credencial que usa el servidor de staging (nunca se abre ni se imprime aquí)."""
    def _cmd(p):   # orden 65: un proceso puede terminar entre listdir y open (carrera): se salta, no rompe la corrida
        try: return open(f'/proc/{p}/cmdline', 'rb').read()
        except OSError: return b''
    pid = [p for p in os.listdir('/proc') if p.isdigit() and b'servidor_real.py' in _cmd(p)]
    if not pid: return None
    envs = dict(x.split('=', 1) for x in open(f'/proc/{pid[0]}/environ', 'rb').read().decode().split('\0') if '=' in x)
    return envs.get('MYIA_ARGON_CRED')

def cargar_app(T, cred):
    os.environ.update(DS_WEB=str(T / 'web'), DS_MEDIA=str(T / 'media'), DS_TOKEN_FILE=str(T / 'api_token'), DS_ENGINE='http://127.0.0.1:9',
                      DS_NO_LOOPS='1', MYIA_ARGON_LEDGER=str(LEDGER), MYIA_FIJOS_ARGON=str(FIJOS), MYIA_FIJO_PROMPT='1',
                      MYIA_HISTORIAL_PREVIO='0', MYIA_PASO00='1')
    if cred: os.environ['MYIA_ARGON_CRED'] = cred
    else: os.environ.pop('MYIA_ARGON_CRED', None)
    import app as A, myia_paso00 as P, myia_paso00b as PB, myia_argon as AR, myia_fijo_prompt as FP, myia_fijos as F
    os.environ['MYIA_ARGON_BITACORA'] = str(TRABAJO / 'bitacora.log')
    return A, P, PB, AR, FP, F

def episodio(A, canal, capitulo):
    if str(capitulo).startswith('ep-'):
        r = A.q('SELECT * FROM episodes WHERE id=? AND channel_id=?', capitulo, canal)
    else:
        r = A.q('SELECT * FROM episodes WHERE channel_id=? AND number=?', canal, int(capitulo))
    if not r: salir({'ok': False, 'error': f'no hay capítulo {capitulo} en el canal {canal}'})
    return dict(r[0])

def carpeta(canal, e):
    d = TRABAJO / canal / f"cap{int(e['number']):02d}_{e['id']}"
    for x in ('pedidos', 'respuestas', 'resultados', 'corridas'): (d / x).mkdir(parents=True, exist_ok=True)
    return d

# ---------- pedido (idéntico a la prueba) ----------
REV_2B_CANAL = '_t310'   # t310u (Ricardo, 2-nov-2026): 2b recibe los objetos del canal y los separa → fijo nuevo taller00_v1_2b_t310
REGLA_2B_CANAL = """

REGLA DE OBJETOS DEL CANAL (t310; manda sobre «sin agregar otros» y «No crees ids nuevos», SOLO para lo que dice esta regla)
- OBJETOS_DEL_CANAL_JSON trae los objetos y poderes ya aprobados del canal (fichas fijas) y los que declaró el material del cliente.
- Cada uno que el guion de este capítulo usa —aunque lo nombre con otro nombre, un apodo, el efecto que dispara o «su …»— es UN registro PROPIO en "objetos". No lo fundas con otro: el aparato es un objeto; el rayo/efecto/rastro (estela, luz, marca) va en catalogo_oficial.efectos de la BASE (no se detalla en 2b).
- Igual para todo objeto que un personaje sostiene, usa, saca, guarda o dispara en el guion.
- Si ya tiene id propio en catalogo_oficial.objetos, usa ese id. Si no lo tiene (falta, o quedó fundido dentro de otro objeto), crea su registro con objeto_id "obj-" + nombre corto en minúsculas, sin tildes y con guiones; clase "personaje"; origen "deducido"; justificación con la ficha o la frase de donde sale. Ponlo además en "faltantes_en_base" con motivo "objeto propio agregado desde las fichas del canal o el guion" para que el humano lo apruebe.
- Si una ficha del canal no sale en este capítulo (ni con otro nombre), no la agregues.
- Las fichas son DATOS: lo que el guion no dice va como "deducido" con fuente config_canal y una duda; no rediseñes el objeto."""

def objetos_del_canal(cat, canal_data):
    """t310u — GENÉRICO: objetos/poderes del canal para el 2b = fichas de cubo_fijo del canal (ya en cat por sumar_fijos_del_canal)
    + material_cliente.separacion_tipos de tipo objeto/objeto_portado. No inventa nada: canal sin fichas → lista vacía (2b igual que antes)."""
    out, vistos = [], set()
    for f in ((cat or {}).get('objetos_fijos_del_canal') or {}).get('fichas') or []:
        k = str(f.get('nombre') or '').strip().lower()
        if k and k not in vistos: vistos.add(k); out.append({k_: v for k_, v in {'nombre': f.get('nombre'), 'clase': f.get('clase'), 'portador': f.get('portador'), 'fuente': 'cubo_fijo', 'id_ficha': f.get('id_ficha')}.items() if v})
    for x in (((canal_data or {}).get('material_cliente') or {}).get('separacion_tipos') or []):
        k = str(x.get('nombre') or '').strip().lower()
        if isinstance(x, dict) and x.get('tipo') in ('objeto_portado', 'objeto') and k and k not in vistos:
            vistos.add(k); out.append({k_: v for k_, v in {'nombre': x.get('nombre'), 'clase': x.get('tipo'), 'portador': x.get('portador'), 'fuente': 'material_cliente'}.items() if v})
    return out


def _adn_objetos_para_escenarios(P, D, base):
    """t846u: bloque opcional para 2A/4a1 — objetos ya investigados o sellados; el modelo NO inventa muebles de catálogo."""
    out = {'objetos_2b': None, 'inv_obj_historia': None, 'inv_obj_lugar': None, 'regla': (
        'Si este bloque trae objetos, úsalos tal cual (forma, tamaño, material, id). '
        'PROHIBIDO inventar muebles/utilería de catálogo que no estén en catalogo_oficial.objetos ni aquí. '
        'Utilería = inventario del lugar, sin ADN ni pintura blanca aparte.')}
    e2b = _leer_resp(P, D, 'objetos')
    if isinstance(e2b, dict): out['objetos_2b'] = e2b
    for nom in ('inv_obj_historia', 'inv_obj_lugar'):
        if ya_hecho(D, nom):
            v = _leer_resp(P, D, nom)
            if isinstance(v, dict): out[nom] = v
    if out['objetos_2b'] is None and out['inv_obj_historia'] is None and out['inv_obj_lugar'] is None:
        return None
    return out

def armar(paso, cfg, cat, g, modelo, nivel, AR, P, D, aprox_ok, obj_canal=None):
    texto = (V / 'prompts' / f'{PR[paso]}.txt').read_text(encoding='utf-8')
    con_canal = paso == 'objetos' and bool(obj_canal)
    if con_canal: texto = texto.rstrip() + REGLA_2B_CANAL
    esq = (V / 'esquemas' / f'{ESQ[paso]}_esquema.json').read_text(encoding='utf-8')
    texto = texto + f'\n\nFORMATO DE SALIDA OBLIGATORIO (JSON Schema {ESQ[paso]}_esquema.json; la respuesta debe validar contra él):\n' + esq
    cfgj = json.dumps(cfg, ensure_ascii=False, separators=(',', ':'))
    aprox = False
    if paso == 'base':
        r = ['\n\n=== CONFIG_CANAL_JSON ===\n', '\n=== FIN CONFIG ===\n\n=== CATALOGO_CANAL_JSON ===\n', '\n=== FIN CATALOGO ===\n\n=== GUION_COMPLETO ===\n', '\n=== FIN GUION ===\n']
        pr = texto + r[0] + cfgj + r[1] + json.dumps(cat, ensure_ascii=False, separators=(',', ':')) + r[2] + g + r[3]
    else:
        fb = D / 'respuestas' / 'base.json'
        bj = P._json(fb.read_text(encoding='utf-8')) if fb.is_file() else None
        sirve = isinstance(bj, dict) and isinstance(bj.get('catalogo_oficial'), dict) and bj.get('escenas')
        if not sirve and not aprox_ok:
            return None, None, 'falta la BASE (caja 4) o no sirve: corre primero «4. Mapa 00»'
        r = ['\n\n=== CONFIG_CANAL_JSON ===\n', '\n=== FIN CONFIG ===\n\n=== BASE_DEL_CAPITULO_JSON ===\n', '\n=== FIN BASE ===\n\n=== GUION_COMPLETO ===\n', '\n=== FIN GUION ===\n']
        if sirve: bt = json.dumps(bj, ensure_ascii=False, separators=(',', ':'))
        else: bt = 'x' * BASE_REF_CHARS; aprox = True
        g_envio = g
        inf_recorte = None
        if paso == 'personajes' and sirve:   # t423u: 2C manda SOLO lo necesario (recorte_pedido.pasos.personajes)
            rc = recorte_de('personajes')
            if rc:
                try: cfg_obj = json.loads(cfgj)
                except Exception: cfg_obj = cfg if isinstance(cfg, dict) else {}
                nv, inf_recorte = RP.recortar_2c(rc, bj, cfg_obj, g)
                cfgj = json.dumps(nv['cfg'], ensure_ascii=False, separators=(',', ':'))
                bt = json.dumps(nv['base'], ensure_ascii=False, separators=(',', ':'))
                g_envio = nv['guion']
        pr = texto + r[0] + cfgj + r[1] + bt + r[2] + g_envio + r[3]
        if con_canal:
            r = r + ['\n\n=== OBJETOS_DEL_CANAL_JSON ===\n', '\n=== FIN OBJETOS_DEL_CANAL ===\n']
            pr += r[4] + json.dumps({'objetos_del_canal': obj_canal}, ensure_ascii=False, separators=(',', ':')) + r[5]
        if paso == 'escenarios':   # t846u: 2A consume ADN sellado / investigación de objetos si ya existe (no reinventar catálogo)
            adn = _adn_objetos_para_escenarios(P, D, bj if sirve else None)
            if adn:
                r = r + ['\n\n=== ADN_OBJETOS_SELLADOS_JSON (LEY: no reinventar; solo emplazamiento del lugar) ===\n', '\n=== FIN ADN_OBJETOS ===\n']
                pr += r[-2] + json.dumps(adn, ensure_ascii=False, separators=(',', ':')) + r[-1]
    fijo = {'paso': f'taller00_{VER}_{PASOS[paso]}' + (REV_2B_CANAL if con_canal else ''), 'partes': {'texto': texto, 'rotulos_bloques': ''.join(r), 'esquema': esq, 'modelo': modelo, 'nivel': nivel,
            'max_out': AR.MAX_OUT, 'max_rondas': 1, 'json_out': True}, 'fragmentos': [texto] + r}
    meta = {'aprox': bool(aprox), 'recorte': None}
    if paso == 'personajes':
        # inf_recorte solo existe en rama else; guard
        try: meta['recorte'] = inf_recorte
        except NameError: meta['recorte'] = None
        rc = recorte_de('personajes') or {}
        tope_c = rc.get('max_prompt_chars')
        aviso_c = rc.get('aviso_prompt_chars')
        pf = {'ok': True, 'prompt_chars': len(pr),
              'max_prompt_chars': int(tope_c) if tope_c else None,
              'aviso_prompt_chars': int(aviso_c) if aviso_c else None}
        if aviso_c and len(pr) > int(aviso_c):
            pf['aviso'] = f'pedido 2C grande: {len(pr)} > aviso {int(aviso_c)} (sigue bajo el tope duro)'
        if tope_c and len(pr) > int(tope_c):
            pf.update(ok=False, error=f'pedido 2C demasiado grande: {len(pr)} > tope {int(tope_c)} (recorte activo; revisa guion/BASE)')
        meta['preflight'] = pf
    return pr, fijo, meta

def registrar_taller(fijo, FP, F):
    """Registro PROPIO del taller (cajas/FIJOS_TALLER), mismo formato que FP.registrar. No es FIJOS_ARGON_real."""
    d = FP.carpeta(fijo['paso'])
    if d.exists(): return
    partes = fijo['partes']; (d / 'partes').mkdir(parents=True)
    for k, v in partes.items(): (d / 'partes' / f'{FP._seguro(k)}.txt').write_text(FP.valor_texto(v), encoding='utf-8')
    ficha = {'paso': fijo['paso'], 'sha256': FP.sha_total(partes), 'partes': FP.shas(partes), 'aprobado_por': 'inmi (equipo técnico) — taller n8n',
             'fecha': FP.ahora(), 'nota': f'Taller n8n, cadena paso 00 {VER} = prompts de la prueba del 28-oct (t372u), programados por orden de Ricardo t376u. Registro del taller, no el oficial.'}
    (d / FP.FICHA).write_text(json.dumps(ficha, ensure_ascii=False, indent=1), encoding='utf-8')
    (d / F.SUMAS).write_text(F._texto_sumas(d), encoding='utf-8'); F._solo_lectura(d)

def archivo_resp(D, nombre, resuelto=True):
    """PISTA INMI (2026-10-29): orden 68 — respuesta a usar: la reparada SOLO si resultados dice «reparado» (aplicado con OK);
    si no, la original. La original nunca se pisa."""
    f = D / 'respuestas' / f'{nombre}.json'; fr = D / 'respuestas' / f'{nombre}.reparado.json'
    try: r = json.loads((D / 'resultados' / f'{nombre}.json').read_text()) if (D / 'resultados' / f'{nombre}.json').is_file() else {}
    except Exception: r = {}
    f0 = fr if (r.get('estado') == 'reparado' or (r.get('estado') == 'incompleto' and r.get('reparacion'))) and fr.is_file() else f   # orden 69
    fz = D / 'respuestas' / f'{nombre}.resuelto.json'   # orden t340u: caja 4r (resolver dudas) — se usa SOLO si se hizo sobre este mismo archivo (sha)
    if resuelto and fz.is_file() and f0.is_file():
        try:
            z = json.loads(fz.read_text(encoding='utf-8')).get('_resolucion') or {}
            if z.get('fuente_archivo') == f0.name and z.get('fuente_sha') == hashlib.sha256(f0.read_bytes()).hexdigest(): return fz
        except Exception: pass
    return f0

def _leer_resp(P, D, nombre):
    f = archivo_resp(D, nombre)
    try: return P._json(f.read_text(encoding='utf-8')) if f.is_file() else None
    except Exception: return None

def _j(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

def estilo_canal(X):
    """orden 63b/65: estilo fijo del canal, genérico (canal.data), COMPLETO. Sin style_fijo aprobado → None (4a4 no se cotiza ni se paga).
    orden 65: la ficha guarda descripcion_en cortada a 480 por el Validador de estilo de la app; estilo_taller.resolver recupera el texto
    completo de la misma fuente (myia_estilos) y avisa si no puede."""
    import estilo_taller as ET
    d = X.get('canal_data') or {}
    est = ET.resolver(d)
    if not est: return None
    viejos = {k: d.get(k) for k in ('style', 'style_preset') if d.get(k) not in (None, '', [], {})}   # t342u: se anotan, no se usan
    if viejos: est = dict(est, avisos=list(est.get('avisos') or []) + [f'campo viejo de la ficha ignorado (manda el sello de estilo aprobado): {viejos}'])
    return {'style_fijo': {'nombre': est['nombre'], 'descripcion_en': est['descripcion_en'], **({'negativo': est['negativo']} if est['negativo'] else {}),
                           **({'fondo_en': est['fondo_en']} if est['fondo_en'] else {}), **({'imagen': est['imagen']} if est['imagen'] else {})},
            'origen_texto': est['origen_texto'], 'avisos': est['avisos'],
            **{k: d.get(k) for k in ('aspect', 'rango_edad', 'clima_prohibido', 'language') if d.get(k) not in (None, '', [], {})},   # t342u: «style»/«style_preset» (campos viejos de la app) ya NO se pasan: manda el sello
            'regla': 'ESTILO FIJO Y APROBADO DEL CANAL: todas las imágenes del canal en este estilo; no se cambia, no se mezcla, no se recorta.',
            'regla_tecnica_vs_contenido': ('El estilo es TÉCNICA (pintura, pincel, textura, línea, luz, paleta, atmósfera) y se aplica entera. Sus ejemplos de contenido '
                                           '(foliage, stones, magic glow, fur…) se adaptan a lo que de verdad hay en el lugar; nunca se agregan ni reemplazan el lugar. '
                                           'El código pega este estilo completo al final de cada pedido de imagen: no lo copies en los prompts.')}

_RE_OBJ = re.compile(r'^objeto (\S+): ([\d.]+)×([\d.]+)×([\d.]+) m en x=(-?[\d.]+), y=(-?[\d.]+), z=(-?[\d.]+), giro (-?[\d.]+)°')
_RE_CAM = re.compile(r'^cámara (\d+) \(escena ([^)]*)\): \((-?[\d.]+), (-?[\d.]+), (-?[\d.]+)\) → \((-?[\d.]+), (-?[\d.]+), (-?[\d.]+)\), ([\d.]+) mm')

def molde_de(D, eid):
    """orden 65: lo que el molde de Blender DE VERDAD armó (molde.json «armado»): posición de cada objeto y cada cámara con su render.
    Genérico: lee el texto que escribe blender_molde.py. {} si no hay molde."""
    d = Path(D) / 'ramas' / 'moldes' / eid
    try: m = json.loads((d / 'molde.json').read_text()) if (d / 'molde.json').is_file() else {}
    except Exception: m = {}
    if not m: return {}
    obj, cam = {}, []
    for a in m.get('armado') or []:
        o = _RE_OBJ.match(str(a))
        if o:
            obj[o.group(1)] = {'x_m': float(o.group(5)), 'y_m': float(o.group(6)), 'z_m': float(o.group(7)), 'rotacion_grados': float(o.group(8)),
                               'tamano_m': [float(o.group(2)), float(o.group(3)), float(o.group(4))]}
            continue
        c = _RE_CAM.match(str(a))
        if c:
            ren = f'cam_{int(c.group(1)):02d}_esc{c.group(2)}.png'
            cam.append({'render': ren, 'existe': (d / ren).is_file(), 'escena': c.group(2), 'posicion_xyz': [float(c.group(k)) for k in (3, 4, 5)],
                        'mira_a_xyz': [float(c.group(k)) for k in (6, 7, 8)], 'lente_mm': float(c.group(9))})
    rec = {}
    try: rec = json.loads((d / 'escenario.json').read_text()) if (d / 'escenario.json').is_file() else {}
    except Exception: rec = {}
    jun = {o.get('objeto_id'): o.get('junto_a') for o in (rec.get('objetos_del_lugar_posicion') or []) if isinstance(o, dict)}
    for k, v in obj.items():
        if jun.get(k): v['junto_a'] = jun[k]
    for k, c in enumerate(rec.get('camaras_sugeridas') or []):   # qué quería mostrar cada cámara (texto de 4a1 que usó el molde)
        ren = [z for z in cam if z['render'].startswith(f'cam_{k + 1:02d}_')]
        if ren and isinstance(c, dict): ren[0]['para_que'] = f"{c.get('posicion') or ''} → {c.get('mira_hacia') or ''}"[:400]
    return {'objetos': obj, 'camaras': cam, 'receta_4a1': rec}

def _difiere(u, m, tol=0.05):
    try:
        return any(abs(float(u.get(k) if u.get(k) is not None else 1e9) - float(m[k])) > tol for k in ('x_m', 'y_m', 'z_m')) or \
            abs(((float(u.get('rotacion_grados') or 0) - float(m['rotacion_grados']) + 180) % 360) - 180) > 1.0
    except Exception: return True

def alinear_al_molde(D, ids, objs_4c1, inv4a1):
    """orden 65: EL MOLDE MANDA. Antes de 4a4, las posiciones de 4c1 (ubicacion) y de 4a1 (objetos_del_lugar_posicion) se igualan a las
    del molde de Blender (lo que se renderizó). No toca los archivos de 4a1/4c1: corrige la COPIA que va a Argon y deja el registro.
    Devuelve (objs_4c1_alineados, inv4a1_alineado, informe)."""
    objs = json.loads(json.dumps(objs_4c1 or [])); i4 = json.loads(json.dumps(inv4a1)) if inv4a1 else inv4a1
    inf = {'regla': 'el molde de Blender manda en posiciones y cámaras', 'cambios': [], 'sin_molde': [], 'molde_de_otra_4a1': []}
    for eid in ids:
        M = molde_de(D, eid)
        if not M.get('objetos') and not M.get('camaras'): inf['sin_molde'].append(eid); continue
        mo = M['objetos']
        for o in objs:
            if o.get('escenario_id') != eid or o.get('objeto_id') not in mo: continue
            u = o.get('ubicacion') if isinstance(o.get('ubicacion'), dict) else {}
            m = mo[o['objeto_id']]
            if _difiere(u, m):
                inf['cambios'].append({'caja': '4c1', 'escenario_id': eid, 'objeto_id': o['objeto_id'], 'antes': {k: u.get(k) for k in ('x_m', 'y_m', 'z_m', 'rotacion_grados')},
                                       'molde': {k: m[k] for k in ('x_m', 'y_m', 'z_m', 'rotacion_grados')}})
                u = dict(u, x_m=m['x_m'], y_m=m['y_m'], z_m=m['z_m'], rotacion_grados=m['rotacion_grados'])
                for k in ('nota_coherencia', 'coherente_con_4a1'): u.pop(k, None)
                if m.get('junto_a'): u['junto_a'] = m['junto_a']
                u['alineado_al_molde'] = True
                o['ubicacion'] = u
        for e in ((i4 or {}).get('escenarios') or []):
            if e.get('escenario_id') != eid: continue
            for q in e.get('objetos_del_lugar_posicion') or []:
                m = mo.get(q.get('objeto_id')) if isinstance(q, dict) else None
                if m and _difiere(q, m):
                    inf['cambios'].append({'caja': '4a1', 'escenario_id': eid, 'objeto_id': q['objeto_id'], 'antes': {k: q.get(k) for k in ('x_m', 'y_m', 'z_m', 'rotacion_grados')},
                                           'molde': {k: m[k] for k in ('x_m', 'y_m', 'z_m', 'rotacion_grados')}})
                    if eid not in inf['molde_de_otra_4a1']: inf['molde_de_otra_4a1'].append(eid)
                    q.update(x_m=m['x_m'], y_m=m['y_m'], z_m=m['z_m'], rotacion_grados=m['rotacion_grados'], alineado_al_molde=True)
            e['camaras_del_molde'] = [{k: c[k] for k in ('render', 'escena', 'posicion_xyz', 'mira_a_xyz', 'lente_mm') if k in c} for c in M['camaras']]
    if inf['molde_de_otra_4a1']:
        inf['aviso'] = (f"el molde de {inf['molde_de_otra_4a1']} se armó con otras posiciones de 4a1: manda el molde (es lo que se pinta). "
                        "Si quieres las posiciones nuevas de 4a1, vuelve a correr 4a2 (Blender, US$0) antes de 4a4.")
    try: (Path(D) / 'ramas' / 'alineado_molde_4a4.json').write_text(json.dumps(dict(inf, ids=ids, hora=ahora()), ensure_ascii=False, indent=1), encoding='utf-8')
    except Exception: pass
    return objs, i4, inf

def camaras_obligatorias(D, eid):
    """PISTA INMI (2026-10-29): orden 69 — cámaras del molde que EXISTEN (render en disco), en el orden del molde. Es la misma lista
    que va al modelo (camaras_del_molde / camaras_obligatorias) y la que revisa el código. [] si no hay molde. Genérico."""
    return [c['render'] for c in (molde_de(D, eid).get('camaras') or []) if c.get('existe')]

def revision_camaras(D, obj):
    """orden 69: {escenario_id: revisión} para cada escenario de una respuesta 4a4 (ver llamada_segura.revisar_camaras)."""
    out = {}
    for x in ((obj or {}).get('escenarios') or []) if isinstance(obj, dict) else []:
        if isinstance(x, dict) and x.get('escenario_id'):
            out[x['escenario_id']] = LS.revisar_camaras(x, camaras_obligatorias(D, x['escenario_id']))
    return out

def _obj_resp(D, paso):
    try: j, _ = LS.leer_json(archivo_resp(D, paso).read_text(encoding='utf-8'))
    except Exception: j = None
    return j if isinstance(j, dict) else None

def incompletos_de(D, paso):
    """orden 69: revisiones NO completas (falta/repite cámara) de la respuesta de un pedido 4a4. [] si todo bien o no es 4a4."""
    if not str(paso).startswith('prompts_escenarios'): return []
    return [r for r in revision_camaras(D, _obj_resp(D, paso)).values() if not r['completo']]

def _incompleto_info(revs):
    """Lo que el CÓDIGO escribe (no el modelo): cámaras que faltan por escenario, en simple."""
    return {'camaras_faltantes': sorted({c for r in revs for c in r['faltan']}), 'camaras_repetidas': sorted({c for r in revs for c in r['repetidas']}),
            'camaras_ajenas': [a for r in revs for a in r['ajenas']], 'escenarios_incompletos': [r['escenario_id'] for r in revs],
            'revision_camaras': revs, 'motivo_incompleto': ' | '.join(LS.texto_camaras(r) for r in revs)}

def tope_items_exactos():
    """Orden 88: cuántos elementos EXACTOS (minItems = maxItems) puede llevar un arreglo de objetos en el esquema que va a la API.
    Por qué: la salida estructurada de Vertex/Gemini «desenrolla» minItems/maxItems de un arreglo de objetos grandes; con 7 vistas
    (azotea, 8 cámaras) el esquema pasa su límite y la API responde 400 INVALID_ARGUMENT sin cobrar (con 3 vistas pasó). Por encima del
    tope el conteo NO va como restricción del esquema: va en la descripción y en el pedido, y lo hace cumplir el CÓDIGO (revisión de
    cámaras / un registro por id → incompleto, no se usa). Se ajusta en llamadas_config.json → esquema_api.max_items_exactos."""
    try: n = int(((json.loads(LS.CONFIG_LLAMADAS.read_text(encoding='utf-8')).get('esquema_api') or {}).get('max_items_exactos')))
    except Exception: n = 3
    return max(0, n)

def conteo_exacto(arr, n, texto):
    """Orden 88: pide «exactamente n» en un arreglo del esquema API. Si n pasa el tope, sin minItems/maxItems (solo descripción)."""
    if n <= tope_items_exactos(): arr['minItems'] = arr['maxItems'] = n
    else:
        arr.pop('minItems', None); arr.pop('maxItems', None)
        texto += f' (el esquema no fija el número porque {n} pasa el límite de la API; lo revisa el código y si no está completo NO se usa)'
    arr['description'] = texto

def esquema_4a4(esq, ids, D):
    """PISTA INMI (2026-10-29): orden 69 — esquema de salida estructurada POR PEDIDO, armado desde el molde (el fijo sigue siendo el
    esquema general). Con 1 escenario: exactamente ese escenario_id; si tiene molde, base.camara.render y cada vista.camara.render
    solo pueden ser cámaras del molde y vistas = cámaras − 1 (minItems = maxItems solo hasta el tope de la API, orden 88); sin molde, render "" y 0 vistas.
    Con varios escenarios (no se usa hoy: 1 por pedido) solo se limita render a las cámaras del grupo."""
    e = json.loads(json.dumps(esq))
    try:
        arr = e['properties']['escenarios']; it = arr['items']; pr = it['properties']
        bc = pr['base']['properties']['camara']['properties']['render']; vs = pr['vistas']; vc = vs['items']['properties']['camara']['properties']['render']
    except (KeyError, TypeError): return e
    cams = {i: camaras_obligatorias(D, i) for i in ids}
    todas = [c for i in ids for c in cams[i]]
    if len(ids) == 1:
        i = ids[0]; c = cams[i]
        arr['minItems'] = arr['maxItems'] = 1
        pr['escenario_id'] = dict(pr.get('escenario_id') or {'type': 'string'}, enum=[i])
        if c:
            bc['enum'] = list(c); vc['enum'] = list(c)
            conteo_exacto(vs, len(c) - 1, f'UNA vista por cada cámara del molde distinta de la de la base: exactamente {len(c) - 1} ({", ".join(c)} menos la de la base)')   # orden 88
        else:
            bc['enum'] = ['']; vs['maxItems'] = 0
    elif todas:
        bc['enum'] = sorted(set(todas) | {''}); vc['enum'] = sorted(set(todas))
    return e

def esquema_inv(p, esq, ids, e2b, cat):
    """PISTA INMI (2026-10-29): orden 72 — esquema de salida estructurada POR PEDIDO de 4a1/4b1/4c1 (genérico, desde las entradas):
    exactamente un registro por id pedido (minItems = maxItems = ids; el id solo puede ser uno de los pedidos). 4c1: escenario_id solo
    los escenarios de esos objetos. 4a1: objetos_del_lugar_posicion.objeto_id solo ids del catálogo oficial. El fijo sigue siendo el general."""
    e = json.loads(json.dumps(esq)); c, k = clave_de(p)
    try: arr = e['properties'][c]; it = arr['items']; pr = it['properties']
    except (KeyError, TypeError): return e
    conteo_exacto(arr, len(ids), f'exactamente {len(ids)} registro(s): uno por cada id pedido ({", ".join(ids)}), sin repetir ni agregar otros')   # orden 88
    pr[k] = dict(pr.get(k) or {'type': 'string'}, enum=list(ids))
    if p == 'inv_obj_lugar' and 'escenario_id' in pr:
        obs = {x.get('objeto_id'): x for x in (e2b or {}).get('objetos', [])}
        eids = sorted({str(obs[i].get('escenario_id')) for i in ids if i in obs and obs[i].get('escenario_id')})
        if eids: pr['escenario_id'] = dict(pr['escenario_id'], enum=eids)
    if p == 'inv_escenarios':
        oids = [x.get('id') for x in (cat or {}).get('objetos', []) if x.get('id')]
        try: po = pr['objetos_del_lugar_posicion']['items']['properties']
        except (KeyError, TypeError): po = None
        if po is not None and oids and 'objeto_id' in po: po['objeto_id'] = dict(po['objeto_id'], enum=oids)
    return e

def moldes_grupo(D, ids):
    """orden 63b/65: renders de Blender de cada escenario (ramas/moldes/<id>/) como adjuntos + índice + resumen del molde
    (con camaras_del_molde y posiciones_del_molde: lo que el molde armó de verdad)."""
    adj, indice, resumen = [], [], []
    for i in ids:
        d = D / 'ramas' / 'moldes' / i
        m = json.loads((d / 'molde.json').read_text()) if (d / 'molde.json').is_file() else {}
        nombres = [n for n in (m.get('renders') or []) if (d / n).is_file()] or sorted(x.name for x in d.glob('*.png')) if d.is_dir() else []
        M = molde_de(D, i)
        cams = {c['render']: c for c in M.get('camaras') or []}
        for n in nombres:
            adj.append(str(d / n))
            tipo = 'planta (vista desde arriba)' if n.startswith('planta') else ('camara' if n.startswith('cam') else ('prueba de luz' if n.startswith('luz') else 'render'))
            fila = {'imagen_n': len(adj), 'escenario_id': i, 'archivo': n, 'tipo': tipo}
            if n in cams: fila['camara'] = {k: cams[n][k] for k in ('escena', 'posicion_xyz', 'mira_a_xyz', 'lente_mm', 'para_que') if k in cams[n]}
            indice.append(fila)
        resumen.append({'escenario_id': i, 'tiene_renders': bool(nombres),
                        'camaras_del_molde': [{k: c[k] for k in ('render', 'escena', 'posicion_xyz', 'mira_a_xyz', 'lente_mm', 'para_que') if k in c} for c in M.get('camaras') or [] if c.get('existe')],
                        'posiciones_del_molde': M.get('objetos') or {},
                        **{k: m[k] for k in ('medidas_m', 'exterior', 'abierto', 'fondo_lejano_no_modelado', 'camaras', 'escenas_con_luz', 'armado', 'avisos') if k in m}})
    return adj, indice, resumen

def _filtra_4b1(inv, e2b, base, ids):
    """objetos de la historia que aparecen en las escenas de estos escenarios."""
    if not isinstance(inv, dict): return []
    nums = {str(e.get('numero')) for e in (base.get('escenas') or []) if e.get('escenario_id') in ids or any(i in _j(e) for i in ids)}
    en_esc = {x.get('objeto_id') for x in (e2b or {}).get('objetos', []) if {str(n) for n in (x.get('escenas') or [])} & nums}
    return [x for x in inv.get('objetos', []) if x.get('objeto_id') in en_esc or any(i in _j(x) for i in ids)]

def variantes_oficiales(e2a):
    """Variantes de estado de 4p (2a) con id estable <escenario_id>__v<n>. Escenario sin variantes → una «normal»."""
    out = []
    for x in (e2a or {}).get('escenarios', []):
        vs = x.get('variantes_estado') or [{'variante': 'normal', 'escenas': [], 'cita': ''}]
        for i, v in enumerate(vs, 1):
            out.append({'variante_id': f"{x.get('escenario_id')}__v{i}", 'escenario_id': x.get('escenario_id'), 'variante': v.get('variante'),
                        'escenas': v.get('escenas', []), 'cita': v.get('cita', '')})
    return out

def _grupos_inv(p, base, e2a, e2b, fuera=()):
    """Lista de grupos (listas de ids oficiales) a investigar, en orden estable. fuera = ids que no se investigan (biblioteca, orden 62)."""
    cat = base.get('catalogo_oficial', {}); m = MAX_POR_LLAMADA[p]
    if p in POR_ESCENARIO:
        ids = [x['id'] for x in cat.get('escenarios', []) if x.get('id') and x['id'] not in fuera]
        if not ids: return []
        n = max(1, math.ceil(len(ids) / m)); k = math.ceil(len(ids) / n)
        return [ids[i:i + k] for i in range(0, len(ids), k)]
    clase_obj = CLASE_DE_INV.get(p)  # t839u: personaje→4b, escenario→4c; utileria no entra aquí (va a 4a4/4a5)
    obs = [x for x in (e2b or {}).get('objetos', []) if clase_de(x) == clase_obj and x.get('objeto_id') and x['objeto_id'] not in fuera]   # orden 72: fuera también aquí
    if p == 'inv_obj_historia':
        ids = [x['objeto_id'] for x in obs]
        if not ids: return []   # t846u: todos cubiertos / fuera → nada que cotizar (evita range step 0)
        n = max(1, math.ceil(len(ids) / m)); k = math.ceil(len(ids) / n)
        return [ids[i:i + k] for i in range(0, len(ids), k)]
    por = {}   # lugar: por escenario, sin partir un escenario si cabe
    for x in obs: por.setdefault(x.get('escenario_id') or '', []).append(x['objeto_id'])
    trozos = []   # PISTA INMI (2026-10-29): orden 72 — un escenario con más objetos que el máximo se parte (antes quedaba un grupo más grande)
    for e_, ids in por.items():
        n = max(1, math.ceil(len(ids) / m)); k = math.ceil(len(ids) / n)
        trozos += [(e_, ids[i:i + k]) for i in range(0, len(ids), k)]
    gr = []
    for _, ids in sorted(trozos, key=lambda t: -len(t[1])):
        for g in gr:
            if len(g) + len(ids) <= m: g.extend(ids); break
        else: gr.append(list(ids))
    return gr

def cfg_obj_historia(p):
    """Orden t336u: config «objetos_historia_en_escenario» del paso (llamadas_config.json) o None."""
    try: d = json.loads(LS.CONFIG_LLAMADAS.read_text(encoding='utf-8')).get('objetos_historia_en_escenario') or {}
    except Exception: d = {}
    return (d.get('pasos') or {}).get(p)

def escenas_de_escenario(base, eid):
    """Escenas (texto) de un escenario: catalogo_oficial.escenarios[].escenas; si no hay, las de base.escenas con ese escenario_id."""
    for x in (base.get('catalogo_oficial') or {}).get('escenarios', []) or []:
        if x.get('id') == eid and x.get('escenas'): return [str(n) for n in x['escenas']]
    return [str(e.get('numero')) for e in (base.get('escenas') or []) if e.get('escenario_id') == eid]

def objetos_historia_por_escenario(base, e2b, ids, tipos=('personaje', 'historia')):
    """Orden t336u + t839u: {eid: [objetos 2b de esas clases que aparecen en escenas del escenario]} en orden 2b.
    tipos acepta clases (personaje/escenario/utileria) y aliases viejos (historia→personaje, lugar→escenario)."""
    clases_want = set()
    for t in tipos:
        if t in CLASES_OK: clases_want.add(t)
        elif t == 'historia': clases_want.add('personaje')
        elif t == 'lugar': clases_want.add('escenario')
    out = {}
    for eid in ids:
        ne = set(escenas_de_escenario(base, eid)); lst = []
        for x in (e2b or {}).get('objetos', []) or []:
            if not x.get('objeto_id') or clase_de(x) not in clases_want: continue
            com = [str(n) for n in (x.get('escenas') or []) if str(n) in ne]
            if com: lst.append(dict(con_clase(x), escenas_en_este_escenario=com))
        out[eid] = lst
    return out

def _pedido_inv(p, texto, cfgj, base, e2a, e2b, inv4a1, g, ids, n_txt, aprox_4a1, extra=None):
    """Arma el pedido de UN grupo. Devuelve (prompt, rotulos). extra (solo 4a4, orden 63b): estilo, 4b1, 4c1, moldes."""
    obs = {x.get('objeto_id'): x for x in (e2b or {}).get('objetos', [])}
    esc = {x.get('escenario_id'): x for x in (e2a or {}).get('escenarios', [])}
    if p in POR_ESCENARIO:
        # t839u: escenario → objetos_del_lugar (4c/molde); utileria → utileria_del_escenario (pintada en 4a4/4a5, sin ADN);
        # efectos de la BASE → efectos_del_capitulo (lado poderes/efectos + pintura 4a)
        d4p = {'escenarios': [esc[i] for i in ids if i in esc],
               'objetos_del_lugar': [con_clase(x) for x in obs.values() if clase_de(x) == 'escenario' and x.get('escenario_id') in ids],
               'utileria_del_escenario': [con_clase(x) for x in obs.values() if clase_de(x) == 'utileria' and x.get('escenario_id') in ids],
               'efectos_del_capitulo': efectos_de(base, ids)}
        if isinstance(e2b, dict) and e2b.get('_adn_sellados_t846'):   # t846u
            d4p['adn_objetos_sellados'] = e2b['_adn_sellados_t846']
        oh = cfg_obj_historia(p)   # orden t336u: objetos de la historia/personaje que aparecen en las escenas de estos escenarios (los ubica 4a1)
        if oh:
            vistos = {}; ofi = {x.get('id') for x in (base.get('catalogo_oficial') or {}).get('objetos', []) or [] if x.get('id')}   # solo ids oficiales (los demás van por faltantes de 2b)
            for eid, xs in objetos_historia_por_escenario(base, e2b, ids, tuple(oh.get('tipos') or ['personaje', 'historia'])).items():
                for x in xs:
                    if x['objeto_id'] not in ofi: continue
                    vistos.setdefault(x['objeto_id'], dict(x, escenas_en_este_escenario={}))['escenas_en_este_escenario'][eid] = x['escenas_en_este_escenario']
            d4p[oh.get('clave_4p') or 'objetos_historia_en_escenario'] = list(vistos.values())
    else:
        d4p = {'objetos': [con_clase(obs[i]) for i in ids if i in obs]}
        if p == 'inv_obj_lugar':
            eids = sorted({obs[i].get('escenario_id') for i in ids if i in obs})
            d4p['escenarios'] = [esc[i] for i in eids if i in esc]
            d4p['efectos_del_capitulo'] = efectos_de(base, eids)
    grupo = {'grupo': n_txt, 'ids': ids, 'nota': 'investiga SOLO estos ids (uno por id)'}
    if p == 'prompts_escenarios':
        grupo = {'grupo': n_txt, 'ids': ids, 'nota': 'un registro por escenario_id; cada variante_id una vez (base.cubre_variante_id o variantes)',
                 'variantes_a_cubrir': [v for v in variantes_oficiales(e2a) if v['escenario_id'] in ids]}
        if extra:   # PISTA INMI (2026-10-29): orden 69 — lista EXACTA de cámaras por escenario (la arma el código desde el molde)
            co = {i: [c_['render'] for c_ in (m_.get('camaras_del_molde') or [])] for m_ in (extra.get('moldes') or []) for i in [m_.get('escenario_id')] if i in ids}
            grupo['camaras_obligatorias'] = {i: co.get(i, []) for i in ids}
            grupo['regla_camaras'] = ('UNA imagen por cámara: la base usa UNA cámara de camaras_obligatorias y CADA una de las demás tiene SU vista '
                                      '(vistas = cámaras − 1). No juntes dos cámaras en una vista, no dejes ninguna sin vista, no repitas cámara. '
                                      'Sin cámaras (sin molde): base.camara.render = "" y sin vistas. El código lo revisa: si falta o se repite una cámara, el escenario queda INCOMPLETO.')
    r = ['\n\n=== CONFIG_CANAL_JSON ===\n', '\n=== FIN CONFIG ===\n\n=== BASE_DEL_CAPITULO_JSON ===\n', '\n=== FIN BASE ===\n\n=== PROFUNDIZACION_4P_JSON ===\n']
    pre = []
    if p == 'prompts_escenarios' and extra:   # orden 63b: el estilo fijo va PRIMERO, en bloque propio (además de dentro de la config)
        r = ['\n\n=== ESTILO_FIJO_DEL_CANAL_JSON (LEY: todas las imágenes en este estilo) ===\n', '\n=== FIN ESTILO FIJO ===\n\n=== CONFIG_CANAL_JSON ===\n'] + r[1:]
        pre = [_j(extra['estilo'])]
    bp = base
    if p == 'prompts_escenarios':   # orden 63: en 4a4 la BASE lleva solo las escenas de los escenarios del grupo (el guion completo sigue entero) → azotea cabe en el tope 0,75
        bp = dict(base, escenas=[e for e in (base.get('escenas') or []) if any(i in _j(e) for i in ids)])
    rc = recorte_de(p) if (p == 'prompts_escenarios' and extra) else None   # t366u (Ricardo): cada escenario recibe SOLO lo suyo
    gg = g
    if rc:
        eids_ = sorted(ids); i4_ = (extra or {}).get('inv4a1') or inv4a1
        try: cfg_ = json.loads(cfgj)
        except Exception: cfg_ = {}
        nv, inf_ = RP.recortar_4a4(rc, ids, bp, cfg_, [x for x in (i4_ or {}).get('escenarios', []) if x.get('escenario_id') in eids_],
                                   extra['inv4b1'], extra['inv4c1'], {'imagenes_adjuntas': extra['indice'], 'moldes': extra['moldes'], 'alineado_al_molde': extra.get('alineado') or {}},
                                   d4p, g, base.get('escenas') or [])
        extra['_recorte'] = inf_
        cfgj, bp, d4p, gg = _j(nv['cfg']), nv['base'], nv['d4p'], nv['guion']
        extra = dict(extra, _rc=nv)
    partes = pre + [cfgj, _j(bp), _j(d4p)]
    if p in NECESITA_4A1:
        r.append('\n=== FIN 4P ===\n\n=== INVESTIGACION_4A1_JSON ===\n')
        eids = sorted(ids) if p == 'prompts_escenarios' else sorted({obs[i].get('escenario_id') for i in ids if i in obs})
        i4 = (extra or {}).get('inv4a1') if (p == 'prompts_escenarios' and extra and extra.get('inv4a1')) else inv4a1   # orden 65: copia alineada al molde
        if i4 is None: partes.append('x' * (REF_4A1_CHARS_POR_ESC * max(1, len(eids))))   # aproximado (solo cotizar)
        elif rc: partes.append(_j({'escenarios': extra['_rc']['i4']}))   # t366u: 4a1 de este escenario, recortado
        else: partes.append(_j({'escenarios': [x for x in i4.get('escenarios', []) if x.get('escenario_id') in eids]}))
        if p == 'prompts_escenarios' and extra:   # orden 63b: 4b1/4c1 filtradas + moldes de Blender (índice de las imágenes adjuntas)
            r.append('\n=== FIN 4A1 ===\n\n=== INVESTIGACION_4B1_JSON (objetos de la historia en estas escenas) ===\n')
            partes.append(_j({'objetos': extra['_rc']['inv4b1'] if rc else extra['inv4b1']}))
            r.append('\n=== FIN 4B1 ===\n\n=== INVESTIGACION_4C1_JSON (objetos del lugar de estos escenarios) ===\n')
            partes.append(_j({'objetos': extra['_rc']['inv4c1'] if rc else extra['inv4c1']}))
            r.append('\n=== FIN 4C1 ===\n\n=== MOLDES_BLENDER_JSON (imagenes_adjuntas = renders que van ANTES de este texto, en este orden) ===\n')
            partes.append(_j(extra['_rc']['moldes'] if rc else {'imagenes_adjuntas': extra['indice'], 'moldes': extra['moldes'], 'alineado_al_molde': extra.get('alineado') or {}}))
            r.append('\n=== FIN MOLDES ===\n\n=== GRUPO_A_INVESTIGAR ===\n')
        else:
            r.append('\n=== FIN 4A1 ===\n\n=== GRUPO_A_INVESTIGAR ===\n')
    else:
        r.append('\n=== FIN 4P ===\n\n=== GRUPO_A_INVESTIGAR ===\n')
    partes.append(_j(grupo))
    r += ['\n=== FIN GRUPO ===\n\n' + ('=== GUION_DEL_ESCENARIO (sus escenas completas; las demás solo con el título) ===\n' if rc else '=== GUION_COMPLETO ===\n'),
          '\n=== FIN GUION ===\n' + (RECORDATORIO_4A4 if p == 'prompts_escenarios' and extra else '')]
    partes.append(gg)
    pr = texto
    for i, q in enumerate(partes): pr += r[i] + q
    pr += r[-1]
    return pr, r

def fijo_inv(p, texto, r, esq, X, mo):
    """Fijo del pedido. PISTA INMI (2026-10-29): orden 68 — 4a4: nombre por cubeta (_o68_mNN) y declara la salida estructurada."""
    partes = {'texto': texto, 'rotulos_bloques': ''.join(r), 'esquema': esq, 'modelo': X['modelo'], 'nivel': X['nivel'],
              'max_out': mo, 'max_rondas': 1, 'json_out': True}
    rev = REV_FIJO.get(p, '')
    if p in ESQUEMA_API:
        partes['json_schema_api'] = 'response_json_schema'
        if p == 'prompts_escenarios': rev = _rev_4a4(mo) + _suf_recorte(p)   # t366u: pedido recortado → fijo propio
        elif p in INV_O72: rev = _rev_inv(mo)   # PISTA INMI (2026-10-29): orden 72 — fijo por cubeta (taller00_v1_4a1_o72_m24, …)
        if p in INV_O72: rev += REV_TEXTO_INV.get(p, '')   # t337u: el texto/esquema cambió (t336u) → fijo NUEVO; el viejo queda intacto
    return {'paso': f'taller00_{VER}_{PASOS[p]}{rev}', 'partes': partes, 'fragmentos': [texto] + r}

def sub_inv(p, ids):
    """orden 72: nombre del pedido 4a1/4b1/4c1 — un id: <p>__<id>; varios: <p>__<primero>__<huella de los ids>."""
    return f'{p}__{ids[0]}' if len(ids) == 1 else f"{p}__{ids[0]}__{hashlib.sha1(','.join(ids).encode()).hexdigest()[:6]}"

def armar_inv(p, X, aprox_ok, tope):
    """4a1/4b1/4c1: un pedido por grupo; si el peor caso de un grupo pasa el tope, se parte en dos (hasta 1 id)."""
    P, AR, D = X['P'], X['AR'], X['D']
    texto = (V / 'prompts' / f'{PR[p]}.txt').read_text(encoding='utf-8')
    texto0 = texto   # orden t331u: el texto sin el FORMATO (para pedidos divididos)
    esq = (V / 'esquemas' / f'{ESQ[p]}_esquema.json').read_text(encoding='utf-8')
    rc0 = recorte_de(p) if p == 'prompts_escenarios' else None
    if rc0 and rc0.get('nota_texto'): texto = texto.rstrip() + '\n\n' + rc0['nota_texto'].strip() + '\n'   # t366u: el modelo sabe que la entrada viene recortada
    texto = texto + f'\n\nFORMATO DE SALIDA OBLIGATORIO (JSON Schema {ESQ[p]}_esquema.json; la respuesta debe validar contra él):\n' + esq
    base, e2a, e2b = _leer_resp(P, D, 'base'), _leer_resp(P, D, 'escenarios'), _leer_resp(P, D, 'objetos')
    # t846u: objetos (4b1/4c1) corren ANTES de escenarios 2a; 2a/4a1 después del ADN sellado
    req = [('base (caja 4)', base), ('objetos 2b (caja 4p/objetos)', e2b)]
    if p in ('inv_escenarios', 'prompts_escenarios'):
        req.append(('escenarios 2a (caja 4e)', e2a))
    falta = [n for n, v in req if not isinstance(v, dict)]
    if falta: return None, f"falta {', '.join(falta)}: corre primero lo que pide el orden 9 (objetos antes de escenarios)"
    if e2a is None: e2a = {'escenarios': []}   # 4c1 puede ir sin 2a
    inv4a1, aprox = None, False
    if p in NECESITA_4A1:
        inv4a1 = _leer_resp(P, D, 'inv_escenarios') if ya_hecho(D, 'inv_escenarios') else None
        if inv4a1 is None:
            if not aprox_ok: return None, f'falta la investigación de escenarios (4a1): {PASOS[p]} va DESPUÉS de 4a1; corre primero 4a1'
            aprox = True
    cfgj = _j(X['cfg'])
    if p == 'inv_escenarios':   # t846u: 4a1 recibe ADN de objetos ya listos (2b/4b1/4c1)
        adn = _adn_objetos_para_escenarios(P, D, base)
        if adn and isinstance(e2b, dict):
            e2b = dict(e2b, _adn_sellados_t846=adn)
    pb = plan_biblioteca(D) if p == 'inv_escenarios' else None
    fuera = set((pb or {}).get('plan', {}).get('4a1', {}).get('fuera_de_grupos') or [])
    if p in INV_O72:   # PISTA INMI (2026-10-29): orden 72 — lo que ya vino VÁLIDO no se agrupa ni se paga; --solo / --solo-fallidos limitan a esos ids
        fuera |= set(X.get('cubiertos') or ())
        rs = X.get('restringir')
        if rs is not None:
            todos = [i for g_ in _grupos_inv(p, base, e2a, e2b, set()) for i in g_]
            fuera |= {i for i in todos if i not in rs}
            if X.get('solo') and not (set(X['solo']) & set(todos)): return None, f"--solo {sorted(X['solo'])}: ninguno es id de {PASOS[p]} en este capítulo"
    pendientes = [list(x) for x in _grupos_inv(p, base, e2a, e2b, fuera)]
    solo = X.get('solo') or set()
    if p == 'prompts_escenarios' and solo:   # orden 63b: prueba barata = UN grupo con EXACTAMENTE los escenarios pedidos (el aprobado), no el grupo automático
        pendientes = [[i] for g_ in pendientes for i in g_ if i in solo]   # PISTA INMI (2026-10-29): orden 68 — un pedido por escenario pedido
        if not pendientes: return None, f'--solo {sorted(solo)}: ninguno es escenario del capítulo'
    est4 = None
    if p == 'prompts_escenarios':   # orden 63b
        est_c = estilo_canal(X)
        if not est_c: return None, 'falta el estilo fijo APROBADO del canal (canal.data.style_fijo con descripcion_en y aprobado=true): 4a4 no se pide sin estilo'
        i4b1 = _leer_resp(P, D, 'inv_obj_historia') if ya_hecho(D, 'inv_obj_historia') else None
        i4c1 = _leer_resp(P, D, 'inv_obj_lugar') if ya_hecho(D, 'inv_obj_lugar') else None
        if (i4b1 is None or i4c1 is None) and not aprox_ok: return None, 'falta la investigación de objetos (4b1 y/o 4c1): 4a4 va después de 4b1 y 4c1'
        def est4(ids):
            adj, ind, mol = moldes_grupo(D, ids)
            c1, a1, al = alinear_al_molde(D, ids, [x for x in (i4c1 or {}).get('objetos', []) if x.get('escenario_id') in ids], inv4a1)   # orden 65: el molde manda
            return {'estilo': est_c, 'inv4b1': _filtra_4b1(i4b1, e2b, base, ids), 'inv4c1': c1, 'inv4a1': a1, 'alineado': al,
                    'indice': ind, 'moldes': mol, 'adjuntos': adj}
    mo = MAX_OUT_4A4 if p == 'prompts_escenarios' else AR.MAX_OUT
    vof = variantes_oficiales(e2a) if p == 'prompts_escenarios' else []
    def mo_de(ids, ex):   # PISTA INMI (2026-10-29): orden 68 — 4a4: cubeta de salida por tamaño (cámaras del molde + variantes)
        if p in INV_O72: return cubeta_inv(p, len(ids))   # orden 72: 4a1/4b1/4c1 por cuántos ids lleva el pedido
        if p != 'prompts_escenarios': return mo
        ncam = sum(len(m_.get('camaras_del_molde') or []) for m_ in (ex or {}).get('moldes') or [])
        return cubeta_4a4(ncam, sum(1 for v in vof if v['escenario_id'] in ids))
    def cuesta(pr, ex, m_=None):
        n = len(ex['adjuntos']) if ex else 0
        return round(AR.estimar(len(pr), max_out=m_ or mo, modelo=X['modelo']) + n * TOKENS_IMG_PEOR * AR.precio(X['modelo'])[0] / 1e6, 4)
    hechos = []
    while pendientes:
        ids = pendientes.pop(0)
        ex = est4(ids) if est4 else None
        pr, r = _pedido_inv(p, texto, cfgj, base, e2a, e2b, inv4a1, X['g'], ids, '?', aprox, ex)
        if cuesta(pr, ex, mo_de(ids, ex)) > tope + 1e-9 and len(ids) > 1:
            h = len(ids) // 2; pendientes[:0] = [ids[:h], ids[h:]]; continue
        hechos.append(ids)
    out, n = [], len(hechos)
    for i, ids in enumerate(hechos, 1):
        ex = est4(ids) if est4 else None
        pr, r = _pedido_inv(p, texto, cfgj, base, e2a, e2b, inv4a1, X['g'], ids, f'{i} de {n}', aprox, ex)
        mq = mo_de(ids, ex)
        fijo = fijo_inv(p, texto, r, esq, X, mq)
        # orden 66: cada --solo con su propio nombre (no se pisan). PISTA INMI (2026-10-29): orden 68 — 4a4 = un escenario, nombre por escenario
        sub = sub_4a4(ids[0]) if p == 'prompts_escenarios' and len(ids) == 1 else f'{p}_g{i}de{n}' + (('_solo_' + hashlib.sha1(','.join(sorted(ids)).encode()).hexdigest()[:6]) if p == 'prompts_escenarios' and solo else '')
        if p in INV_O72: sub = sub_inv(p, ids)   # orden 72: nombre por ids (nunca pisa un pedido anterior)
        q = {'sub': sub, 'ids': ids, 'pr': pr, 'fijo': fijo, 'aprox': aprox, 'est': cuesta(pr, ex, mq), 'max_out': mq,
             'esquema': ((esquema_4a4(json.loads(esq), ids, D) if p == 'prompts_escenarios' and ex else
                          esquema_inv(p, json.loads(esq), ids, e2b, base.get('catalogo_oficial', {})) if p in INV_O72 else json.loads(esq)) if p in ESQUEMA_API else None)}   # orden 69/72
        if p == 'prompts_escenarios' or p in INV_O72:   # para un reintento por MAX_TOKENS con la cubeta siguiente (si cabe en el tope); orden 72: también 4a1/4b1/4c1
            q['rearmar'] = {'texto': texto, 'r': r, 'esq': esq, 'pr': pr, 'n_adj': len(ex['adjuntos']) if ex else 0, 'p': p,
                            'cubetas': CUBETAS_INV if p in INV_O72 else CUBETAS_4A4}
        if q['esquema'] is not None and p in INV_O72:   # orden t331u (Ricardo): esquema > límite → pedido DIVIDIDO por partes declaradas
            dv = armar_dividido(p, X, q, texto0, texto, esq, r, mq, lambda pr_: cuesta(pr_, ex, mq))
            if dv: q['dividir'] = dv; q['est'] = round(sum(z['est'] for z in dv['partes']), 4); q.pop('rearmar', None)
        if ex:   # orden 63b: inventario de lo que entra (se muestra al cotizar, antes de pagar)
            q['adjuntos'] = ex['adjuntos']
            q['entrada'] = {'bloques': [l.strip() for z in r for l in z.split('\n') if l.startswith('=== ') and not l.startswith('=== FIN')], 'imagenes': len(ex['adjuntos']),
                            'imagenes_lista': [f"{z['escenario_id']}/{z['archivo']}" for z in ex['indice']],
                            'chars_texto': len(pr), 'tokens_texto_aprox': -(-len(pr) // AR.CHARS_POR_TOKEN), 'tokens_imagenes_peor': len(ex['adjuntos']) * TOKENS_IMG_PEOR,
                            'max_out': mq, 'objetos_4b1': [z.get('objeto_id') for z in ex['inv4b1']], 'objetos_4c1': [z.get('objeto_id') for z in ex['inv4c1']],
                            'estilo_fijo': (ex['estilo'].get('style_fijo') or {}).get('nombre'), 'estilo_chars': len((ex['estilo'].get('style_fijo') or {}).get('descripcion_en') or ''),
                            'estilo_origen': ex['estilo'].get('origen_texto'), 'estilo_avisos': ex['estilo'].get('avisos'),
                            'alineado_al_molde': len((ex.get('alineado') or {}).get('cambios') or []), 'alineado_aviso': (ex.get('alineado') or {}).get('aviso'),
                            'camaras_del_molde': {m_['escenario_id']: [c_['render'] for c_ in m_.get('camaras_del_molde') or []] for m_ in ex['moldes']},
                            'vistas_exigidas': {i: max(0, len(camaras_obligatorias(D, i)) - 1) for i in ids}, 'escenas_en_base': [e.get('numero') for e in (base.get('escenas') or []) if any(k in _j(e) for k in ids)],
                            'timeout_s': PC.timeout_paso(sub, len(pr), mq), 'recorte': ex.get('_recorte')}   # t366u: tope de tiempo calculado y qué se quitó
        out.append(q)
    if pb:
        sv = pb['plan']['4a1'].get('solo_variantes') or []
        if sv:
            q, err = armar_solo_variantes(X, base, e2a, e2b, cfgj, sv)
            if err: return None, err
            out += q
    return out, None

def armar_dividido(p, X, q, texto0, texto, esq, r, mq, cuesta):
    """Orden t331u (Ricardo: «pártelo en dos llamadas estratégicas que no cambien los resultados»). GENÉRICO: si el esquema del pedido
    pasa de dividir_esquema.limite_propiedades y el paso tiene partes en llamadas_config.json, arma UNA llamada por parte, con la MISMA
    entrada completa; solo cambia el FORMATO (sus campos). La parte con contexto_de lleva al final, como contexto fijo, los campos
    declarados de la salida de la parte anterior (se pegan al correr; al cotizar se cuenta un peor caso). None si no hay que dividir."""
    pl = DE.plan(p, q['esquema'])          # por pedido (enum de ids, conteos): lo que va a la API
    if not pl: return None
    pg = DE.plan(p, json.loads(esq))       # general: lo que se congela en el fijo y valida cada parte
    partes = []
    for k, (pt, ptg) in enumerate(zip(pl['partes'], pg['partes'])):
        tp = texto0 + DE.texto_formato(pg, ptg)
        rr = list(r)
        if pt.get('contexto_de'):
            a_, b_ = DE.rotulos_contexto(pt); rr = rr[:-1] + [rr[-1] + a_, b_]
        pr = tp + q['pr'][len(texto):]
        f = fijo_inv(p, tp, rr, json.dumps(ptg['esquema'], ensure_ascii=False), X, mq); f['paso'] += f"_div{pt['nombre']}"
        extra_ctx = (REF_4A1_CHARS_POR_ESC * max(1, len(q['ids'])) + len(rr[-2][-400:]) + len(rr[-1])) if pt.get('contexto_de') else 0   # peor caso del contexto (cotizar)
        partes.append({'nombre': pt['nombre'], 'nota': pt.get('nota'), 'sub': f"_div{pt['nombre']}_{q['sub']}", 'pr': pr, 'fijo': f, 'esquema': pt['esquema'],
                       'propiedades': pt['propiedades'], 'contexto_de': pt.get('contexto_de'), 'contexto_campos': pt.get('contexto_campos') or [],
                       'est': cuesta('x' * (len(pr) + extra_ctx))})
    return {'plan': pl, 'partes': partes, 'propiedades_completo': pl['propiedades_completo'], 'limite': pl['limite']}

def llamar_dividido(a, X, x, tope, limite=None, dormir=time.sleep):
    """Orden t331u: corre las partes EN ORDEN (cada una es un llamar_uno normal: ledger antes, intentos acotados, revisión), une por la
    clave y valida la UNIÓN contra el esquema COMPLETO del pedido. La unión queda en respuestas/<paso>.json (lo mismo que 4a2/4a4/4a5
    leían antes). Una parte ya hecha y válida (con el mismo fijo e ids, y con TODAS las anteriores también reutilizadas) no se vuelve a pagar."""
    D, AR = X['D'], X['AR']; p = x['paso']; dv = x['_dividir']; pl = dv['plan']; inv = inv_de(p)
    limite = (a.ok if a.ok is not None else x['peor_caso_usd']) if limite is None else limite
    info = {'paso': p, 'fijo_paso': x['_fijo']['paso'], 'ids': x.get('ids'), 'dividido': True, 'propiedades_completo': dv['propiedades_completo'],
            'limite_propiedades': dv['limite'], 'partes': [], 'inicio': ahora(), 'aprobado': a.aprobado, 'ok_usd': a.ok, 'limite_usd': round(limite, 4),
            'corrida_n8n': a.corrida, 'salida_estructurada': True, 'estimado_peor_caso': x['peor_caso_usd'], 'intentos': []}
    gast, objs, reusa, t0 = 0.0, {}, not getattr(a, 'repetir', False), time.time()   # t337u: --repetir = no reutilizar partes
    def fin(estado, **kw):
        info.update(estado=estado, usd_real=round(sum(z.get('usd_real') or 0 for z in info['partes'] if z.get('estado') != 'ya_hecho'), 4),
                    usd_posible_cobro=round(sum(z.get('usd_posible_cobro') or 0 for z in info['partes']), 4), segundos=round(time.time() - t0, 1), fin_hora=ahora(), **kw)
        (D / 'resultados' / f'{p}.json').write_text(json.dumps(info, ensure_ascii=False, indent=1)); return info
    for pt in dv['partes']:
        sp = pt['sub']; h = _resp_util(D, sp) if reusa else None
        if h and (h.get('estado') not in ('ok', 'reparado') or h.get('fijo_paso') != pt['fijo']['paso'] or h.get('ids') != x.get('ids')): h = None
        if h:
            info['partes'].append({'parte': pt['nombre'], 'paso': sp, 'estado': 'ya_hecho', 'usd_real': h.get('usd_real'), 'propiedades': pt['propiedades']})
        else:
            reusa = False
            pr, mo = pt['pr'], x.get('_max_out') or AR.MAX_OUT
            if pt.get('contexto_de'):
                a_, b_ = DE.rotulos_contexto(pt); pr = pr + a_ + DE.contexto(pl, pt, objs.get(pt['contexto_de'])) + b_
            est = round(AR.estimar(len(pr), max_out=mo, modelo=X['modelo']), 4)
            if est > tope + 1e-9: return fin('no_llamado', motivo=f"parte {pt['nombre']}: peor caso {est} > tope por llamada {tope}")
            if gast + est > limite + 1e-9: return fin('no_llamado', motivo=f"parte {pt['nombre']}: {est} pasaría lo aprobado (gastado {round(gast, 4)} de {round(limite, 4)})")
            xp = {k: v for k, v in x.items() if k not in ('_dividir', '_rearmar')}
            xp.update(paso=sp, prueba=f"{PASOS.get(inv, inv)}-{pt['nombre']}", _pr=pr, _fijo=pt['fijo'], _esquema=pt['esquema'], peor_caso_usd=est)
            r = llamar_uno(a, X, xp, tope, limite=limite - gast, dormir=dormir)
            gast += float(r.get('usd_real') or 0) + float(r.get('usd_posible_cobro') or 0)
            info['partes'].append({'parte': pt['nombre'], 'paso': sp, 'estado': r.get('estado'), 'usd_real': r.get('usd_real'), 'usd_posible_cobro': r.get('usd_posible_cobro'),
                                   'tokens_entrada': r.get('tokens_entrada'), 'tokens_salida': r.get('tokens_salida'), 'fin': r.get('fin'), 'propiedades': pt['propiedades'],
                                   'esquema_errores_parte': r.get('esquema_errores'), 'error': r.get('error') or r.get('motivo')})
            info['intentos'] += r.get('intentos') or []
            if r.get('estado') not in ('ok', 'reparado'): return fin('error' if r.get('estado') in ('error', 'no_llamado') else r.get('estado'), parte_fallida=pt['nombre'])
        objs[pt['nombre']] = _obj_resp(D, sp)
    uni = DE.unir(pl, [objs[pt['nombre']] for pt in dv['partes']])
    (D / 'respuestas' / f'{p}.json').write_text(json.dumps(uni, ensure_ascii=False, indent=1), encoding='utf-8')
    err = DE.validar(uni, x['_esquema'])
    ri = revisar_ids_resp(inv, uni, x.get('ids') or []) if inv else {'completo': True}
    info.update(json_valido=True, esquema_errores=err, union_validada_contra='esquema COMPLETO del pedido',
                tokens_entrada=[REDACTED]
    if inv: info['revision_ids'] = {k: ri[k] for k in ('buenos', 'faltan', 'ajenos', 'repetidos', 'sin_campos', 'recibidos')}
    if err or not ri['completo']:
        return fin('incompleto', ids_buenos=[] if err else ri['buenos'], ids_faltan=list(x.get('ids') or []) if err else [i for i in (x.get('ids') or []) if i not in ri['buenos']],
                   motivo_incompleto=('la unión no valida contra el esquema completo: ' + '; '.join(err[:8])) if err else LS.texto_ids(ri, p))
    return fin('ok')

def armar_solo_variantes(X, base, e2a, e2b, cfgj, sv):
    """Orden 62: escenarios de la biblioteca con estados nuevos → pedido corto con la investigación guardada (no se repite la 4a1)."""
    D = X['D']
    lib = _leer_resp(X['P'], D, 'biblioteca_inv_escenarios') or {}
    guard = {x.get('escenario_id'): x for x in lib.get('escenarios', []) if isinstance(x, dict)}
    falta = [z['id'] for z in sv if z['id'] not in guard]
    if falta: return None, f'falta la investigación guardada de {falta} en respuestas/biblioteca_inv_escenarios.json: corre primero 4a0 (biblioteca plan --materializar)'
    texto = (V / 'prompts' / f"{SOLO_VAR['pr']}.txt").read_text(encoding='utf-8')
    esq = (V / 'esquemas' / f"{SOLO_VAR['pr']}_esquema.json").read_text(encoding='utf-8')
    texto = texto + f"\n\nFORMATO DE SALIDA OBLIGATORIO (JSON Schema {SOLO_VAR['pr']}_esquema.json; la respuesta debe validar contra él):\n" + esq
    esc = {x.get('escenario_id'): x for x in (e2a or {}).get('escenarios', [])}
    obs = (e2b or {}).get('objetos', [])
    m = SOLO_VAR['max']; ids_all = [z['id'] for z in sv]; n = math.ceil(len(ids_all) / m); out = []
    for i in range(n):
        ids = ids_all[i * m:(i + 1) * m]; n_txt = f'{i + 1} de {n}'
        d4p = {'escenarios': [esc[k] for k in ids if k in esc], 'objetos_del_lugar': [con_clase(x) for x in obs if clase_de(x) == 'escenario' and x.get('escenario_id') in ids], 'utileria_del_escenario': [con_clase(x) for x in obs if clase_de(x) == 'utileria' and x.get('escenario_id') in ids], 'efectos_del_capitulo': efectos_de(base, ids)}
        grupo = {'grupo': n_txt, 'ids': ids, 'nota': 'SOLO los estados nuevos; lo guardado no se cambia',
                 'estados_nuevos': {z['id']: z.get('estados_nuevos') or [{'variante': v} for v in z.get('variantes_nuevas', [])] for z in sv if z['id'] in ids}}
        guardada = {'escenarios': [{k: v for k, v in guard[k_].items() if k != '_de_biblioteca'} for k_ in ids]}
        r = ['\n\n=== CONFIG_CANAL_JSON ===\n', '\n=== FIN CONFIG ===\n\n=== BASE_DEL_CAPITULO_JSON ===\n', '\n=== FIN BASE ===\n\n=== PROFUNDIZACION_4P_JSON ===\n',
             '\n=== FIN 4P ===\n\n=== INVESTIGACION_GUARDADA_JSON ===\n', '\n=== FIN GUARDADA ===\n\n=== GRUPO_A_INVESTIGAR ===\n',
             '\n=== FIN GRUPO ===\n\n=== GUION_COMPLETO ===\n', '\n=== FIN GUION ===\n']
        partes = [cfgj, _j(base), _j(d4p), _j(guardada), _j(grupo), X['g']]
        pr = texto
        for k, q in enumerate(partes): pr += r[k] + q
        pr += r[-1]
        fijo = {'paso': SOLO_VAR['fijo'], 'partes': {'texto': texto, 'rotulos_bloques': ''.join(r), 'esquema': esq, 'modelo': X['modelo'], 'nivel': X['nivel'],
                'max_out': X['AR'].MAX_OUT, 'max_rondas': 1, 'json_out': True}, 'fragmentos': [texto] + r}
        out.append({'sub': f'inv_escenarios_var_g{i + 1}de{n}', 'ids': ids, 'pr': pr, 'fijo': fijo, 'aprox': False, 'solo_variantes': True})
    return out, None

def union_vieja(D, p):
    """orden t340u: la unión respuestas/<p>.json está VIEJA si alguno de sus grupos (_taller.grupos) tiene respuesta más nueva (p. ej. re-corrida --repetir)."""
    fu = D / 'respuestas' / f'{p}.json'
    if not fu.is_file(): return False
    try: gr = (json.loads(fu.read_text(encoding='utf-8')).get('_taller') or {}).get('grupos') or []
    except Exception: return False
    for g in gr:
        f = archivo_resp(D, g, resuelto=False)
        if f.is_file() and f.stat().st_mtime > fu.stat().st_mtime + 1: return True
    return False

def unir_inv(X, p, pasos):
    """Si todos los grupos de p salieron bien, junta sus respuestas en respuestas/<p>.json (lo leen 4a2…4c3) y revisa los ids."""
    P, D = X['P'], X['D']
    grupos = [x for x in pasos if x.get('inv') == p]
    if ya_hecho_completo(D, p) and not union_vieja(D, p): return None   # orden t340u: unión vieja (un grupo es más nuevo) → se vuelve a unir, gratis
    pb = plan_biblioteca(D) if p == 'inv_escenarios' else None
    lib = (_leer_resp(P, D, 'biblioteca_inv_escenarios') or {}) if pb else {}
    ids_lib = [z['id'] for z in (pb or {}).get('plan', {}).get('4a1', {}).get('omitir', []) + (pb or {}).get('plan', {}).get('4a1', {}).get('solo_variantes', [])]
    regs_lib = [x for x in lib.get('escenarios', []) if isinstance(x, dict) and x.get('escenario_id') in ids_lib]
    if pb and (pb.get('pendiente_usuario') or []): return None   # dudosas sin confirmar: no se junta nada todavía
    if not grupos and not regs_lib: return None
    if not all(x['ya_hecho'] for x in grupos): return None
    var = [x for x in grupos if x.get('solo_variantes')]; grupos_inv = [x for x in grupos if not x.get('solo_variantes')]
    base = _leer_resp(P, D, 'base') or {}; cat = base.get('catalogo_oficial', {})
    clave =[REDACTED]
    vof = {v['variante_id'] for v in variantes_oficiales(_leer_resp(P, D, 'escenarios'))} if p == 'prompts_escenarios' else set()
    oficiales = {x.get('id') for x in cat.get(clave, [])}; oficiales_obj = {x.get('id') for x in cat.get('objetos', [])}
    uni = {clave: [], 'faltantes_en_base': [], 'contradicciones': [], 'dudas': []}
    desconocidos, pedidos, vistos_resp = set(), [], set()
    for x in grupos_inv:
        j = _leer_resp(P, D, x['paso']) or {}
        pedidos += x['ids']
        for k in uni:
            vs = [v for v in (j.get(k) or []) if v is not None]
            if k == clave and x.get('cubre_desde'):   # PISTA INMI (2026-10-29): orden 68 — de una respuesta compartida se toma SOLO lo de sus ids (sin repetir)
                vs = [v for v in vs if not isinstance(v, dict) or v.get(idk) in x['ids'] or v.get(idk) not in oficiales]
            elif k != clave and x.get('cubre_desde') and x.get('cubre_desde') in vistos_resp: vs = []
            if k != clave:   # PISTA INMI (2026-10-29): orden 72 — la misma nota de dos pedidos va una vez
                ya_ = {json.dumps(v, sort_keys=True, ensure_ascii=False) for v in uni[k]}
                vs = [v for v in vs if json.dumps(v, sort_keys=True, ensure_ascii=False) not in ya_]
            uni[k] += vs
        if x.get('cubre_desde'): vistos_resp.add(x['cubre_desde'])
    de_lib = set()
    if regs_lib:   # orden 62: lo guardado entra tal cual (ids ya traducidos al capítulo por biblioteca.py); + estados nuevos de «solo variantes»
        resp_var = {}
        for x in var:
            j = _leer_resp(P, D, x['paso']) or {}
            for v in (j.get('escenarios') or []):
                if isinstance(v, dict): resp_var[v.get('escenario_id')] = v
            for k in ('faltantes_en_base', 'contradicciones', 'dudas'): uni[k] += [v for v in (j.get(k) or []) if v is not None]
        for r0 in regs_lib:
            r1 = json.loads(json.dumps(r0)); i = r1.get('escenario_id'); pedidos.append(i); de_lib.add(i)
            nv = resp_var.get(i)
            if nv:
                for k in ('variantes_por_escena', 'luz_por_escena', 'camaras_sugeridas'):
                    r1[k] = list(r1.get(k) or []) + [q for q in (nv.get(k) or []) if q is not None]
                av = r1.get('ambiente_vivo') if isinstance(r1.get('ambiente_vivo'), dict) else {}
                av['ambiente_por_escena'] = list(av.get('ambiente_por_escena') or []) + [q for q in (nv.get('ambiente_por_escena') or []) if q is not None]
                r1['ambiente_vivo'] = av
                r1['_solo_variantes'] = {'cambios_sobre_guardado': nv.get('cambios_sobre_guardado') or []}
            elif i in {z['id'] for z in pb['plan']['4a1'].get('solo_variantes', [])}:
                continue   # pedía estados nuevos y no llegaron: queda en ids_sin_respuesta
            uni[clave].append(r1)
    pedidos += [i for i in ids_lib if i not in pedidos]   # reutilizado sin investigación guardada → queda en ids_sin_respuesta
    amb_ascensos, amb_ids_corregidos, amb_conteo = [], [], {}
    limpios = []   # lo que trae un id no oficial se aparta: no llega a 4a2…4c3 (queda anotado en ids_inventados)
    vistos_id, repetidos = set(), []   # orden 72: un registro por id (si llegara dos veces, vale el primero y el otro se anota)
    for v in uni[clave]:
        if not isinstance(v, dict) or v.get(idk) not in oficiales: desconocidos.add(str(v.get(idk) if isinstance(v, dict) else v)); continue
        if v.get(idk) in vistos_id: repetidos.append(v.get(idk)); continue
        vistos_id.add(v.get(idk))
        pos = []
        for o in (v.get('objetos_del_lugar_posicion') or []):
            if isinstance(o, dict) and o.get('objeto_id') in oficiales_obj: pos.append(o)
            elif v.get(idk) in de_lib: pass   # objeto del lugar de otro capítulo que este catálogo no tiene: se omite sin contarlo como inventado
            else: desconocidos.add(str(o.get('objeto_id') if isinstance(o, dict) else o))
        if 'objetos_del_lugar_posicion' in v: v['objetos_del_lugar_posicion'] = pos
        if p == 'inv_escenarios':   # orden 61 (dos zonas): ambiente_vivo = zona AMBIENTE, ids propios amb-…; se valida por forma, NO contra la lista oficial
            import ambiente as AMB
            am, cam = AMB.normalizar(v.get(idk), v.get('ambiente_vivo'))
            amb_ascensos.extend(dict(x, escenario_id=v.get(idk)) for x in AMB.marcar_ascenso(am, cat.get('objetos', []), 'catalogo_oficial (caja 4)'))
            amb_ids_corregidos.extend(f"{v.get(idk)}: {c}" for c in cam)
            v['ambiente_vivo'] = am; amb_conteo[v.get(idk)] = AMB.conteo(am)
        if p == 'prompts_escenarios':   # variantes y objetos visibles: solo ids oficiales
            b = v.get('base') if isinstance(v.get('base'), dict) else {}
            if b.get('cubre_variante_id') is not None and b.get('cubre_variante_id') not in vof:
                desconocidos.add(str(b.get('cubre_variante_id'))); b['cubre_variante_id'] = None
            vv = []
            for q in (v.get('variantes') or []):
                if isinstance(q, dict) and q.get('variante_id') in vof: vv.append(q)
                else: desconocidos.add(str(q.get('variante_id') if isinstance(q, dict) else q))
            v['variantes'] = vv
            import paso00_pintar as PNT   # orden 65: vistas (cámara del molde), en_vistas y zonas del guion cubiertas — misma regla que usa 4a5
            avs = PNT.validar_escenario(v, D)
            uni.setdefault('_revision_vistas', []).extend(avs)
            for c in [b] + vv + list(v.get('vistas') or []):
                ob = []
                for o in (c.get('objetos_visibles') or []):
                    if isinstance(o, dict) and o.get('objeto_id') in oficiales_obj: ob.append(o)
                    else: desconocidos.add(str(o.get('objeto_id') if isinstance(o, dict) else o))
                c['objetos_visibles'] = ob
        limpios.append(v)
    uni[clave] = limpios
    llegaron = {v.get(idk) for v in uni[clave]}
    usd = round(sum((_resp_util(D, n_) or {}).get('usd_real') or 0 for n_ in dict.fromkeys(x['paso'] for x in grupos)), 4)   # orden 68: una respuesta compartida se cuenta una vez
    if p == 'prompts_escenarios':
        cubiertas = {(v.get('base') or {}).get('cubre_variante_id') for v in uni[clave]} | {q.get('variante_id') for v in uni[clave] for q in v.get('variantes', [])}
        uni['_variantes_sin_prompt'] = sorted(vof - cubiertas)
    uni['_taller'] = {'caja': PASOS[p], 'grupos': [x['paso'] for x in grupos], 'ids_inventados': sorted(desconocidos), 'ids_repetidos_apartados': repetidos,
                      'ids_sin_respuesta': [i for i in pedidos if i not in llegaron], 'usd_real': usd, 'hora': ahora()}
    if pb: uni['_taller']['biblioteca'] = {'reutilizados_sin_pagar': sorted(de_lib - {x for g in var for x in g['ids']}), 'solo_variantes': [x for g in var for x in g['ids']],
                                           'investigados': [x for g in grupos_inv for x in g['ids']], 'plan_hora': pb.get('hora')}
    if p == 'inv_escenarios': uni['_taller'].update(ambiente_por_escenario=amb_conteo, ambiente_ascensos=amb_ascensos, ambiente_ids_corregidos=amb_ids_corregidos)
    for f_ in (D / 'respuestas' / f'{p}.json', D / 'resultados' / f'{p}.json'):   # orden 68: la unión vieja (incompleta) se guarda en archivo/, no se pierde
        if f_.is_file():
            (D / 'archivo').mkdir(exist_ok=True); shutil.copy2(f_, D / 'archivo' / f"{f_.parent.name}_{p}_{time.strftime('%Y%m%d-%H%M%S')}.json")
    (D / 'respuestas' / f'{p}.json').write_text(json.dumps(uni, ensure_ascii=False, indent=1), encoding='utf-8')
    res = {'paso': p, 'estado': 'ok', 'usd_real': usd, 'grupos': uni['_taller']['grupos'], 'registros': len(uni[clave]), **({'biblioteca': uni['_taller']['biblioteca']} if pb else {}),
           'ids_inventados': uni['_taller']['ids_inventados'], 'ids_sin_respuesta': uni['_taller']['ids_sin_respuesta'], 'fin_hora': ahora(), **({'ambiente_por_escenario': amb_conteo, 'ambiente_ascensos': len(amb_ascensos), 'ambiente_ids_corregidos': len(amb_ids_corregidos)} if p == 'inv_escenarios' else {}), **({'variantes_sin_prompt': uni['_variantes_sin_prompt'], 'imagenes_base': len(uni[clave]),
           'ediciones': sum(len(v.get('variantes', [])) for v in uni[clave]), 'vistas': sum(len(v.get('vistas') or []) for v in uni[clave]),
           'revision_vistas': uni.get('_revision_vistas') or []} if p == 'prompts_escenarios' else {})}
    (D / 'resultados' / f'{p}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res

def fijos_aceptados(p):
    a_ = {f'taller00_{VER}_{PASOS[p]}{r_}' for r_ in REV_ACEPTADAS.get(p, (REV_FIJO[p],))}
    return a_ | ({None} if p in SIN_FIJO_LEGADO else set())   # orden 72: 4b1/4c1 viejos (sin fijo del taller) siguen valiendo

def cobertura_inv(D, p):
    """PISTA INMI (2026-10-29): orden 72 — {id: pedido} de los ids que ya vinieron VÁLIDOS (revisados por el código) en cualquier
    pedido anterior de 4a1/4b1/4c1. El más nuevo gana. Esos ids no se vuelven a pagar."""
    cubre = {}
    for z in solo_hechos(D, p):
        for i in z['trae']: cubre.setdefault(i, z)
    return cubre

_ESTADO_TXT = {'truncado': 'la respuesta se cortó (MAX_TOKENS)', 'json_roto': 'JSON roto que no se pudo reparar', 'error': 'error al llamar',
               'no_llamado': 'no se llamó', 'incompleto': 'incompleta'}

def fallidos_inv(D, p):
    """orden 72: {id: {paso, estado, texto}} de los ids cuyo ÚLTIMO intento no sirvió (y que no están cubiertos por otro pedido válido).
    Es lo que pide --solo-fallidos (gratis de calcular; sin red)."""
    ult = {}
    fs = [f for f in (D / 'resultados').glob(f'{p}_*.json') if inv_de(f.stem) == p]
    for f in sorted(fs, key=lambda f: (f.stat().st_mtime, f.name)):
        try: r = json.loads(f.read_text())
        except Exception: continue
        ids = [str(i) for i in (r.get('ids') or [])]
        h = _resp_util(D, f.stem)
        rv = revisar_ids_resp(p, _obj_resp(D, f.stem), ids) if h else None
        for i in ids:
            if rv and i in rv['buenos']: ult[i] = None; continue
            if rv: t = LS.texto_ids({**rv, 'pedidos': [i], 'buenos': [], 'faltan': [i] if i in rv['faltan'] else [], 'sin_campos': {i: rv['sin_campos'][i]} if i in rv['sin_campos'] else {},
                                     'ajenos': [], 'repetidos': [i] if i in rv['repetidos'] else [], 'sin_id': 0, 'completo': False}, i)
            else: t = f"{i}: {_ESTADO_TXT.get(r.get('estado'), r.get('estado'))}" + (f" — {str(r.get('error') or r.get('motivo') or '')[:160]}" if (r.get('error') or r.get('motivo')) else '')
            ult[i] = {'paso': f.stem, 'estado': r.get('estado') if not rv else 'incompleto', 'texto': t}
    cub = cobertura_inv(D, p)
    return {i: v for i, v in ult.items() if v and i not in cub}

def solo_hechos(D, p):
    """Orden 66: grupos sueltos de 4a4 (--solo) ya hechos y válidos, con sus ids.
    PISTA INMI (2026-10-29): orden 68 — también los pedidos por escenario (prompts_escenarios__<id>) y los grupos automáticos
    viejos; solo si su JSON es válido (ya_hecho) y con un fijo aceptado. 'trae' = ids que de verdad vinieron en la respuesta."""
    out = []
    fs = sorted((D / 'resultados').glob(f'{p}_*.json'), key=lambda f: (not f.stem.startswith(f'{p}__'), -f.stat().st_mtime, f.name))
    for f in fs:
        if not (f.stem.startswith(f'{p}__') or re.fullmatch(re.escape(p) + r'_g\d+de\d+(_solo(_[0-9a-f]+)?)?', f.stem)): continue
        h = _resp_util(D, f.stem)   # orden 69: JSON que sirve; las cámaras se revisan por escenario (abajo)
        if not h or not h.get('ids'): continue
        if REV_FIJO.get(p) and h.get('fijo_paso') not in fijos_aceptados(p): continue
        j = _obj_resp(D, f.stem)
        clave_, idk_ = clave_de(p)   # PISTA INMI (2026-10-29): orden 72 — genérico (4a1/4b1/4c1 por objeto_id / escenario_id)
        trae = [v.get(idk_) for v in ((j or {}).get(clave_) or []) if isinstance(v, dict)]
        if p in INV_O72: trae = revisar_ids_resp(p, j, h['ids'])['buenos']   # orden 72: solo los registros que el CÓDIGO da por buenos
        rc = revision_camaras(D, j) if p == 'prompts_escenarios' else {}
        inc = [i for i in h['ids'] if i in trae and i in rc and not rc[i]['completo']]   # PISTA INMI (2026-10-29): orden 69 — incompleto = no trae
        out.append({'paso': f.stem, 'ids': list(h['ids']), 'usd': h.get('usd_real'), 'trae': [i for i in h['ids'] if i in trae and i not in inc],
                    'incompletos': [rc[i] for i in inc]})
    return out

def incompleto_antes(D, eid):
    """orden 69: la última respuesta USABLE de 4a4 que trae eid con cámaras faltantes/repetidas (None si ninguna)."""
    for z in solo_hechos(D, 'prompts_escenarios'):
        for r in z.get('incompletos') or []:
            if r['escenario_id'] == eid: return dict(r, paso=z['paso'], texto=LS.texto_camaras(r))
    return None

def _resp_util(D, paso):
    """PISTA INMI (2026-10-29): orden 68 — respuesta que SIRVE como JSON: estado ok con JSON válido (json_valido no False), o
    «reparado» (arreglo local aplicado con OK) con su .reparado.json. Antes un JSON roto quedaba «ok» y no se volvía a pedir.
    orden 69: también «incompleto» (JSON bueno, pero faltan cámaras): sirve para saber QUÉ falta, nunca cuenta como hecho."""
    f = D / 'resultados' / f'{paso}.json'
    if not f.is_file(): return None
    try: r = json.loads(f.read_text())
    except Exception: return None
    if r.get('estado') in ('ok', 'incompleto') and r.get('json_valido') is not False and (D / 'respuestas' / f'{paso}.json').is_file(): return r
    if r.get('estado') in ('reparado', 'incompleto') and (D / 'respuestas' / f'{paso}.reparado.json').is_file() and archivo_resp(D, paso).name.endswith('.reparado.json'): return r
    return None

def respaldar_previo(D, paso):
    """t531u: copia (no mueve) lo que ya había de este paso antes de repetirlo. Genérico, cualquier canal/capítulo."""
    import shutil, datetime as _dt
    dst = D / 'respaldos_repetir' / (_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=-5))).strftime('%Y%m%d_%H%M%S') + f'_bogota_{paso}')
    n = 0
    for sub, pat in (('pedidos', f'{paso}.txt'), ('respuestas', f'{paso}*.json'), ('resultados', f'{paso}*'), ('pedidos', f'_div*_{paso}*'), ('respuestas', f'_div*_{paso}*'), ('resultados', f'_div*_{paso}*')):   # t337u: también las partes divididas
        for f in sorted((D / sub).glob(pat)):
            if f.is_file(): (dst / sub).mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst / sub / f.name); n += 1
    return {'carpeta': str(dst), 'archivos': n}

def ya_hecho(D, paso):
    """hecho = _resp_util y, en 4a4 (orden 69), TODOS sus escenarios con una imagen por cámara del molde (lo revisa el código cada vez:
    no se confía en el estado guardado ni en camaras_faltantes del modelo). «incompleto» nunca cuenta como hecho."""
    r = _resp_util(D, paso)
    if not r or r.get('estado') == 'incompleto': return None
    if incompletos_de(D, paso): return None
    p_ = inv_de(paso)   # PISTA INMI (2026-10-29): orden 72 — 4a1/4b1/4c1: el código revisa un registro por id (no se confía en el estado guardado)
    if p_ and r.get('ids') and not revisar_ids_resp(p_, _obj_resp(D, paso), r['ids'])['completo']: return None
    return r

def ya_hecho_completo(D, paso):
    """orden 68: la unión de 4a4 solo cuenta como hecha si no le falta ningún escenario (ids_sin_respuesta vacío)."""
    h = ya_hecho(D, paso)
    if h and paso in INV and h.get('ids_sin_respuesta'): return None   # orden 72: vale para 4a1/4b1/4c1 también
    return h

def reparables(D, p):
    """orden 68: respuestas de p con JSON roto que el arreglo local (gratis) deja válidas. No cambia nada."""
    out = []
    for f in sorted((D / 'resultados').glob(f'{p}_*.json')):
        if p in INV_O72 and inv_de(f.stem) != p: continue
        try: r = json.loads(f.read_text())
        except Exception: continue
        if r.get('estado') not in ('ok', 'json_roto') or r.get('json_valido') is not False: continue
        fr = D / 'respuestas' / f'{f.stem}.json'
        if not fr.is_file(): continue
        rv = LS.revisar_respuesta(fr.read_text(encoding='utf-8'), None, r.get('fin'))
        if rv['estado'] != 'reparable': continue
        clave_, idk_ = clave_de(p)   # PISTA INMI (2026-10-29): orden 72 — genérico
        out.append({'paso': f.stem, 'ids': r.get('ids'), 'arreglos': [{k: v for k, v in e.items() if k != 'contexto'} for e in rv['ediciones']],
                    'escenarios_recuperados': [v.get('escenario_id') for v in (rv['obj'].get('escenarios') or []) if isinstance(v, dict)],
                    'ids_recuperados': [v.get(idk_) for v in (rv['obj'].get(clave_) or []) if isinstance(v, dict)],
                    **({'revision_ids': LS.texto_ids(revisar_ids_resp(p, rv['obj'], r.get('ids') or []), f.stem) or 'completo'} if p in INV_O72 else {}),
                    'archivo_reparado_escrito': (D / 'respuestas' / f'{f.stem}.reparado.json').is_file(),
                    **(lambda rc: {'camaras': {k: ('completo' if v['completo'] else LS.texto_camaras(v)) for k, v in rc.items()},   # PISTA INMI (2026-10-29): orden 69
                                   'escenarios_completos': [k for k, v in rc.items() if v['completo']]})(revision_camaras(D, rv['obj']) if p == 'prompts_escenarios' else {}),
                    'aplicar': f'paso00_cadena.py reparar {f.stem} --aplicar --aprobado QUIEN (US$0, con OK de Ricardo)'})
    return out

def sumar_fijos_del_canal(canal_id, cfg, cat):
    """t528u (Ricardo, 2-nov-2026) — GENÉRICO para cualquier canal. Antes, la BASE (caja 4) y el 4p solo recibían
    el catálogo de studio.db (objetos de lugar/historia) y la biblia/ficha del canal: NO veían lo ya aprobado en
    cubo_fijo (objetos_pj y poderes del canal) ni las decisiones de Ricardo en cubo_fijo/overrides.json.
    Resultado: un objeto que el guion nombra con otro nombre (apodo, el efecto que dispara) se fundía con otro o se
    rediseñaba según una regla vieja de la biblia. Aquí se agregan, como DATOS (el texto del prompt no cambia):
      - cat['objetos_fijos_del_canal']: fichas de cubo_fijo cuyo «canal» es exactamente el id de este canal;
      - cfg['decisiones_vigentes_del_canal']: reglas y prohibiciones globales de overrides.json para este canal.
    No inventa nada: si el canal no tiene fichas ni overrides, no agrega nada."""
    cubo = CAJAS / 'cubo_fijo'; fijos = []
    for carpeta_, clase in (('objetos_pj', 'objeto'), ('poderes', 'poder')):
        for f in sorted((cubo / carpeta_).glob('*.json')):
            try: d = json.loads(f.read_text(encoding='utf-8'))
            except Exception: continue
            if canal_id not in (d.get('canal'), d.get('canal_id')) or not d.get('nombre'): continue   # canal_id: fichas viejas con apodo (cubo_fijo_canal_id.py)
            fijos.append({k: v for k, v in {'id_ficha': d.get('id'), 'nombre': d.get('nombre'), 'clase': d.get('clase') or clase,
                          'portador': d.get('portador') or d.get('dueno'), 'sale_de': d.get('sale_de')}.items() if v})
    if fijos:
        cat['objetos_fijos_del_canal'] = {
            'nota': ('Objetos y poderes YA APROBADOS de este canal (fichas fijas). Si el guion usa uno con otro nombre '
                     '(apodo, el efecto que dispara, «su …»), es el MISMO: va en catalogo_oficial.objetos con en_canal '
                     '«reutilizado», el nombre que dice el guion y una duda que lo relacione. Un objeto que un personaje lleva '
                     'o usa es objeto aparte, no parte del personaje. Un poder/efecto (rayo, estela, holograma) va en catalogo_oficial.efectos, no en objetos.'),
            'fichas': fijos}
    try:
        ov = json.loads((cubo / 'overrides.json').read_text(encoding='utf-8'))
        g_ = ((ov.get('canales') or {}).get(canal_id) or {}).get('global') or {}
    except Exception:
        g_ = {}
    if g_.get('reglas') or g_.get('prohibiciones'):
        cfg['decisiones_vigentes_del_canal'] = {
            'nota': ('Decisiones humanas MÁS RECIENTES del canal (cubo_fijo/overrides.json). Si chocan con la biblia, la '
                     'ficha o material_cliente, mandan estas: no las cuentes como contradicción ni rediseñes el objeto.'),
            'fuente': g_.get('fuente') or 'cubo_fijo/overrides.json',
            'reglas': g_.get('reglas') or [], 'prohibiciones': g_.get('prohibiciones') or []}
    try:   # t321u — GENÉRICO: la dimensión (2D/3D) del estilo APROBADO del canal manda sobre textos viejos de la biblia
        import estilo_oficial as _EO
        _d = _EO.dimension(canal_id)
        if _d.get('dimension') in ('2D', '3D'):
            cfg['estilo_vigente_del_canal'] = {
                'dimension': _d['dimension'], 'fuente': _d.get('fuente'),
                'nota': (f"Estilo aprobado y sellado del canal: {_d['dimension']}. Manda sobre cualquier línea de la biblia o la ficha "
                         'que diga otra dimensión (texto viejo): no lo cuentes como contradicción ni lo uses para describir.')}
    except Exception:
        pass
    return cfg, cat

def preparar(a, pagar):
    bloquear_red(permitir_google=pagar)
    T = Path(os.environ['TALLER_DATOS']) if os.environ.get('TALLER_DATOS') else copiar_datos()
    cred = ruta_credencial() if pagar else None
    if pagar and not cred: salir({'ok': False, 'error': 'no encuentro la credencial del servidor de staging (¿está corriendo servidor_real.py?)'})
    A, P, PB, AR, FP, F = cargar_app(T, cred)
    e = episodio(A, a.canal, a.capitulo)
    cfg = P.config_de(A, e); g = P.guion_de(A, e); canal = A.get_channel(e['channel_id']); cat = PB.catalogo_de(canal)
    sumar_fijos_del_canal(e['channel_id'], cfg, cat)   # t528u: lo aprobado del canal (cubo_fijo) llega a la BASE y al 4p
    modelo, nivel = P.argon_de(cfg)
    if (modelo, nivel) != ('gemini-4-argon', 'HIGH'): salir({'ok': False, 'error': f'modelo del canal {modelo} {nivel}, se esperaba gemini-4-argon HIGH'})
    D = carpeta(a.canal, e)
    cd = canal.get('data') if isinstance(canal, dict) else None
    try: cd = json.loads(cd) if isinstance(cd, str) else (cd or {})
    except Exception: cd = {}
    return dict(T=T, A=A, P=P, PB=PB, AR=AR, FP=FP, F=F, e=e, cfg=cfg, g=g, cat=cat, modelo=modelo, nivel=nivel, D=D, canal_data=cd)

def cotizacion(a, X, aprox_ok):
    tc = X['AR'].tope_de_canal(X['cfg']); tope = TOPE_LLAMADA if tc is None else min(TOPE_LLAMADA, tc)
    pasos = []
    X['solo'] = set(z for z in (getattr(a, 'solo', None) or '').split(',') if z)
    for p in CAJA[a.caja]:
        if p in INV:
            nuevo = bool(getattr(a, 'como_nuevo', False)) and p in INV_O72   # PISTA INMI (2026-10-29): orden 72 — peor caso «desde cero» (solo cotizar)
            rep_ = bool(getattr(a, 'repetir', False)) and p in INV_O72   # t337u: --repetir también en 4a1/4b1/4c1 (genérico): nada cuenta como hecho
            h = None if (nuevo or rep_) else ya_hecho_completo(X['D'], p)
            if h and union_vieja(X['D'], p): h = None   # orden t340u: un grupo se volvió a correr → se cotiza por grupos (lo hecho vale US$0) y se vuelve a unir
            if h and p in INV_O72 and not X['solo'] and not getattr(a, 'solo_fallidos', False):
                # t453u (Ricardo): la unión puede estar «hecha» pero VIEJA si el catálogo (4p/objetos) cambió después.
                # Se pregunta al mismo armado (gratis, sin red) qué ids del catálogo ACTUAL no están cubiertos; si hay alguno, no cuenta como hecho.
                X['cubiertos'] = set(cobertura_inv(X['D'], p)); X['restringir'] = None; X['fallidos_inv'] = {}; X['reparables'] = []
                try: partes_cat, _e = armar_inv(p, X, aprox_ok, tope)
                except Exception: partes_cat = None
                pend = sorted({i for q in (partes_cat or []) for i in (q.get('ids') or [])})
                if pend:
                    X.setdefault('catalogo_cambio', {})[p] = pend; h = None
            if h:
                pasos.append({'paso': p, 'prueba': PASOS[p], 'inv': p, 'ids': None, 'peor_caso_usd': 0.0, 'cabe_en_tope': True, 'ya_hecho': True,
                              'usd_real_anterior': h.get('usd_real'), 'aproximado_sin_base': False}); continue
            cubre, fall = {}, {}
            if p in INV_O72:   # orden 72: lo ya válido (por id) cuenta como hecho; --solo / --solo-fallidos limitan lo que se pide
                cubre = {} if (nuevo or rep_) else cobertura_inv(X['D'], p)
                fall = {} if nuevo else fallidos_inv(X['D'], p)
                X['cubiertos'] = set(cubre)
                rs = None
                if X['solo']: rs = set(X['solo'])
                if getattr(a, 'solo_fallidos', False): rs = set(fall) if rs is None else rs & set(fall)
                X['restringir'] = rs
                X['fallidos_inv'] = fall
                X['reparables'] = reparables(X['D'], p)
            partes, err = armar_inv(p, X, aprox_ok, tope)
            if partes is None: salir({'ok': False, 'caja': a.caja, 'error': err})
            n0 = len(pasos)
            if p in INV_O72 and cubre and X.get('restringir') is None:
                por_ = {}
                for i, z in cubre.items(): por_.setdefault(z['paso'], (z, []))[1].append(i)
                for ps_, (z, ids_) in sorted(por_.items()):
                    pasos.append({'paso': ps_, 'prueba': PASOS[p], 'inv': p, 'ids': ids_, 'peor_caso_usd': 0.0, 'cabe_en_tope': True, 'ya_hecho': True,
                                  'usd_real_anterior': z['usd'], 'aproximado_sin_base': False, 'grupo_suelto': True, 'cubre_desde': ps_})
            for q in partes:
                est = q.get('est') if q.get('est') is not None else X['AR'].estimar(len(q['pr']), modelo=X['modelo'])
                hq = None if (nuevo or getattr(a, 'repetir', False)) else ya_hecho(X['D'], q['sub'])
                if hq and hq.get('ids') != q['ids']: hq = None   # cambió el grupo: no cuenta como hecho
                if hq and q.get('solo_variantes'):
                    if hq.get('fijo_paso') != SOLO_VAR['fijo']: hq = None
                elif hq and REV_FIJO.get(p) and hq.get('fijo_paso') not in fijos_aceptados(p):
                    hq = None   # orden 61/61c: hecho con un texto fijo no aceptado → no cuenta
                pasos.append({'paso': q['sub'], 'prueba': PASOS[p], 'inv': p, 'ids': q['ids'], 'prompt_chars': len(q['pr']), 'peor_caso_usd': est,
                              'aproximado_sin_base': q['aprox'], 'cabe_en_tope': (max(z['est'] for z in q['dividir']['partes']) if q.get('dividir') else est) <= tope + 1e-9, 'ya_hecho': bool(hq),
                              'usd_real_anterior': hq.get('usd_real') if hq else None, '_pr': q['pr'], '_fijo': q['fijo'], **({'solo_variantes': True} if q.get('solo_variantes') else {}),
                              **({'entrada': q['entrada'], '_adj': q['adjuntos']} if q.get('entrada') else {}), **({'_max_out': q['max_out']} if q.get('max_out') else {}),
                              **({'_esquema': q['esquema']} if q.get('esquema') is not None else {}), **({'_rearmar': q['rearmar']} if q.get('rearmar') else {}),   # orden 68
                              **({'_dividir': q['dividir'], 'dividido_en': [{'parte': z['nombre'], 'paso': z['sub'], 'propiedades': z['propiedades'], 'peor_caso_usd': z['est'], 'nota': z['nota']} for z in q['dividir']['partes']],
                                  'propiedades_completo': q['dividir']['propiedades_completo']} if q.get('dividir') else {}),   # orden t331u
                              **({'max_out_tokens': q['max_out'], 'salida_estructurada': True, 'fallo_antes': {i: fall[i]['texto'] for i in q['ids'] if i in fall}} if p in INV_O72 else {})})   # orden 72
            if p == 'prompts_escenarios':   # PISTA INMI (2026-10-29): orden 68 — por escenario: lo que ya vino VÁLIDO (en cualquier pedido anterior) cuenta como hecho; se cotiza solo lo que falta o vino roto
                cubre = {}
                for z in solo_hechos(X['D'], p):
                    for i in z['trae']: cubre.setdefault(i, z)
                for k_, x in enumerate(pasos[n0:], n0):
                    i = (x.get('ids') or [None])[0]
                    if x['ya_hecho'] or len(x.get('ids') or []) != 1 or i not in cubre or cubre[i]['paso'] == x['paso']: continue
                    z = cubre[i]
                    pasos[k_] = {'paso': z['paso'], 'prueba': PASOS[p], 'inv': p, 'ids': [i], 'peor_caso_usd': 0.0, 'cabe_en_tope': True, 'ya_hecho': True,
                                 'usd_real_anterior': z['usd'], 'aproximado_sin_base': False, 'grupo_suelto': True, 'cubre_desde': z['paso']}
                X['reparables'] = reparables(X['D'], p)
                for x in pasos[n0:]:   # PISTA INMI (2026-10-29): orden 69 — por qué se vuelve a pedir: la respuesta anterior vino con cámaras de menos
                    if not x['ya_hecho'] and len(x.get('ids') or []) == 1:
                        ia = incompleto_antes(X['D'], x['ids'][0])
                        if ia: x['incompleto_antes'] = {k: ia[k] for k in ('paso', 'faltan', 'repetidas', 'ajenas', 'imagenes_esperadas', 'vistas_esperadas', 'vistas_recibidas', 'texto')}
            continue
        pr, fijo, nota = armar(p, X['cfg'], X['cat'], X['g'], X['modelo'], X['nivel'], X['AR'], X['P'], X['D'], aprox_ok, obj_canal=objetos_del_canal(X['cat'], X.get('canal_data')))   # t310u
        if pr is None: salir({'ok': False, 'caja': a.caja, 'error': nota})
        meta = nota if isinstance(nota, dict) else {'aprox': nota == 'aprox'}
        if isinstance(nota, str): salir({'ok': False, 'caja': a.caja, 'error': nota})  # compat
        pf = meta.get('preflight') or {}
        if pf and pf.get('ok') is False: salir({'ok': False, 'caja': a.caja, 'error': pf.get('error'), 'preflight': pf, 'recorte': meta.get('recorte')})
        est = X['AR'].estimar(len(pr), modelo=X['modelo'])
        h = None if getattr(a, 'repetir', False) else ya_hecho(X['D'], p)   # t531u: --repetir = volver a pedir aunque ya esté hecho (genérico)
        pasos.append({'paso': p, 'prueba': PASOS[p], 'prompt_chars': len(pr), 'peor_caso_usd': est, 'aproximado_sin_base': bool(meta.get('aprox')),
                      'cabe_en_tope': est <= tope + 1e-9, 'ya_hecho': bool(h), 'usd_real_anterior': h.get('usd_real') if h else None,
                      '_pr': pr, '_fijo': fijo,
                      **({'recorte': meta['recorte']} if meta.get('recorte') else {}),
                      **({'preflight': pf} if pf else {})})
    solo = set(x for x in (getattr(a, 'solo', None) or '').split(',') if x)
    if solo and CAJA[a.caja][0] in ('prompts_escenarios',) + INV_O72:   # orden 63: prueba barata = solo el/los grupo(s) con esos ids (orden 72: también 4a1/4b1/4c1)
        pasos = [x for x in pasos if x.get('ids') and solo & set(x['ids'])]
    total = round(sum(x['peor_caso_usd'] for x in pasos if not x['ya_hecho']), 4)
    return pasos, total, tope, tc

def publico(pasos): return [{k: v for k, v in x.items() if not k.startswith('_')} for x in pasos]

def marca_corrida(D, corrida, que):
    if not corrida: return False
    f = D / 'corridas' / f'{corrida}_{que}'
    if f.exists(): return True
    f.write_text(ahora()); return False

def cmd_cotizar(a):
    X = preparar(a, pagar=False)
    try:
        rep = marca_corrida(X['D'], a.corrida, f'cotizar_{a.caja}')
        pasos, total, tope, tc = cotizacion(a, X, aprox_ok=True)
        parcial = getattr(a, 'solo', None) or getattr(a, 'solo_fallidos', False) or getattr(a, 'como_nuevo', False)   # orden 72: tampoco con --solo-fallidos / --como-nuevo
        u = unir_inv(X, CAJA[a.caja][0], pasos) if CAJA[a.caja][0] in INV and not parcial else None   # orden 63b: con --solo no se une (sería un 4a4 a medias)
        r = {'ok': True, 'accion': 'cotizar', 'caja': a.caja, 'canal': a.canal, 'capitulo': int(X['e']['number']), 'episodio': X['e']['id'],
             'titulo': X['e'].get('title'), 'modelo': f"{X['modelo']} {X['nivel']}", 'pasos': publico(pasos), 'total_peor_caso_usd': total,
             'tope_por_llamada_usd': tope, 'tope_canal_usd': tc, 'todo_cabe': all(x['cabe_en_tope'] for x in pasos), 'repetido_en_esta_corrida': rep,
             'carpeta': str(X['D']), 'hora': ahora(), 'gratis': True}
        if CAJA[a.caja][0] == 'inv_escenarios': r['biblioteca'] = resumen_biblioteca(X['D'], pasos, u)
        if CAJA[a.caja][0] == 'prompts_escenarios':   # PISTA INMI (2026-10-29): orden 68 — reintentar SOLO lo que falta; lo reparable gratis se muestra aparte
            r['falta_pedir'] = [i for x in pasos if not x['ya_hecho'] for i in (x.get('ids') or [])]
            r['ya_validos'] = sorted({i for x in pasos if x['ya_hecho'] for i in (x.get('ids') or [])})
            r['reparables_gratis'] = X.get('reparables') or []
            r['incompletos'] = [dict(x['incompleto_antes'], escenario_id=x['ids'][0]) for x in pasos if x.get('incompleto_antes')]   # orden 69
        if CAJA[a.caja][0] in INV_O72:   # PISTA INMI (2026-10-29): orden 72 — mismo informe que 4a4, por id
            fa = X.get('fallidos_inv') or {}
            r.update(falta_pedir=[i for x in pasos if not x['ya_hecho'] for i in (x.get('ids') or [])],
                     ya_validos=sorted({i for x in pasos if x['ya_hecho'] for i in (x.get('ids') or [])}), reparables_gratis=X.get('reparables') or [],
                     fallidos_antes=[dict(v, id=i) for i, v in sorted(fa.items())], pedidos_a_pagar=sum(1 for x in pasos if not x['ya_hecho']),
                     ids_por_pedido=MAX_POR_LLAMADA[CAJA[a.caja][0]], solo_fallidos=bool(getattr(a, 'solo_fallidos', False)), como_nuevo=bool(getattr(a, 'como_nuevo', False)),
                     revision='el código revisa cada respuesta: un registro por id pedido, con sus campos obligatorios (ok / reparado / incompleto / json_roto / truncado)')
            if getattr(a, 'solo_fallidos', False) and not r['falta_pedir']: r['nota'] = 'no hay nada fallido que volver a pedir'
            if r['como_nuevo']: r['nota'] = 'como nuevo: peor caso si se pidiera TODO desde cero (no cambia nada, no une; lo hecho sigue valiendo)'
        nom = f"cotizacion_{a.caja}{'_como_nuevo' if getattr(a, 'como_nuevo', False) else ''}.json"
        (X['D'] / 'resultados' / nom).write_text(json.dumps(r, ensure_ascii=False, indent=1))
        if a.caja in PASO_DE_CAJA and not parcial:   # VER pre-pago (inmi 2-nov-2026): manifiesto SECO del paso Argon, para «VER⇢<paso>» del flujo
            try:
                MFD = CAJAS / 'ver_prepago' / 'manifiestos'; MFD.mkdir(parents=True, exist_ok=True)
                (MFD / f"prepago_{a.caja}_{a.canal}_cap{int(X['e']['number']):02d}.json").write_text(json.dumps({
                    'tipo': 'argon_texto', 'caja': a.caja, 'paso': PASO_DE_CAJA[a.caja], 'canal': a.canal, 'capitulo': int(X['e']['number']),
                    'episodio': X['e']['id'], 'cotizacion': str(X['D'] / 'resultados' / nom), 'guarda': str(GATE_00), 'ledger': str(LEDGER),
                    'creado': ahora()}, ensure_ascii=False, indent=1))
            except Exception as e: r['aviso_manifiesto'] = f'no se escribió el manifiesto VER: {e}'
        return r
    finally:
        if not os.environ.get('TALLER_DATOS'): shutil.rmtree(X['T'], ignore_errors=True)

def resumen_biblioteca(D, pasos, union=None):
    pb = plan_biblioteca(D)
    if not pb: return None
    a1 = pb['plan']['4a1']
    return {'reutilizados_usd0': [z['id'] for z in a1.get('omitir', [])], 'solo_variantes': [z['id'] for z in a1.get('solo_variantes', [])],
            'investigar': [i for x in pasos if not x.get('solo_variantes') and x.get('ids') for i in x['ids']], 'pendiente_usuario': pb.get('pendiente_usuario') or [],
            'propios': a1.get('propio', []), 'junto_sin_pagar': bool(union), 'plan_hora': pb.get('hora'),
            'texto': pb.get('resumen')}

def _estado_ledger(AR, id_):
    """Estado de la línea id_ en el ledger (None si no se anotó: falló ANTES de la llamada)."""
    try: return next((r.get('estado') for r in AR._leer() if r.get('id') == id_), None)
    except Exception: return 'desconocido'

def llamar_uno(a, X, x, tope, limite=None, dormir=time.sleep):
    """UN pedido de Argon con intentos ACOTADOS (orden 68, Ricardo).
    PISTA INMI (2026-10-29): antes era un solo intento y un JSON roto quedaba «ok». Ahora:
    - cada intento = id propio (…, -i2, -i3, -i4) con SU línea de ledger ANTES de llamar (myia_argon.llamar);
    - 429 → la línea queda no_cobrado (no gasta) y se espera Retry-After/retryDelay o 20-40-80 s (+azar); hasta MAX_INTENTOS;
    - otro error → error_posible_cobro (cuenta el peor caso) y 1 reintento como mucho, solo si `limite` (lo aprobado que queda) alcanza;
    - error antes de la llamada (fijo, precio, credencial, tope) o 400/403/404 → no se repite;
    - la respuesta se revisa: JSON válido → ok; JSON roto de estructura → arreglo local gratis (estado «reparado», la original
      queda intacta y la arreglada en respuestas/<p>.reparado.json); si no se puede → 1 reintento pago (-rjson) SOLO si el
      límite alcanza; cortada por MAX_TOKENS → 4a4 reintenta (-rmax) con la cubeta siguiente si cabe en el tope; si no, «json_roto»/«truncado»
      (NO cuenta como hecho: la próxima cotización lo vuelve a pedir).
    - ritmo entre llamadas a Argon, compartido entre procesos (TALLER_RITMO_ARGON_S, 5 s)."""
    if x.get('_dividir'): return llamar_dividido(a, X, x, tope, limite, dormir)   # orden t331u: esquema partido en N llamadas
    AR, P = X['AR'], X['P']; D = X['D']; p = x['paso']; pr = x['_pr']; fijo = x['_fijo']; est = x['peor_caso_usd']
    limite = (a.ok if a.ok is not None else est) if limite is None else limite
    esq_api =[REDACTED]
    if esq_api is not None:
        import inspect
        if 'esquema' not in inspect.signature(AR.llamar).parameters:
            return {'paso': p, 'estado': 'no_llamado', 'motivo': 'myia_argon.llamar no acepta esquema (falta la pieza A de la orden 68 en el staging): no se anotó ni se llamó'}
    _pc = PC.prechequeo(pr, esq_api, x.get('_max_out'))   # t358u: revisión GRATIS antes de pagar (tamaño de esquema/prompt)
    if _pc: return {'paso': p, 'estado': 'no_llamado', 'motivo': 'prechequeo gratis (t358u), no se anotó ni se llamó: ' + '; '.join(_pc), 'prechequeo': _pc}
    registrar_taller(fijo, X['FP'], X['F'])
    lock = D / 'resultados' / f'{p}.corriendo'
    try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, ahora().encode()); os.close(fd)
    except FileExistsError: return {'paso': p, 'estado': 'no_llamado', 'motivo': f'ya hay una corrida en curso ({lock.name})'}
    try:
        (D / 'pedidos' / f'{p}.txt').write_text(pr, encoding='utf-8')
        base_id = f"taller00-{x.get('prueba') or PASOS.get(p, p)}-{X['e']['id']}-{time.strftime('%Y%m%d-%H%M%S')}"
        if '__' in p: base_id += '-' + p.split('__', 1)[1]   # orden 68: un pedido por escenario → el id lleva el escenario (sin choques en el mismo segundo)
        ia = incompleto_antes(D, x['ids'][0]) if p.startswith('prompts_escenarios__') and len(x.get('ids') or []) == 1 else None   # orden 69
        info = {'paso': p, 'fijo_paso': fijo['paso'], 'ids': x.get('ids'), 'id': base_id, **({'antes_incompleto': {k: ia[k] for k in ('paso', 'faltan', 'repetidas', 'ajenas', 'texto')}} if ia else {}), 'prompt_chars': len(pr), 'estimado_peor_caso': est, 'tope_llamada': tope, 'aprobado': a.aprobado,
                'ok_usd': a.ok, 'limite_usd': round(limite, 4), 'corrida_n8n': a.corrida, 'inicio': ahora(), 'salida_estructurada': esq_api is not None, 'intentos': []}
        mo = x.get('_max_out') or AR.MAX_OUT; adj = x.get('_adj') or None
        if adj: info.update(imagenes=len(adj), entrada=x.get('entrada'))
        info['max_out'] = mo
        try: esq_local = json.loads(fijo['partes'].get('esquema') or 'null')
        except Exception: esq_local = None
        salida = D / 'respuestas' / f'{p}.json'
        caja = {'cobrado': 0.0, 'posible': 0.0}
        ritmo = LS.Ritmo(TRABAJO / '_ritmo', X['modelo'], LS.num_env('TALLER_RITMO_ARGON_S', 5), dormir=dormir)
        max_int = int(getattr(a, 'max_intentos', None) or MAX_INTENTOS)
        t0 = time.time()
        usar_cache = not getattr(a, 'repetir', False)   # t366u: --repetir = pagar de nuevo a propósito

        def pedir(etiqueta, pr_, fijo_, mo_, est_):
            hu_ = huella_pedido(pr_, fijo_, mo_, esq_api, adj, X['modelo'], X['nivel'])
            info.setdefault('huellas', []).append(hu_)
            def uno(n):
                id_ = base_id + etiqueta + ('' if n == 1 else f'-i{n}')
                # t366u (Ricardo): NO PAGAR DOS VECES. 1) este mismo pedido ya se pagó y su respuesta es válida → se usa (US$0, no se llama).
                c_ = cache_leer(D, hu_, esq_local) if usar_cache else None
                if c_:
                    salida.write_text(c_['texto'], encoding='utf-8')
                    info['desde_cache'] = {'huella': hu_, 'id_pagado': c_.get('id_pagado'), 'fecha': c_.get('fecha'), 'usd_pagado_antes': c_.get('usd_pagado')}
                    return c_.get('id_pagado') or id_, {'texto': c_['texto'], 'usd': 0.0, 'tokens_entrada': c_.get('tokens_entrada') or 0, 'tokens_salida': c_.get('tokens_salida') or 0, 'fin': c_.get('fin')}
                # 2) es un REINTENTO (n>1): si el intento anterior sí dejó una respuesta válida en disco después de empezar, no se vuelve a pedir.
                if n > 1 and salida.exists() and salida.stat().st_mtime >= t0:
                    try: tx_ = salida.read_text(encoding='utf-8')
                    except Exception: tx_ = ''
                    if tx_ and LS.revisar_respuesta(tx_, esq_local, None)['estado'] == 'ok':
                        info['reintento_evitado'] = {'intento': n, 'motivo': 'el intento anterior ya dejó una respuesta válida en disco'}
                        return id_, {'texto': tx_, 'usd': 0.0, 'tokens_entrada': 0, 'tokens_salida': 0, 'fin': 'reutilizada'}
                if caja['cobrado'] + caja['posible'] + est_ > limite + 1e-9:
                    raise LS.SinPresupuesto(f'otro intento ({est_}) pasaría lo aprobado: gastado {round(caja["cobrado"] + caja["posible"], 4)} de {round(limite, 4)}')
                os.environ['MYIA_ARGON_PRESUPUESTO_USD'] = str(round(AR.total() + est_, 4))
                info['id'] = id_
                try:
                    r = AR.llamar(id_, pr_, str(salida), est_, f'taller n8n paso00 cadena {p} intento {n}{etiqueta} (aprobado: {a.aprobado})', transporte=X.get('transporte') or LS.transporte_texto(AR, PC.timeout_paso(p, len(pr_), mo_)),
                                  modelo=X['modelo'], nivel=X['nivel'], max_out=mo_, adjuntos=adj, fijo=fijo_, cotizacion=AR.cotizacion(est_, modelo=X['modelo']),
                                  ok_usd=est_, tope_usd=tope, **({'esquema': esq_api} if esq_api is not None else {}))
                except Exception as exc:
                    el = _estado_ledger(AR, id_)
                    if el is None: raise LS.NoLlamado(f'{type(exc).__name__}: {str(exc)[:300]}') from exc   # falló antes del ledger: no se llamó
                    if LS.es_timeout(exc): AR.marcar(id_, 'timeout', est_, ''); el = 'timeout'   # orden 81: peor caso + reintento
                    if el != 'no_cobrado': caja['posible'] += est_
                    raise
                caja['cobrado'] += float(r.get('usd') or 0)
                if usar_cache:
                    try: cache_guardar(D, hu_, p, id_, r.get('texto') or salida.read_text(encoding='utf-8'), r); info['_huella_pagada'] = hu_   # vale solo si al final queda ok/reparado
                    except Exception: pass
                return id_, r
            try:
                (id_, r), ints = LS.intentar(uno, max_intentos=max_int, max_transitorios=1, dormir=dormir, ritmo=ritmo, ahora=ahora,
                                             espera_base=LS.num_env('TALLER_ESPERA_429_S', 20), espera_max=LS.num_env('TALLER_ESPERA_MAX_S', 120),
                                             puede_otro=lambda n, c: caja['cobrado'] + caja['posible'] + est_ <= limite + 1e-9)
            except LS.IntentosAgotados as e:
                for k_, z in enumerate(e.intentos, 1): z['id'] = base_id + etiqueta + ('' if z['n'] == 1 else f"-i{z['n']}")
                info['intentos'] += e.intentos
                raise
            for z in ints: z['id'] = base_id + etiqueta + ('' if z['n'] == 1 else f"-i{z['n']}")
            info['intentos'] += ints
            return id_, r

        try:
            id_, r = pedir('', pr, fijo, mo, est)
            rv = LS.revisar_respuesta(r.get('texto') or salida.read_text(encoding='utf-8'), esq_local, r.get('fin'))
            otra = None
            if rv['estado'] == 'json_roto': otra = ('-rjson', pr, fijo, mo, est)
            elif rv['estado'] == 'truncado' and x.get('_rearmar') and mo < tuple(x['_rearmar'].get('cubetas') or CUBETAS_4A4)[-1]:   # orden 72: también 4a1/4b1/4c1
                rz = x['_rearmar']; mo2 = next(m for m in tuple(rz.get('cubetas') or CUBETAS_4A4) if m > mo)
                est2 = round(AR.estimar(len(rz['pr']), max_out=mo2, modelo=X['modelo']) + rz['n_adj'] * TOKENS_IMG_PEOR * AR.precio(X['modelo'])[0] / 1e6, 4)
                if est2 <= tope + 1e-9:
                    f2 = fijo_inv(rz.get('p') or 'prompts_escenarios', rz['texto'], rz['r'], rz['esq'], X, mo2); registrar_taller(f2, X['FP'], X['F'])
                    otra = ('-rmax', pr, f2, mo2, est2)
                else: info['sin_reintento'] = f'cortado por MAX_TOKENS y la cubeta siguiente ({mo2}) costaría {est2} > tope {tope}'
            if otra and caja['cobrado'] + caja['posible'] + otra[4] <= limite + 1e-9:   # UN reintento pago por respuesta mala, solo si alcanza lo aprobado
                (D / 'archivo').mkdir(exist_ok=True); roto = D / 'archivo' / f'{p}.{id_}.mala.json'; shutil.copy2(salida, roto)
                info['respuesta_mala'] = {'id': id_, 'estado': rv['estado'], 'archivo': str(roto), 'error_json': rv.get('error_json'), 'fin': str(r.get('fin'))}
                id_, r = pedir(otra[0], otra[1], otra[2], otra[3], otra[4])
                info.update(fijo_paso=otra[2]['paso'], max_out=otra[3])
                mo = otra[3]
                rv = LS.revisar_respuesta(r.get('texto') or salida.read_text(encoding='utf-8'), esq_local, r.get('fin'))
            elif otra:
                info['sin_reintento'] = f"respuesta {rv['estado']} y otro intento ({otra[4]}) pasaría lo aprobado ({round(limite, 4)}; gastado {round(caja['cobrado'] + caja['posible'], 4)})"
            info.update(tokens_entrada=r['tokens_entrada'], tokens_salida=r['tokens_salida'], fin=str(r['fin']), pct_salida=round(100 * (r['tokens_salida'] or 0) / mo, 1),
                        json_valido=rv['json_valido'], esquema_errores=rv.get('esquema_errores') or [])
            if rv['estado'] == 'ok': info['estado'] = 'ok'
            elif rv['estado'] == 'reparable':
                (D / 'respuestas' / f'{p}.reparado.json').write_text(rv['texto_reparado'], encoding='utf-8')
                info.update(estado='reparado', reparacion={'arreglos': [{k: v for k, v in e.items() if k != 'contexto'} for e in rv['ediciones']], 'error_json': rv.get('error_json'),
                                                         'archivo': str(D / 'respuestas' / f'{p}.reparado.json'), 'original_intacta': str(salida)})
            else: info.update(estado=rv['estado'], error_json=rv.get('error_json'), motivo=rv.get('motivo'))
            if info['estado'] in ('ok', 'reparado') and p.startswith('prompts_escenarios'):   # PISTA INMI (2026-10-29): orden 69 — revisión GRATIS de cámaras
                rc = revision_camaras(D, rv.get('obj'))
                info['camaras_revisadas'] = {k: {'esperadas': v['imagenes_esperadas'], 'completo': v['completo']} for k, v in rc.items()}
                malos = [v for v in rc.values() if not v['completo']]
                if malos: info.update(estado='incompleto', **_incompleto_info(malos))   # no cuenta como hecho: la próxima cotización lo vuelve a pedir
            if info['estado'] in ('ok', 'reparado') and inv_de(p):   # PISTA INMI (2026-10-29): orden 72 — revisión GRATIS: un registro por id pedido
                ri = revisar_ids_resp(inv_de(p), rv.get('obj'), x.get('ids') or [])
                info['revision_ids'] = {k: ri[k] for k in ('buenos', 'faltan', 'ajenos', 'repetidos', 'sin_campos', 'recibidos')}
                if not ri['completo']:   # lo bueno que trae sirve (cuenta por id); lo que falta se vuelve a pedir (--solo-fallidos)
                    info.update(estado='incompleto', ids_buenos=ri['buenos'], ids_faltan=[i for i in (x.get('ids') or []) if i not in ri['buenos']],
                                motivo_incompleto=LS.texto_ids(ri, p))
            if info['estado'] in ('ok', 'reparado') and (p == 'personajes' or p.startswith('prompts_escenarios')):   # t440 (Ricardo): 2C/4a4 entregan lo que 4a1b necesita. GRATIS
                try:
                    sys.path.insert(0, str(CAJAS)); import entregas_origen as EO
                    info['entrega_origen'] = EO.tras_paso(D, p)
                except Exception as exc_eo:
                    info['entrega_origen'] = {'ok': False, 'error': f'{type(exc_eo).__name__}: {str(exc_eo)[:300]}'}
        except LS.IntentosAgotados as exc:
            info.update(estado='error', error=str(exc)[:500])
        except Exception as exc:
            info.update(estado='error', error=f'{type(exc).__name__}: {str(exc)[:500]}')
        info.update(usd_real=round(caja['cobrado'], 4), usd_posible_cobro=round(caja['posible'], 4),
                    reintentos_429=sum(1 for z in info['intentos'] if z.get('clase') == '429'))
        info['segundos'] = round(time.time() - t0, 1); info['fin_hora'] = ahora()
        hp_ = info.pop('_huella_pagada', None)
        if hp_ and info.get('estado') in ('ok', 'reparado'): info['cache_guardado'] = cache_validar(D, hp_)   # t366u: la próxima vez este mismo pedido no se paga
        try:   # t366u (Ricardo): aviso en BITACORA_OPTIMIZACION.md si la caja se acerca a su tope de tiempo o de dinero
            tmo = PC.timeout_paso(p, len(pr), mo) or LS.tope_s('texto'); info['timeout_s'] = tmo
            pt_, pd_ = PC.avisos_umbral(); g_ = caja['cobrado'] + caja['posible']; av = []
            if info.get('estado') == 'error' and 'imeout' in str(info.get('error') or '') + str(info.get('intentos') or ''): av.append(f'se cortó por tiempo (tope {int(tmo)} s)')
            elif info['segundos'] >= pt_ * tmo: av.append(f"tardó {info['segundos']} s = {round(100 * info['segundos'] / tmo)} % del tope de {int(tmo)} s")
            if limite and g_ >= pd_ * limite: av.append(f'gastó/arriesgó US$ {round(g_, 4)} = {round(100 * g_ / limite)} % de lo aprobado (US$ {round(limite, 4)})')
            if av: info['aviso_bitacora'] = PC.aviso_bitacora(f"caja {p} ({X['e']['id']}, {info.get('estado')}): " + '; '.join(av) + f". Pedido {len(pr)} chars, max_out {mo}.")
        except Exception: pass
        (D / 'resultados' / f'{p}.json').write_text(json.dumps(info, ensure_ascii=False, indent=1))
        return info
    finally:
        lock.unlink(missing_ok=True)

def huella_pedido(pr_, fijo_, mo_, esq_api, adj, modelo, nivel):
    """t366u (Ricardo: «no pagar dos veces»): huella del pedido EXACTO (texto, fijo, esquema, max_out, imágenes, modelo). Misma huella = mismo pedido."""
    def _a(z):
        try: return [Path(str(z)).name, Path(str(z)).stat().st_size]
        except Exception: return [str(z)[:200], None]
    h = hashlib.sha256(json.dumps([pr_, (fijo_ or {}).get('paso'), esq_api, mo_, [_a(z) for z in (adj or [])], modelo, nivel], ensure_ascii=False, sort_keys=True, default=str).encode('utf-8'))
    return h.hexdigest()[:32]

def cache_leer(D, huella, esq_local):
    """Respuesta YA PAGADA y VÁLIDA de este mismo pedido (respuestas/_cache/<huella>.json), o None. Se revisa otra vez antes de usarla."""
    f = D / 'respuestas' / '_cache' / f'{huella}.json'
    try: c = json.loads(f.read_text(encoding='utf-8'))
    except Exception: return None
    if c.get('huella') != huella or not c.get('texto') or not c.get('valida'): return None   # solo respuestas que quedaron «ok»/«reparado» (no incompletas)
    rv = LS.revisar_respuesta(c['texto'], esq_local, c.get('fin'))
    return c if rv['estado'] in ('ok', 'reparable') else None

def cache_validar(D, huella):
    """La respuesta de esta huella terminó ok/reparado (pasó la revisión de cámaras/ids) → se puede reutilizar sin pagar."""
    f = D / 'respuestas' / '_cache' / f'{huella}.json'
    try: c = json.loads(f.read_text(encoding='utf-8')); c['valida'] = True; f.write_text(json.dumps(c, ensure_ascii=False), encoding='utf-8'); return True
    except Exception: return False

def cache_guardar(D, huella, p, id_, texto, r):
    try:
        d = D / 'respuestas' / '_cache'; d.mkdir(parents=True, exist_ok=True)
        (d / f'{huella}.json').write_text(json.dumps({'huella': huella, 'paso': p, 'id_pagado': id_, 'fecha': ahora(), 'usd_pagado': r.get('usd'), 'tokens_entrada': r.get('tokens_entrada'),
                                                    'tokens_salida': r.get('tokens_salida'), 'fin': str(r.get('fin')), 'valida': False, 'texto': texto}, ensure_ascii=False), encoding='utf-8')
    except Exception: pass

BUENOS = ('ok', 'reparado', 'ya_hecho')   # orden 68: estados que cuentan como hechos

# ---- COMPUERTA 00 (inmi 2-nov-2026, orden Ricardo t523u). GENÉRICA, cualquier canal. Los pasos Argon del paso 00 (4 base, 4p profundiza,
# 5 personajes, 4a1/4b1/4c1 investigar) SOLO pagan si existe HABILITAR_PAGO_00 junto al script, con líneas «monto=<USD>», «desde=<ISO con zona>»,
# «pasos=4,4p,...» y, si se quiere amarrar, «canal=<id>» y «capitulo=<n>». El tope es TOTAL: lo gastado en el ledger (ids taller00-, desde
# «desde») + el --ok de esta llamada no puede pasar el monto. 4a4 sigue con su propia compuerta (HABILITAR_PAGO_4A4). Se borra al terminar.
GATE_00 = CAJAS / 'HABILITAR_PAGO_00'
PASO_DE_CAJA = {'base': '4', 'profundiza': '4p', 'escenarios': '4p', 'objetos': '4p', 'personajes': '5',
                'investigar_escenarios': '4a1', 'investigar_objetos_historia': '4b1', 'investigar_objetos_lugar': '4c1', 'resolver_dudas': '4r'}   # t348u: caja 4r resolver dudas
def gastado_00(desde):
    import csv, datetime as _dt
    tot = 0.0
    if not LEDGER.is_file(): return 0.0
    with open(LEDGER, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            if not str(r.get('id', '')).startswith('taller00-') or r.get('estado') == 'no_cobrado': continue
            try: fe = _dt.datetime.fromisoformat(r['fecha'])
            except Exception: continue
            if fe.tzinfo is None or fe < desde: continue
            try: tot += float(r.get('costo_estimado_usd') or 0)
            except ValueError: pass
    return round(tot, 4)
def compuerta_00(a):
    """None si se puede pagar; si no, el motivo (y no se llama a nada)."""
    import datetime as _dt
    paso = PASO_DE_CAJA.get(a.caja)
    if not paso: return f'caja {a.caja}: sin compuerta conocida; no se paga'
    if not GATE_00.is_file(): return f'paso {paso} ({a.caja}) cerrado: falta {GATE_00} (permiso de pago de Ricardo). No se llamó a nada.'
    t = GATE_00.read_text(errors='replace')
    kv = dict(re.findall(r'^\s*([a-z_]+)\s*=\s*(\S+)\s*$', t, re.M))
    try: monto = float(kv['monto']); desde = _dt.datetime.fromisoformat(kv['desde'])
    except Exception: return f'{GATE_00.name} sin monto=<USD> o sin desde=<ISO>: no se paga'
    if desde.tzinfo is None: return f'{GATE_00.name}: desde sin zona horaria: no se paga'
    pasos = [x.strip().lower() for x in kv.get('pasos', '').split(',') if x.strip()]
    if paso not in pasos: return f'paso {paso} ({a.caja}) no está en pasos= de {GATE_00.name} ({pasos}): no se paga'
    if kv.get('canal') and kv['canal'] != a.canal: return f'{GATE_00.name} es para el canal {kv["canal"]}, no {a.canal}: no se paga'
    if kv.get('capitulo') and str(kv['capitulo']) != str(a.capitulo): return f'{GATE_00.name} es para el capítulo {kv["capitulo"]}, no {a.capitulo}: no se paga'
    g = gastado_00(desde)
    if g + float(a.ok or 0) > monto + 1e-9:
        return f'tope total {monto} de {GATE_00.name}: ya gastado {g} + este peor caso {a.ok} lo pasa. No se llamó a nada.'
    if PC.activo() and not os.environ.get('TALLER_HIJO'):   # t358u: 4b1 y 4c1 a la vez → reserva entre procesos contra el mismo monto (sin carrera)
        return PC.reservar_compuerta(TRABAJO / '_reservas_pago_00.json', monto, g, float(a.ok or 0), f'{a.caja} {a.canal} cap{a.capitulo}')
    return None

def par_inv(a, X, pasos, tope, n):
    """t358u (Ricardo): pedidos de 4a1/4b1/4c1/4a4 A LA VEZ (máx n; PC.ranura limita también entre procesos, p. ej. 4b1+4c1 juntos).
    Tope ATÓMICO: antes de lanzar se reserva en una Bolsa(a.ok) el peor caso de TODOS los pendientes; cada pedido puede tomar además,
    solo de lo que sobra, un extra para un reintento; al terminar asienta lo real (+ posible cobro). Nunca se compromete más que --ok.
    Ledger: cada intento lo anota myia_argon.llamar ANTES de llamar (con candado). 4a1 dividido: cada escenario corre A y luego B
    (B necesita A); los escenarios van a la vez. Si un pedido falla no se lanzan los que faltan (como antes)."""
    pend = [x for x in pasos if not x['ya_hecho']]
    bolsa = PC.Bolsa(a.ok)
    if not bolsa.reservar(sum(x['peor_caso_usd'] for x in pend)):
        return [{'paso': x['paso'], 'estado': 'no_llamado', 'motivo': f'peor caso total pasa lo aprobado {a.ok}'} for x in pend]
    for x in pend:   # registro de fijos ANTES (en fila): los hilos solo lo leen
        registrar_taller(x['_fijo'], X['FP'], X['F'])
        for pt in ((x.get('_dividir') or {}).get('partes') or []): registrar_taller(pt['fijo'], X['FP'], X['F'])
    def fn(x):
        est = x['peor_caso_usd']; extra = bolsa.extra(est); t0 = time.time()
        try:
            if getattr(a, 'repetir', False): x['respaldo_previo'] = respaldar_previo(X['D'], x['paso'])
            with PC.ranura('argon', TRABAJO / '_ranuras') as rn:
                info = llamar_uno(a, X, x, tope, limite=round(est + extra, 6))
        except Exception as exc:
            rn, info = None, {'paso': x['paso'], 'estado': 'error', 'error': f'{type(exc).__name__}: {str(exc)[:300]}'}
        bolsa.asentar(est + extra, float(info.get('usd_real') or 0) + float(info.get('usd_posible_cobro') or 0))
        info['paralelo'] = {'reservado_usd': round(est + extra, 4), 'ranura': rn, 'segundos_total': round(time.time() - t0, 1)}
        return info
    rr = PC.correr_paralelo(pend, fn, n, parar_si=lambda r: r.get('estado') not in BUENOS)
    por = {t['paso']: r for t, r, _, _ in rr}; res = []
    for x in pasos:
        if x['ya_hecho']: res.append({'paso': x['paso'], 'estado': 'ya_hecho', 'usd_real': x['usd_real_anterior']}); continue
        r = por.get(x['paso']) or {'paso': x['paso'], 'estado': 'no_llamado'}; res.append(r)
        if r.get('estado') in BUENOS: x['ya_hecho'] = True
    tl = [{'paso': t['paso'], 'inicio': i, 'fin': f_} for t, _, i, f_ in rr]
    (X['D'] / 'resultados' / f"{a.caja}_paralelo.json").write_text(json.dumps({'a_la_vez': n, 'ok_usd': a.ok, 'gastado_usd': round(bolsa.gastado, 4),
        'max_comprometido_usd': round(bolsa.max_comprometido, 4), 'linea_de_tiempo': tl, 'hora': ahora()}, ensure_ascii=False, indent=1))
    return res

def cmd_juntos(argv):
    """t358u: «juntos caja:ok,caja:ok … --canal --capitulo --aprobado [--corrida]» — corre varias cajas pagadas INDEPENDIENTES
    (p. ej. 4b1 y 4c1) AL MISMO TIEMPO, cada una en su propio proceso con su propio --ok (cada proceso pasa su compuerta y reserva
    su monto contra HABILITAR_PAGO_00 sin carrera). Una caja con ok 0 se salta. Nunca suma más llamadas a la vez que «paralelo.argon»."""
    ap = argparse.ArgumentParser(prog='paso00_cadena.py juntos')
    ap.add_argument('lista'); ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', default='1')
    ap.add_argument('--aprobado', required=True); ap.add_argument('--corrida', default=None)
    a = ap.parse_args(argv)
    PERMITIDAS = set((PC.cfg().get('juntos') or {}).get('cajas_permitidas') or [])
    tareas = []
    for z in a.lista.split(','):
        caja, _, ok = z.partition(':')
        if caja not in CAJA or (PERMITIDAS and caja not in PERMITIDAS): return {'ok': False, 'error': f'caja no permitida en juntos: {caja}', 'llamadas_hechas': 0}
        try: ok = float(ok or 0)
        except ValueError: return {'ok': False, 'error': f'ok no válido para {caja}', 'llamadas_hechas': 0}
        tareas.append((caja, ok))
    hijos, t0 = [], time.time()
    for caja, ok in tareas:
        if ok <= 0: continue
        cmd = [sys.executable, __file__, 'correr', caja, '--canal', a.canal, '--capitulo', str(a.capitulo), '--ok', str(ok), '--aprobado', a.aprobado] + (['--corrida', a.corrida] if a.corrida else [])
        hijos.append((caja, ok, time.time(), subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)))
    res = []
    for caja, ok, ti, h in hijos:
        o, e = h.communicate(); lin = o.decode(errors='replace').strip().splitlines()
        try: r = json.loads(lin[-1])
        except Exception: r = {'ok': False, 'error': 'sin salida JSON', 'stderr': e.decode(errors='replace')[-400:]}
        res.append({'caja': caja, 'ok_usd': ok, 'segundos': round(time.time() - ti, 1), **{k: r.get(k) for k in ('ok', 'error', 'usd_real_total', 'usd_posible_cobro_total')}, 'detalle': r})
    return {'ok': all(r.get('ok') for r in res), 'accion': 'juntos', 'cajas': res, 'saltadas': [c for c, ok in tareas if ok <= 0],
            'usd_real_total': round(sum(float(r.get('usd_real_total') or 0) for r in res), 4), 'segundos': round(time.time() - t0, 1), 'hora': ahora()}

def cmd_correr(a):
    if a.ok is None or not a.aprobado: salir({'ok': False, 'error': 'falta --ok (precio aprobado) y --aprobado (quién aprobó)'})
    if getattr(a, 'como_nuevo', False): salir({'ok': False, 'error': '--como-nuevo es solo para cotizar (peor caso desde cero); correr no lo acepta'})   # orden 72
    if str(a.caja).startswith('prompts_escenarios') and not (Path(__file__).resolve().parent / 'HABILITAR_PAGO_4A4').is_file():
        salir({'ok': False, 'error': '4a4 está en SOLO COTIZAR (orden 59): no se llama a Argon. Para habilitar el pago hace falta el archivo HABILITAR_PAGO_4A4 junto al script, con orden de Ricardo.'})
    if str(a.caja).startswith('prompts_escenarios'):   # orden 63b: si el archivo trae un monto, --ok no puede pasarlo
        import re as _re
        _m = _re.search(r'\d+(?:\.\d+)?', (Path(__file__).resolve().parent / 'HABILITAR_PAGO_4A4').read_text(errors='replace'))
        if _m and a.ok > float(_m.group()) + 1e-9: salir({'ok': False, 'error': f'--ok {a.ok} pasa el monto habilitado en HABILITAR_PAGO_4A4 ({_m.group()})'})
    if not str(a.caja).startswith('prompts_escenarios'):   # compuerta 00 (inmi 2-nov-2026, orden Ricardo t523u): sin archivo, nada de Argon
        _g = compuerta_00(a)
        if _g: salir({'ok': False, 'error': _g, 'llamadas_hechas': 0})
    if a.caja == 'investigar_escenarios':   # orden 62: con dudosas sin confirmar no se paga nada (podría pagarse un lugar ya guardado)
        _ds = sorted((TRABAJO / a.canal).glob(f'cap{int(a.capitulo):02d}_*')) if str(a.capitulo).isdigit() else []
        _pb = plan_biblioteca(_ds[0]) if _ds else None
        if _pb and _pb.get('pendiente_usuario'):
            salir({'ok': False, 'error': f"hay escenarios dudosos sin confirmar en la biblioteca (4a0): {[z.get('id') for z in _pb['pendiente_usuario']]}. Confírmalos antes de pagar."})
    X = preparar(a, pagar=True)
    PC.blindar_ledger(X['AR'], LEDGER)   # t358u: ledger con candado (varias llamadas a la vez)
    try:
        if len(CAJA[a.caja]) > 1 and not os.environ.get('TALLER_HIJO'):
            # profundiza: un proceso por pedido, al mismo tiempo (como en la prueba). Se revisa precio y tope antes de lanzar.
            pasos, total, tope, tc = cotizacion(a, X, aprox_ok=False)
            if total > a.ok + 1e-9: salir({'ok': False, 'error': f'el precio subió: peor caso {total} > aprobado {a.ok}. Vuelve a cotizar.', 'pasos': publico(pasos)})
            malos = [x['paso'] for x in pasos if not x['ya_hecho'] and not x['cabe_en_tope']]
            if malos: salir({'ok': False, 'error': f'no cabe en el tope por llamada {tope}: {malos}', 'pasos': publico(pasos)})
            env = dict(os.environ, TALLER_DATOS=str(X['T']), TALLER_HIJO='1')
            hijos = []
            for i, x in enumerate(pasos):
                if x['ya_hecho']: continue
                if i: time.sleep(5)
                cmd = [sys.executable, __file__, 'correr', x['paso'], '--canal', a.canal, '--capitulo', str(a.capitulo), '--ok', str(x['peor_caso_usd']),
                       '--aprobado', a.aprobado] + (['--corrida', a.corrida] if a.corrida else []) + (['--repetir'] if getattr(a, 'repetir', False) else [])
                hijos.append((x['paso'], subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=open(X['D'] / 'resultados' / f"{x['paso']}.log", 'a'))))
            res = []
            for p, h in hijos:
                o = h.communicate()[0].decode(errors='replace').strip().splitlines()
                try: res.append(json.loads(o[-1]))
                except Exception: res.append({'paso': p, 'estado': 'error', 'error': 'sin salida JSON (ver resultados/*.log)'})
            hechos = [{'paso': x['paso'], 'estado': 'ya_hecho', 'usd_real': x['usd_real_anterior']} for x in pasos if x['ya_hecho']]
            todos = [(r['resultados'][0] if r.get('resultados') else r) for r in res] + hechos
            return {'ok': all(r.get('estado') in BUENOS for r in todos), 'accion': 'correr', 'caja': a.caja, 'resultados': todos,   # orden 68: «reparado» también sirve
                    'usd_real_total': round(sum(r.get('usd_real') or 0 for r in todos if r.get('estado') != 'ya_hecho'), 4), 'carpeta': str(X['D']), 'hora': ahora()}
        pasos, total, tope, tc = cotizacion(a, X, aprox_ok=False)
        if CAJA[a.caja][0] in INV:
            # 4a1/4b1/4c1: un llamado por grupo, uno tras otro; un intento cada uno; si uno falla, no se sigue con los demás
            if total > a.ok + 1e-9: return {'ok': False, 'error': f'el precio subió: peor caso {total} > aprobado {a.ok}. Vuelve a cotizar.', 'pasos': publico(pasos)}
            malos = [x['paso'] for x in pasos if not x['ya_hecho'] and not x['cabe_en_tope']]
            if malos: return {'ok': False, 'error': f'no cabe en el tope por llamada {tope}: {malos}', 'pasos': publico(pasos)}
            n_par = PC.max_a_la_vez('argon') if PC.activo() else 1   # t358u: varios pedidos a la vez (llamadas_config.json «paralelo»)
            n_par = n_par if sum(1 for z in pasos if not z['ya_hecho']) > 1 else 1
            res, gastado = (par_inv(a, X, pasos, tope, n_par) if n_par > 1 else []), 0.0
            for k_, x in enumerate(pasos if n_par <= 1 else []):
                if x['ya_hecho']: res.append({'paso': x['paso'], 'estado': 'ya_hecho', 'usd_real': x['usd_real_anterior']}); continue
                # PISTA INMI (2026-10-29): orden 68 — límite de ESTE pedido = lo aprobado − lo ya gastado − el peor caso de los que faltan
                resto = sum(z['peor_caso_usd'] for z in pasos[k_ + 1:] if not z['ya_hecho'])
                if getattr(a, 'repetir', False): x['respaldo_previo'] = respaldar_previo(X['D'], x['paso'])   # t337u: respaldo antes de pagar
                info = llamar_uno(a, X, x, tope, limite=a.ok - gastado - resto); res.append(info)
                gastado += float(info.get('usd_real') or 0) + float(info.get('usd_posible_cobro') or 0)
                if info.get('estado') not in BUENOS: break
                x['ya_hecho'] = True
            u = (unir_inv(X, CAJA[a.caja][0], pasos) if not (getattr(a, 'solo', None) or getattr(a, 'solo_fallidos', False))
                 else {'nota': 'prueba --solo / --solo-fallidos: no se une aquí; la próxima cotización (gratis) junta todo si ya está completo'})   # orden 72
            ok = all(r.get('estado') in BUENOS for r in res) and len(res) == len(pasos)
            return {'ok': ok, 'accion': 'correr', 'caja': a.caja, 'resultados': res, 'union': u,
                    'usd_real_total': round(sum(r.get('usd_real') or 0 for r in res if r.get('estado') != 'ya_hecho'), 4),
                    'usd_posible_cobro_total': round(sum(r.get('usd_posible_cobro') or 0 for r in res), 4), 'carpeta': str(X['D']), 'hora': ahora()}
        x = pasos[0]
        if x['ya_hecho']:
            return {'ok': True, 'accion': 'correr', 'caja': a.caja, 'resultados': [{'paso': x['paso'], 'estado': 'ya_hecho', 'usd_real': x['usd_real_anterior']}],
                    'nota': 'ya había resultado bueno; no se volvió a pagar', 'carpeta': str(X['D'])}
        if x['peor_caso_usd'] > a.ok + 1e-9: return {'ok': False, 'error': f"el precio subió: {x['peor_caso_usd']} > aprobado {a.ok}. Vuelve a cotizar.", 'pasos': publico(pasos)}
        if not x['cabe_en_tope']: return {'ok': False, 'error': f"peor caso {x['peor_caso_usd']} pasa el tope por llamada {tope}", 'pasos': publico(pasos)}
        if getattr(a, 'repetir', False): x['respaldo_previo'] = respaldar_previo(X['D'], x['paso'])   # t531u: se respalda lo viejo antes de pagar
        info = llamar_uno(a, X, x, tope, limite=a.ok)
        return {'ok': info.get('estado') in BUENOS, 'accion': 'correr', 'caja': a.caja, 'resultados': [info], 'usd_real_total': info.get('usd_real', 0),
                'carpeta': str(X['D']), 'hora': ahora()}
    finally:
        if not os.environ.get('TALLER_DATOS'): shutil.rmtree(X['T'], ignore_errors=True)

def cmd_revisar(argv):
    """PISTA INMI (2026-10-29): orden 69 — revisar prompts_escenarios [--dry-run]. GRATIS: sin red, sin app, sin ledger.
    Revisa con el CÓDIGO las respuestas 4a4 que ya están (una imagen por cámara del molde) y deja escrito lo que falta:
    - pedido de UN escenario (prompts_escenarios__<id>) con cámaras de menos o repetidas → resultados estado «incompleto»
      + camaras_faltantes (las calcula el código; copia del resultado anterior en archivo/);
    - pedido viejo con varios escenarios → sigue «ok» para los que están completos y anota escenarios_incompletos.
    No toca ninguna respuesta. La cotización ya lo tiene en cuenta aunque no se corra esto (revisa cada vez)."""
    ap = argparse.ArgumentParser(prog='paso00_cadena.py revisar')
    ap.add_argument('caja', nargs='?', default='prompts_escenarios', choices=['prompts_escenarios'])
    ap.add_argument('--canal', default='cn-gnesis-digital-el-de-ed178619'); ap.add_argument('--capitulo', default='1')
    ap.add_argument('--dry-run', dest='dry_run', action='store_true')
    a = ap.parse_args(argv)
    base = TRABAJO / a.canal
    ds = sorted(base.glob(f'cap{int(a.capitulo):02d}_*')) if str(a.capitulo).isdigit() else sorted(base.glob(f'cap*_{a.capitulo}'))
    if not ds: return {'ok': False, 'error': f'no hay carpeta del capítulo {a.capitulo}'}
    D = ds[0]; p = 'prompts_escenarios'; filas, cambiados = [], []
    for f in sorted((D / 'resultados').glob(f'{p}*.json')):
        if not (f.stem == p or f.stem.startswith(f'{p}__') or re.fullmatch(re.escape(p) + r'_g\d+de\d+(_solo(_[0-9a-f]+)?)?', f.stem)): continue
        r = _resp_util(D, f.stem)
        if not r: filas.append({'paso': f.stem, 'revisado': False, 'motivo': 'sin respuesta JSON que sirva (no cuenta como hecho)'}); continue
        rc = revision_camaras(D, _obj_resp(D, f.stem))
        malos = [v for v in rc.values() if not v['completo']]
        fila = {'paso': f.stem, 'estado_antes': r.get('estado'), 'escenarios': {k: ('completo' if v['completo'] else 'INCOMPLETO') + f" ({v['imagenes_esperadas']} cámaras, base + {v['vistas_recibidas']} vistas)" for k, v in rc.items()},
                'incompletos': [dict(escenario_id=v['escenario_id'], faltan=v['faltan'], repetidas=v['repetidas'], ajenas=v['ajenas'], texto=LS.texto_camaras(v)) for v in malos]}
        nuevo_r = None
        if malos and len(rc) == 1 and f.stem.startswith(f'{p}__') and r.get('estado') != 'incompleto':
            nuevo_r = dict(r, estado='incompleto', estado_antes_de_revisar=r.get('estado'), revisado_o69=ahora(), **_incompleto_info(malos))
        elif malos and len(rc) > 1 and sorted(r.get('escenarios_incompletos') or []) != sorted(v['escenario_id'] for v in malos):
            nuevo_r = dict(r, revisado_o69=ahora(), **_incompleto_info(malos))
        fila['estado_despues'] = (nuevo_r or r).get('estado'); filas.append(fila)
        if nuevo_r and not a.dry_run:
            (D / 'archivo').mkdir(exist_ok=True); shutil.copy2(f, D / 'archivo' / f"resultados_{f.stem}_antes_revisar_{time.strftime('%Y%m%d-%H%M%S')}.json")
            f.write_text(json.dumps(nuevo_r, ensure_ascii=False, indent=1)); cambiados.append(f.stem)
        elif nuevo_r: cambiados.append(f.stem + ' (dry-run: no se escribió)')
    inc = sorted({z['escenario_id'] for x in filas for z in x.get('incompletos') or []})
    return {'ok': True, 'accion': 'revisar' + (' (dry-run)' if a.dry_run else ''), 'caja': p, 'carpeta': str(D), 'revisados': filas, 'escritos': cambiados,
            'escenarios_incompletos': inc, 'texto': [z['texto'] for x in filas for z in x.get('incompletos') or []], 'usd': 0.0, 'llamadas_hechas': 0, 'hora': ahora()}

def cmd_reparar(argv):
    """PISTA INMI (2026-10-29): orden 68 — reparar <paso> [--dry-run] [--aplicar --aprobado QUIEN]. GRATIS: sin red, sin app, sin ledger.
    - --dry-run: solo muestra qué arreglaría y qué recupera (no escribe nada).
    - sin opciones: escribe respuestas/<paso>.reparado.json AL LADO de la original (la original no se toca). NO cambia resultados:
      no cuenta como hecho, no se une y no se pinta.
    - --aplicar --aprobado QUIEN (con OK de Ricardo): marca resultados/<paso>.json como «reparado» (copia del anterior en archivo/),
      así la próxima cotización lo cuenta como hecho y lo une gratis."""
    ap = argparse.ArgumentParser(prog='paso00_cadena.py reparar')
    ap.add_argument('paso'); ap.add_argument('--canal', default='cn-gnesis-digital-el-de-ed178619'); ap.add_argument('--capitulo', default='1')
    ap.add_argument('--dry-run', dest='dry_run', action='store_true'); ap.add_argument('--aplicar', action='store_true'); ap.add_argument('--aprobado', default=None)
    ap.add_argument('--max-arreglos', dest='max_arreglos', type=int, default=3)
    a = ap.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', a.paso) or a.paso.endswith('.reparado'): return {'ok': False, 'error': f'paso no válido: {a.paso}'}
    if a.aplicar and not a.aprobado: return {'ok': False, 'error': '--aplicar necesita --aprobado QUIEN (OK de Ricardo)'}
    base = TRABAJO / a.canal
    ds = sorted(base.glob(f'cap{int(a.capitulo):02d}_*')) if str(a.capitulo).isdigit() else sorted(base.glob(f'cap*_{a.capitulo}'))
    if not ds: return {'ok': False, 'error': f'no hay carpeta del capítulo {a.capitulo}'}
    D = ds[0]; fo = D / 'respuestas' / f'{a.paso}.json'; fr = D / 'respuestas' / f'{a.paso}.reparado.json'; fres = D / 'resultados' / f'{a.paso}.json'
    if not fo.is_file(): return {'ok': False, 'error': f'no existe {fo}'}
    res = json.loads(fres.read_text()) if fres.is_file() else {}
    esq = None
    m = next((k for k in sorted(INV, key=len, reverse=True) if a.paso == k or a.paso.startswith(k + '_')), None) or (a.paso if a.paso in ESQ else None)
    if m:
        try: esq = json.loads((V / 'esquemas' / f'{ESQ[m]}_esquema.json').read_text(encoding='utf-8'))
        except Exception: esq = None
    texto = fo.read_text(encoding='utf-8')
    sha = hashlib.sha256(texto.encode('utf-8')).hexdigest()
    rv = LS.revisar_respuesta(texto, esq, res.get('fin'), a.max_arreglos)
    out = {'ok': rv['estado'] in ('ok', 'reparable'), 'accion': 'reparar' + (' (dry-run)' if a.dry_run else ''), 'paso': a.paso, 'original': str(fo), 'sha256_original': sha,
           'estado_revision': rv['estado'], 'error_json': rv.get('error_json'), 'resultados_estado_antes': res.get('estado'), 'json_valido_antes': res.get('json_valido'),
           'usd': 0.0, 'llamadas_hechas': 0}
    if rv['estado'] == 'ok':
        out['nota'] = 'la respuesta ya es JSON válido: no hay nada que reparar'; return out
    if rv['estado'] != 'reparable':
        out.update(motivo=rv.get('motivo'), nota='no se puede reparar localmente (no se inventa contenido): hay que volver a pedirla (cotizar la cuenta como pendiente)'); return out
    obj = rv['obj']; clave = 'escenarios' if isinstance(obj.get('escenarios'), list) else ('objetos' if isinstance(obj.get('objetos'), list) else None)
    recup = []
    for v in (obj.get(clave) or []) if clave else []:
        if not isinstance(v, dict): continue
        e_ = {'id': v.get('escenario_id') or v.get('objeto_id')}
        if 'base' in v or 'vistas' in v or 'variantes' in v:
            e_.update(base_cubre=(v.get('base') or {}).get('cubre_variante_id'), vistas=[z.get('vista_id') for z in v.get('vistas') or [] if isinstance(z, dict)],
                      variantes=[z.get('variante_id') for z in v.get('variantes') or [] if isinstance(z, dict)])
        recup.append(e_)
    out.update(arreglos=rv['ediciones'], recuperado=recup, ids_pedidos=res.get('ids'),
               ids_sin_respuesta=[i for i in (res.get('ids') or []) if i not in {z['id'] for z in recup}], esquema_errores=rv.get('esquema_errores') or [],
               archivo_reparado=str(fr), sha256_reparado=hashlib.sha256(rv['texto_reparado'].encode('utf-8')).hexdigest())
    if a.dry_run:
        out['nota'] = 'dry-run: no se escribió nada'; return out
    if fr.is_file() and fr.read_text(encoding='utf-8') != rv['texto_reparado']:
        return dict(out, ok=False, error=f'{fr.name} ya existe con otro contenido: no se pisa')
    if not fr.is_file(): fr.write_text(rv['texto_reparado'], encoding='utf-8')
    out['escrito'] = str(fr)
    if not a.aplicar:
        out['nota'] = ('escrito SOLO el archivo reparado al lado de la original. resultados NO cambia: no cuenta como hecho, no se une y no se pinta. '
                       f'Para usarlo (US$0, con OK de Ricardo): paso00_cadena.py reparar {a.paso} --aplicar --aprobado QUIEN')
        return out
    (D / 'archivo').mkdir(exist_ok=True)
    if fres.is_file(): shutil.copy2(fres, D / 'archivo' / f"resultados_{a.paso}_{time.strftime('%Y%m%d-%H%M%S')}.json")
    res2 = dict(res, estado='reparado', json_valido=False, reparacion={'arreglos': [{k: v for k, v in e.items() if k != 'contexto'} for e in rv['ediciones']],
                'archivo': str(fr), 'original_intacta': str(fo), 'sha256_original': sha, 'aprobado': a.aprobado, 'hora': ahora(), 'usd': 0.0})
    fres.write_text(json.dumps(res2, ensure_ascii=False, indent=1))
    out.update(aplicado=True, nota='marcado «reparado»: la próxima cotización lo cuenta como hecho y lo une gratis')
    return out

def cmd_estado(a):
    bloquear_red(False)
    # sin cargar la app: busca la carpeta del capítulo
    base = TRABAJO / a.canal
    ds = sorted(base.glob(f'cap{int(a.capitulo):02d}_*')) if str(a.capitulo).isdigit() else sorted(base.glob(f'cap*_{a.capitulo}'))
    if not ds: return {'ok': True, 'accion': 'estado', 'nada_todavia': True}
    D = ds[0]; out = {}
    for p in PASOS:
        f = D / 'resultados' / f'{p}.json'
        out[p] = json.loads(f.read_text()) if f.is_file() else None
    return {'ok': True, 'accion': 'estado', 'carpeta': str(D), 'pasos': out}

if __name__ == '__main__':
    # t880u: comando gratuito de recuperacion, sin IA ni compuertas.
    if len(sys.argv) > 1 and sys.argv[1] == 'revisar_guardar01':
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import revisar_guardar_01
                r = revisar_guardar_01.main(sys.argv[2:])
        except SystemExit as ex:
            r = {'ok': False, 'error': 'argumentos no validos para revisar_guardar01', 'llamadas_pagas': 0, 'usd_gastado': 0}
        except Exception as ex:
            r = {'ok': False, 'error': f'{type(ex).__name__}: {str(ex)[:500]}', 'llamadas_pagas': 0, 'usd_gastado': 0}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'ramas':   # ramas 4a/4b/4c: GRATIS, sin red, sin app (ver paso00_ramas.py)
        import io, contextlib
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import paso00_ramas
                r = paso00_ramas.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para ramas (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'biblioteca':   # orden 62: biblioteca del canal (4a0 reconocer/confirmar, 4a7 guardar). GRATIS, sin red, sin app
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import biblioteca
                r = biblioteca.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para biblioteca (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'pintar':   # orden 63: caja 4a5 Nano Banana. cotizar GRATIS sin red; correr cerrado sin cajas/HABILITAR_PAGO_4A5
        import io, contextlib
        if len(sys.argv) < 3 or sys.argv[2] != 'correr': bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import paso00_pintar
                r = paso00_pintar.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para pintar (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'guion':   # inmi 5-nov-2026: 3b Cargar mi guion (formulario n8n). GRATIS, sin red, sin IA
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import guion_cargar
                r = guion_cargar.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para guion (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'personajes':   # PISTA INMI (2026-10-29): orden 75 — Cargar personajes. GRATIS, sin red, sin app, sin ledger
        import io, contextlib
        bloquear_red(False)   # orden 76: hoja-leer / hoja-separar (pago, con guarda) abren SOLO *.googleapis.com dentro de personajes_hoja._app
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import personajes
                r = personajes.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para personajes (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'cubemap':   # 2-nov-2026 (Ricardo t401u): fondo cubemap universal «FC ·» (cajas/fondo_cubemap). cubo/cotizar/proyectar GRATIS sin red; pintar SOLO con cajas/HABILITAR_PAGO_FC
        import io, contextlib
        if len(sys.argv) < 3 or sys.argv[2] != 'pintar': bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); sys.path.insert(0, str(CAJAS / 'fondo_cubemap')); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import cubemap
                r = cubemap.n8n(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para cubemap (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'dirigir':   # t477-479u (Ricardo): 01 «Argon dirige la escena» desde n8n. Sin --correr = cotiza GRATIS sin red.
        # Con --correr paga SOLO si existe cajas/HABILITAR_PAGO_01 (monto) + --ok + --aprobado (paso01_pago: ledger antes de cada intento,
        # tope por llamada, abre solo *.googleapis.com). Mismo código que «ver cubo 01» (paso01_cubos.main).
        import io, contextlib
        if '--correr' not in sys.argv[2:]: bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            if len(sys.argv) < 3 or sys.argv[2] != '01': raise ValueError('dirigir: solo el cubo 01')
            with contextlib.redirect_stdout(buf):
                import paso01_cubos
                r = paso01_cubos.main(sys.argv[2:])
        except SystemExit as s_:
            r = {'ok': False, 'error': f'argumentos no válidos para dirigir (código {s_.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'storyboard':   # 1-nov-2026 planeador de storyboard (cajas/storyboard): cotizar/validar/traducir GRATIS sin red; correr SOLO con cajas/HABILITAR_PAGO_SB (paso01_pago.app() abre solo *.googleapis.com)
        import io, contextlib
        if len(sys.argv) < 3 or sys.argv[2] != 'correr': bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); sys.path.insert(0, str(CAJAS / 'storyboard')); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import cubo_sb
                r = cubo_sb.n8n(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para storyboard (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'ver':   # orden 66: ver imágenes (moldes 4a2/4a3, pintura 4a5) en n8n. SOLO LECTURA, GRATIS, sin red
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                if len(sys.argv) > 3 and sys.argv[2] == "prepago":   # VER pre-pago Argon texto (inmi 2-nov-2026): SECO, lee compuerta 00 + ledger + cotización como root
                    if not re.fullmatch(r"prepago_[A-Za-z0-9._-]+\.json", sys.argv[3]): raise ValueError("manifiesto no válido")
                    sys.path.insert(0, str(CAJAS / 'ver_prepago')); import ver_prepago
                    r = ver_prepago.argon_texto_r(json.loads((CAJAS / 'ver_prepago' / 'manifiestos' / sys.argv[3]).read_text()))
                elif len(sys.argv) > 2 and sys.argv[2] == "objetos":   # t528u: objetos que faltan en la base/4p contra el canal y el guion (GRATIS, sin red, solo lectura)
                    import paso00_objetos_faltantes as OF
                    r = OF.main(sys.argv[3:])
                elif len(sys.argv) > 2 and sys.argv[2] == "o109":   # o109: cubo 01 consolidado + cubo 02 molde 3D por toma (GRATIS desde aquí)
                    import cubo_o109
                    r = cubo_o109.main(sys.argv[3:])
                elif len(sys.argv) > 2 and sys.argv[2] == "o98":   # o98 noche: cubo 11 texto por código / cubo 12 revisión (GRATIS, solo lectura)
                    import cubo_o98
                    r = cubo_o98.main(sys.argv[3:])
                else:
                    import ver_imagenes
                    r = ver_imagenes.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para ver (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'revisar':   # PISTA INMI (2026-10-29): orden 69 — revisión de cámaras de 4a4. GRATIS, sin red, sin app, no toca el ledger
        bloquear_red(False)
        try: r = cmd_revisar(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para revisar (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'animatic':   # programa imágenes (31-oct-2026): armar/leer animatic MP4. GRATIS, sin red, sin IA (ffmpeg local)
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import armar_animatic
                r = armar_animatic.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para animatic (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'escena':   # paso 2 programa imágenes (31-oct-2026): armar/leer ficha Nivel 2. GRATIS, sin red, sin IA
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import armar_escena
                r = armar_escena.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para escena (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'estilo':   # paso 1 programa imágenes (31-oct-2026): fijar/leer muestra oficial. GRATIS, sin red, sin IA
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import estilo_oficial
                r = estilo_oficial.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para estilo (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'resolver':   # orden t340u/t341u: caja 4r resolver dudas (género + historia + dramatismo). cotizar/aplicar GRATIS, sin red
        import io, contextlib
        bloquear_red(False)
        sys.path.insert(0, str(CAJAS)); buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                import paso00_resolver
                r = paso00_resolver.main(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para resolver (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'juntos':   # t358u: cajas pagadas independientes a la vez (4b1 + 4c1)
        try: r = cmd_juntos(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para juntos (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    if len(sys.argv) > 1 and sys.argv[1] == 'reparar':   # orden 68: arreglo local de JSON roto. GRATIS, sin red, sin app, no toca el ledger
        bloquear_red(False)
        try: r = cmd_reparar(sys.argv[2:])
        except SystemExit as s:
            r = {'ok': False, 'error': f'argumentos no válidos para reparar (código {s.code})'}
        except Exception as exc:
            r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        salir(r)
    ap = argparse.ArgumentParser()
    ap.add_argument('accion', choices=['cotizar', 'correr', 'estado'])
    ap.add_argument('caja', nargs='?', default='base', choices=list(CAJA))
    ap.add_argument('--canal', default='cn-gnesis-digital-el-de-ed178619')
    ap.add_argument('--capitulo', default='1')
    ap.add_argument('--corrida', default=None)
    ap.add_argument('--ok', type=float, default=None)
    ap.add_argument('--aprobado', default=None)
    ap.add_argument('--solo', default=None, help='4a4/4a1/4b1/4c1: solo estos ids (prueba barata, orden 63/72)')
    ap.add_argument('--solo-fallidos', dest='solo_fallidos', action='store_true', help='orden 72: 4a1/4b1/4c1 — solo los ids cuyo último intento no sirvió')
    ap.add_argument('--repetir', action='store_true', help='t531u: base/escenarios/objetos/personajes — volver a pedir aunque ya esté hecho; antes respalda pedidos/respuestas/resultados viejos en <capítulo>/respaldos_repetir/<hora Bogotá>_<paso>/ (no borra nada). Igual exige HABILITAR_PAGO_00 y --ok')
    ap.add_argument('--como-nuevo', dest='como_nuevo', action='store_true', help='orden 72: cotizar el peor caso desde cero (no cambia nada)')
    ap.add_argument('--reintento-429', dest='reintento_429', action='store_true', help='(compatibilidad) orden 68: los reintentos acotados ante 429 van siempre')
    ap.add_argument('--max-intentos', dest='max_intentos', type=int, default=MAX_INTENTOS, help='orden 68: intentos por pedido ante 429 (1..6)')
    a = ap.parse_args()
    a.max_intentos = max(1, min(6, a.max_intentos))
    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):   # nada de la app se mezcla con el JSON de salida
            r = {'cotizar': cmd_cotizar, 'correr': cmd_correr, 'estado': cmd_estado}[a.accion](a)
    except SystemExit as s:
        raise
    except Exception as exc:
        r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
    salir(r)
