#!/usr/bin/env python3
"""PISTA INMI (2026-10-29): orden 75 — «Cargar personajes» (Ricardo: «Sí, arma el cubo Cargar personajes así, sin gastar»;
«que no se generen los protagonistas»; «quiero arreglos universales, recuerda cualquier canal»). GRATIS: sin red, sin app, sin ledger.

Regla dura: los cubos de pintar NUNCA generan ni inventan personajes. Un personaje sale SIEMPRE de las imágenes que el USUARIO cargó
para su VERSIÓN (traje, herido, de niño…). Si la versión que pide una escena falta (o no está aprobada) → se detiene esa imagen/toma
con un aviso claro; lo demás sigue (ajuste «si_falta_version»).

PENDIENTE (orden 91, pedido por Ricardo 2026-10-29): Validar con IA el guion/historia contra las hojas ANTES de crear las formas de
personajes (quién es cada forma, objeto vs persona, quién usa qué), universal para cualquier canal de fantasía. Pedido por Ricardo 2026-10-29.
(Todavía NO está hecho: hoy una forma que es un objeto se corrige a mano con «reemplazar-refs --tipo-forma objeto».)

GENÉRICO (regla 6): aquí no hay nombres de canales, personajes ni versiones. Los nombres vienen SOLO de lo que sube el usuario y del
mapa del paso 00 (respuestas/base.json → catalogo_oficial.personajes[].formas y respuestas/personajes.json → estados por escena).
Las palabras que delatan una figura o ropa puesta están en personajes_config.json (varios idiomas, ampliables).

Dónde se guarda (por CANAL, sirve para todos los capítulos; mismo orden que el protocolo de versiones del 25-oct):
  <biblioteca>/<canal>/personajes/personajes.json                    ← lista: personaje → versiones → imágenes (+ ajustes)
  <biblioteca>/<canal>/personajes/<personaje>/<versión>/refs/*.png    ← las imágenes que subió el usuario

Uso (por la entrada restringida de n8n):  paso00_cadena personajes <accion> --canal C [--capitulo N] …
  revisar   [--prellenar]    lista de avisos: imágenes repetidas entre versiones, versiones sin imágenes, versiones que pide el mapa
                             (cargada / sin aprobar / falta) y la cotización del costo extra. --prellenar copia antes lo que ya existe
                             en el estudio (solo lectura) SIN inventar nada y sin pisar lo del usuario.
  ficha     --sesion S --datos B64URL(json)   datos de la versión del formulario (personaje, versión, descripción, aprobada…)
  subir     --sesion S --nombre F --parte i --de n --datos B64URL   un trozo de una imagen del formulario
  guardar   --sesion S       arma las imágenes de la sesión y las guarda en su versión (revisa tipo, tamaño, máximo y repetidas)
  hoja-recibir|hoja-cotizar|hoja-aplicar|hoja-leer|hoja-separar   orden 76: leer UNA hoja de personaje con IA (ver personajes_hoja.py)
  refs      --capitulo N --escena E [--personaje P] [--momento inicio|fin|transformacion]   imágenes que un cubo de pintar debe adjuntar
  aprobar   (--personaje P[:V][,…] | --todos) --aprobado QUIEN [--excepto B64URL([{version:'P:V', nota}])] [--cita-b64] [--fecha ISO]
            orden 86: estado «aprobada» + aprobado_por/fecha/cita; «completado_ia» queda como historia + revisado; las excepciones quedan pendientes con nota.
  alias-version --personaje P --version V --nombre-b64 ALIAS [--forma-id F] --aprobado QUIEN
            orden 88: otro nombre (y forma_id del mapa) para una versión ya cargada; el mapa la encuentra por ese nombre.
  relleno   --capitulo N [--personaje P (--tipo relleno|solo_voz | --descripcion-b64 | --todos = aprobado) --aprobado QUIEN]
            orden 88: personajes del mapa sin hoja → relleno (descripción del guion, estilo del canal, sin imagen, pendiente de revisión)
            o solo_voz (sin imagen). Solo de ese capítulo (<capítulo>/personajes_relleno.json). revisar/refs ya no los marcan como falta.
  reemplazar-refs --personaje P:V --imagen ARCHIVO --aprobado QUIEN [--tipo-forma persona|objeto] [--nota-b64] [--cita-b64] [--fecha ISO]
            orden 91: la imagen que DIO el usuario reemplaza las refs de UNA versión (sin IA, US$0). ARCHIVO está en
            <biblioteca>/<canal>/personajes/_entrada/. Las imágenes anteriores (pintadas por IA) se MUEVEN a <versión>/refs_reemplazadas/
            (nada se borra). Versión: origen «usuario», completado_por_IA false, aprobada por QUIEN con su cita. «objeto» = cosa que
            alguien lleva o usa (sin frente/espalda de cuerpo): los cubos la adjuntan como objeto, no como figura.
  dividir   --personaje P --aprobado QUIEN [--datos B64URL(json)]   orden 85: un personaje guardado como UNO con varias versiones que en
            realidad son personas distintas → un personaje por versión (sus refs se MUEVEN a su carpeta, estado y «completado_ia» intactos).
            El nombre viejo queda como GRUPO (resuelve a todos) y cada nombre de versión viejo como alias del nuevo personaje.
"""
import argparse, base64, fcntl, hashlib, json, os, re, shutil, sqlite3, time, unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('MYIA_PERSONAJES_CONFIG', str(AQUI / 'personajes_config.json')))
LLAMADAS_CONFIG = Path(os.environ.get('MYIA_LLAMADAS_CONFIG', str(AQUI / 'llamadas_config.json')))   # t366s1473: guarda_personajes
RAIZ = Path(os.environ.get('MYIA_BIBLIOTECA', '/opt/myia-taller-n8n/trabajo/biblioteca'))
TRABAJO = Path(os.environ.get('MYIA_TRABAJO', '/opt/myia-taller-n8n/trabajo/paso00_cadena'))
ESQUEMA = 'myia-personajes-canal/1'
MAGIA = {b'\x89PNG': '.png', b'\xff\xd8\xff': '.jpg', b'RIFF': '.webp'}

# ---------------- utilidades ----------------
def ahora(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')
def cfg():
    return json.loads(CONFIG.read_text(encoding='utf-8'))
def sin_tildes(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '')) if not unicodedata.combining(c))
def slug(s):
    t = re.sub(r'[^a-z0-9]+', '-', sin_tildes(s).lower()).strip('-')
    return t[:60] or 'sin-nombre'
def igual(a, b): return bool(a) and bool(b) and slug(a) == slug(b)
def sha(b): return hashlib.sha256(b).hexdigest()
def leer_json(f, defecto=None):
    try: return json.loads(Path(f).read_text(encoding='utf-8'))
    except Exception: return defecto
def escribir_json(f, o):
    f = Path(f); f.parent.mkdir(parents=True, exist_ok=True); t = f.with_suffix(f.suffix + '.tmp')
    t.write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8'); t.replace(f)
