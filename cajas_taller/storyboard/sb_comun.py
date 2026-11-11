"""PISTA INMI (2026-11-01) ADAPTIVE CINEMATIC DIRECTOR (planeador de storyboard, solo texto/JSON) — piezas comunes y GRATIS.
Genérico (regla 6): aquí no hay canales, capítulos ni personajes. Todo lo de un canal vive en canales/<canal>.json (3 niveles separados)."""
import copy, json, re, sys, unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CAJAS = AQUI.parent
for _p in (str(CAJAS), str(AQUI / 'vendor' / 'camera_dsl' / 'scripts')):
    if _p not in sys.path: sys.path.insert(0, _p)
import camera_dsl as DSL   # copia fija MIT, commit 7cbc087 (vendor/camera_dsl/VENDOR.txt)

DSL_COMMIT = '7cbc087dabe0d4a8ec7a4ecf5b24d786783806d3'
POR_DEFINIR = 'por definir'
NIVELES = ('nivel_1_genero_tono', 'nivel_2_estilo_visual', 'nivel_3_direccion_artistica')


def leer(f, d=None):
    try: return json.loads(Path(f).read_text(encoding='utf-8'))
    except Exception: return d


def guardar(f, x):
    f = Path(f); f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + '.tmp'); tmp.write_text(json.dumps(x, ensure_ascii=False, indent=1), encoding='utf-8'); tmp.replace(f)
    return str(f)


def ajustes(): return leer(AQUI / 'config' / 'ajustes_sb.json')


def texto(rel): return (AQUI / rel).read_text(encoding='utf-8')


# ---------------- texto ----------------
def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', s)).strip()


def palabras(s): return norm(s).split()


def cita_en(cita, texto_base, umbral=.6):
    """La cita está copiada del texto: >= 60 % de sus pares de palabras seguidas aparecen tal cual (igual criterio que el 01)."""
    w = palabras(cita); g = f' {norm(texto_base)} '
    if len(w) < 2: return not w or f' {w[0]} ' in g
    pares = [f' {w[i]} {w[i + 1]} ' for i in range(len(w) - 1)]
    return sum(1 for p in pares if p in g) / len(pares) >= umbral


def posicion(cita, texto_base):
    """Índice (en palabras) donde empieza la cita dentro del texto, o None. Busca 4, 3 y 2 palabras seguidas."""
    w, g = palabras(cita), palabras(texto_base)
    for k in (4, 3, 2, 1):
        if len(w) < k: continue
        for s in range(0, len(w) - k + 1):
            pat = w[s:s + k]
            for i in range(len(g) - k + 1):
                if g[i:i + k] == pat: return max(0, i - s)
    return None


# ---------------- guion de la escena ----------------
ESC_RX = re.compile(r'^\s*ESCENA\s+([A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+)\b', re.M)


def guion_escena(guion, numero):
    """Trozo del guion completo que corresponde a la escena (cabeceras «ESCENA N.»). None si no se encuentra."""
    if not guion: return None
    marcas = [(m.start(), m.group(1)) for m in ESC_RX.finditer(guion)]
    for k, (ini, n) in enumerate(marcas):
        if norm(n) == norm(numero):
            fin = marcas[k + 1][0] if k + 1 < len(marcas) else len(guion)
            return guion[ini:fin].strip()
    return None


HABLA_RX = re.compile(r'^\s*([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9 .\'()-]{0,40}):\s*$')


def dialogos(trozo):
    """[{quien_guion, texto, orden}] de las líneas de diálogo/narración del trozo (NOMBRE: en su línea + el texto que sigue)."""
    out, quien = [], None
    for l in (trozo or '').splitlines():
        m = HABLA_RX.match(l)
        if m: quien = m.group(1).strip(); continue
        s = l.strip()
        if not s: continue
        if quien and (s.startswith('—') or s.startswith('-') or s.startswith('«') or s.startswith('"')):
            out.append({'quien_guion': quien, 'texto': s.lstrip('—-').strip(), 'orden': len(out)})
        quien = None
    return out


ARTICULOS = {'el', 'la', 'los', 'las', 'the'}


def quien_a_id(nombre, fichas, narrador='NARRADOR'):
    """Nombre del guion (p. ej. «NOVIA») → id de ficha (p. ej. «LA NOVIA»). No renombra: solo empareja. None si no hay."""
    if norm(nombre) in ('narrador', 'narradora', 'narrator', 'voz en off', 'vo'): return narrador
    a = [w for w in palabras(nombre) if w not in ARTICULOS]
    for f in fichas:
        b = [w for w in palabras(f.get('name')) if w not in ARTICULOS]
        if a and a == b: return f['id']
    for f in fichas:
        b = [w for w in palabras(f.get('name')) if w not in ARTICULOS]
        if a and b and (set(a) <= set(b) or set(b) <= set(a)): return f['id']
    return None


