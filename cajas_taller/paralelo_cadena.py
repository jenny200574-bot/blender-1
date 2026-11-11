"""t358u (Ricardo): optimización de la cadena paso00 — GENÉRICO (cualquier canal y capítulo), manejado por llamadas_config.json «paralelo».
Piezas (todas gratis; no llaman a nada por sí mismas):
- candado_ledger / blindar_ledger: el ledger se lee-modifica-escribe; con varias llamadas a la vez se protege con un candado
  (fcntl entre procesos + lock entre hilos). La línea del ledger se sigue escribiendo ANTES de cada llamada (myia_argon.llamar).
- Bolsa: tope de pago ATÓMICO entre llamadas paralelas: cada pedido RESERVA su peor caso antes de llamar; si no cabe, no se llama.
- reservar_compuerta: reserva entre PROCESOS (p. ej. 4b1 y 4c1 a la vez) contra el monto de HABILITAR_PAGO_00 (no toca ese archivo).
- correr_paralelo: corre una lista de tareas con un máximo de N a la vez (anti-429 de Vertex); anota hora de inicio y fin de cada una.
- prechequeo: revisión GRATIS de tamaño de esquema/prompt antes de pagar (evita 400 INVALID_ARGUMENT seguros)."""
import os, json, time, fcntl, threading, contextlib, atexit
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

CONFIG = Path(__file__).resolve().parent / 'llamadas_config.json'
_LK = threading.RLock()

def cfg():
    try: return json.loads(CONFIG.read_text(encoding='utf-8')).get('paralelo') or {}
    except Exception: return {}

def activo(): return bool(cfg().get('activo', False)) and os.environ.get('TALLER_PARALELO', '1') != '0'

def max_a_la_vez(grupo='argon'):
    """Máximo de llamadas a la vez (TALLER_PARALELO_<GRUPO> lo cambia). 1 = como antes (en fila)."""
    v = os.environ.get(f'TALLER_PARALELO_{grupo.upper()}') or (cfg().get('max_a_la_vez') or {}).get(grupo, 1)
    try: return max(1, int(v))
    except ValueError: return 1

_TL = threading.local()

@contextlib.contextmanager
def candado(ruta):
    """Candado exclusivo entre procesos (fcntl) y entre hilos. Reentrante en el mismo hilo (registrar → total → _leer no se traba)."""
    ruta = Path(ruta); k = str(ruta.absolute()); held = getattr(_TL, 'held', None)
    if held is None: held = _TL.held = {}
    if held.get(k):
        held[k] += 1
        try: yield None
        finally: held[k] -= 1
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with _LK, open(ruta, 'a+') as h:
        fcntl.flock(h, fcntl.LOCK_EX); held[k] = 1
        try: yield h
        finally: held[k] = 0; fcntl.flock(h, fcntl.LOCK_UN)

@contextlib.contextmanager
def ranura(grupo, carpeta, n=None, espera_s=1.0):
    """Semáforo ENTRE PROCESOS Y HILOS: como mucho n tareas del grupo a la vez en todo el servidor (p. ej. 4b1 y 4c1 juntos
    no pasan de 3 llamadas a Argon a la vez → menos 429). Ranuras = archivos con flock no bloqueante."""
    n = int(n or max_a_la_vez(grupo)); carpeta = Path(carpeta); carpeta.mkdir(parents=True, exist_ok=True); t0 = time.time()
    while True:
        for i in range(n):
            h = open(carpeta / f'{grupo}_{i}.lock', 'a+')
            try: fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: h.close(); continue
            try:
                h.seek(0); h.truncate(); h.write(f'{os.getpid()} {threading.get_ident()} {time.time()}'); h.flush()
                yield {'ranura': i, 'espero_s': round(time.time() - t0, 2)}
            finally:
                fcntl.flock(h, fcntl.LOCK_UN); h.close()
            return
        time.sleep(espera_s)

def timeout_fijo(paso):
    """Segundos de «timeout_por_paso» para este paso (por prefijo); None = el general. Es el respaldo cuando no se sabe el tamaño."""
    t = cfg().get('timeout_por_paso') or {}
    k = next((k for k in sorted(t, key=len, reverse=True) if str(paso) == k or str(paso).startswith(k)), None)
    return float(t[k]) if k else None

def timeout_auto(chars=None, max_out=None):
    """t366u (Ricardo): tope de tiempo CALCULADO por el tamaño del pedido (config «timeout_automatico»). Lo que más tarda es la SALIDA
    (medido 4a4 3-nov-2026: ~13 s por cada 1000 tokens de salida + ~13 s fijos; la entrada pesa poco): segundos =
    margen × (s_fijo + s_por_1000_chars × chars/1000 + s_por_1000_tokens_salida × max_out/1000), dentro de [min_s, max_s]. None si está apagado o falta el tamaño."""
    a = cfg().get('timeout_automatico') or {}
    if not a.get('activo') or chars is None or max_out is None: return None
    t = float(a.get('margen', 1.25)) * (float(a.get('s_fijo', 30)) + float(a.get('s_por_1000_chars', 0.15)) * float(chars) / 1000
                                         + float(a.get('s_por_1000_tokens_salida', 13)) * float(max_out) / 1000)
    return float(round(min(float(a.get('max_s', 1200)), max(float(a.get('min_s', 360)), t))))