def valido_id(s): return bool(re.fullmatch(r'[A-Za-z0-9._-]{1,120}', str(s or '')))
def b64(s):
    s = str(s or ''); return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def carpeta_capitulo(canal, capitulo):
    if not valido_id(canal) or capitulo in (None, ''): return None
    b = TRABAJO / canal
    if not b.is_dir(): return None
    ds = sorted(b.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(b.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None

def raiz(canal): return RAIZ / canal / 'personajes'
def manifiesto_f(canal): return raiz(canal) / 'personajes.json'

class Candado:
    def __init__(self, canal): self.f = raiz(canal) / '.candado'
    def __enter__(self):
        self.f.parent.mkdir(parents=True, exist_ok=True); self.h = open(self.f, 'w'); fcntl.flock(self.h, fcntl.LOCK_EX); return self
    def __exit__(self, *a): fcntl.flock(self.h, fcntl.LOCK_UN); self.h.close()

def leer_manifiesto(canal):
    m = leer_json(manifiesto_f(canal)) or {}
    m.setdefault('esquema', ESQUEMA); m.setdefault('canal', canal); m.setdefault('personajes', []); m.setdefault('ajustes', {})
    return m

def ajustes(m=None):
    a = dict(cfg()['ajustes_por_defecto']); a.update((m or {}).get('ajustes') or {}); return a

def guardar_manifiesto(canal, m):
    m['actualizado'] = ahora(); escribir_json(manifiesto_f(canal), m)

# ---------------- mapa del paso 00 (qué versión pide cada escena) ----------------
def mapa(D):
    """{pid: {'nombre', 'formas': {fid: {'nombre', 'escenas': [(escena, momento)]}}}} desde el paso 00. Sin red."""
    D = Path(D); base = leer_json(D / 'respuestas' / 'base.json') or {}; pj = leer_json(D / 'respuestas' / 'personajes.json') or {}
    out = {}
    for p in ((base.get('catalogo_oficial') or {}).get('personajes') or []):
        if not isinstance(p, dict) or not p.get('id'): continue
        e = out.setdefault(p['id'], {'nombre': p.get('nombre') or p['id'], 'formas': {}})
        for f in p.get('formas') or []:
            if isinstance(f, dict) and (f.get('forma_id') or f.get('id')):
                e['formas'].setdefault(f.get('forma_id') or f.get('id'), {'nombre': '' if _vacio(f.get('nombre')) else str(f.get('nombre')).strip(), 'escenas': []})
    for p in (pj.get('personajes') or []):
        if not isinstance(p, dict) or not p.get('personaje_id'): continue
        e = out.setdefault(p['personaje_id'], {'nombre': p['personaje_id'], 'formas': {}})
        for st in p.get('estados') or []:
            if not isinstance(st, dict): continue
            for mom in ('inicio', 'fin'):
                fid = ((st.get(mom) or {}).get('forma_id') or '').strip()
                if not fid or fid.lower() in ('falta', 'desconocido'): continue
                fo = e['formas'].setdefault(fid, {'nombre': '', 'escenas': []})
                par = (str(st.get('escena')), mom)
                if par not in fo['escenas']: fo['escenas'].append(par)
    return out

def estados_escena(D, escena):
    """[(pid, forma_inicio, forma_fin)] de los personajes que el paso 00 pone en esa escena."""
    pj = leer_json(Path(D) / 'respuestas' / 'personajes.json') or {}; out = []
    for p in (pj.get('personajes') or []):
        for st in (p.get('estados') or []) if isinstance(p, dict) else []:
            if isinstance(st, dict) and str(st.get('escena')) == str(escena):
                fi = ((st.get('inicio') or {}).get('forma_id') or '').strip(); ff = ((st.get('fin') or {}).get('forma_id') or '').strip() or fi
                out.append((p.get('personaje_id'), fi or ff, ff))
    return out

# ---------------- buscar en lo cargado ----------------
def buscar_personaje(m, pid=None, nombre=None):
    for p in m.get('personajes') or []:
        if pid and (p.get('id') == pid or pid in (p.get('ids_mapa') or [])): return p
    for p in m.get('personajes') or []:   # PISTA INMI (orden 77): también por «alias» (nombres viejos, p. ej. la etiqueta del mapa)
        if nombre and (igual(p.get('nombre'), nombre) or any(igual(x, nombre) for x in p.get('alias') or [])): return p
    return None

def nombrar(canal, quien, nombre, por, descripcion=None):
    """PISTA INMI (orden 77): nombre (y descripción) PUESTOS A MANO por una persona. El nombre viejo queda como alias (el mapa del
    paso 00 sigue encontrándolo) y el campo queda en «manual»: la IA (hoja-aplicar) nunca lo pisa. No aprueba nada."""
    if not str(nombre or '').strip() or not str(por or '').strip() or _vacio(nombre): raise ValueError('falta --nombre y --aprobado (quién lo decidió)')
    nombre = str(nombre).strip()
    with Candado(canal):
        m = leer_manifiesto(canal); pm = buscar_personaje(m, quien, quien)
        if pm is None: raise ValueError(f'no encuentro el personaje «{quien}» (nombre, alias o id)')
        otro = buscar_personaje(m, None, nombre)
        if otro is not None and otro is not pm: raise ValueError(f'«{nombre}» ya es otro personaje ({otro["id"]})')
        al = pm.setdefault('alias', [])
        if not igual(pm.get('nombre'), nombre) and not any(igual(x, pm.get('nombre')) for x in al): al.append(pm['nombre'])
        al[:] = [x for x in al if not igual(x, nombre)]
        pm['nombre'] = nombre; man = pm.setdefault('manual', {}); f = ahora()
        man['nombre'] = {'por': str(por).strip(), 'fecha': f}
        if not _vacio(descripcion):
            pm['descripcion'] = str(descripcion).strip(); man['descripcion'] = {'por': str(por).strip(), 'fecha': f}
        guardar_manifiesto(canal, m)
    return {'ok': True, 'accion': 'personajes nombrar', 'id': pm['id'], 'nombre': pm['nombre'], 'alias': pm['alias'],
            'descripcion': pm.get('descripcion'), 'manual': sorted(pm['manual'])}

def buscar_version(p, fid=None, nombre=None):
    if not p: return None
    for v in p.get('versiones') or []:
        if fid and (v.get('forma_id') == fid or fid in (v.get('ids_mapa') or [])): return v
    for v in p.get('versiones') or []:
        if nombre and igual(v.get('nombre'), nombre): return v
    for v in p.get('versiones') or []:   # orden 88: también por «alias» de la VERSIÓN (otro nombre que el mapa usa para la misma versión)
        if nombre and any(igual(x, nombre) for x in v.get('alias') or []): return v
    return None

def alias_version(canal, quien, version, alias, por, forma_id=None):
    """Orden 88: otro nombre (y opcionalmente otro forma_id del mapa) para una versión YA cargada. Así el mapa del paso 00 que llama
    a la misma versión con otro nombre la encuentra (revisar, refs). Genérico; no aprueba ni cambia imágenes; queda quién y cuándo."""
    if not str(alias or '').strip() or _vacio(alias): raise ValueError('falta --nombre-b64 (el alias)')
    if not str(por or '').strip(): raise ValueError('falta --aprobado (quién lo decidió)')
    alias = str(alias).strip(); forma_id = str(forma_id or '').strip() or None
    with Candado(canal):
        m = leer_manifiesto(canal); pm = buscar_personaje(m, quien, quien)
        if pm is None: raise ValueError(f'no encuentro el personaje «{quien}» (nombre, alias o id)')
        v = next((x for x in pm.get('versiones') or [] if x.get('id') == version), None) or buscar_version(pm, version, version)
        if v is None: raise ValueError(f'«{pm["nombre"]}» no tiene la versión «{version}»')
        otra = buscar_version(pm, forma_id, alias)
        if otra is not None and otra is not v: raise ValueError(f'«{alias}» ya es otra versión de {pm["nombre"]} ({otra.get("nombre")})')
        al = v.setdefault('alias', [])
        if not igual(v.get('nombre'), alias) and not any(igual(x, alias) for x in al): al.append(alias)
        if forma_id and forma_id != v.get('forma_id'):
            ids = v.setdefault('ids_mapa', [])
            if forma_id not in ids: ids.append(forma_id)
        v.setdefault('alias_historia', []).append({'alias': alias, 'forma_id': forma_id, 'por': str(por).strip(), 'fecha': ahora()})
        guardar_manifiesto(canal, m)
    return {'ok': True, 'accion': 'personajes alias-version', 'personaje': pm['nombre'], 'version': v.get('nombre'), 'alias': v.get('alias'),
            'ids_mapa': v.get('ids_mapa') or [], 'estado': v.get('estado')}

# ---------------- grupos (orden 85) ----------------
def buscar_grupo(m, pid=None, nombre=None):
    """PISTA INMI (orden 85): un GRUPO es un personaje viejo que se dividió en varios (uno por versión). Lo encuentra por id, id del mapa,
    nombre o alias. El grupo no es un personaje: resuelve a sus miembros."""
    for g in m.get('grupos') or []:
        if pid and (g.get('id') == pid or pid in (g.get('ids_mapa') or [])): return g
    for g in m.get('grupos') or []:
        if nombre and (igual(g.get('nombre'), nombre) or igual(g.get('id'), nombre) or any(igual(x, nombre) for x in g.get('alias') or [])): return g
    return None

def miembros_grupo(m, g):
    """[(personaje, versión)] de un grupo, en su orden."""
    out = []
    for mi in (g or {}).get('miembros') or []:
        pm = buscar_personaje(m, mi.get('personaje'))
        if pm is None: continue
        v = next((x for x in pm.get('versiones') or [] if x.get('id') == mi.get('version')), None)
        if v is None and len(pm.get('versiones') or []) == 1: v = pm['versiones'][0]
        out.append((pm, v))
    return out

def es_miembro(pm, quien):
    """¿«quien» (id, nombre o alias) nombra a este personaje?"""
    return bool(quien) and (pm.get('id') == quien or igual(pm.get('nombre'), quien) or any(igual(x, quien) for x in pm.get('alias') or []))

def resolver(m, pid=None, nombre=None):
    """Personaje(s) que nombra un id/nombre del guion o de un plan: [(personaje, versión|None)]. Un personaje → él; un grupo → sus miembros."""
    p = buscar_personaje(m, pid, nombre)
    if p is not None: return [(p, None)]
    return miembros_grupo(m, buscar_grupo(m, pid, nombre))

def _texto_lista(x):
    if isinstance(x, list): x = '; '.join(str(y).strip() for y in x if str(y).strip())
    return None if _vacio(x) or not str(x or '').strip() else str(x).strip()

def _altura(x):
    if isinstance(x, (int, float)): return float(x)
    mm = re.search(r'(\d+(?:[.,]\d+)?)\s*m\b', str(x or ''))
    return float(mm.group(1).replace(',', '.')) if mm else None

def _ficha_de_hoja(canal, v):
    """Lo que la lectura de la hoja (orden 76) dice del personaje al que pertenece esta versión: nombre, nunca cambia, rol… Sin red."""
    pi = v.get('propuesto_ia') or {}; hid = pi.get('hoja')
    if not hid or not valido_id(hid): return None
    L = leer_json(raiz(canal) / '_hojas' / hid / 'lectura.json') or {}
    vn = pi.get('nombre_en_hoja') or v.get('nombre')
    for p in L.get('personajes') or []:
        if not isinstance(p, dict): continue
        vs = [x for x in p.get('versiones') or [] if isinstance(x, dict)]
        if any(igual(x.get('nombre'), vn) or igual(x.get('nombre_en_mapa'), vn) for x in vs):
            vx = next(x for x in vs if igual(x.get('nombre'), vn) or igual(x.get('nombre_en_mapa'), vn))
            return {'nombre': p.get('nombre'), 'nunca_cambia': p.get('nunca_cambia'), 'altura': vx.get('altura') or p.get('altura'),
                    'descripcion': p.get('descripcion'), 'rol': p.get('rol'), 'edad': p.get('edad'), 'personalidad': p.get('personalidad'),
                    'fuente': f'_hojas/{hid}/lectura.json'}
    return None

def _cambiar_rutas(o, viejo, nuevo):
    """Cambia el comienzo de rutas (relativas o absolutas) dentro de un JSON; nada más."""
    if isinstance(o, str): return nuevo + o[len(viejo):] if o.startswith(viejo) else o
    if isinstance(o, list): return [_cambiar_rutas(x, viejo, nuevo) for x in o]
    if isinstance(o, dict): return {_cambiar_rutas(k, viejo, nuevo): _cambiar_rutas(x, viejo, nuevo) for k, x in o.items()}
    return o

def dividir(canal, quien, por, datos=None):
    """PISTA INMI (orden 85): «separa» un personaje guardado como UNO cuyas versiones son personas distintas → UN personaje por versión.
    Genérico (cualquier canal). Por cada versión: personaje nuevo con nombre, nunca cambia, altura, descripción (de --datos, si no de la
    lectura de su hoja; si no hay, el nombre de la versión y lo demás vacío, sin inventar) y esa ÚNICA versión, que se MUEVE tal cual
    (refs, vistas, vistas_info con «completado_ia», refs_reemplazadas, estado) a <personaje nuevo>/<versión>/. Nada se aprueba ni se borra.
    El viejo queda en «grupos» (id, nombre, alias, ids del mapa → resuelve a todos los miembros) y cada nombre de versión viejo
    queda como alias de su personaje nuevo. datos = {versión (id o nombre): {nombre, nunca_cambia, altura_m, descripcion, id}}."""
    if not str(por or '').strip(): raise ValueError('falta --aprobado (quién lo decidió)')
    datos = datos or {}; R = raiz(canal); hechos, avisos, movidas = [], [], []
    with Candado(canal):
        m = leer_manifiesto(canal); pm = buscar_personaje(m, quien, quien)
        if pm is None:
            g = buscar_grupo(m, quien, quien)
            raise ValueError(f'«{quien}» ya está dividido (grupo {g["id"]})' if g else f'no encuentro el personaje «{quien}» (nombre, alias o id)')
        vs = list(pm.get('versiones') or [])
        if len(vs) < 2: raise ValueError(f'«{pm["nombre"]}» tiene {len(vs)} versión(es): no hay qué dividir')
        usados = {p.get('id') for p in m['personajes'] if p is not pm} | {g.get('id') for g in m.get('grupos') or []} | {pm['id']}
        carpetas = {p.get('carpeta') for p in m['personajes'] if p is not pm} | {pm.get('carpeta')}
        plan = []
        for v in vs:
            d = datos.get(v.get('id')) or datos.get(v.get('nombre')) or next((x for k, x in datos.items() if igual(k, v.get('nombre'))), None)
            h = None if d else _ficha_de_hoja(canal, v)
            fuente = 'datos' if d else (h['fuente'] if h else None); d = d or h or {}
            nombre = str(d.get('nombre') or '').strip() or v['nombre']
            if not d.get('nombre'): avisos.append(f'{v["nombre"]}: sin nombre propio (ni datos ni hoja) → el personaje se llama como la versión')
            otro = buscar_personaje(m, None, nombre)
            if otro is not None and otro is not pm: raise ValueError(f'«{nombre}» ya es otro personaje ({otro["id"]}); usa --datos con otro nombre')
            if any(igual(nombre, x['nombre']) for x in plan): raise ValueError(f'dos versiones darían el mismo nombre «{nombre}»; usa --datos')
            base = slug(d.get('id') or nombre); nid, k = base, 2
            while nid in usados or nid in carpetas or (R / nid).exists(): nid = f'{base}-{k}'; k += 1
            usados.add(nid); carpetas.add(nid)
            src = R / pm['carpeta'] / v['carpeta']; dst = R / nid / v['carpeta']
            plan.append({'v': v, 'nombre': nombre, 'id': nid, 'd': d, 'fuente': fuente, 'src': src, 'dst': dst})
        try:   # mover carpetas (si algo falla, se devuelven)
            for x in plan:
                if x['src'].is_dir():
                    x['dst'].parent.mkdir(parents=True, exist_ok=True); shutil.move(str(x['src']), str(x['dst'])); movidas.append(x)
                else: avisos.append(f'{x["v"]["nombre"]}: no había carpeta {x["src"].relative_to(R)}')
        except Exception:
            for x in reversed(movidas): shutil.move(str(x['dst']), str(x['src']))
            raise
        nuevos, f = [], ahora()
        for x in plan:
            v = x['v']; viejo, nuevo = f'{pm["carpeta"]}/{v["carpeta"]}/', f'{x["id"]}/{v["carpeta"]}/'
            v2 = _cambiar_rutas(v, viejo, nuevo)
            for j in sorted(x['dst'].rglob('*.json')) if x['dst'].is_dir() else []:   # fichas de cada imagen: solo rutas
                o = leer_json(j)
                if o is not None:
                    o2 = _cambiar_rutas(_cambiar_rutas(o, str(R / viejo), str(R / nuevo)), viejo, nuevo)
                    if o2 != o: escribir_json(j, o2)
            d = x['d']; alias = [a for a in dict.fromkeys([v['nombre'], f'{pm["nombre"]} – {v["nombre"]}']) if not igual(a, x['nombre'])]
            p = {'id': x['id'], 'nombre': x['nombre'], 'carpeta': x['id'], 'ids_mapa': [], 'alias': alias, 'grupo': pm['id'],
                 'nunca_cambia': _texto_lista(d.get('nunca_cambia')),
                 'altura_m': _altura(d.get('altura_m') if d.get('altura_m') not in (None, '') else d.get('altura')) or v.get('altura_m'),
                 'descripcion': _texto_lista(d.get('descripcion')) or v.get('descripcion'),
                 'versiones': [v2], 'origen': 'division',
                 'dividido_de': {'personaje': pm['id'], 'nombre': pm['nombre'], 'version': v['id'], 'carpeta_antes': viejo.rstrip('/'),
                                 'datos_de': x['fuente'], 'por': str(por).strip(), 'fecha': f}}
            for k2 in ('rol', 'edad', 'personalidad'):
                if not _vacio(d.get(k2)) and d.get(k2) not in ([], ''): p[k2] = d[k2]
            if p['altura_m'] is None: avisos.append(f'{x["nombre"]}: sin altura (no se inventa)')
            if p['nunca_cambia'] is None: avisos.append(f'{x["nombre"]}: sin «nunca cambia» (no se inventa)')
            nuevos.append(p)
            hechos.append({'id': p['id'], 'nombre': p['nombre'], 'alias': alias, 'version': v2['nombre'], 'estado': v2.get('estado'),
                           'vistas': v2.get('vistas') or {}, 'refs': v2.get('refs') or [],
                           'completado_ia': {k3: (i or {}).get('completado_ia') for k3, i in (v2.get('vistas_info') or {}).items()}})
        antes = {k: x for k, x in pm.items() if k != 'versiones'}
        g = {'id': pm['id'], 'nombre': pm['nombre'], 'alias': list(pm.get('alias') or []), 'ids_mapa': list(pm.get('ids_mapa') or []),
             'carpeta': pm.get('carpeta'), 'miembros': [{'personaje': p['id'], 'nombre': p['nombre'], 'version': p['versiones'][0]['id'],
                                                         'version_nombre': p['versiones'][0]['nombre']} for p in nuevos],
             'antes': antes, 'dividido': {'por': str(por).strip(), 'fecha': f},
             'nota': 'grupo: el nombre, alias e ids del mapa resuelven a TODOS los miembros; cada versión vieja es alias de su miembro'}
        i = m['personajes'].index(pm); m['personajes'][i:i + 1] = nuevos
        m.setdefault('grupos', []).append(g)
        vieja = R / pm['carpeta']
        if vieja.is_dir() and not any(vieja.iterdir()): vieja.rmdir()
        guardar_manifiesto(canal, m)
    return {'ok': True, 'accion': 'personajes dividir', 'grupo': {k: g[k] for k in ('id', 'nombre', 'alias', 'ids_mapa', 'miembros')},
            'personajes': hechos, 'avisos': avisos, 'llamadas_hechas': 0, 'usd': 0.0,
            'nota': 'nada se aprobó ni se borró; las imágenes se movieron con su estado y sus marcas «completado por IA»'}

def _fecha_ok(f):
    """Fecha que dio el usuario (ISO con zona, ej. 2026-10-29T16:59:00-0500); sin fecha → ahora."""
    if f in (None, ''): return ahora()
    f = str(f).strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:?\d{2}|Z)', f): raise ValueError('fecha no válida (ISO con zona, ej. 2026-10-29T16:59:00-0500)')
    return f

def _clave_version(m, pv):
    """'personaje:version' (ids, nombres o alias) → (personaje, versión) o ValueError. Sin ':' → todas las versiones del personaje (o del grupo)."""
    pq, _, vq = str(pv).partition(':')
    pares = resolver(m, pq.strip(), pq.strip())
    if not pares: raise ValueError(f'no hay personaje «{pq}»')
    if not vq.strip(): return [(p, v) for p, _v in pares for v in p.get('versiones') or []]
    out = [(p, buscar_version(p, vq.strip(), vq.strip())) for p, _v in pares]
    out = [(p, v) for p, v in out if v is not None]
    if not out: raise ValueError(f'«{pq}» no tiene la versión «{vq}»')
    return out

def aprobar(canal, por, que=None, todos=False, excepto=None, cita=None, fecha=None):
    """orden 86: aprobar versiones (el mismo campo que mira todo el taller: estado «aprobada»). Gratis, sin IA.
    que: lista 'personaje[:version]' (o el nombre de un grupo); todos=True → todas las versiones del canal.
    excepto: lista {'version': 'personaje:version', 'nota': texto} que quedan PENDIENTES y llevan la nota (p.ej. «repintar»).
    Guarda aprobado_por, fecha y la cita textual; las marcas «completado_ia» NO se borran: quedan como historia + revisado/aprobado por QUIEN.
    Una versión sin sus imágenes en disco NO se aprueba (aviso). Una ya aprobada no se toca."""
    if not str(por or '').strip(): raise ValueError('falta --aprobado (quién lo aprobó)')
    if not todos and not que: raise ValueError('falta --personaje o --todos')
    fecha = _fecha_ok(fecha); cita = str(cita or '').strip() or None
    with Candado(canal):
        m = leer_manifiesto(canal); R = raiz(canal)
        sel = [(p, v) for p in m['personajes'] for v in p.get('versiones') or []] if todos else [x for q in que for x in _clave_version(m, q)]
        exc = []
        for e in excepto or []:
            if not isinstance(e, dict) or not e.get('version'): raise ValueError('excepto: cada uno lleva «version» = personaje:version')
            for p, v in _clave_version(m, e['version']): exc.append((p, v, str(e.get('nota') or '').strip() or None))
        ids_exc = {(p['id'], v['id']) for p, v, _n in exc}
        aprobadas, ya, no, pendientes = [], [], [], []
        hecho = set()
        for p, v in sel:
            k = (p['id'], v['id'])
            if k in hecho or k in ids_exc: continue
            hecho.add(k); nom = f"{p['nombre']} – {v['nombre']}"
            if v.get('estado') == 'aprobada': ya.append(nom); continue
            vis = v.get('vistas') or {}
            faltan = [n for n, r in vis.items() if not (R / r).is_file()] if vis else ([] if refs_en_disco(canal, v) else ['imágenes'])
            if faltan: no.append({'version': nom, 'motivo': f"faltan en disco: {', '.join(faltan)}"}); continue
            rev = {'por': por, 'fecha': fecha, 'aprobado': True}
            v['estado'] = 'aprobada'; v['aprobada'] = fecha; v['aprobado_por'] = por
            v['aprobacion'] = {'por': por, 'fecha': fecha, 'cita': cita, 'registrada': ahora()}
            for n, i in (v.get('vistas_info') or {}).items():
                if isinstance(i, dict) and i.get('completado_ia'): i['completado_ia_revisado'] = rev
                fj = (R / vis[n]).with_suffix('.json') if n in vis else None
                if fj and fj.is_file():
                    d = leer_json(fj) or {}; d.update(aprobada=True, aprobado_por=por, aprobada_fecha=fecha)
                    if d.get('completado_ia'): d['completado_ia_revisado'] = rev
                    escribir_json(fj, d)
            aprobadas.append({'personaje': p['id'], 'version': v['id'], 'nombre': nom})
        for p, v, nota in exc:
            if nota:
                notas = v.setdefault('notas', [])
                if not any(x.get('texto') == nota for x in notas): notas.append({'por': por, 'fecha': fecha, 'texto': nota, 'cita': cita, 'repintar': True})
            pendientes.append({'personaje': p['id'], 'version': v['id'], 'nombre': f"{p['nombre']} – {v['nombre']}", 'estado': v.get('estado'), 'nota': nota})
        guardar_manifiesto(canal, m)
    return {'ok': True, 'accion': 'personajes aprobar', 'aprobado_por': por, 'fecha': fecha, 'cita': cita, 'aprobadas': aprobadas,
            'ya_estaban': ya, 'no_aprobadas': no, 'pendientes': pendientes, 'llamadas_hechas': 0, 'usd': 0.0}

TIPOS_FORMA = ('persona', 'objeto')   # orden 91: «objeto» = algo que alguien lleva/usa (sin cuerpo, sin vistas frente/espalda)

def entrada_dir(canal): return raiz(canal) / '_entrada'

def reemplazar_refs(canal, que, imagen, por, tipo_forma=None, nota=None, cita=None, fecha=None):
    """orden 91: la imagen que DIO el usuario pasa a ser LA referencia de una versión (genérico, gratis, sin IA).
    - imagen: nombre de archivo dentro de <canal>/personajes/_entrada/ (png/jpg/webp; se revisa por los bytes).
    - todo lo que había en <versión>/refs/ (pintado por IA o recortes) se MUEVE a <versión>/refs_reemplazadas/ y queda anotado.
    - la versión queda: origen «usuario», completado_por_IA false, sin vistas frente/espalda (si la imagen es de un objeto),
      aprobada por QUIEN con su cita y fecha; las notas «repintar» anteriores quedan resueltas."""
    if not str(por or '').strip(): raise ValueError('falta --aprobado (quién dio la imagen)')
    if tipo_forma is not None and tipo_forma not in TIPOS_FORMA: raise ValueError(f'--tipo-forma: {" | ".join(TIPOS_FORMA)}')
    if not valido_id(imagen) or imagen.startswith('.'): raise ValueError('--imagen: solo el nombre de un archivo de _entrada/')
    src = entrada_dir(canal) / imagen
    if not src.is_file(): raise ValueError(f'no está {src}')
    data = src.read_bytes(); ext = next((e for k, e in MAGIA.items() if data.startswith(k)), None)
    if ext is None: raise ValueError('la imagen no es png/jpg/webp')
    fecha = _fecha_ok(fecha); cita = str(cita or '').strip() or None; nota = str(nota or '').strip() or None
    with Candado(canal):
        m = leer_manifiesto(canal); R = raiz(canal)
        pares = _clave_version(m, que)
        if len(pares) != 1: raise ValueError('--personaje debe nombrar UNA versión (personaje:versión)')
        p, v = pares[0]
        vdir = Path((v.get('refs') or [None])[0] or f"{p.get('carpeta') or slug(p['nombre'])}/{v.get('carpeta') or slug(v['nombre'])}/refs/x").parent.parent
        rdir, odir = R / vdir / 'refs', R / vdir / 'refs_reemplazadas'
        rdir.mkdir(parents=True, exist_ok=True); odir.mkdir(parents=True, exist_ok=True)
        h = sha(data); nuevo = (vdir / 'refs' / f'{h[:16]}{ext}').as_posix()
        movidas, mapa_rutas = [], {}
        for x in sorted(rdir.iterdir()):
            if not x.is_file() or x.name == Path(nuevo).name: continue
            dst = odir / x.name
            if dst.exists(): dst = odir / f'{x.stem}_{int(time.time())}{x.suffix}'
            viejo = (vdir / 'refs' / x.name).as_posix(); hx = sha(x.read_bytes()) if x.suffix != '.json' else None
            shutil.move(str(x), str(dst)); mapa_rutas[viejo] = (vdir / 'refs_reemplazadas' / dst.name).as_posix()
            if hx: movidas.append({'antes': viejo, 'ref': mapa_rutas[viejo], 'sha256': hx, 'origen': (v.get('refs_origen') or {}).get(viejo),
                                   'motivo': f'reemplazada por la imagen que dio {por}', 'fecha': ahora()})
        for e in v.get('refs_reemplazadas') or []:   # las anotadas antes también se movieron: su ruta nueva
            if e.get('ref') in mapa_rutas: e['antes'], e['ref'] = e['ref'], mapa_rutas[e['ref']]
        ya = {e.get('ref') for e in v.get('refs_reemplazadas') or []}
        v.setdefault('refs_reemplazadas', []).extend(e for e in movidas if e['ref'] not in ya)
        (R / nuevo).write_bytes(data)
        info = {'origen': 'usuario', 'proporcionada_por': por, 'completado_por_IA': False, 'archivo_original': imagen, 'sha256': h,
                'tipo_forma': tipo_forma or v.get('tipo_forma') or 'persona', 'fecha': fecha, 'cita': cita, 'nota': nota, 'registrada': ahora()}
        escribir_json((R / nuevo).with_suffix('.json'), info)
        if v.get('vistas') or v.get('vistas_info'):
            v.setdefault('historial', []).append({'que': 'vistas reemplazadas', 'vistas': {k: mapa_rutas.get(r, r) for k, r in (v.get('vistas') or {}).items()},
                                                   'vistas_info': v.get('vistas_info'), 'fecha': ahora()})
        v.pop('vistas', None); v.pop('vistas_info', None)
        v['refs'], v['refs_sha256'], v['refs_origen'] = [nuevo], [h], {nuevo: 'usuario'}
        v['origen'] = 'usuario'; v['completado_por_IA'] = False; v['proporcionada_por'] = {'por': por, 'fecha': fecha, 'cita': cita}
        if tipo_forma: v['tipo_forma'] = tipo_forma
        for n in v.get('notas') or []:
            if n.get('repintar') and not n.get('resuelta'): n['resuelta'] = {'por': por, 'fecha': fecha, 'como': 'imagen dada por el usuario (sin repintar)'}
        if nota:
            notas = v.setdefault('notas', [])
            if not any(x.get('texto') == nota for x in notas): notas.append({'por': por, 'fecha': fecha, 'texto': nota, 'cita': cita})
            v['uso'] = nota
        v['estado'] = 'aprobada'; v['aprobada'] = fecha; v['aprobado_por'] = por
        v['aprobacion'] = {'por': por, 'fecha': fecha, 'cita': cita, 'registrada': ahora()}
        guardar_manifiesto(canal, m)
    return {'ok': True, 'accion': 'personajes reemplazar-refs', 'personaje': p['id'], 'version': v['id'], 'nombre': f"{p['nombre']} – {v['nombre']}",
            'ref_nueva': nuevo, 'tipo_forma': v.get('tipo_forma'), 'movidas_a_refs_reemplazadas': list(mapa_rutas.values()),
            'estado': v['estado'], 'aprobado_por': por, 'cita': cita, 'llamadas_hechas': 0, 'usd': 0.0}

def refs_en_disco(canal, v):
    return [raiz(canal) / r for r in (v.get('refs') or []) if (raiz(canal) / r).is_file()]

def lado_en_toma(D, toma, pid):
    """PISTA INMI (orden 80): ¿la cámara ve al personaje de FRENTE o de ESPALDA en esa toma? 'frente' | 'espalda' | None.
    Primero cubo 06 (proyecciones: el punto «frente» del cuerpo más cerca de la cámara que las caderas, la MISMA regla del cubo 07);
    si 06 no tiene los puntos, cubo 07 (lados.json: ve_frente, solo filas con lado_imagen). Sin datos → None (no se adivina)."""
    if D is None or toma in (None, ''): return None
    D = Path(D)
    for t in (leer_json(D / 'cubos' / '06' / 'proyecciones.json') or {}).get('tomas') or []:
        if str(t.get('id')) != str(toma): continue
        uv = t.get('uv') or {}; fr, ci, cd = uv.get(f'{pid}|frente'), uv.get(f'{pid}|cadera_izquierda'), uv.get(f'{pid}|cadera_derecha')
        if fr and ci and cd and len(fr) > 2 and len(ci) > 2 and len(cd) > 2:
            return 'frente' if fr[2] < (ci[2] + cd[2]) / 2 else 'espalda'
    for f in (leer_json(D / 'cubos' / '07' / 'lados.json') or {}).get('lados') or []:
        if str(f.get('toma')) == str(toma) and f.get('personaje') == pid and f.get('lado_imagen') and f.get('ve_frente') is not None:
            return 'frente' if f['ve_frente'] else 'espalda'
    return None

def imagenes_version(canal, v, lado=None, mx=3):
    """PISTA INMI (orden 80): imágenes de una versión para un cubo. Si la versión tiene el juego estándar (vistas frente/espalda):
    lado conocido → esa vista (la otra solo si hoja.vistas.refs_por_lado.adjuntar_otra_vista); lado desconocido → las vistas en orden
    «sin_lado». Sin vistas → como antes (refs en disco)."""
    if v.get('_hoja_sello'): return [Path(v['_hoja_sello'])]   # t480u: la hoja aprobada del sello manda sobre la foto del cliente
    R = raiz(canal); vis = {k: R / r for k, r in (v.get('vistas') or {}).items() if r and (R / r).is_file()}
    if not vis: return refs_en_disco(canal, v)[:mx]
    rl = cfg()['hoja']['vistas']['refs_por_lado']
    if lado in vis:
        orden = [lado] + ([k for k in rl['sin_lado'] if k != lado] if rl['adjuntar_otra_vista'] else [])
    else: orden = list(rl['sin_lado'])
    return [vis[k] for k in orden if k in vis][:mx]

def estado_version(canal, v, aj):
    if v is None: return 'falta'
    if v.get('_hoja_sello'): return 'cargada'   # t480u: hoja APROBADA del sello (cubo_fijo, sha verificado) = versión cargada y aprobada
    if not refs_en_disco(canal, v): return 'sin_imagenes'
    if aj.get('solo_versiones_aprobadas', True) and v.get('estado') != 'aprobada': return 'sin_aprobar'
    return 'cargada'

# ---------------- guarda de texto (figuras y ropa puesta) ----------------
def _palabras(lst): return sorted({sin_tildes(w).lower().strip() for w in lst if str(w).strip()}, key=len, reverse=True)
def _rx(lst): return re.compile(r'(?<![\w])(' + '|'.join(re.escape(w) for w in _palabras(lst)) + r')(?![\w])', re.I) if lst else None
_CACHE = {}
def cfg_guarda():
    """t366s1473 (3-nov-2026): reglas de contexto de la guarda (llamadas_config.json → guarda_personajes). Sin archivo o sin sección → {}."""
    try: return json.loads(LLAMADAS_CONFIG.read_text(encoding='utf-8')).get('guarda_personajes') or {}
    except Exception: return {}

def _alt(lst): return '|'.join(re.escape(w) for w in _palabras(lst))

def _rx_mod(g):
    """Modificador de lugar/objeto/medida: «child bed», «child's bedroom», «kid-height», «cama de niño», «altura de un niño».
    Devuelve [(regex, grupo_del_modificador)]: solo se tapa la palabra del modificador, el resto de la frase se sigue revisando."""
    mods, out = g.get('modificadores') or [], []
    if not mods: return out
    M = _alt(mods)
    if g.get('sustantivos_contexto'):
        # entre el modificador y el sustantivo pueden ir hasta N adjetivos («children's rectangular wooden garden table»), pero NO
        # verbos en -ing, preposiciones, artículos ni partes del cuerpo («a child's hand on the table», «a child near the bed» siguen siendo persona)
        n_e = int(g.get('max_palabras_entre', 0) or 0); ne = g.get('no_entre') or []
        entre = (r'(?:(?!(?:' + _alt(ne) + r')(?![\w-]))(?![\w-]*ing(?![\w-]))[\w-]+\s+){0,' + str(n_e) + '}') if n_e > 0 else ''
        out.append((re.compile(r"(?<![\w])(" + M + r")(?:'s|s'|’s)?(?:\s+|-)" + entre + r"(?:" + _alt(g['sustantivos_contexto']) + r")(?![\w])", re.I), 1))
    if g.get('sustantivos_contexto_es') and g.get('conectores_es'):
        art = r'(?:(?:' + _alt(g.get('articulos') or []) + r')\s+)?' if g.get('articulos') else ''
        out.append((re.compile(r'(?<![\w])(?:' + _alt(g['sustantivos_contexto_es']) + r')(?:\s+(?:' + _alt(g['conectores_es']) + r")\s+|\s+d['’])" + art
                               + r'(?:(?:los|las|de|of)\s+)?(' + M + r')(?![\w])', re.I), 1))
    return out

# t460u (Ricardo): «uniform matte gray plastic» / «color uniforme» describen material parejo, NO un uniforme puesto.
# Solo se tapa cuando la palabra va pegada a un término de material/color/acabado/medida; «wearing a uniform», «school uniform» siguen golpeando.
_UNIF_W = (r'matte|mate|glossy|brillante|satin|satinado|soft|suave|smooth|liso|flat|plano|even|solid|solido|light|lighting|luz|'
           r'colou?rs?|tone|tono|texture|textura|finish|acabado|surface|superficie|gr[ae]y|gris|white|blanco|black|negro|[a-z]+-(?:gr[ae]y|colou?red|toned)|'
           r'plastic|plastico|metal|metalico|wood|madera|paint|pintura|spacing|espaciado|size|tamano|height|altura|thickness|grosor|width|ancho|pattern|patron|layer|capa|coat|coating|'
           r'fabric|tela|material|material(?:es)?|density|densidad|distribution|distribucion|thick|grueso|thin|delgado')
_UNIF_ADJ = re.compile(r'(?<![\w])(uniformes?|uniform)(?=\s+(?:and\s+|y\s+)?(?:' + _UNIF_W + r')(?![\w]))', re.I)
_UNIF_POST = re.compile(r'(?<![\w])(?:colou?r|tono|textura|acabado|grosor|tamano|altura|material|plastico|metal)\s+(?:de\s+)?(uniformes?)(?![\w])', re.I)

def _tapa_unif(s):
    for rx in (_UNIF_ADJ, _UNIF_POST):
        s = rx.sub(lambda m: m.group(0)[:m.start(1)-m.start(0)] + ' ' * (m.end(1)-m.start(1)) + m.group(0)[m.end(1)-m.start(0):], s)
    return s

def enmascarar(s):
    """Tapa con espacios (mismo largo) las palabras de persona usadas como MODIFICADOR (no son una figura a pintar)."""
    s = _tapa_unif(s)   # t460u: «uniform/uniforme» como ADJETIVO (color/material parejo) no es ropa
    for rx, gi in _rxs()['mod']:
        s = rx.sub(lambda m: m.group(0)[:m.start(gi) - m.start(0)] + ' ' * (m.end(gi) - m.start(gi)) + m.group(0)[m.end(gi) - m.start(0):], s)
    return s

def nombres_catalogo(mp):
    """Nombres e ids de personajes del catálogo del capítulo (mapa del paso 00). Genérico: salen de los datos, no del código."""
    g = cfg_guarda()
    if mp is None or not g.get('usar_catalogo', True): return []
    n_min = int(g.get('min_letras_nombre') or 3); out = set()
    for pid, p in (mp or {}).items():
        for v in [pid, (p or {}).get('nombre')] + list(((p or {}).get('formas') or {}).keys()):
            v = sin_tildes(str(v or '')).strip().lower()
            if len(v) >= n_min: out.add(v)
    return sorted(out, key=len, reverse=True)

def _rx_nombres(nombres):
    return re.compile(r'(?<![\w-])(' + '|'.join(re.escape(n) for n in nombres) + r')(?![\w-])', re.I) if nombres else None

def _rxs():
    c = cfg(); g = cfg_guarda(); k = json.dumps([c.get('palabras_figura'), c.get('palabras_prenda'), c.get('negaciones'), g], sort_keys=True)
    if _CACHE.get('k') != k:
        _CACHE.update(mod=_rx_mod(g))
        _CACHE.update(k=k, fig=_rx(c.get('palabras_figura') or []), pre=_rx(c.get('palabras_prenda') or []),
                      neg=re.compile(r'^\s*(?:[A-Za-z ]{0,20}:\s*)?(' + '|'.join(re.escape(w) for w in _palabras(c.get('negaciones') or [])) + r')\b', re.I),
                      negw=re.compile(r'(?<![\w])(' + '|'.join(re.escape(w) for w in _palabras(c.get('negaciones') or [])) + r')(?![\w])', re.I))
    return _CACHE

def frases(txt):
    return [f for f in re.split(r'(?<=[.;!?])\s+|\n+', str(txt or '')) if f.strip()]

def _negado(s, ini):
    """¿Hay una negación en las N palabras antes de la posición ini (misma frase)? N = ventana_negacion_palabras."""
    n = int(cfg().get('ventana_negacion_palabras') or 5)
    antes = ' '.join(re.findall(r'[\w-]+', s[:ini])[-n:])
    return bool(antes) and _rxs()['negw'].search(antes) is not None

def revisar_frase(f, nombres=None):
    """Golpes de UNA frase: figura (palabras de persona), prenda (ropa puesta) y personaje (nombre/id del catálogo).
    t366s1473: las palabras de persona usadas como modificador de lugar/objeto/medida no cuentan (enmascarar)."""
    R = _rxs(); s = sin_tildes(f).lower()
    if R['neg'].match(s) or s.strip().startswith('avoid'): return {}
    out = {}; sm = enmascarar(s)
    for k in ('fig', 'pre'):
        if R[k]:
            h = sorted({m.group(1) for m in R[k].finditer(sm) if not _negado(s, m.start())})
            if h: out['figura' if k == 'fig' else 'prenda'] = h
    rn = _rx_nombres(nombres)
    if rn:
        h = sorted({m.group(1) for m in rn.finditer(s) if not _negado(s, m.start())})
        if h: out['personaje'] = h
    return out

def _etiqueta(f, clave):
    e = _palabras(cfg().get(clave) or [])
    return bool(e) and re.match(r'^\s*(' + '|'.join(re.escape(w) for w in e) + r')\s*:', sin_tildes(f).lower()) is not None

def guarda_texto(txt, nombres=None):
    """Revisa un pedido de imagen. Devuelve {'golpes': [{frase, figura, prenda}], 'en_tema': bool}. en_tema = lo que se PIDE pintar
    (la primera frase que no es de estilo, o una frase con etiqueta de tema como «SUBJECT:») describe una figura o ropa puesta.
    Las frases de estilo y de negación («No people…», «Avoid:») no cuentan. Etiquetas y palabras: personajes_config.json."""
    fs = [f for f in frases(txt) if not _etiqueta(f, 'etiquetas_estilo')]; golpes = []; en_tema = False
    for i, f in enumerate(fs):
        r = revisar_frase(f, nombres)
        if r:
            golpes.append({'frase': f.strip()[:200], **r})
            if i == 0 or _etiqueta(f, 'etiquetas_tema'): en_tema = True
    return {'golpes': golpes, 'en_tema': en_tema}

def partir(txt, nombres=None):
    """Separa un pedido MEZCLADO: deja solo las frases que describen objetos (quita las de figura o ropa puesta). GRATIS, sin inventar."""
    queda, quitadas = [], []
    for f in frases(txt):
        (quitadas if (revisar_frase(f, nombres) and not _etiqueta(f, 'etiquetas_estilo')) else queda).append(f.strip())
    return ' '.join(queda), quitadas

def fichas(s):
    v = set(sin_tildes(x).lower() for x in cfg().get('vacias') or [])
    return {t for t in re.split(r'[^a-z0-9]+', sin_tildes(s).lower()) if len(t) >= 4 and t not in v}

def vincular(oid, nombre, mp):
    """Versiones del mapa cuyo nombre comparte palabras con el objeto (p. ej. un «objeto» que es la ropa de una versión). Genérico."""
    ft = fichas(f'{oid} {nombre or ""}'); out = []
    for pid, p in (mp or {}).items():
        for fid, f in p['formas'].items():
            com = ft & fichas(f.get('nombre') or '')
            if com: out.append({'personaje_id': pid, 'personaje': p['nombre'], 'forma_id': fid, 'version': f.get('nombre') or fid, 'palabras': sorted(com)})
    return out

def revisar_pedido(oid, texto, mp=None, nombre=None):
    """Guarda única para 4a5/4b2/4c2 (y cubos siguientes). Devuelve None (pasa) o {'accion': 'bloquear'|'partir', 'texto', 'motivo', …}."""
    nombres = nombres_catalogo(mp)   # t366s1473: personajes REALES del catálogo (nombre/id/forma) también cuentan
    g = guarda_texto(texto, nombres)
    if not g['golpes']: return None
    vin = vincular(oid, nombre, mp) if any('prenda' in x for x in g['golpes']) else []
    if g['en_tema']:
        mot = ('describe ropa puesta de un personaje' if any('prenda' in x for x in g['golpes'])
               else ('nombra al personaje «' + next(x['personaje'][0] for x in g['golpes'] if 'personaje' in x) + '» del catálogo')
               if any('personaje' in x for x in g['golpes']) else 'describe una persona o figura')
        if vin: mot += ' → es la versión «' + vin[0]['version'] + '» de ' + vin[0]['personaje'] + ' (va en Cargar personajes)'
        return {'accion': 'bloquear', 'motivo': f'NO se pinta: {mot}. Los personajes nunca se generan; salen de sus imágenes cargadas.',
                'golpes': g['golpes'], 'vinculo': vin}
    nuevo, quit = partir(texto, nombres)
    if len(nuevo) < 40:
        return {'accion': 'bloquear', 'motivo': 'NO se pinta: casi todo el pedido describe una figura o ropa puesta.', 'golpes': g['golpes'], 'vinculo': vin}
    return {'accion': 'partir', 'texto': nuevo, 'quitadas': quit, 'golpes': g['golpes'], 'vinculo': vin,
            'motivo': f'objeto MEZCLADO: se pinta solo la parte que es objeto (se quitaron {len(quit)} frase(s) de figura o ropa puesta)'}

# ---------------- marcar «no usar» (no borra nada) ----------------
def no_usar(D, carpeta_rel):
    return {x.get('id'): x for x in ((leer_json(Path(D) / carpeta_rel / 'NO_USAR.json') or {}).get('items') or []) if isinstance(x, dict)}

def marcar_no_usar(D, carpeta_rel, ids, motivo, quien):
    f = Path(D) / carpeta_rel / 'NO_USAR.json'; d = leer_json(f) or {'nota': 'Imágenes marcadas «no usar». NO se borran; ningún cubo las usa como referencia.', 'items': []}
    ya = {x.get('id') for x in d['items']}
    for i in ids:
        if i not in ya: d['items'].append({'id': i, 'archivo': f'{i}.png', 'motivo': motivo, 'marcado': ahora(), 'por': quien})
    escribir_json(f, d); return d

# ---------------- relleno (orden 88) ----------------
# Personajes del mapa del capítulo SIN hoja cargada (ni personaje ni grupo del canal) y que el paso 00 marca como NUEVOS de este
# capítulo (catalogo_oficial.personajes[].en_canal = «nuevo»): el cubo los crea solo, marcados. Uno «reutilizado» sin hoja sigue FALTA.
#   relleno  → figura secundaria de ESTE capítulo: descripción genérica sacada del guion y del paso 00, en el estilo del canal,
#              pendiente de revisión; sin imagen de referencia (no se paga nada); el 01 planifica con la descripción.
#   solo_voz → solo se oye (nunca en cuadro): sin imagen ni descripción visual.
# Se guardan en <capítulo>/personajes_relleno.json: NO pasan a otros capítulos (salvo que una persona lo apruebe y lo cargue
# como personaje del canal). Nunca pisa lo que ya está (descripciones revisadas a mano quedan).
ESQUEMA_RELLENO = 'myia-relleno-capitulo/1'
_MARCAS = re.compile(r'\s*\((?:explicito|explícito|implicito|implícito|heredado|desconocido|inferido)[^)]*\)', re.I)

def relleno_f(D): return Path(D) / 'personajes_relleno.json'

def _guion_capitulo(D):
    p = Path(D) / 'pedidos'
    for f in sorted(p.glob('*.txt')) if p.is_dir() else []:
        mm = re.search(r'=== GUION_COMPLETO ===\n(.*?)\n=== FIN GUION ===', f.read_text(encoding='utf-8', errors='replace'), re.S)
        if mm: return mm.group(1)
    return ''

def _citas_guion(guion, nombre, mx=3):
    """Frases del guion donde aparece el personaje (acción o diálogo). Sin red."""
    ls = [x.strip() for x in str(guion or '').splitlines()]; out = []
    partes = [sin_tildes(z).lower().strip() for z in re.split(r'\s*/\s*', str(nombre)) if z.strip()]
    rx = re.compile(r'(?<![\w])(' + '|'.join(re.escape(z) for z in partes) + r')(?![\w])') if partes else None
    for i, x in enumerate(ls):
        if not x or rx is None: continue
        if x.endswith(':') and any(slug(x[:-1]) == slug(z) for z in partes):
            j = i + 1
            while j < len(ls) and not ls[j]: j += 1
            if j < len(ls): out.append(f'dice: {ls[j]}')
            continue
        elif rx.search(sin_tildes(x).lower()): out.append(x)
    vistos = []
    for x in out:
        if not any(x in y or y in x for y in vistos): vistos.append(x)
    return vistos[:mx]

def tipo_relleno(nombre, estados, presencias=None):
    """'solo_voz' si el paso 00 lo pone SOLO como voz en todas sus escenas (base.json escenas[].personajes[].presencia), o si el nombre
    o el paso 00 dicen que solo se oye; si no, 'relleno'. Palabras en personajes_config.json → relleno."""
    if presencias and set(presencias) <= {'solo_voz'}: return 'solo_voz'
    C = cfg().get('relleno') or {}
    nm = sin_tildes(nombre).lower()
    if any(re.search(r'(?<![\w])' + re.escape(sin_tildes(w).lower()) + r'(?![\w])', nm) for w in C.get('solo_voz_nombre') or []): return 'solo_voz'
    t = sin_tildes(json.dumps(estados or [], ensure_ascii=False)).lower()
    return 'solo_voz' if any(sin_tildes(w).lower() in t for w in C.get('solo_voz_texto') or []) else 'relleno'

def _limpio(lst):
    out = []
    for x in lst:
        y = _MARCAS.sub('', str(x or '')).strip(' .;')
        if y and not _vacio(y) and y not in out: out.append(y)
    return out

def _estilo_canal(canal):
    try:
        import estilo_taller as ET
        e = ET.resolver(ET.canal_datos(canal)); return (e or {}).get('nombre')
    except Exception: return None

def descripcion_relleno(nombre, tipo, estados, citas, estilo):
    """Descripción genérica (texto del guion + paso 00 + estilo del canal). La IA no interviene; queda pendiente de revisión."""
    if tipo == 'solo_voz':
        return f'{nombre}: SOLO VOZ en este capítulo (no se ve en cuadro; sin imagen).' + (f' En el guion: «{citas[0]}».' if citas else '')
    an = _limpio([a for st in estados or [] for mo in ('inicio', 'fin') for a in ((st.get(mo) or {}).get('animo') or [])])
    ro = _limpio([a for st in estados or [] for mo in ('inicio', 'fin') for a in ((st.get(mo) or {}).get('ropa') or [])])
    t = [f'{nombre}: personaje de RELLENO de este capítulo (figura secundaria, no es un personaje cargado del canal).']
    if citas: t.append('En el guion: ' + ' / '.join(f'«{c}»' for c in citas) + '.')
    if an: t.append('Actitud: ' + '; '.join(an[:3]) + '.')
    t.append(('Ropa: ' + '; '.join(ro[:2]) + '. ' if ro else '') + 'Lo que el guion no describe se diseña genérico y discreto, sin parecerse a ningún personaje principal.')
    if estilo: t.append(f'Estilo del canal: {estilo}.')
    return ' '.join(t)

def relleno_capitulo(canal, D, escribir=True):
    """{pid: ficha de relleno} del capítulo. Crea (solo, gratis) las fichas que falten para los personajes del mapa sin hoja; no pisa nada."""
    if not D: return {}
    D = Path(D); f = relleno_f(D); doc = leer_json(f) or {}; lista = dict(doc.get('personajes') or {})
    m = leer_manifiesto(canal); mp = mapa(D); nuevos = []
    base = leer_json(D / 'respuestas' / 'base.json') or {}
    en_canal = {p.get('id'): p.get('en_canal') for p in (base.get('catalogo_oficial') or {}).get('personajes') or [] if isinstance(p, dict)}
    pres = {}
    for e in base.get('escenas') or []:
        for x in (e.get('personajes') or []) if isinstance(e, dict) else []:
            if isinstance(x, dict) and x.get('personaje_id'): pres.setdefault(x['personaje_id'], []).append(x.get('presencia'))
    pj = {p.get('personaje_id'): p for p in (leer_json(D / 'respuestas' / 'personajes.json') or {}).get('personajes') or [] if isinstance(p, dict)}
    guion, estilo = None, None
    for pid, p in mp.items():
        if pid in lista or not any(fo['escenas'] for fo in p['formas'].values()): continue
        if buscar_personaje(m, pid, p['nombre']) is not None or buscar_grupo(m, pid, p['nombre']) is not None: continue
        if en_canal.get(pid) != 'nuevo': continue   # solo los NUEVOS de este capítulo; uno del canal («reutilizado») sin hoja sigue siendo FALTA
        if guion is None: guion, estilo = _guion_capitulo(D), _estilo_canal(canal)
        sts = (pj.get(pid) or {}).get('estados') or []
        tipo = tipo_relleno(p['nombre'], sts, pres.get(pid)); citas = _citas_guion(guion, p['nombre'])
        for c in (str(t.get('cita_guion') or '').strip() for t in (pj.get(pid) or {}).get('tramos') or [] if isinstance(t, dict)):
            k = sin_tildes(c).lower().strip(' —-«»".')
            if c and not any(k in sin_tildes(x).lower() or sin_tildes(x).lower().strip(' —-«»".') in sin_tildes(c).lower() for x in citas): citas.append(c)
        lista[pid] = {'id': pid, 'nombre': p['nombre'], 'tipo': tipo, 'capitulo': D.name,
                      'escenas': sorted({e for fo in p['formas'].values() for e, _ in fo['escenas']}, key=lambda x: (len(x), x)),
                      'formas': sorted(p['formas']), 'descripcion': descripcion_relleno(p['nombre'], tipo, sts, citas[:3], estilo),
                      'imagen': None, 'estado': 'pendiente_revision', 'reusar_en_otros_capitulos': False,
                      'origen': 'creado por el cubo (orden 88): guion + paso 00 + estilo del canal, sin IA, US$0', 'creado': ahora()}
        nuevos.append(pid)
    if nuevos and escribir:
        with Candado(canal):
            doc2 = leer_json(f) or {}; actual = dict(doc2.get('personajes') or {})
            for pid in nuevos: actual.setdefault(pid, lista[pid])
            escribir_json(f, {'esquema': ESQUEMA_RELLENO, 'canal': canal, 'capitulo': D.name, 'actualizado': ahora(),
                              'regla': 'Relleno y solo voz de ESTE capítulo. No se reutilizan en otros capítulos salvo aprobación. '
                                       'Descripciones pendientes de revisión de una persona.', 'personajes': actual})
            lista = actual
    return lista

def relleno_cambiar(canal, D, quien, tipo=None, por=None, descripcion=None, aprobar=False):
    """Una persona corrige un relleno: tipo (relleno|solo_voz), descripción, o lo marca revisado/aprobado. Solo este capítulo."""
    if not D: raise ValueError('falta --capitulo')
    if not str(por or '').strip(): raise ValueError('falta --aprobado (quién lo decidió)')
    if tipo and tipo not in ('relleno', 'solo_voz'): raise ValueError('--tipo debe ser relleno o solo_voz')
    relleno_capitulo(canal, D)
    with Candado(canal):
        f = relleno_f(D); doc = leer_json(f) or {}; ps = doc.get('personajes') or {}
        x = ps.get(quien) or next((y for y in ps.values() if igual(y.get('nombre'), quien)), None)
        if x is None: raise ValueError(f'«{quien}» no es relleno de este capítulo')
        if tipo: x['tipo'] = tipo
        if descripcion: x['descripcion'] = str(descripcion).strip()
        if aprobar: x['estado'] = 'aprobado'
        x.setdefault('cambios', []).append({'por': str(por).strip(), 'fecha': ahora(), 'tipo': tipo, 'descripcion': bool(descripcion), 'aprobado': bool(aprobar)})
        doc['actualizado'] = ahora(); escribir_json(f, doc)
    return {'ok': True, 'accion': 'personajes relleno', 'personaje': x}

# ---------------- precio ----------------
def precio_ref(canal):
    try:
        import estilo_taller as ET
        I = ET.imagen_canal(ET.canal_datos(canal)); return float(I['usd_referencia_extra']), float(I['usd_por_imagen']), I.get('fuente_precio')
    except Exception as e:
        return None, None, f'sin precio del canal ({type(e).__name__})'

# ---------------- revisar (lista de avisos) ----------------
def revisar(canal, D=None):
    m = leer_manifiesto(canal); aj = ajustes(m); mx = int(aj['max_imagenes_por_version'])
    dup, vistos, sin_img, demasiadas = [], {}, [], []
    for p in m['personajes']:
        for v in p.get('versiones') or []:
            rs = refs_en_disco(canal, v)
            if not rs: sin_img.append({'personaje': p['nombre'], 'version': v['nombre']})
            if len(rs) > mx: demasiadas.append({'personaje': p['nombre'], 'version': v['nombre'], 'imagenes': len(rs), 'se_usan': mx})
            for r in rs: vistos.setdefault(sha(r.read_bytes()), []).append({'personaje': p['nombre'], 'version': v['nombre'], 'archivo': r.name})
    for h, l in vistos.items():
        if len({(x['personaje'], x['version']) for x in l}) > 1: dup.append({'sha256': h[:12], 'en': l})
    mp = mapa(D) if D else {}
    ref, img, fuente = precio_ref(canal)
    rel = relleno_capitulo(canal, D) if D else {}   # orden 88
    necesarias = []
    for pid, p in mp.items():
        pm = buscar_personaje(m, pid, p['nombre'])
        g = buscar_grupo(m, pid, p['nombre']) if pm is None else None   # orden 85: un grupo pide a TODOS sus miembros
        x = rel.get(pid) if pm is None and g is None else None
        for fid, f in p['formas'].items():
            if not f['escenas']: continue
            if x:   # orden 88: relleno / solo voz del capítulo → no es «falta»; no lleva imagen ni costo extra
                necesarias.append({'personaje': p['nombre'], 'personaje_id': pid, 'version': f.get('nombre') or fid, 'forma_id': fid,
                                   'escenas': sorted({e for e, _ in f['escenas']}, key=lambda y: (len(y), y)), 'estado': x['tipo'], 'imagenes': 0,
                                   'repetida': False, 'relleno': {'descripcion': x['descripcion'], 'estado': x['estado']},
                                   **({'usd_extra_por_imagen': 0.0, 'usd_extra_si_se_aprueba': 0.0} if ref is not None else {})})
                continue
            pares = miembros_grupo(m, g) if g else [(pm, buscar_version(pm, fid, f.get('nombre')))]
            for pmx, v in pares:
                est = estado_version(canal, v, aj)
                n = min(mx, len(refs_en_disco(canal, v))) if v else 0
                fila_si = round(ref * n, 4) if (ref is not None and est in ('cargada', 'sin_aprobar')) else 0.0
                fila = {'personaje': pmx['nombre'] if g else p['nombre'], 'personaje_id': pmx['id'] if g else pid,
                        'version': (v or {}).get('nombre') or f.get('nombre') or fid, 'forma_id': fid,
                        'escenas': sorted({e for e, _ in f['escenas']}, key=lambda x: (len(x), x)), 'estado': est, 'imagenes': n,
                        'repetida': bool(v) and any(any(x['personaje'] == pmx['nombre'] and x['version'] == v['nombre'] for x in d['en']) for d in dup)}
                if g: fila['grupo'] = {'id': g['id'], 'nombre': g['nombre'], 'id_mapa': pid}
                if ref is not None:
                    fila['usd_extra_por_imagen'] = round(ref * n, 4) if est == 'cargada' else 0.0
                    fila['usd_extra_si_se_aprueba'] = fila_si
                necesarias.append(fila)
    TXT = {'falta': 'FALTA: no hay versión cargada', 'sin_imagenes': 'SIN IMÁGENES', 'sin_aprobar': 'SIN APROBAR', 'cargada': 'cargada'}
    avisos = []
    for d in dup:
        avisos.append('REPETIDA: la misma imagen está en ' + ' y '.join(sorted({f"{x['personaje']} – {x['version']}" for x in d['en']})) + '. Sube una imagen distinta para cada versión.')
    for x in sin_img: avisos.append(f"SIN IMÁGENES: {x['personaje']} – {x['version']}.")
    for x in demasiadas: avisos.append(f"{x['personaje']} – {x['version']}: tiene {x['imagenes']} imágenes; se usan las primeras {x['se_usan']}.")
    for x in necesarias:
        if x['estado'] not in ('cargada', 'relleno', 'solo_voz'):
            avisos.append(f"Escena(s) {', '.join(x['escenas'])} necesita(n) {x['personaje']} – {x['version']}: {TXT[x['estado']]} → esa imagen o toma se DETIENE (no se inventa).")
    obj = objetos_que_son_personaje(D, mp) if D else []
    for o in obj:
        avisos.append(f"OBJETO que es personaje: {o['id']} ({o['cubo']}) → {o['accion_txt']}" + (f". Va con la versión {', '.join(o['version_del_mapa'])}." if o['version_del_mapa'] else ''))
    usd = sum(x.get('usd_extra_por_imagen') or 0 for x in necesarias)
    return {'ok': True, 'accion': 'personajes revisar', 'canal': canal, 'carpeta': str(raiz(canal)), 'ajustes': aj,
            'personajes': [{'nombre': p['nombre'], 'versiones': [{'nombre': v['nombre'], 'estado': v.get('estado'), 'imagenes': len(refs_en_disco(canal, v)),
                                                                'origen': v.get('origen')} for v in p.get('versiones') or []]} for p in m['personajes']],
            'grupos': [{'id': g['id'], 'nombre': g['nombre'], 'ids_mapa': g.get('ids_mapa') or [], 'miembros': [x['nombre'] for x in g.get('miembros') or []]}
                       for g in m.get('grupos') or []],
            'relleno_del_capitulo': [{'id': k, 'nombre': v['nombre'], 'tipo': v['tipo'], 'escenas': v['escenas'], 'estado': v['estado']} for k, v in rel.items()],
            'objetos_que_son_personaje': obj, 'repetidas': dup, 'sin_imagenes': sin_img, 'demasiadas': demasiadas, 'necesarias_del_mapa': necesarias,
            'cuenta': {k: sum(1 for x in necesarias if x['estado'] == k) for k in ('cargada', 'sin_aprobar', 'sin_imagenes', 'falta')},
            'cotizacion': {'usd_referencia_extra': ref, 'usd_por_imagen': img, 'fuente': fuente,
                           'explicacion': 'Cada imagen del personaje que se adjunta suma usd_referencia_extra a CADA imagen o toma donde sale esa versión. Cargar personajes cuesta US$0.',
                           'usd_extra_si_cada_version_sale_en_una_imagen': round(usd, 4),
                           'usd_extra_si_se_aprueba_lo_cargado': round(sum(x.get('usd_extra_si_se_aprueba') or 0 for x in necesarias), 4)},
            'avisos': avisos, 'llamadas_hechas': 0, 'usd': 0.0}

# ---------------- prellenar desde el estudio (solo lectura, sin inventar) ----------------
def _vacio(x): return x is None or str(x).strip().lower() in set(cfg()['estudio'].get('vacios') or [])

def prellenar(canal, D, db=None, datos=None):
    E = cfg()['estudio']; db = Path(db or E['db']); datos = Path(datos or E['datos'])
    mp = mapa(D) if D else {}
    if not mp: return {'agregadas': [], 'aviso': 'sin mapa del paso 00: no se prellena nada'}
    if not db.is_file(): return {'agregadas': [], 'aviso': 'no está la base del estudio: no se prellena nada'}
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True); con.row_factory = sqlite3.Row
    try: filas = {r['id']: dict(r) for r in con.execute('select id, name, formas, images, deleted from characters')}
    finally: con.close()
    agregadas = []
    with Candado(canal):
        m = leer_manifiesto(canal); mx = int(ajustes(m)['max_imagenes_por_version'])
        for pid, p in mp.items():
            fila = filas.get(pid)
            if not fila or fila.get('deleted'): continue
            try: formas = json.loads(fila.get('formas') or '[]')
            except Exception: formas = []
            for fo in formas:
                fid = fo.get('id') or fo.get('forma_id'); nombre = '' if _vacio(fo.get('nombre')) else str(fo.get('nombre')).strip()   # «falta» no es un nombre
                rutas = [datos / r for r in (fo.get('imagenes_referencia') or []) if isinstance(r, str) and (datos / r).is_file()]
                if not fid or not nombre or not rutas: continue
                pm = buscar_personaje(m, pid, p['nombre'])
                if pm is None and buscar_grupo(m, pid, p['nombre']): break   # orden 85: ya se dividió; no se vuelve a crear
                if pm is None:
                    pm = {'id': pid, 'nombre': p['nombre'], 'carpeta': slug(p['nombre']), 'ids_mapa': [pid], 'nunca_cambia': None, 'versiones': [], 'origen': 'estudio'}
                    m['personajes'].append(pm)
                if buscar_version(pm, fid, nombre) is not None: continue   # nunca se pisa lo que ya está (del usuario o de antes)
                vs = slug(nombre); dst = raiz(canal) / pm['carpeta'] / vs / 'refs'; dst.mkdir(parents=True, exist_ok=True); refs = []
                for r in rutas[:mx]:
                    f = dst / (sha(r.read_bytes())[:16] + r.suffix.lower()); shutil.copy2(r, f) if not f.exists() else None
                    refs.append(str(f.relative_to(raiz(canal))))
                v = {'id': vs, 'nombre': nombre, 'forma_id': fid, 'ids_mapa': [fid], 'carpeta': vs,
                     'descripcion': None if _vacio(fo.get('descripcion')) else fo.get('descripcion'),
                     'altura_m': None if _vacio(fo.get('altura_m')) else fo.get('altura_m'),
                     'nunca_cambia': None if _vacio(fo.get('rasgos_que_no_cambian')) else fo.get('rasgos_que_no_cambian'),
                     'refs': refs, 'refs_sha256': [sha((raiz(canal) / r).read_bytes()) for r in refs], 'estado': 'pendiente', 'origen': 'estudio',
                     'desde': None, 'hasta': None, 'creada': ahora()}
                pm['versiones'].append(v); agregadas.append(f"{pm['nombre']} – {nombre}")
        if agregadas: guardar_manifiesto(canal, m)
    return {'agregadas': agregadas, 'aviso': (f'se copiaron {len(agregadas)} versión(es) del estudio, quedan SIN APROBAR hasta que las apruebes' if agregadas else 'nada nuevo en el estudio')}