# ---------------- DSL ----------------
_REG = None


def registro():
    global _REG
    if _REG is None: _REG = DSL.registry()
    return _REG


def categoria(token):
    c = registro().commands.get(token)
    return (c or {}).get('category') if isinstance(c, dict) else getattr(c, 'category', None)


def tokens_de(cat):
    R = registro().commands
    return sorted(k for k, v in R.items() if (v.get('category') if isinstance(v, dict) else getattr(v, 'category', None)) == cat)


def analizar(dsl):
    try: return DSL.analyze(str(dsl or ''))
    except Exception as e: return {'status': 'ERROR', 'shots': [], 'diagnostics': [{'rule': 'PARSE', 'type': 'ERROR', 'message': f'{type(e).__name__}: {e}'}]}


def comandos(r):
    """[(t0, t1, canonical, args)] de todos los segmentos de un análisis."""
    out = []
    for sh in r.get('shots') or []:
        for sg in sh.get('segments') or []:
            for c in sg.get('commands') or []:
                out.append((sg.get('t0'), sg.get('t1'), c.get('canonical'), c.get('args') or {}))
    return out


# ---------------- niveles por canal ----------------
def config_canal(canal):
    return leer(AQUI / 'canales' / f'{canal}.json')


def _mezclar(a, b):
    if not isinstance(b, dict): return copy.deepcopy(b)
    out = copy.deepcopy(a) if isinstance(a, dict) else {}
    for k, v in b.items(): out[k] = _mezclar(out.get(k), v) if isinstance(v, dict) else copy.deepcopy(v)
    return out


def niveles(canal, capitulo, escena, cfg=None):
    """Los 3 niveles efectivos para una escena: canal → por_capitulo[cap] → por_escena["cap/esc"]. Cada nivel se pisa SOLO consigo mismo
    (nunca se mezcla un nivel con otro). Devuelve (niveles, avisos)."""
    cfg = cfg if cfg is not None else config_canal(canal)
    av = []
    if not cfg: return {k: {'estado': POR_DEFINIR} for k in NIVELES}, [f'no existe storyboard/canales/{canal}.json: los 3 niveles quedan «por definir» (correr config-iniciar)']
    cap = str(int(capitulo)) if str(capitulo).isdigit() else str(capitulo)
    capas = [cfg, (cfg.get('por_capitulo') or {}).get(cap) or {}, (cfg.get('por_escena') or {}).get(f'{cap}/{escena}') or {}]
    out = {}
    for k in NIVELES:
        v = {}
        for c in capas:
            if isinstance(c.get(k), dict): v = _mezclar(v, c[k])
        out[k] = v or {'estado': POR_DEFINIR}
        if str(out[k].get('estado', '')).startswith(POR_DEFINIR): av.append(f'{k}: «por definir»')
    return out, av


def reglamento(n3):
    """Nivel 3: el reglamento con nombre (config/reglamentos/<NOMBRE>.json). None si «por definir» o si no existe el archivo."""
    nom = (n3 or {}).get('reglamento')
    if not nom or str(nom).startswith(POR_DEFINIR): return None
    return leer(AQUI / 'config' / 'reglamentos' / f'{nom}.json')


def resumen_niveles(nv):
    """Lo que la respuesta debe copiar en niveles_aplicados (prueba de que no confundió los niveles)."""
    n1, n2, n3 = (nv.get(k) or {} for k in NIVELES)
    return {'nivel_1_generos': sorted(n1.get('generos') or []) or [POR_DEFINIR],
            'nivel_2_estilo': n2.get('estilo_catalogo') or POR_DEFINIR,
            'nivel_3_reglamento': n3.get('reglamento') or POR_DEFINIR}


def diagnosticos(r):
    d = list(r.get('diagnostics') or [])
    for sh in r.get('shots') or []: d += sh.get('diagnostics') or []
    return d


def errores_dsl(r):
    """Mensajes de los diagnósticos que el DSL marca como error (ERROR / HARD_CONFLICT). Las advertencias no cuentan."""
    out = [f"{x.get('rule')}: {x.get('message')}" + (f" (arreglo: {x['fix']})" if x.get('fix') else '') for x in diagnosticos(r) if x.get('type') in ('ERROR', 'HARD_CONFLICT')]
    if r.get('status') == 'ERROR' and not out: out.append('el DSL marca ERROR')
    return out