def timeout_paso(paso, chars=None, max_out=None):
    """Segundos máximos de UNA llamada de texto. Si se sabe el tamaño (chars del pedido y max_out) y timeout_automatico está activo,
    manda el CALCULADO; si no, el de «timeout_por_paso»; None = el general (llamadas_config.timeout_s.texto)."""
    t = timeout_auto(chars, max_out)
    return t if t is not None else timeout_fijo(paso)

def aviso_bitacora(texto, carpeta_base=None):
    """t366u (Ricardo): deja UNA línea en BITACORA_OPTIMIZACION.md (config «avisos_bitacora.archivo») cuando una caja se acerca a su tope
    de tiempo o de dinero. Nunca rompe la llamada: si no puede escribir, no pasa nada."""
    try:
        a = json.loads(CONFIG.read_text(encoding='utf-8')).get('avisos_bitacora') or {}
        if not a.get('activo', True): return None
        ar = Path(a.get('archivo') or (Path(carpeta_base or CONFIG.parent).parent / 'BITACORA_OPTIMIZACION.md'))
        linea = f"- {time.strftime('%Y-%m-%d %H:%M')} (hora VPS) ⚠️ {texto}\n"
        with candado(Path(str(ar) + '.lock')):
            nuevo = not ar.exists()
            with open(ar, 'a', encoding='utf-8') as f:
                if nuevo: f.write('# BITÁCORA DE OPTIMIZACIÓN — taller n8n\n\n')
                f.write(linea)
        return str(ar)
    except Exception:
        return None

def avisos_umbral():
    a = {}
    try: a = json.loads(CONFIG.read_text(encoding='utf-8')).get('avisos_bitacora') or {}
    except Exception: pass
    return float(a.get('pct_tiempo', 80)) / 100, float(a.get('pct_dinero', 80)) / 100

def blindar_ledger(AR, ledger):
    """Envuelve AR.registrar y AR.marcar con el candado del ledger. registrar: además fija MYIA_ARGON_PRESUPUESTO_USD = total + est
    DENTRO del candado (antes lo fijaba cada llamada justo antes: con hilos, uno podía pisar el valor del otro)."""
    if getattr(AR, '_blindado_t358', False): return AR
    lk = Path(str(ledger) + '.lock'); reg0, mar0 = AR.registrar, AR.marcar
    def registrar(id_, modelo, est, nota, *a, **k):
        with candado(lk):
            if os.environ.get('MYIA_ARGON_PRESUPUESTO_USD'): os.environ['MYIA_ARGON_PRESUPUESTO_USD'] = str(round(AR.total() + float(est), 4))
            return reg0(id_, modelo, est, nota, *a, **k)
    def marcar(*a, **k):
        with candado(lk): return mar0(*a, **k)
    leer0 = AR._leer
    def _leer(*a, **k):
        with candado(lk): return leer0(*a, **k)
    AR.registrar, AR.marcar, AR._leer, AR._blindado_t358 = registrar, marcar, _leer, True
    return AR

class Bolsa:
    """Tope total aprobado (--ok) compartido por llamadas paralelas. reservar() es atómico: gastado + reservado + monto ≤ tope."""
    def __init__(self, tope):
        self.tope, self.gastado, self.reservado, self.lk, self.max_comprometido = float(tope), 0.0, 0.0, threading.Lock(), 0.0
    def reservar(self, monto):
        with self.lk:
            if self.gastado + self.reservado + monto > self.tope + 1e-9: return False
            self.reservado += monto; self.max_comprometido = max(self.max_comprometido, self.gastado + self.reservado); return True
    def extra(self, deseado):
        """Reserva adicional (para un reintento pagado) solo con lo que sobra; devuelve lo que se pudo reservar."""
        with self.lk:
            d = max(0.0, min(deseado, self.tope - self.gastado - self.reservado))
            self.reservado += d; self.max_comprometido = max(self.max_comprometido, self.gastado + self.reservado); return round(d, 6)
    def asentar(self, reservado, gastado_real):
        with self.lk: self.reservado -= reservado; self.gastado += float(gastado_real or 0)
    def libre(self):
        with self.lk: return round(self.tope - self.gastado - self.reservado, 4)