# ---------------- formulario: ficha + trozos + guardar ----------------
def _sesion(canal, s):
    if not valido_id(s): raise ValueError('sesión no válida')
    return raiz(canal) / '_subidas' / s

def ficha(canal, s, datos):
    d = json.loads(b64(datos).decode('utf-8'))
    for k in ('personaje', 'version'):
        if not str(d.get(k) or '').strip(): raise ValueError(f'falta «{k}»')
    escribir_json(_sesion(canal, s) / 'ficha.json', d); return {'ok': True, 'sesion': s}

def subir(canal, s, nombre, parte, de, datos):
    C = cfg()['subida']
    if not valido_id(nombre) or Path(nombre).suffix.lower() not in C['extensiones']: raise ValueError('nombre de imagen no válido (png, jpg, webp)')
    if not (1 <= parte <= de <= C['max_trozos']): raise ValueError('trozo fuera de rango')
    f = _sesion(canal, s) / 'trozos' / f'{nombre}.{parte:04d}.{de:04d}'; f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b64(datos)); return {'ok': True, 'parte': parte, 'de': de}

def guardar(canal, s, capitulo=None):
    C = cfg(); ses = _sesion(canal, s); fi = leer_json(ses / 'ficha.json')
    if not fi: raise ValueError('la sesión no tiene ficha')
    imgs, avisos = {}, []
    for t in sorted((ses / 'trozos').glob('*')) if (ses / 'trozos').is_dir() else []:
        nom, parte, de = t.name.rsplit('.', 2); imgs.setdefault(nom, {'de': int(de), 'partes': {}})['partes'][int(parte)] = t
    with Candado(canal):
        m = leer_manifiesto(canal); aj = ajustes(m); mx = int(aj['max_imagenes_por_version'])
        pn = str(fi['personaje']).strip(); vn = str(fi['version']).strip()
        pm = buscar_personaje(m, None, pn)
        if pm is None:
            pm = {'id': slug(pn), 'nombre': pn, 'carpeta': slug(pn), 'ids_mapa': [], 'nunca_cambia': None, 'versiones': [], 'origen': 'usuario'}; m['personajes'].append(pm)
        if fi.get('nunca_cambia'): pm['nunca_cambia'] = fi['nunca_cambia']
        v = buscar_version(pm, None, vn)
        if v is None:
            v = {'id': slug(vn), 'nombre': vn, 'forma_id': None, 'ids_mapa': [], 'carpeta': slug(vn), 'refs': [], 'refs_sha256': [], 'estado': 'pendiente',
                 'origen': 'usuario', 'desde': None, 'hasta': None, 'creada': ahora()}; pm['versiones'].append(v)
        for k in ('descripcion', 'altura_m'):
            if fi.get(k) not in (None, ''): v[k] = fi[k]
        if fi.get('forma_mapa'): v['ids_mapa'] = sorted(set(v.get('ids_mapa') or []) | {str(fi['forma_mapa'])})
        if str(fi.get('aprobada') or '').strip().lower() in ('si', 'sí', 'yes', 'true', '1'): v['estado'] = 'aprobada'; v['aprobada'] = ahora()
        dst = raiz(canal) / pm['carpeta'] / v['carpeta'] / 'refs'; dst.mkdir(parents=True, exist_ok=True); nuevas = []
        for nom, x in sorted(imgs.items()):
            if sorted(x['partes']) != list(range(1, x['de'] + 1)): avisos.append(f'{nom}: llegó incompleta, no se guardó'); continue
            b = b''.join(x['partes'][i].read_bytes() for i in range(1, x['de'] + 1))
            ext = next((e for k, e in MAGIA.items() if b.startswith(k)), None)
            if not ext or (ext == '.webp' and b[8:12] != b'WEBP'): avisos.append(f'{nom}: no es una imagen png, jpg ni webp, no se guardó'); continue
            if len(b) > C['subida']['max_mb_por_imagen'] * 1024 * 1024: avisos.append(f'{nom}: pesa más de {C["subida"]["max_mb_por_imagen"]} MB, no se guardó'); continue
            h = sha(b)
            if h in (v.get('refs_sha256') or []): avisos.append(f'{nom}: ya estaba en esta versión'); continue
            f = dst / (h[:16] + ext); f.write_bytes(b); v['refs'].append(str(f.relative_to(raiz(canal)))); v.setdefault('refs_sha256', []).append(h); nuevas.append(f.name)
        if len(refs_en_disco(canal, v)) > mx: avisos.append(f'la versión tiene más de {mx} imágenes: se usan las primeras {mx}')
        guardar_manifiesto(canal, m)
    shutil.rmtree(ses, ignore_errors=True)
    D = carpeta_capitulo(canal, capitulo) if capitulo else None
    r = revisar(canal, D); r.update(accion='personajes guardar', guardado={'personaje': pn, 'version': vn, 'estado': v['estado'], 'imagenes_nuevas': nuevas}, avisos=avisos + r['avisos'])
    return r

