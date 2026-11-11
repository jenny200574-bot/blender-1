#!/usr/bin/env python3
"""MYIA · Taller n8n · ORDEN 62 (pt433u): BIBLIOTECA DE ESCENARIOS DEL CANAL (continuidad). Genérico: cualquier canal.

QUÉ HACE
  Un escenario APROBADO queda guardado en el canal como escenario fijo: molde Blender (4a2: .blend, molde.json, renders),
  investigación 4a1 (con perfil_real y ambiente_vivo), objetos del lugar (4c1) y de la historia (4b1), prompts 4a4,
  imagen BASE pintada (4a5) y sus VARIANTES. Si los protagonistas vuelven a ese lugar en otro capítulo, se reconoce y se
  reutiliza: no se re-investiga ni se repinta la base; solo se agregan variantes nuevas. GRATIS: sin red, sin IA.

DÓNDE VIVE   (raíz = $MYIA_BIBLIOTECA o /opt/myia-taller-n8n/trabajo/biblioteca)
  <raíz>/<canal>/escenarios/<escenario_id>/
      ficha.json            versión actual, capítulos donde aparece, huella, estado «aprobado», sinónimos, alias, variantes
      molde/v1/             copia de ramas/moldes/<id>/ (molde.blend, molde.json, planta.png, cam_*.png, luz_*.png, escenario.json)
      base/v1/base.png      imagen base pintada (4a5) + base.json (prompt 4a4 y de dónde salió)
      datos/v1/             inv_4a1.json (perfil_real + ambiente_vivo), fichas_4p.json, prompts_4a4.json, objetos_lugar.json (+ imágenes 4c2)
      variantes/v1/         <escenario_id>__v1-var01.png … (ediciones de la base; cada una con su .json)
      historial/            eventos.jsonl (solo se agrega) + ficha_<hora>.json (foto de la ficha antes de cada cambio). NUNCA se borra nada.
  <raíz>/<canal>/objetos/<objeto_id>/  ficha.json + datos (4b1) + imagen (4b2): objetos de la HISTORIA (viajan con los personajes).
  Por capítulo (carpeta del paso 00): ramas/biblioteca_reconocer.json (decisiones) y, al materializar, copias en ramas/moldes y ramas/imagenes.

CONECTADA AL TALLER n8n (orden 62, pt444u): se llama por «paso00_cadena biblioteca <accion> …» (misma entrada restringida n8ntaller).
  4a0 (antes de 4a1): «plan --reconocer --materializar»; las dudosas piden «confirmar» en pantalla; 4a1 (paso00_cadena) lee
  ramas/biblioteca_plan.json: NO investiga los reutilizados (US$0) y para los que traen estados nuevos usa el prompt «4a1 solo variantes».
  4a7 (después de 4a6): «guardar --ids a,b | --todos». Datos reales de la orden 61c: 4a1 con perfil_real + ambiente_vivo (autorrevisión
  en los grupos hechos con el fijo _o61c), texto fijo de cada grupo (fijo_paso) y moldes Blender reales (ramas/moldes/<id>, huella).

RECONOCER (por escenario del catálogo oficial del capítulo, caja 4), EN ESTE ORDEN:
  0. el escenario se guardó DESDE ESTE MISMO capítulo (mismo episodio y mismo id)                → «propio» (no se toca: 4a1 normal)
  1. mismo id oficial (o un id ya confirmado antes como alias)            → «reutilizar» (automático)
  2. mismo nombre normalizado o un sinónimo (sin tildes ni palabras vacías) → «reutilizar» (automático; el nombre queda como sinónimo)
  3. coincidencia dudosa (palabras en común / parecido de texto ≥ UMBRAL)  → «confirmar»: NUNCA se reutiliza en automático; lo aprueba el usuario
  4. nada                                                                   → «nuevo» (va a investigación 4a1 normal)
  Un «no es el mismo» del usuario queda anotado en la ficha (no_es) y no se vuelve a preguntar.

REUTILIZAR (plan por caja, gratis)
  4a1: no investiga los reutilizados; solo «solo_variantes» si el capítulo trae estados que la biblioteca no tiene.
  4a2: usa el molde guardado (no vuelve a correr Blender).    4a4/4a5: no repite la base; solo cotiza/pinta ediciones nuevas.
  4b1/4c1 (+4b2/4c2): los objetos guardados mantienen su aspecto (datos e imagen); solo se investigan los nuevos.
  Los «confirmar» esperan la decisión (la cotización los cuenta como nuevos, peor caso).

CAMBIOS PERMANENTES (el lugar queda cambiado para siempre, p. ej. pared rota que no se repara)
  - «variante persistente» (cambia el aspecto, NO la forma): la variante pasa a ser el ESTADO VIGENTE desde ese capítulo; el molde no
    cambia y las variantes nuevas se editan sobre esa imagen.
  - «versión nueva» (cambia la forma: medidas, aberturas, muros, bloques de Blender): se crea v2 (molde/v2, base/v2, datos/v2);
    Blender re-arma una vez y la base v2 se pinta UNA vez editando la imagen del estado anterior. v1 queda intacta (recuerdos/flashbacks).
  - modo «auto»: si toca la geometría → versión nueva; si no → variante persistente.

CLI (una línea JSON en stdout):
  biblioteca.py reconocer  --canal C --capitulo N
  biblioteca.py confirmar  --canal C --capitulo N --escenario ID_CAP (--es ID_BIB | --nuevo)
  biblioteca.py plan       --canal C --capitulo N [--reconocer] [--materializar]
  biblioteca.py guardar    --canal C --capitulo N (--escenario ID_CAP | --ids A,B | --decisiones 4a6_decisiones.json | --todos) --aprobado QUIEN
  biblioteca.py permanente --canal C --escenario ID_BIB --capitulo N --variante VAR [--modo auto|variante|version] [--toca-geometria] [--motivo T]
  biblioteca.py buscar     --canal C TEXTO
  biblioteca.py listar     --canal C
"""
import os, re, sys, json, time, shutil, hashlib, difflib, argparse, unicodedata, fcntl
from pathlib import Path

RAIZ = Path(os.environ.get('MYIA_BIBLIOTECA', '/opt/myia-taller-n8n/trabajo/biblioteca'))
TRABAJO = Path(os.environ.get('MYIA_TRABAJO', '/opt/myia-taller-n8n/trabajo/paso00_cadena'))
ESQUEMA = 'myia-biblioteca-escenario/1'
UMBRAL_DUDOSA = 0.5          # parecido mínimo para preguntar «¿es el mismo?»
UMBRAL_VARIANTE = 0.6        # parecido mínimo para decir que un estado del capítulo ya está guardado
VACIAS = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'e', 'en', 'un', 'una', 'al', 'a', 'con', 'por', 'para', 'su', 'sus', 'lo', 'esc', 'obj', 'objeto'}
IMG = {'4a5': 'ramas/imagenes/4a5', '4b2': 'ramas/imagenes/4b2', '4c2': 'ramas/imagenes/4c2'}
EXT_IMG = ('.png', '.jpg', '.jpeg', '.webp')