def correr_paralelo(tareas, fn, n, parar_si=None, espaciar_s=0.0):
    """tareas: lista; fn(tarea) → dict. Máximo n a la vez. Si parar_si(resultado) es True, no se lanzan las que faltan
    (las que ya empezaron terminan). Devuelve [(tarea, resultado|None, t_ini, t_fin)] en el orden original."""
    out = [None] * len(tareas); alto = threading.Event(); lk = threading.Lock(); ult = [0.0]
    def uno(i):
        if alto.is_set(): out[i] = (tareas[i], {'estado': 'no_llamado', 'motivo': 'se paró: falló otro pedido de la misma corrida'}, None, None); return
        if espaciar_s:
            with lk:
                w = ult[0] + espaciar_s - time.time()
                if w > 0: time.sleep(w)
                ult[0] = time.time()
        t0 = time.time()
        try: r = fn(tareas[i])
        except Exception as exc: r = {'estado': 'error', 'error': f'{type(exc).__name__}: {str(exc)[:300]}'}
        out[i] = (tareas[i], r, t0, time.time())
        if parar_si and parar_si(r): alto.set()
    with ThreadPoolExecutor(max_workers=max(1, int(n))) as ex: list(ex.map(uno, range(len(tareas))))
    return out

# --- reserva entre procesos contra HABILITAR_PAGO_00 (4b1 y 4c1 al mismo tiempo) -------------------------------------------
def _vivo(pid):
    try: os.kill(int(pid), 0); return True
    except Exception: return False

def reservar_compuerta(archivo, monto_tope, gastado, ok, quien):
    """Bajo candado: limpia reservas de procesos muertos y reserva `ok` solo si gastado + reservas de OTROS procesos + ok ≤ monto.
    Devuelve None si quedó reservado, o el motivo. La reserva se suelta sola al salir el proceso (atexit) o si el proceso muere."""
    archivo = Path(archivo)
    with candado(str(archivo) + '.lock'):
        try: rs = json.loads(archivo.read_text()) if archivo.is_file() else {}
        except Exception: rs = {}
        rs = {k: v for k, v in rs.items() if _vivo(k) and int(k) != os.getpid()}
        otros = round(sum(float(v.get('ok') or 0) for v in rs.values()), 4)
        if gastado + otros + float(ok) > float(monto_tope) + 1e-9:
            return f'tope total {monto_tope}: gastado {gastado} + reservado por otras corridas en curso {otros} + este {ok} lo pasa. No se llamó a nada.'
        rs[str(os.getpid())] = {'ok': float(ok), 'quien': quien, 'hora': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
        archivo.write_text(json.dumps(rs, ensure_ascii=False, indent=1))
    atexit.register(soltar_compuerta, archivo)
    return None

def soltar_compuerta(archivo):
    archivo = Path(archivo)
    with candado(str(archivo) + '.lock'):
        try: rs = json.loads(archivo.read_text()) if archivo.is_file() else {}
        except Exception: rs = {}
        rs.pop(str(os.getpid()), None); archivo.write_text(json.dumps(rs, ensure_ascii=False, indent=1))

# --- prechequeo gratis ---------------------------------------------------------------------------------------------------
def contar_esquema(esq):
    n = {'propiedades': 0, 'anyof': 0, 'enum': 0, 'prof': 0}
    def rec(x, d):
        n['prof'] = max(n['prof'], d)
        if isinstance(x, dict):
            if isinstance(x.get('properties'), dict): n['propiedades'] += len(x['properties'])
            if 'anyOf' in x: n['anyof'] += 1
            if 'enum' in x: n['enum'] += 1
            for v in x.values(): rec(v, d + 1)
        elif isinstance(x, list):
            for v in x: rec(v, d + 1)
    rec(esq, 0); return n

def prechequeo(pr, esq, max_out=None):
    """GRATIS, sin red. Devuelve [] si se puede pagar, o la lista de motivos por los que Vertex lo rechazaría seguro (no se paga)."""
    c = cfg().get('prechequeo') or {}; mal = []
    if not c.get('activo', True): return mal
    if pr is not None and len(pr) > int(c.get('max_prompt_chars', 900000)): mal.append(f"prompt de {len(pr)} caracteres > {c.get('max_prompt_chars')}")
    if esq is not None and (not isinstance(esq, str) or esq.strip()[:1] in ('{', '[')):   # texto libre o vacío = no es esquema JSON, no se revisa
        try: e = json.loads(esq) if isinstance(esq, str) else esq
        except Exception as exc: return mal + [f'esquema no es JSON válido: {exc}']
        k = contar_esquema(e); kb = len(json.dumps(e)) / 1024
        try:
            import dividir_esquema as DE; k['propiedades'] = DE.contar(e)   # mismo conteo que usa la división A/B
        except Exception: pass
        if k['propiedades'] > int(c.get('max_propiedades', 205)): mal.append(f"esquema con {k['propiedades']} propiedades > {c.get('max_propiedades')} (Vertex responde 400)")
        if kb > float(c.get('max_esquema_kb', 60)): mal.append(f"esquema de {kb:.1f} KB > {c.get('max_esquema_kb')} KB")
        if k['prof'] > int(c.get('max_profundidad', 40)): mal.append(f"esquema con profundidad {k['prof']} > {c.get('max_profundidad')}")
    if max_out is not None and int(max_out) > int(c.get('max_out_tope', 65536)): mal.append(f"max_out {max_out} > {c.get('max_out_tope')}")
    return mal