def hoja_sello(canal, pid, pm=None):
    """t480u (Ricardo): hoja APROBADA del sello del personaje (cajas/cubo_fijo/personajes/*.json: sellado, hoja_aprobada con
    aprobado_por/cuando y sha256 verificado). Se busca por id del capítulo o de la biblioteca en ids_canal. Nunca inventa: sin sello
    aprobado o con sha distinto → None. Gratis, sin red."""
    import glob as _g, hashlib as _h
    ids = {str(pid)} | (({str(pm.get('id'))} | set(pm.get('ids_mapa') or [])) if pm else set())
    for f in sorted(_g.glob('/opt/myia-taller-n8n/cajas/cubo_fijo/personajes/*.json')):
        try: e = json.loads(Path(f).read_text(encoding='utf-8'))
        except Exception: continue
        if e.get('canal') not in (None, canal) or not e.get('sellado'): continue
        if not (ids & ({e.get('id')} | set(e.get('ids_canal') or []))): continue
        ha = e.get('hoja_aprobada') or {}
        r = ha.get('ruta')
        if not (r and ha.get('aprobado_por') and ha.get('cuando') and Path(r).is_file()): continue
        if ha.get('sha256') and _h.sha256(Path(r).read_bytes()).hexdigest() != ha['sha256']: continue
        return r
    return None