def ahora(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')

# ---------------- utilidades ----------------
def slug(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')

def fichas_de(s):
    """Palabras significativas (sin tildes, sin palabras vacías)."""
    return [w for w in slug(s).split('-') if w and w not in VACIAS]

def norm(s): return ' '.join(sorted(set(fichas_de(s))))   # nombre normalizado: orden y repeticiones no importan

def parecido(a, b):
    ta, tb = set(fichas_de(a)), set(fichas_de(b))
    if not ta or not tb: return 0.0
    jac = len(ta & tb) / len(ta | tb)
    rat = difflib.SequenceMatcher(None, ' '.join(sorted(ta)), ' '.join(sorted(tb))).ratio()
    if not ta & tb: return round(rat, 3) if rat >= 0.85 else 0.0   # sin palabras en común solo cuenta un error de letras (p. ej. «habitasion»)
    return round(max(jac, rat), 3)

def sinonimos_de_nombre(nombre, eid=None):
    """Nombre completo + cada parte separada por «/» o «—» que tenga ≥2 palabras significativas (una palabra sola es muy ambigua)."""
    out = [norm(nombre)]
    for p in re.split(r'\s*(?:/|—|–|\|)\s*', str(nombre or '')):
        if len(set(fichas_de(p))) >= 2: out.append(norm(p))
    if eid and len(set(fichas_de(eid))) >= 2: out.append(norm(eid))
    return sorted({x for x in out if x})

def sha_archivo(f):
    h = hashlib.sha256()
    with open(f, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def sha_json(o): return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def leer_json(f, defecto=None):
    try:
        t = Path(f).read_text(encoding='utf-8').strip()
        if t.startswith('```'): t = t.strip('`'); t = t[t.find('{'):]
        return json.loads(t[t.find('{'):t.rfind('}') + 1]) if not t.startswith('[') else json.loads(t)
    except Exception: return defecto

def escribir_json(f, o):
    f = Path(f); f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + '.tmp'); tmp.write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8'); os.replace(tmp, f)
    return str(f)

def copiar_sin_pisar(src, dst):
    """Copia un archivo; si ya existe con OTRO contenido no lo pisa: guarda la copia nueva con sufijo (nada se pierde)."""
    src, dst = Path(src), Path(dst); dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if sha_archivo(dst) == sha_archivo(src): return str(dst)
        n = 2
        while (dst.with_name(f'{dst.stem}.{n}{dst.suffix}')).exists(): n += 1
        dst = dst.with_name(f'{dst.stem}.{n}{dst.suffix}')
    shutil.copy2(src, dst); return str(dst)

def copiar_carpeta(src, dst):
    out = []
    for f in sorted(Path(src).rglob('*')):
        if f.is_file() and f.name not in ('.candado',) and not f.name.endswith(('.tmp', '.blend1')):   # .blend1 = copia automática de Blender
            out.append(copiar_sin_pisar(f, Path(dst) / f.relative_to(src)))
    return out

def imagen(carp, nombre):
    for e in EXT_IMG:
        f = Path(carp) / f'{nombre}{e}'
        if f.is_file(): return f
    return None

class Candado:
    def __init__(self, canal): self.f = RAIZ / canal / '.candado'
    def __enter__(self):
        self.f.parent.mkdir(parents=True, exist_ok=True); self.h = open(self.f, 'w'); fcntl.flock(self.h, fcntl.LOCK_EX); return self
    def __exit__(self, *a): fcntl.flock(self.h, fcntl.LOCK_UN); self.h.close()

# ---------------- capítulo (misma estructura que paso00_cadena / paso00_ramas) ----------------
def carpeta_capitulo(canal, capitulo):
    base = TRABAJO / canal
    ds = sorted(base.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(base.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None

def resp(D, nombre): return leer_json(Path(D) / 'respuestas' / f'{nombre}.json')

def por_id(lst, k): return {x.get(k): x for x in (lst or []) if isinstance(x, dict) and x.get(k)}

def datos_capitulo(D):
    base = resp(D, 'base') or {}; cat = base.get('catalogo_oficial') or {}
    return {'base': base, 'cat_esc': por_id(cat.get('escenarios'), 'id'), 'cat_obj': por_id(cat.get('objetos'), 'id'),
            'e2a': por_id((resp(D, 'escenarios') or {}).get('escenarios'), 'escenario_id'),
            'e2b': por_id((resp(D, 'objetos') or {}).get('objetos'), 'objeto_id'),
            'inv_esc': por_id((resp(D, 'inv_escenarios') or {}).get('escenarios'), 'escenario_id'),
            'inv_oh': por_id((resp(D, 'inv_obj_historia') or {}).get('objetos'), 'objeto_id'),
            'inv_ol': por_id((resp(D, 'inv_obj_lugar') or {}).get('objetos'), 'objeto_id'),
            'p4a4': por_id((resp(D, 'prompts_escenarios') or {}).get('escenarios'), 'escenario_id'),
            'blender': por_id(leer_json(Path(D) / 'ramas' / '4a2_entrada_blender.json', []) if isinstance(leer_json(Path(D) / 'ramas' / '4a2_entrada_blender.json', []), list) else [], 'id'),
            'inv_meta': meta_4a1(D)}

def meta_4a1(D):
    """Orden 61c: de qué grupo (y con qué texto fijo) salió la investigación 4a1 de cada escenario."""
    out = {}; uni = leer_json(Path(D) / 'respuestas' / 'inv_escenarios.json') or {}
    amb = ((uni.get('_taller') or {}).get('ambiente_por_escenario')) or {}
    for g in sorted((Path(D) / 'resultados').glob('inv_escenarios_g*de*.json')):
        r = leer_json(g) or {}
        if r.get('estado') != 'ok': continue
        for i in r.get('ids') or []:
            out[i] = {'grupo': g.stem, 'fijo_paso': r.get('fijo_paso'), 'usd_real_grupo': r.get('usd_real'), 'hora': r.get('fin_hora'), 'ambiente_conteo': amb.get(i)}
    return out

def numero_cap(D): m = re.match(r'cap(\d+)_(.*)', Path(D).name); return (int(m.group(1)), m.group(2)) if m else (None, Path(D).name)

# ---------------- biblioteca: lectura ----------------
def dir_esc(canal, eid): return RAIZ / canal / 'escenarios' / eid
def dir_obj(canal, oid): return RAIZ / canal / 'objetos' / oid

def fichas(canal, que='escenarios'):
    d = RAIZ / canal / que
    return [f for f in (leer_json(x / 'ficha.json') for x in sorted(d.iterdir()) if (x / 'ficha.json').is_file()) if f] if d.is_dir() else []

def ficha(canal, eid, que='escenarios'): return leer_json(RAIZ / canal / que / eid / 'ficha.json')

def evento(d, tipo, **datos):
    h = Path(d) / 'historial'; h.mkdir(parents=True, exist_ok=True)
    with open(h / 'eventos.jsonl', 'a', encoding='utf-8') as fh: fh.write(json.dumps({'hora': ahora(), 'evento': tipo, **datos}, ensure_ascii=False) + '\n')

def guardar_ficha(d, f, motivo):
    """Foto de la ficha anterior en historial/ y luego escribe la nueva (nunca se borra una ficha vieja)."""
    d = Path(d); vieja = d / 'ficha.json'
    if vieja.is_file():
        h = d / 'historial'; h.mkdir(parents=True, exist_ok=True)
        n = h / f"ficha_{time.strftime('%Y%m%d_%H%M%S')}.json"; k = 2
        while n.exists(): n = h / f"ficha_{time.strftime('%Y%m%d_%H%M%S')}_{k}.json"; k += 1
        shutil.copy2(vieja, n)
    f['actualizado'] = ahora(); escribir_json(vieja, f); evento(d, 'ficha', motivo=motivo, version_actual=f.get('version_actual'))

# ---------------- RECONOCER ----------------
def _candidatos(f):
    """Textos con los que se compara una ficha: nombre, sinónimos e ids (alias incluidos)."""
    return sorted(set(f.get('sinonimos') or []) | {norm(f.get('nombre'))} | {norm(i) for i in [f.get('escenario_id') or f.get('objeto_id')] + (f.get('alias_ids') or [])})

def reconocer_uno(item_id, nombre, int_ext, bib, idk='escenario_id', epi=None):
    """Devuelve {decision, como, biblioteca_id, puntaje, motivo, otros}. bib = lista de fichas del canal.
    epi = episodio del capítulo: una ficha guardada desde ESTE episodio con OTRO id es otro lugar por definición (el catálogo del capítulo ya los separa)."""
    if epi: bib = [f for f in bib if not any(z.get('episodio') == epi and z.get('id_en_capitulo') != item_id for z in f.get('capitulos', []))]
    # 1. mismo id oficial (o alias ya confirmado)
    for f in bib:
        if item_id == f.get(idk): return {'decision': 'reutilizar', 'como': 'id', 'biblioteca_id': f[idk], 'puntaje': 1.0, 'motivo': 'mismo id oficial'}
    for f in bib:
        if item_id in (f.get('alias_ids') or []): return {'decision': 'reutilizar', 'como': 'id_alias', 'biblioteca_id': f[idk], 'puntaje': 1.0, 'motivo': f'id {item_id} ya confirmado antes como el mismo lugar'}
    # 2. nombre normalizado o sinónimo
    n = norm(nombre); ni = norm(item_id)
    for f in bib:
        if n and n in (f.get('no_es') or []): continue
        c = set(f.get('sinonimos') or []) | {norm(f.get('nombre'))}
        if n and n in c: return {'decision': 'reutilizar', 'como': 'nombre', 'biblioteca_id': f[idk], 'puntaje': 1.0, 'motivo': f'mismo nombre normalizado o sinónimo «{n}»'}
        if ni and len(ni.split()) >= 2 and ni in c: return {'decision': 'reutilizar', 'como': 'nombre', 'biblioteca_id': f[idk], 'puntaje': 1.0, 'motivo': f'el id coincide con el nombre/sinónimo «{ni}»'}
    # 3. coincidencia dudosa → confirmar (nunca automático)
    pun = []
    for f in bib:
        if n in (f.get('no_es') or []) or ni in (f.get('no_es') or []): continue
        p = max([parecido(nombre, c) for c in _candidatos(f)] + [parecido(item_id, c) for c in _candidatos(f)] + [0])
        if int_ext and f.get('int_ext') and int_ext != f.get('int_ext'): p = round(p - 0.15, 3)   # interior vs exterior: baja la confianza
        if p >= UMBRAL_DUDOSA: pun.append((p, f[idk], f.get('nombre')))
    pun.sort(reverse=True)
    if pun:
        return {'decision': 'confirmar', 'como': 'dudosa', 'biblioteca_id': pun[0][1], 'puntaje': pun[0][0],
                'motivo': f'se parece a «{pun[0][2]}» ({pun[0][0]:.2f}); el usuario debe decir si es el mismo lugar',
                'otros': [{'biblioteca_id': b, 'nombre': nm, 'puntaje': p} for p, b, nm in pun[1:4]]}
    return {'decision': 'nuevo', 'como': None, 'biblioteca_id': None, 'puntaje': 0.0, 'motivo': 'no está en la biblioteca del canal'}

def reconocer(canal, capitulo):
    D = carpeta_capitulo(canal, capitulo)
    if D is None: return {'ok': False, 'error': f'no hay carpeta del capítulo {capitulo} del canal {canal}'}
    X = datos_capitulo(D)
    if not X['cat_esc']: return {'ok': False, 'error': 'falta respuestas/base.json (caja 4) con catalogo_oficial.escenarios'}
    bib, bibo = fichas(canal, 'escenarios'), fichas(canal, 'objetos')
    previo = leer_json(D / 'ramas' / 'biblioteca_reconocer.json') or {}
    prev_esc = por_id(previo.get('escenarios'), 'id')
    esc, usados = [], {}
    epi = numero_cap(D)[1]
    for i, c in X['cat_esc'].items():
        propio = next((f for f in bib if any(z.get('episodio') == epi and z.get('id_en_capitulo') == i for z in f.get('capitulos', []))), None)
        if propio:   # se guardó desde este mismo capítulo: no se reutiliza en sí mismo (4a1 sigue normal; nada se copia)
            esc.append({'id': i, 'nombre': c.get('nombre'), 'int_ext': c.get('int_ext'), 'escenas': c.get('escenas', []), 'decision': 'propio', 'como': 'mismo_capitulo',
                        'biblioteca_id': propio['escenario_id'], 'puntaje': 1.0, 'motivo': 'guardado desde este mismo capítulo'}); continue
        r = reconocer_uno(i, c.get('nombre'), c.get('int_ext'), bib, epi=epi)
        p = prev_esc.get(i) or {}
        if p.get('como') in ('confirmado_usuario', 'rechazado_usuario'): r = {k: p[k] for k in ('decision', 'como', 'biblioteca_id', 'puntaje', 'motivo') if k in p}   # lo que decidió el usuario manda
        if r['decision'] == 'reutilizar':
            if r['biblioteca_id'] in usados:   # dos lugares del capítulo no pueden ser el mismo escenario fijo en automático
                r = dict(r, decision='confirmar', como='dudosa', motivo=f"«{usados[r['biblioteca_id']]}» ya usa ese escenario fijo; confirmar")
            else: usados[r['biblioteca_id']] = i
        esc.append({'id': i, 'nombre': c.get('nombre'), 'int_ext': c.get('int_ext'), 'escenas': c.get('escenas', []), **r})
    obj = []
    for i, c in X['cat_obj'].items():   # objetos de la HISTORIA (viajan con los personajes): mismo orden de reconocimiento contra biblioteca/<canal>/objetos
        if c.get('tipo') != 'historia': continue
        r = reconocer_uno(i, c.get('nombre'), None, bibo, idk='objeto_id')
        if r['decision'] == 'reutilizar' or r['decision'] == 'confirmar':
            obj.append({'id': i, 'nombre': c.get('nombre'), 'tipo': c.get('tipo'), **r})
    # objetos del lugar dentro de los escenarios reutilizados
    for e in esc:
        if e['decision'] != 'reutilizar': continue
        fe = ficha(canal, e['biblioteca_id']) or {}
        ver = fe.get('version_actual')
        ol = leer_json(dir_esc(canal, e['biblioteca_id']) / 'datos' / ver / 'objetos_lugar.json', []) if ver else []
        bol = [{'objeto_id': o.get('objeto_id'), 'nombre': o.get('nombre') or o.get('objeto_id'), 'sinonimos': sinonimos_de_nombre(o.get('nombre') or '', o.get('objeto_id'))} for o in ol]
        for oid, o in X['e2b'].items():
            if o.get('tipo') == 'lugar' and o.get('escenario_id') == e['id'] and not any(z['id'] == oid for z in obj):
                c = X['cat_obj'].get(oid, {})
                r = reconocer_uno(oid, c.get('nombre') or oid, None, bol, idk='objeto_id')
                obj.append({'id': oid, 'nombre': c.get('nombre'), 'tipo': 'lugar', 'escenario_id': e['id'], 'de_escenario_fijo': e['biblioteca_id'], **r})
    out = {'canal': canal, 'capitulo': numero_cap(D)[0], 'carpeta': str(D), 'hora': ahora(), 'escenarios': esc, 'objetos': obj,
           'resumen': {k: sum(1 for e in esc if e['decision'] == k) for k in ('reutilizar', 'confirmar', 'nuevo', 'propio')}}
    out['pendiente_usuario'] = [{'id': e['id'], 'nombre': e['nombre'], 'parece': e['biblioteca_id'], 'puntaje': e['puntaje']} for e in esc if e['decision'] == 'confirmar']
    escribir_json(D / 'ramas' / 'biblioteca_reconocer.json', out)
    return dict(ok=True, accion='reconocer', archivo=str(D / 'ramas' / 'biblioteca_reconocer.json'), **out)

def confirmar(canal, capitulo, eid_cap, es=None, nuevo=False):
    """El usuario responde una coincidencia dudosa. --es ID_BIB = es el mismo lugar (se reutiliza); --nuevo = es otro lugar."""
    D = carpeta_capitulo(canal, capitulo)
    rec = leer_json(D / 'ramas' / 'biblioteca_reconocer.json') if D else None
    if not rec: return {'ok': False, 'error': 'primero corre «reconocer» para este capítulo'}
    e = next((x for x in rec['escenarios'] if x['id'] == eid_cap), None)
    if not e: return {'ok': False, 'error': f'{eid_cap} no está en el reconocimiento del capítulo'}
    with Candado(canal):
        if es:
            f = ficha(canal, es)
            if not f: return {'ok': False, 'error': f'{es} no está en la biblioteca del canal'}
            e.update(decision='reutilizar', como='confirmado_usuario', biblioteca_id=es, puntaje=1.0, motivo='el usuario confirmó que es el mismo lugar')
            f['alias_ids'] = sorted(set(f.get('alias_ids') or []) | {eid_cap})
            f['sinonimos'] = sorted(set(f.get('sinonimos') or []) | {norm(e['nombre'])})
            guardar_ficha(dir_esc(canal, es), f, f'confirmado por el usuario: {eid_cap} «{e["nombre"]}» es este lugar')
        elif nuevo:
            antes = e.get('biblioteca_id')
            e.update(decision='nuevo', como='rechazado_usuario', motivo='el usuario dijo que es otro lugar', biblioteca_id=None, puntaje=0.0)
            if antes and ficha(canal, antes):
                f = ficha(canal, antes); f['no_es'] = sorted(set(f.get('no_es') or []) | {norm(e['nombre']), norm(eid_cap)})
                guardar_ficha(dir_esc(canal, antes), f, f'el usuario dijo que {eid_cap} «{e["nombre"]}» NO es este lugar')
        else: return {'ok': False, 'error': 'falta --es ID_BIB o --nuevo'}
    rec['resumen'] = {k: sum(1 for x in rec['escenarios'] if x['decision'] == k) for k in ('reutilizar', 'confirmar', 'nuevo', 'propio')}
    rec['pendiente_usuario'] = [{'id': x['id'], 'nombre': x['nombre'], 'parece': x['biblioteca_id'], 'puntaje': x['puntaje']} for x in rec['escenarios'] if x['decision'] == 'confirmar']
    escribir_json(D / 'ramas' / 'biblioteca_reconocer.json', rec)
    return {'ok': True, 'accion': 'confirmar', 'escenario': e, 'resumen': rec['resumen']}

# ---------------- PLAN DE REUTILIZACIÓN (lo consultan 4a1, 4a2, 4a4, 4a5, 4b1/4b2, 4c1/4c2) ----------------
def estados_capitulo(X, eid):
    return [{'variante_id': f'{eid}__v{k}', 'variante': v.get('variante'), 'escenas': v.get('escenas', [])}
            for k, v in enumerate((X['e2a'].get(eid) or {}).get('variantes_estado') or [{'variante': 'normal', 'escenas': []}], 1)]

def es_normal(txt): return bool(re.match(r'^\s*normal\b', str(txt or ''), re.I)) and len(fichas_de(txt)) <= 3

def casar_variantes(canal, eid_bib, estados):
    """Para cada estado del capítulo: ¿ya existe en la biblioteca (misma versión vigente)? Devuelve (reutilizadas, nuevas)."""
    f = ficha(canal, eid_bib) or {}; ver = f.get('version_actual')
    guard = [v for v in f.get('variantes', []) if v.get('version') == ver]
    vig = (f.get('estado_vigente') or {}).get('variante_id')
    reus, nuevas = [], []
    for s in estados:
        if es_normal(s['variante']):
            reus.append(dict(s, usa=vig or 'base', motivo='estado normal = base / estado vigente')); continue
        best = max(((parecido(s['variante'], v.get('descripcion')), v) for v in guard), key=lambda t: t[0], default=(0, None))
        if best[1] is not None and best[0] >= UMBRAL_VARIANTE: reus.append(dict(s, usa=best[1]['variante_id'], puntaje=best[0], imagen=best[1].get('imagen')))
        else: nuevas.append(dict(s, editar_sobre=vig or 'base'))
    return reus, nuevas

def plan(canal, capitulo, materializar=False, re_reconocer=False):
    D = carpeta_capitulo(canal, capitulo)
    if D is None: return {'ok': False, 'error': f'no hay carpeta del capítulo {capitulo} del canal {canal} (corre primero 4 y 4p)'}
    if re_reconocer:
        r = reconocer(canal, capitulo)
        if not r.get('ok'): return r
    rec = leer_json(D / 'ramas' / 'biblioteca_reconocer.json') if D else None
    if not rec: r = reconocer(canal, capitulo); rec = leer_json(D / 'ramas' / 'biblioteca_reconocer.json') if r.get('ok') else None
    if not rec: return {'ok': False, 'error': 'no se pudo reconocer el capítulo'}
    X = datos_capitulo(D)
    P = {'4a1': {'investigar': [], 'omitir': [], 'solo_variantes': [], 'esperan_confirmacion': [], 'propio': []},
         '4a2': {'armar': [], 'molde_de_biblioteca': {}, 'version_nueva_rearmar': []},
         '4a5': {'pintar_base': [], 'base_de_biblioteca': {}, 'ediciones_nuevas': [], 'ediciones_reutilizadas': []},
         '4b1_4c1': {'investigar': [], 'mantener_aspecto': [], 'esperan_confirmacion': []}}
    for e in rec['escenarios']:
        i = e['id']; estados = estados_capitulo(X, i)
        if e['decision'] == 'nuevo':
            P['4a1']['investigar'].append(i); P['4a2']['armar'].append(i); P['4a5']['pintar_base'].append(i)
            P['4a5']['ediciones_nuevas'] += [s['variante_id'] for s in estados[1:]]   # estimado: la base cubre la 1.ª variante (igual que paso00_ramas)
            continue
        if e['decision'] == 'confirmar':
            P['4a1']['esperan_confirmacion'].append(i); continue
        if e['decision'] == 'propio':
            P['4a1']['propio'].append(i); continue
        b = e['biblioteca_id']; f = ficha(canal, b) or {}; ver = f.get('version_actual'); vd = f.get('versiones_por_id', {}).get(ver, {})
        reus, nuevas = casar_variantes(canal, b, estados)
        meta = (f.get('investigacion_4a1') or {})
        if nuevas: P['4a1']['solo_variantes'].append({'id': i, 'biblioteca_id': b, 'variantes_nuevas': [s['variante'] for s in nuevas],
                                                      'estados_nuevos': [{'variante_id': s['variante_id'], 'variante': s['variante'], 'escenas': s['escenas']} for s in nuevas],
                                                      'fijo_paso_guardado': meta.get('fijo_paso')})
        else: P['4a1']['omitir'].append({'id': i, 'biblioteca_id': b, 'fijo_paso_guardado': meta.get('fijo_paso')})
        molde = dir_esc(canal, b) / 'molde' / ver
        if (molde / 'molde.json').is_file(): P['4a2']['molde_de_biblioteca'][i] = str(molde)
        elif f.get('solo_recuerdo_o_pantalla'): pass
        else: P['4a2']['version_nueva_rearmar'].append({'id': i, 'biblioteca_id': b, 'version': ver})
        base_img = vd.get('base')
        if base_img and (dir_esc(canal, b) / base_img).is_file(): P['4a5']['base_de_biblioteca'][i] = str(dir_esc(canal, b) / base_img)
        else:   # versión nueva sin base todavía: se pinta UNA vez, editando la imagen del estado anterior
            P['4a5']['pintar_base'].append(i)
            ref = vd.get('referencia_para_pintar')
            if ref: P['4a5'].setdefault('referencia_para_base', {})[i] = str(dir_esc(canal, b) / ref)
        P['4a5']['ediciones_reutilizadas'] += [{'variante_id': s['variante_id'], 'usa': s['usa']} for s in reus if s.get('usa') != 'base']
        P['4a5']['ediciones_nuevas'] += [s['variante_id'] for s in nuevas]
        e['estado_vigente'] = f.get('estado_vigente'); e['version'] = ver
    for o in rec.get('objetos', []):
        k = 'mantener_aspecto' if o['decision'] == 'reutilizar' else 'esperan_confirmacion'
        P['4b1_4c1'][k].append({'id': o['id'], 'tipo': o.get('tipo'), 'biblioteca_id': o['biblioteca_id']})
    keep = {o['id'] for o in rec.get('objetos', []) if o['decision'] == 'reutilizar'}
    P['4b1_4c1']['investigar'] = [oid for oid in X['cat_obj'] if oid not in keep and oid not in {z['id'] for z in P['4b1_4c1']['esperan_confirmacion']}]
    P['4a1']['fuera_de_grupos'] = [x['id'] for x in P['4a1']['omitir']] + [x['id'] for x in P['4a1']['solo_variantes']]   # 4a1 (paso00_cadena) no los investiga
    out = {'ok': True, 'accion': 'plan', 'canal': canal, 'capitulo': rec.get('capitulo'), 'episodio': numero_cap(D)[1], 'hora': ahora(), 'plan': P,
           'resumen_reconocer': rec['resumen'], 'pendiente_usuario': rec.get('pendiente_usuario', []),
           'ruta': 'confirmar' if rec.get('pendiente_usuario') else 'seguir',
           'resumen': (f"biblioteca del canal: {len(fichas(canal))} escenarios guardados · capítulo: {rec['resumen'].get('reutilizar', 0)} reutilizados (US$0 en 4a1), "
                       f"{len(P['4a1']['solo_variantes'])} con estados nuevos (4a1 solo variantes), {rec['resumen'].get('nuevo', 0)} nuevos (investigación normal), "
                       f"{rec['resumen'].get('confirmar', 0)} dudosos (confirmar), {rec['resumen'].get('propio', 0)} guardados desde este mismo capítulo")}
    if materializar: out['materializado'] = materializar_en_capitulo(canal, D, rec, P)
    escribir_json(D / 'ramas' / 'biblioteca_plan.json', out)
    return out

def materializar_en_capitulo(canal, D, rec, P):
    """Copia a la carpeta del capítulo lo guardado, para que las cajas de siempre lo lean (no se toca la biblioteca)."""
    hecho = {'moldes': [], 'bases': [], 'variantes': [], 'investigacion': []}
    inv = []
    for e in rec['escenarios']:
        if e['decision'] != 'reutilizar': continue
        i, b = e['id'], e['biblioteca_id']; f = ficha(canal, b) or {}; ver = f.get('version_actual')
        if i in P['4a2']['molde_de_biblioteca']:
            dst = D / 'ramas' / 'moldes' / i
            copiar_carpeta(P['4a2']['molde_de_biblioteca'][i], dst)
            m = leer_json(dst / 'molde.json', {}); m.update(de_biblioteca={'escenario_id': b, 'version': ver}, ok=True); escribir_json(dst / 'molde.json', m)
            hecho['moldes'].append(i)
        if i in P['4a5']['base_de_biblioteca']:
            src = Path(P['4a5']['base_de_biblioteca'][i]); copiar_sin_pisar(src, D / IMG['4a5'] / f'{i}{src.suffix}'); hecho['bases'].append(i)
        for z in P['4a5']['ediciones_reutilizadas']:
            if not z['variante_id'].startswith(i + '__'): continue
            v = next((q for q in f.get('variantes', []) if q['variante_id'] == z['usa']), None)
            if v and v.get('imagen') and (dir_esc(canal, b) / v['imagen']).is_file():
                src = dir_esc(canal, b) / v['imagen']; copiar_sin_pisar(src, D / IMG['4a5'] / f"{z['variante_id']}{src.suffix}"); hecho['variantes'].append(z['variante_id'])
        r = leer_json(dir_esc(canal, b) / 'datos' / ver / 'inv_4a1.json')
        if r: inv.append(dict(r, escenario_id=i, _de_biblioteca={'escenario_id': b, 'version': ver, 'estado_vigente': f.get('estado_vigente')})); hecho['investigacion'].append(i)
    if inv: escribir_json(D / 'respuestas' / 'biblioteca_inv_escenarios.json', {'escenarios': inv, '_taller': {'caja': 'biblioteca', 'usd_real': 0, 'hora': ahora()}})
    return hecho

# ---------------- GUARDAR (caja nueva «4a7 · Guardar escenario aprobado») ----------------
def _objetos_historia_de(X, eid):
    esc = set(map(str, (X['cat_esc'].get(eid) or {}).get('escenas') or []))
    return [oid for oid, o in X['cat_obj'].items() if o.get('tipo') == 'historia' and esc & set(map(str, o.get('escenas') or []))]

def _guardar_objeto_historia(canal, D, X, oid, cap, eid_bib):
    d = dir_obj(canal, oid); f = ficha(canal, oid, 'objetos')
    c = X['cat_obj'].get(oid, {})
    if not f:
        f = {'esquema': ESQUEMA, 'canal': canal, 'objeto_id': oid, 'nombre': c.get('nombre'), 'tipo': 'historia', 'sinonimos': sinonimos_de_nombre(c.get('nombre'), oid),
             'alias_ids': [], 'no_es': [], 'estado': 'aprobado', 'capitulos': [], 'escenarios': [], 'creado': ahora()}
        if X['inv_oh'].get(oid): escribir_json(d / 'datos' / 'inv_4b1.json', X['inv_oh'][oid])
        if X['e2b'].get(oid): escribir_json(d / 'datos' / 'ficha_4p.json', X['e2b'][oid])
        im = imagen(D / IMG['4b2'], oid)
        if im: f['imagen'] = os.path.relpath(copiar_sin_pisar(im, d / 'imagen' / im.name), d)
        f['huella'] = sha_json({'inv': X['inv_oh'].get(oid), 'img': sha_archivo(im) if im else None})
    if cap not in f['capitulos']: f['capitulos'].append(cap)
    if eid_bib not in f['escenarios']: f['escenarios'].append(eid_bib)
    guardar_ficha(d, f, f'capítulo {cap}')
    return oid

def guardar(canal, capitulo, eid_cap, aprobado, auto=False):
    D = carpeta_capitulo(canal, capitulo)
    if D is None: return {'ok': False, 'error': f'no hay carpeta del capítulo {capitulo}'}
    X = datos_capitulo(D); cap, epi = numero_cap(D)
    c = X['cat_esc'].get(eid_cap)
    if not c: return {'ok': False, 'error': f'{eid_cap} no está en el catálogo oficial del capítulo'}
    rec = leer_json(D / 'ramas' / 'biblioteca_reconocer.json') or {}
    bib = fichas(canal)
    propio = next((f for f in bib if any(z.get('episodio') == epi and z.get('id_en_capitulo') == eid_cap for z in f.get('capitulos', []))), None)
    if propio: return {'ok': True, 'accion': 'guardar', 'como': 'ya_guardado', 'escenario_id': propio['escenario_id'], 'id_en_capitulo': eid_cap}
    r = next((x for x in rec.get('escenarios', []) if x['id'] == eid_cap and x.get('como') in ('confirmado_usuario', 'rechazado_usuario')), None)   # lo que decidió el usuario manda
    r = r or reconocer_uno(eid_cap, c.get('nombre'), c.get('int_ext'), bib, epi=epi)   # si no, se reconoce en vivo (la biblioteca pudo cambiar)
    dudosa = None
    if r['decision'] == 'confirmar':
        if not auto: return {'ok': False, 'error': f'{eid_cap} tiene una coincidencia dudosa con {r["biblioteca_id"]}: primero «confirmar» (--es o --nuevo)'}
        # t445 (Ricardo): modo automático. Una coincidencia DUDOSA nunca se fusiona (evita falsos positivos): se guarda como lugar
        # NUEVO con su propio id del capítulo y queda anotado «posible_duplicado_de». No hay bucle: la próxima vez casa por id (regla 1).
        dudosa = {'biblioteca_id': r['biblioteca_id'], 'puntaje': r.get('puntaje'), 'motivo': r.get('motivo'), 'otros': r.get('otros') or []}
    with Candado(canal):
        if r['decision'] == 'reutilizar': res = _guardar_reuso(canal, D, X, c, eid_cap, r['biblioteca_id'], cap, epi, aprobado)
        else: res = _guardar_nuevo(canal, D, X, c, eid_cap, cap, epi, aprobado)
        if auto and res.get('ok'):
            bid = res.get('escenario_id') or eid_cap; dbib = dir_esc(canal, bid); f = ficha(canal, bid) or {}
            # recortes 4a6 del capítulo (sin pisar)
            rc = []
            for p in sorted((D / 'ramas' / 'imagenes' / '4a6').glob(f'{eid_cap}*.png')):
                dst = dbib / 'recortes_4a6' / f'cap{cap:02d}' / p.name if isinstance(cap, int) else dbib / 'recortes_4a6' / str(epi) / p.name
                copiar_sin_pisar(p, dst); rc.append(str(dst))
            cambios = False
            if dudosa and f.get('posible_duplicado_de') != dudosa: f['posible_duplicado_de'] = dudosa; cambios = True
            if rc: f['recortes_4a6'] = sorted(set(f.get('recortes_4a6') or []) | set(rc)); cambios = True
            if cambios and f: guardar_ficha(dbib, f, f'auto 4a7 ({aprobado})' + (f' · posible duplicado de {dudosa["biblioteca_id"]} ({dudosa["puntaje"]})' if dudosa else ''))
            res = dict(res, modo='auto', posible_duplicado_de=dudosa, recortes_4a6=len(rc))
        return res

def _guardar_nuevo(canal, D, X, c, eid, cap, epi, aprobado):
    d = dir_esc(canal, eid)
    if (d / 'ficha.json').is_file(): return {'ok': False, 'error': f'{eid} ya existe en la biblioteca: no se pisa (usa «permanente --modo version» para una versión nueva)'}
    ver = 'v1'; faltan = []; e2a = X['e2a'].get(eid) or {}; inv = X['inv_esc'].get(eid); p4 = X['p4a4'].get(eid)
    sin_molde = bool(e2a.get('solo_recuerdo_o_pantalla'))
    # molde (4a2)
    md = D / 'ramas' / 'moldes' / eid
    molde_ok = (md / 'molde.json').is_file()
    if molde_ok: copiar_carpeta(md, d / 'molde' / ver)
    elif not sin_molde: faltan.append('molde 4a2')
    # datos (4a1 con perfil_real y ambiente_vivo, 4p, 4a4, objetos del lugar 4c1)
    if inv: escribir_json(d / 'datos' / ver / 'inv_4a1.json', inv)
    else: faltan.append('investigación 4a1')
    av = (inv or {}).get('ambiente_vivo') or {}
    meta = dict(X['inv_meta'].get(eid) or {}, autorrevision=bool(av.get('autorrevision')), perfil_real=bool(av.get('perfil_real')),
                densidad_objetivo=(av.get('autorrevision') or {}).get('densidad_objetivo') if isinstance(av.get('autorrevision'), dict) else None)
    if X['blender'].get(eid): escribir_json(d / 'datos' / ver / 'entrada_blender_4a2.json', X['blender'][eid])   # receta con la que Blender armó el molde
    mj = leer_json(md / 'molde.json', {}) if molde_ok else {}
    if e2a: escribir_json(d / 'datos' / ver / 'fichas_4p.json', e2a)
    if p4: escribir_json(d / 'datos' / ver / 'prompts_4a4.json', p4)
    else: faltan.append('prompts 4a4')
    ol = []
    for oid, o in X['e2b'].items():
        if o.get('tipo') == 'lugar' and o.get('escenario_id') == eid:
            q = {'objeto_id': oid, 'nombre': (X['cat_obj'].get(oid) or {}).get('nombre'), 'ficha_4p': o, 'inv_4c1': X['inv_ol'].get(oid)}
            im = imagen(D / IMG['4c2'], oid)
            if im: q['imagen'] = os.path.relpath(copiar_sin_pisar(im, d / 'datos' / ver / 'objetos_lugar' / im.name), d)
            ol.append(q)
    escribir_json(d / 'datos' / ver / 'objetos_lugar.json', ol)
    # base (4a5) y variantes
    bi = imagen(D / IMG['4a5'], eid); base_rel = None
    if bi:
        base_rel = os.path.relpath(copiar_sin_pisar(bi, d / 'base' / ver / f'base{bi.suffix}'), d)
        escribir_json(d / 'base' / ver / 'base.json', {'de_capitulo': cap, 'archivo_origen': str(bi), 'prompt_4a4': (p4 or {}).get('base'), 'sha256': sha_archivo(bi)})
    else: faltan.append('imagen base 4a5')
    cubre = ((p4 or {}).get('base') or {}).get('cubre_variante_id') or f'{eid}__v1'
    variantes = []
    for n, s in enumerate(estados_capitulo(X, eid), 1):
        vid = f'{eid}__{ver}-var{n:02d}'
        im = imagen(D / IMG['4a5'], s['variante_id'])
        q = {'variante_id': vid, 'descripcion': s['variante'], 'version': ver, 'capitulo': cap, 'variante_capitulo_id': s['variante_id'],
             'escenas_origen': s['escenas'], 'persistente': False, 'cubierta_por_base': s['variante_id'] == cubre, 'imagen': None,
             'prompt_4a4': next((z for z in (p4 or {}).get('variantes', []) if z.get('variante_id') == s['variante_id']), None)}
        if q['cubierta_por_base']: q['imagen'] = base_rel
        elif im: q['imagen'] = os.path.relpath(copiar_sin_pisar(im, d / 'variantes' / ver / f'{vid}{im.suffix}'), d); escribir_json(d / 'variantes' / ver / f'{vid}.json', q)
        variantes.append(q)
    oh = [_guardar_objeto_historia(canal, D, X, oid, cap, eid) for oid in _objetos_historia_de(X, eid)]
    huella = sha_json({'inv': inv, 'fijo_4a1': meta.get('fijo_paso'), 'molde': mj.get('huella') or (sha_archivo(md / 'molde.json') if molde_ok else None), 'base': sha_archivo(bi) if bi else None})
    f = {'esquema': ESQUEMA, 'canal': canal, 'escenario_id': eid, 'nombre': c.get('nombre'), 'int_ext': c.get('int_ext'),
         'tipo_lugar': (inv or {}).get('tipo_lugar'), 'solo_recuerdo_o_pantalla': sin_molde,
         'perfil_real_que_es': (av.get('perfil_real') or {}).get('que_es') if isinstance(av.get('perfil_real'), dict) else None,
         'investigacion_4a1': meta, 'molde_4a2': {'huella': mj.get('huella'), 'renders': len(mj.get('renders') or []), 'camaras': mj.get('camaras'), 'blender': mj.get('blender')} if molde_ok else None,
         'sinonimos': sinonimos_de_nombre(c.get('nombre'), eid), 'alias_ids': [], 'no_es': [],
         'estado': 'aprobado', 'aprobado_por': aprobado, 'aprobado_hora': ahora(), 'completo': not faltan, 'faltan': faltan,
         'version_actual': ver, 'huella': huella,
         'versiones_por_id': {ver: {'version': ver, 'desde_capitulo': cap, 'madre': None, 'motivo': 'primera aprobación', 'huella': huella,
                                    'molde': f'molde/{ver}' if molde_ok else None, 'base': base_rel, 'datos': f'datos/{ver}'}},
         'estado_vigente': {'version': ver, 'variante_id': None, 'desde_capitulo': cap},
         'variantes': variantes, 'objetos_lugar': [o['objeto_id'] for o in ol], 'objetos_historia': oh,
         'capitulos': [{'capitulo': cap, 'episodio': epi, 'id_en_capitulo': eid, 'nombre_en_capitulo': c.get('nombre'), 'version': ver, 'como': 'nuevo',
                        'variantes_nuevas': [v['variante_id'] for v in variantes], 'hora': ahora()}], 'creado': ahora()}
    guardar_ficha(d, f, f'aprobado en capítulo {cap} por {aprobado}'); evento(d, 'guardar_nuevo', capitulo=cap, faltan=faltan)
    return {'ok': True, 'accion': 'guardar', 'como': 'nuevo', 'escenario_id': eid, 'version': ver, 'completo': not faltan, 'faltan': faltan,
            'variantes': len(variantes), 'objetos_lugar': len(ol), 'objetos_historia': len(oh), 'carpeta': str(d)}

def _guardar_reuso(canal, D, X, c, eid_cap, b, cap, epi, aprobado):
    """Capítulo que REUTILIZÓ un escenario fijo: no se toca la base ni el molde; se agregan capítulo, alias y variantes nuevas."""
    d = dir_esc(canal, b); f = ficha(canal, b); ver = f['version_actual']
    if any(z['capitulo'] == cap and z['id_en_capitulo'] == eid_cap for z in f['capitulos']): return {'ok': True, 'accion': 'guardar', 'como': 'ya_guardado', 'escenario_id': b}
    reus, nuevas = casar_variantes(canal, b, estados_capitulo(X, eid_cap))
    n0 = sum(1 for v in f['variantes'] if v['version'] == ver); agregadas = []
    for k, s in enumerate(nuevas, 1):
        vid = f'{b}__{ver}-var{n0 + k:02d}'; im = imagen(D / IMG['4a5'], s['variante_id'])
        q = {'variante_id': vid, 'descripcion': s['variante'], 'version': ver, 'capitulo': cap, 'variante_capitulo_id': s['variante_id'], 'escenas_origen': s['escenas'],
             'persistente': False, 'cubierta_por_base': False, 'editada_sobre': s.get('editar_sobre'), 'imagen': None,
             'prompt_4a4': next((z for z in (X['p4a4'].get(eid_cap) or {}).get('variantes', []) if z.get('variante_id') == s['variante_id']), None)}
        if im: q['imagen'] = os.path.relpath(copiar_sin_pisar(im, d / 'variantes' / ver / f'{vid}{im.suffix}'), d); escribir_json(d / 'variantes' / ver / f'{vid}.json', q)
        f['variantes'].append(q); agregadas.append(vid)
    if eid_cap != b: f['alias_ids'] = sorted(set(f.get('alias_ids') or []) | {eid_cap})
    f['sinonimos'] = sorted(set(f.get('sinonimos') or []) | {norm(c.get('nombre'))})
    f['capitulos'].append({'capitulo': cap, 'episodio': epi, 'id_en_capitulo': eid_cap, 'nombre_en_capitulo': c.get('nombre'), 'version': ver, 'como': 'reutilizado',
                           'variantes_reutilizadas': [s.get('usa') for s in reus], 'variantes_nuevas': agregadas, 'aprobado_por': aprobado, 'hora': ahora()})
    oh = [_guardar_objeto_historia(canal, D, X, oid, cap, b) for oid in _objetos_historia_de(X, eid_cap)]
    f['objetos_historia'] = sorted(set(f.get('objetos_historia') or []) | set(oh))
    guardar_ficha(d, f, f'reutilizado en capítulo {cap} como {eid_cap}; {len(agregadas)} variantes nuevas')
    return {'ok': True, 'accion': 'guardar', 'como': 'reutilizado', 'escenario_id': b, 'id_en_capitulo': eid_cap, 'version': ver,
            'variantes_nuevas': agregadas, 'variantes_reutilizadas': len(reus), 'base_repintada': False, 'molde_rehecho': False}

# ---------------- CAMBIOS PERMANENTES ----------------
def permanente(canal, eid, capitulo, variante, modo='auto', toca_geometria=False, motivo=''):
    with Candado(canal):
        d = dir_esc(canal, eid); f = ficha(canal, eid)
        if not f: return {'ok': False, 'error': f'{eid} no está en la biblioteca'}
        v = next((q for q in f['variantes'] if variante in (q['variante_id'], q.get('variante_capitulo_id'))), None)
        if not v:
            best = max(((parecido(variante, q.get('descripcion')), q) for q in f['variantes']), key=lambda t: t[0], default=(0, None))
            v = best[1] if best[0] >= UMBRAL_VARIANTE else None
        if not v: return {'ok': False, 'error': f'no encuentro la variante «{variante}» en {eid}'}
        if modo == 'auto': modo = 'version' if toca_geometria else 'variante'
        cap = int(capitulo)
        if modo == 'variante':
            v['persistente'] = True; v['persistente_desde_capitulo'] = cap; v['motivo_persistente'] = motivo
            f['estado_vigente'] = {'version': f['version_actual'], 'variante_id': v['variante_id'], 'desde_capitulo': cap, 'motivo': motivo or v['descripcion']}
            guardar_ficha(d, f, f'variante persistente {v["variante_id"]} desde el capítulo {cap}')
            return {'ok': True, 'accion': 'permanente', 'modo': 'variante', 'estado_vigente': f['estado_vigente'],
                    'efecto': 'molde igual; las variantes nuevas se editan sobre esta imagen; la base original queda para recuerdos'}
        vieja = f['version_actual']; nueva = f'v{int(vieja[1:]) + 1}'
        while nueva in f['versiones_por_id']: nueva = f'v{int(nueva[1:]) + 1}'
        copiar_carpeta(d / 'datos' / vieja, d / 'datos' / nueva)
        escribir_json(d / 'datos' / nueva / 'cambio_permanente.json', {'desde_capitulo': cap, 'madre': vieja, 'variante_origen': v['variante_id'],
                                                                         'descripcion': v['descripcion'], 'motivo': motivo, 'toca_geometria': True,
                                                                         'nota': 'Blender (4a2) re-arma con la receta de inv_4a1.json + este cambio; 4a5 pinta la base UNA vez editando la imagen de la variante origen'})
        f['versiones_por_id'][nueva] = {'version': nueva, 'desde_capitulo': cap, 'madre': vieja, 'motivo': motivo or v['descripcion'], 'huella': None,
                                         'molde': None, 'base': None, 'datos': f'datos/{nueva}', 'referencia_para_pintar': v.get('imagen'), 'estado': 'pendiente_molde_y_base'}
        f['version_actual'] = nueva; f['estado_vigente'] = {'version': nueva, 'variante_id': None, 'desde_capitulo': cap, 'motivo': motivo or v['descripcion']}
        guardar_ficha(d, f, f'versión nueva {nueva} (madre {vieja}) desde el capítulo {cap}')
        return {'ok': True, 'accion': 'permanente', 'modo': 'version', 'version_nueva': nueva, 'madre_intacta': vieja,
                'pendiente': ['4a2 re-arma el molde de ' + nueva, '4a5 pinta 1 base de ' + nueva + ' editando la variante origen']}

def guardar_version_pendiente(canal, eid, D, eid_cap):
    """Cuando la versión nueva ya tiene molde y base en un capítulo, se copian a molde/vN y base/vN."""
    d = dir_esc(canal, eid); f = ficha(canal, eid); ver = f['version_actual']; vd = f['versiones_por_id'][ver]
    md = Path(D) / 'ramas' / 'moldes' / eid_cap
    if (md / 'molde.json').is_file() and not vd.get('molde'): copiar_carpeta(md, d / 'molde' / ver); vd['molde'] = f'molde/{ver}'
    bi = imagen(Path(D) / IMG['4a5'], eid_cap)
    if bi and not vd.get('base'): vd['base'] = os.path.relpath(copiar_sin_pisar(bi, d / 'base' / ver / f'base{bi.suffix}'), d)
    if vd.get('molde') and vd.get('base'): vd['estado'] = 'lista'
    guardar_ficha(d, f, f'versión {ver}: molde={bool(vd.get("molde"))} base={bool(vd.get("base"))}'); return vd

# ---------------- BUSCAR / LISTAR ----------------
def resumen_ficha(f):
    return {'escenario_id': f['escenario_id'], 'nombre': f.get('nombre'), 'int_ext': f.get('int_ext'), 'version_actual': f.get('version_actual'),
            'estado': f.get('estado'), 'completo': f.get('completo'), 'capitulos': [z['capitulo'] for z in f.get('capitulos', [])],
            'variantes': len(f.get('variantes', [])), 'estado_vigente': f.get('estado_vigente'), 'alias_ids': f.get('alias_ids', [])}

def listar(canal):
    e = fichas(canal); o = fichas(canal, 'objetos')
    return {'ok': True, 'accion': 'listar', 'canal': canal, 'escenarios': [resumen_ficha(f) for f in e],
            'objetos_historia': [{'objeto_id': x['objeto_id'], 'nombre': x.get('nombre'), 'capitulos': x.get('capitulos')} for x in o]}

def buscar(canal, texto):
    out = []
    for f in fichas(canal):
        r = reconocer_uno(texto, texto, None, [f])
        p = 1.0 if r['decision'] == 'reutilizar' else max([parecido(texto, c) for c in _candidatos(f)] + [0])
        if p >= 0.3: out.append(dict(resumen_ficha(f), puntaje=p, como=r['como'] or 'parecido'))
    out.sort(key=lambda x: -x['puntaje'])
    return {'ok': True, 'accion': 'buscar', 'texto': texto, 'resultados': out}

# ---------------- CLI ----------------
def main(argv=None):
    ap = argparse.ArgumentParser(prog='biblioteca.py', description='Biblioteca de escenarios del canal (orden 62). Gratis, sin red.')
    sp = ap.add_subparsers(dest='accion', required=True)
    for n in ('reconocer', 'confirmar', 'plan', 'guardar', 'permanente', 'buscar', 'listar'):
        p = sp.add_parser(n); p.add_argument('--canal', required=True)
        if n in ('reconocer', 'confirmar', 'plan', 'guardar', 'permanente'): p.add_argument('--capitulo', required=True)
        if n == 'confirmar': p.add_argument('--escenario', required=True); p.add_argument('--es'); p.add_argument('--nuevo', action='store_true')
        if n == 'plan': p.add_argument('--materializar', action='store_true'); p.add_argument('--reconocer', action='store_true')
        if n == 'guardar':
            p.add_argument('--escenario'); p.add_argument('--ids'); p.add_argument('--decisiones'); p.add_argument('--todos', action='store_true'); p.add_argument('--aprobado', required=True); p.add_argument('--auto', action='store_true')
        if n == 'permanente':
            p.add_argument('--escenario', required=True); p.add_argument('--variante', required=True)
            p.add_argument('--modo', choices=['auto', 'variante', 'version'], default='auto'); p.add_argument('--toca-geometria', action='store_true'); p.add_argument('--motivo', default='')
        if n == 'buscar': p.add_argument('texto')
    a = ap.parse_args(argv)
    if a.accion == 'reconocer': return reconocer(a.canal, a.capitulo)
    if a.accion == 'confirmar': return confirmar(a.canal, a.capitulo, a.escenario, a.es, a.nuevo)
    if a.accion == 'plan': return plan(a.canal, a.capitulo, a.materializar, a.reconocer)
    if a.accion == 'permanente': return permanente(a.canal, a.escenario, a.capitulo, a.variante, a.modo, a.toca_geometria, a.motivo)
    if a.accion == 'buscar': return buscar(a.canal, a.texto)
    if a.accion == 'listar': return listar(a.canal)
    if a.accion == 'guardar':
        if a.escenario: ids = [a.escenario]
        elif a.ids:
            D = carpeta_capitulo(a.canal, a.capitulo); cat = datos_capitulo(D)['cat_esc'] if D else {}
            ids = [x.strip() for x in a.ids.split(',') if x.strip()]
            if [x for x in ids if x not in cat]: return {'ok': False, 'error': f"no están en el catálogo del capítulo: {[x for x in ids if x not in cat]}", 'catalogo': list(cat)}
        elif a.decisiones:   # exportado por la galería 4a6 («⬇ decisiones»)
            j = leer_json(a.decisiones, {}) or {}; ids = [x['id'] for x in j.get('decisiones', []) if x.get('estado') == 'aprobado' and '__' not in x['id']]
        elif a.todos:
            D = carpeta_capitulo(a.canal, a.capitulo); ids = list(datos_capitulo(D)['cat_esc']) if D else []
        else: return {'ok': False, 'error': 'falta --escenario, --decisiones o --todos'}
        res = [guardar(a.canal, a.capitulo, i, a.aprobado, auto=getattr(a, 'auto', False)) for i in ids]
        return {'ok': all(r.get('ok') for r in res), 'accion': 'guardar', 'resultados': res}

if __name__ == '__main__':
    try: r = main()
    except SystemExit: raise
    except Exception as exc: r = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + '\n')