# ---------------- refs por escena (lo usan los cubos que pintan personajes) ----------------
def refs_para(canal, D, escena, personaje=None, momento=None, toma=None, lado=None):
    """Imágenes que un cubo DEBE adjuntar para los personajes de una escena, según el mapa del paso 00.
    momento: 'inicio' | 'fin' | 'transformacion' (antes y después) | None (si la versión cambia en la escena → las dos, como transformación).
    Si una versión falta o no está aprobada → 'detener' con aviso (según ajuste si_falta_version). Nunca inventa.
    Orden 80: toma (lee cubos 07/06) o lado ('frente' | 'espalda') eligen la vista estándar que corresponde."""
    m = leer_manifiesto(canal); aj = ajustes(m); mx = int(aj['max_imagenes_por_version']); mp = mapa(D)
    ref, _, _ = precio_ref(canal)
    usar, detener, grupos, solo_voz = [], [], {}, []
    rel = relleno_capitulo(canal, D)   # orden 88
    for pid, fi, ff in estados_escena(D, escena):
        mnom = (mp.get(pid) or {}).get('nombre')
        pm = buscar_personaje(m, pid, mnom)
        g = buscar_grupo(m, pid, mnom) if pm is None else None
        if g:   # orden 85: el guion nombra un GRUPO → cada miembro con su única versión (o el que pide --personaje)
            todos = miembros_grupo(m, g)
            pares = todos if (not personaje or personaje in (pid, g['id']) or igual(personaje, mnom) or igual(personaje, g['nombre'])
                              or any(igual(personaje, a) for a in g.get('alias') or [])) else [x for x in todos if es_miembro(x[0], personaje)]
            if not pares: continue
            grupos[pid] = {'grupo': g['id'], 'nombre': g['nombre'], 'miembros': [{'id': x['id'], 'nombre': x['nombre']} for x, _ in pares]}
            for pmx, v in pares:
                est = estado_version(canal, v, aj)
                if est != 'cargada':
                    detener.append(f'Escena {escena}: falta {pmx["nombre"]} – {(v or {}).get("nombre") or "?"} ({est.replace("_", " ")}; del grupo {g["nombre"]}). '
                                   'Esta imagen/toma NO se pinta; carga la versión en «Cargar personajes».')
                    continue
                lx = lado or lado_en_toma(D, toma, pmx['id']) or lado_en_toma(D, toma, pid); rs = imagenes_version(canal, v, lx, mx)
                vx = {str(raiz(canal) / r): k for k, r in (v.get('vistas') or {}).items() if r}
                usar.append({'personaje': pmx['nombre'], 'personaje_id': pmx['id'], 'grupo_id': pid, 'grupo': g['nombre'], 'version': v['nombre'],
                             'forma_id': v.get('forma_id'), 'imagenes': [str(r) for r in rs], 'lado': lx, 'vistas_usadas': [vx.get(str(r)) for r in rs],
                             'nunca_cambia': pmx.get('nunca_cambia'), 'descripcion': v.get('descripcion'), 'altura_m': pmx.get('altura_m') or v.get('altura_m'),
                             'tipo_forma': v.get('tipo_forma') or 'persona', 'uso': v.get('uso')})   # orden 91
            continue
        if personaje and personaje not in (pid, mnom) and not igual(personaje, mnom): continue
        if pm is None and pid in rel:   # orden 88: relleno (sin imagen, con descripción) o solo voz (nunca en cuadro)
            x = rel[pid]
            if x['tipo'] == 'solo_voz':
                solo_voz.append({'personaje': x['nombre'], 'personaje_id': pid, 'descripcion': x['descripcion']}); continue
            # orden 89: sus imágenes pintadas se adjuntan SOLO si una persona aprobó el relleno (pendiente_revision → sin imagen, con descripción)
            iv = {k: Path(D) / r for k, r in (x.get('imagenes') or {}).items() if r and (Path(D) / r).is_file()} if x.get('estado') == 'aprobado' else {}
            lx = lado or lado_en_toma(D, toma, pid); ks = [k for k in ([lx] if lx in iv else list(iv)[:1])]
            usar.append({'personaje': x['nombre'], 'personaje_id': pid, 'version': 'relleno', 'forma_id': fi or ff, 'imagenes': [str(iv[k]) for k in ks], 'lado': lx if ks else None,
                         'vistas_usadas': ks, 'nunca_cambia': None, 'descripcion': x['descripcion'], 'tipo': 'relleno', 'estado_revision': x['estado'],
                         'imagenes_pintadas': sorted(iv) if iv else sorted(x.get('imagenes') or {})})
            continue
        fids = {'inicio': [fi], 'fin': [ff], 'transformacion': [fi, ff]}.get(momento) or ([fi] if fi == ff else [fi, ff])
        for fid in dict.fromkeys(x for x in fids if x):
            fnom = ((mp.get(pid) or {}).get('formas', {}).get(fid) or {}).get('nombre') or fid
            v = buscar_version(pm, fid, fnom)
            if v is None and pm and len(pm.get('versiones') or []) == 1 and len((mp.get(pid) or {}).get('formas') or {}) == 1:
                v = pm['versiones'][0]   # t480u: una sola forma en el capítulo y una sola versión en la biblioteca → es esa (por datos)
            hs = hoja_sello(canal, pid, pm)
            if v is not None and hs: v = {**v, '_hoja_sello': hs}
            est = estado_version(canal, v, aj)
            pnom = (mp.get(pid) or {}).get('nombre') or pid
            if est != 'cargada':
                detener.append(f'Escena {escena}: falta {pnom} – {fnom} ({est.replace("_", " ")}). Esta imagen/toma NO se pinta; carga la versión en «Cargar personajes».')
                continue
            lx = lado or lado_en_toma(D, toma, pid); rs = imagenes_version(canal, v, lx, mx)
            vx = {str(raiz(canal) / r): k for k, r in (v.get('vistas') or {}).items() if r}
            usar.append({'personaje': pnom, 'personaje_id': pid, 'version': v['nombre'], 'forma_id': fid, 'imagenes': [str(r) for r in rs],
                         'lado': lx, 'vistas_usadas': [vx.get(str(r)) for r in rs],
                         'nunca_cambia': (pm or {}).get('nunca_cambia'), 'descripcion': v.get('descripcion'),
                         'tipo_forma': v.get('tipo_forma') or 'persona', 'uso': v.get('uso')})   # orden 91
    n = sum(len(x['imagenes']) for x in usar)
    return {'ok': not detener, 'detener': detener, 'si_falta_version': aj['si_falta_version'], 'usar': usar, 'n_imagenes_personaje': n, 'grupos': grupos,
            'solo_voz': solo_voz,
            'usd_extra': round((ref or 0) * n, 4) if ref is not None else None,
            'regla': 'Los personajes NUNCA se generan: solo estas imágenes. Si algo falta, se detiene esa imagen o toma.'}

def objetos_que_son_personaje(D, mp):
    """4b1/4c1: objetos (o estados) cuyo pedido describe una figura o ropa puesta. Se sacan de los objetos (4b2/4c2 no los pintan)
    y se enlazan con la versión del personaje del mapa. Genérico; sin red."""
    out = []
    try:
        import paso00_pintar as PN
    except Exception: return out
    for caja in ('4b2', '4c2'):
        K = PN.CAJAS_PINTAR[caja]
        try: regs, _ = PN.investigacion_valida(D, K['inv'])
        except Exception: continue
        for oid, v in (regs or {}).items():
            pedidos = [(oid, v.get('prompt_imagen'))] + [(f'{oid}__estado{k}', e.get('prompt_imagen')) for k, e in enumerate(v.get('prompts_por_estado') or [], 1) if isinstance(e, dict)]
            for iid, t in pedidos:
                g = revisar_pedido(oid, str(t or ''), mp, v.get('nombre'))
                if g: out.append({'id': iid, 'cubo': f"{K['cubo_inv']}/{caja}", 'accion': g['accion'],
                                  'accion_txt': 'NO se pinta (es figura o ropa puesta)' if g['accion'] == 'bloquear' else 'se pinta solo la parte que es objeto',
                                  'version_del_mapa': [f"{x['personaje']} – {x['version']}" for x in g.get('vinculo') or []]})
    return out

def guia_prompt(usar, primera=1):
    """Texto que el cubo pega al pedido cuando adjunta imágenes de personajes (genérico)."""
    t, k = [], primera
    for x in usar:
        n = len(x['imagenes'])
        if not n: continue
        rng = f'{k}' if n == 1 else f'{k}–{k + n - 1}'
        vu = [z for z in x.get('vistas_usadas') or [] if z]
        vista = (' (' + ', then '.join({'frente': 'full-body front view', 'espalda': 'full-body back view'}.get(z, z) for z in vu) + ')') if vu else ''
        if x.get('tipo_forma') == 'objeto':   # orden 91: una forma que es un OBJETO (alguien lo lleva o lo usa), no una figura
            t.append(f"Reference image(s) {rng}: the OBJECT «{x['version']}» (the form «{x['version']}» of «{x['personaje']}» is this object, not a person). "
                     "Copy its shape, materials, colors and glow exactly; draw it only where the scene says, worn or used as described; never turn it into a figure."
                     + (f" Usage (as written by the user): {x['uso']}." if x.get('uso') else ''))
            k += n; continue
        t.append(f"Reference image(s) {rng}: the character «{x['personaje']}» in version «{x['version']}»{vista}. Copy face, body, clothes and colors exactly; do not invent or change the character."
                 + (f" Never changes: {x['nunca_cambia']}." if x.get('nunca_cambia') else ''))
        k += n
    return ' '.join(t)

# ---------------- entrada ----------------
def main(argv):
    ap = argparse.ArgumentParser(prog='paso00_cadena.py personajes')
    ap.add_argument('accion', choices=['revisar', 'ficha', 'subir', 'guardar', 'refs',
                                       'hoja-recibir', 'hoja-cotizar', 'hoja-aplicar', 'hoja-leer', 'hoja-separar', 'nombrar',
                                       'dividir', 'resolver', 'aprobar', 'alias-version', 'relleno', 'relleno-cotizar', 'relleno-pintar', 'reemplazar-refs'])   # orden 91   # orden 88, 89   # orden 85, 86   # PISTA INMI (2026-10-29): orden 76 — leer hoja
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', default=None)
    ap.add_argument('--prellenar', action='store_true')
    ap.add_argument('--sesion'); ap.add_argument('--nombre'); ap.add_argument('--parte', type=int); ap.add_argument('--de', type=int); ap.add_argument('--datos')
    ap.add_argument('--hoja'); ap.add_argument('--ok', type=float); ap.add_argument('--aprobado'); ap.add_argument('--solo'); ap.add_argument('--forzar')
    ap.add_argument('--simulada')   # orden 76: SOLO hoja-cotizar, lectura hecha a mano (base64url JSON) para cotizar gratis; nunca sirve para separar
    ap.add_argument('--max-intentos', dest='max_intentos', type=int)
    ap.add_argument('--descripcion')   # orden 77: nombrar (campo manual)
    ap.add_argument('--descripcion-b64', dest='descripcion_b64')   # igual, en base64url (la entrada SSH parte por espacios)
    ap.add_argument('--nombre-b64', dest='nombre_b64')   # nombre con tildes o espacios (la entrada SSH solo deja ASCII simple)
    ap.add_argument('--escena'); ap.add_argument('--personaje'); ap.add_argument('--momento', choices=['inicio', 'fin', 'transformacion'])
    ap.add_argument('--toma'); ap.add_argument('--lado', choices=['frente', 'espalda']); ap.add_argument('--vistas')   # orden 80
    ap.add_argument('--version'); ap.add_argument('--forma-id', dest='forma_id'); ap.add_argument('--tipo', choices=['relleno', 'solo_voz'])   # orden 88
    ap.add_argument('--imagen'); ap.add_argument('--tipo-forma', dest='tipo_forma', choices=list(TIPOS_FORMA)); ap.add_argument('--nota-b64', dest='nota_b64')   # orden 91
    ap.add_argument('--todos', action='store_true'); ap.add_argument('--excepto'); ap.add_argument('--cita-b64', dest='cita_b64'); ap.add_argument('--fecha')   # orden 86
    a = ap.parse_args(argv)
    if not valido_id(a.canal): return {'ok': False, 'error': 'canal no válido'}
    D = carpeta_capitulo(a.canal, a.capitulo) if a.capitulo else None
    try:
        if a.accion.startswith('hoja-'):   # orden 76: leer hoja (personajes_hoja.py)
            if a.accion != 'hoja-recibir' and not valido_id(a.hoja): return {'ok': False, 'error': 'falta --hoja (id)'}
            import personajes_hoja as PH
            return PH.main(a.accion, a, D)
        if a.accion == 'revisar':
            pre = prellenar(a.canal, D) if a.prellenar else None
            r = revisar(a.canal, D)
            if pre is not None: r['prellenado'] = pre
            if a.capitulo and D is None: r['avisos'].insert(0, f'no hay carpeta del capítulo {a.capitulo}: no se revisa el mapa')
            return r
        if a.accion == 'nombrar':   # orden 77
            b = lambda t: base64.urlsafe_b64decode(t + '=' * (-len(t) % 4)).decode('utf-8')
            if a.nombre_b64: a.nombre = b(a.nombre_b64)
            if a.descripcion_b64: a.descripcion = base64.urlsafe_b64decode(a.descripcion_b64 + '=' * (-len(a.descripcion_b64) % 4)).decode('utf-8')
            return nombrar(a.canal, a.personaje, a.nombre, a.aprobado, a.descripcion)
        if a.accion == 'dividir':   # orden 85
            if not a.personaje: return {'ok': False, 'error': 'falta --personaje'}
            d = json.loads(b64(a.datos).decode('utf-8')) if a.datos else None
            if d is not None and not isinstance(d, dict): return {'ok': False, 'error': '--datos no es un objeto'}
            return dividir(a.canal, a.personaje, a.aprobado, d)
        if a.accion == 'resolver':   # orden 85: ¿a quién(es) nombra este id/nombre? (gratis, solo lectura)
            q = a.personaje or (b64(a.nombre_b64).decode('utf-8') if a.nombre_b64 else None)
            if not q: return {'ok': False, 'error': 'falta --personaje'}
            m = leer_manifiesto(a.canal); g = buscar_grupo(m, q, q) if buscar_personaje(m, q, q) is None else None
            return {'ok': True, 'accion': 'personajes resolver', 'pregunta': q, 'grupo': g['nombre'] if g else None,
                    'personajes': [{'id': p['id'], 'nombre': p['nombre'], 'version': (v or {}).get('nombre')} for p, v in resolver(m, q, q)]}
        if a.accion == 'aprobar':   # orden 86: --personaje P[:V][,P2…] o --todos; --excepto B64URL([{version, nota}]); --cita-b64; --fecha ISO
            que = [x for x in str(a.personaje or '').split(',') if x.strip()]
            exc = json.loads(b64(a.excepto).decode('utf-8')) if a.excepto else []
            if not isinstance(exc, list): return {'ok': False, 'error': '--excepto no es una lista'}
            cita = b64(a.cita_b64).decode('utf-8') if a.cita_b64 else None
            return aprobar(a.canal, a.aprobado, que, a.todos, exc, cita, a.fecha)
        if a.accion == 'reemplazar-refs':   # orden 91: --personaje P:V --imagen ARCHIVO(_entrada/) --aprobado QUIEN [--tipo-forma] [--nota-b64] [--cita-b64] [--fecha]
            if not a.personaje or not a.imagen: return {'ok': False, 'error': 'falta --personaje P:V o --imagen'}
            return reemplazar_refs(a.canal, a.personaje, a.imagen, a.aprobado, a.tipo_forma,
                                   b64(a.nota_b64).decode('utf-8') if a.nota_b64 else None, b64(a.cita_b64).decode('utf-8') if a.cita_b64 else None, a.fecha)
        if a.accion == 'alias-version':   # orden 88: --personaje P --version V --nombre-b64 ALIAS [--forma-id F] --aprobado QUIEN
            al = b64(a.nombre_b64).decode('utf-8') if a.nombre_b64 else a.nombre
            return alias_version(a.canal, a.personaje, a.version, al, a.aprobado, a.forma_id)
        if a.accion in ('relleno-cotizar', 'relleno-pintar'):   # orden 89: referencias pintadas del relleno (relleno_pintar.py)
            if D is None: return {'ok': False, 'error': 'falta --capitulo'}
            import relleno_pintar as RP
            solo = [x for x in (a.solo or '').split(',') if x]; fz = [x for x in (a.forzar or '').split(',') if x]
            return RP.cotizar(a.canal, D, solo, fz) if a.accion == 'relleno-cotizar' else RP.pintar(a.canal, D, a, solo, fz)
        if a.accion == 'relleno':   # orden 88: --capitulo N [lista] | --personaje P (--tipo T | --descripcion-b64 | --todos=aprobar) --aprobado QUIEN
            if D is None: return {'ok': False, 'error': 'falta --capitulo'}
            if not a.personaje:
                r = relleno_capitulo(a.canal, D)
                return {'ok': True, 'accion': 'personajes relleno', 'capitulo': D.name, 'archivo': str(relleno_f(D)), 'personajes': list(r.values())}
            de = base64.urlsafe_b64decode(a.descripcion_b64 + '=' * (-len(a.descripcion_b64) % 4)).decode('utf-8') if a.descripcion_b64 else a.descripcion
            return relleno_cambiar(a.canal, D, a.personaje, a.tipo, a.aprobado, de, a.todos)
        if a.accion == 'ficha': return ficha(a.canal, a.sesion, a.datos)
        if a.accion == 'subir': return subir(a.canal, a.sesion, a.nombre, a.parte, a.de, a.datos)
        if a.accion == 'guardar': return guardar(a.canal, a.sesion, a.capitulo)
        if a.accion == 'refs':
            if D is None or not a.escena: return {'ok': False, 'error': 'falta --capitulo o --escena'}
            return refs_para(a.canal, D, a.escena, a.personaje, a.momento, a.toma, a.lado)
    except ValueError as e:
        return {'ok': False, 'error': str(e)}
