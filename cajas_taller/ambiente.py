"""MYIA · Taller n8n · orden 61: ZONA AMBIENTE de los escenarios (genérico, cualquier canal).
Dos zonas: la HISTORIA usa ids oficiales de la caja 4 (y se filtran los ids inventados); el AMBIENTE (ambiente_vivo de 4a1)
es decorado libre con ids propios amb-<escenario_id>-<slug> y origen «ambiente». El ambiente se valida por forma/esquema,
no contra la lista oficial.
ASCENSO: si un elemento de ambiente coincide con un objeto que la historia usa (catálogo oficial, 4b/4c o pasos siguientes),
se marca ascender_a_oficial = {objeto_id, motivo} y conserva TODOS sus datos; no se borra. Quien pinta o arma en 3D usa el
objeto oficial y no duplica el bloque.
Orden 61b: PASO 1 perfil_real (cómo es de verdad el lugar: sirve para la Luna, los Alpes, el fondo del mar o un cuarto) y
fondo_lejano (lo que se ve más allá de la zona de acción y no se construye). extras_fondo = vida de fondo con tipo persona/animal."""
import re, unicodedata

LISTAS = ('superficies', 'utileria_ambiente', 'senales_uso', 'extras_fondo', 'ambiente_por_escena', 'vista_por_aberturas', 'fondo_lejano')
CON_ID = ('utileria_ambiente', 'extras_fondo')
PATRON = re.compile(r'^amb-[a-z0-9-]+$')
NO_IDS_HISTORIA = ('objeto_id', 'personaje_id', 'forma_id', 'escenario_id', 'id')

def slug(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-') or 'x'

def _norm_nombre(s): return slug(s).replace('-', ' ').strip()

def normalizar(esc_id, am):
    """Limpia ambiente_vivo de un escenario: perfil_real (dict) + solo listas conocidas y dicts, sin ids de historia, ambiente_id válido y único, origen «ambiente»."""
    am = am if isinstance(am, dict) else {}
    out, cambios, vistos = {}, [], set()
    pr = am.get('perfil_real')
    if not isinstance(pr, dict):
        if pr not in (None, {}): cambios.append('perfil_real no era un objeto → {}')
        pr = {}
    out['perfil_real'] = {kk: vv for kk, vv in pr.items() if kk not in NO_IDS_HISTORIA}
    for k in LISTAS:
        keep = []
        for q in (am.get(k) or []):
            if not isinstance(q, dict): continue
            q = {kk: vv for kk, vv in q.items() if kk not in NO_IDS_HISTORIA}
            if k in CON_ID:
                aid = str(q.get('ambiente_id') or '')
                if not PATRON.match(aid) or not aid.startswith('amb-'):
                    nuevo = f"amb-{slug(esc_id)}-{'extras-' if k == 'extras_fondo' else ''}{slug(q.get('nombre') or q.get('que_hacen') or q.get('donde'))}"
                    cambios.append(f'{aid or "(sin id)"} → {nuevo}'); aid = nuevo
                base, n = aid, 2
                while aid in vistos: aid = f'{base}-{n}'; n += 1
                vistos.add(aid); q['ambiente_id'] = aid
            if k == 'extras_fondo' and q.get('tipo') not in ('persona', 'animal'):
                q['tipo'] = 'animal' if re.search(r'(^|-)(animal(es)?|pez|peces|aves?|perros?|gatos?|ganado|vacas?|caballos?|cardumen|bandada|insectos?|pajaros?)(-|$)', slug(q.get('aspecto')) + '-' + slug(q.get('que_hacen'))) else 'persona'
            if k != 'ambiente_por_escena': q['origen'] = 'ambiente'
            keep.append(q)
        out[k] = keep
    if isinstance(am.get('autorrevision'), dict): out['autorrevision'] = am['autorrevision']   # orden 61c: densidad objetivo, capas y lo agregado al revisar
    return out, cambios

def conteo(am): return {k: len((am or {}).get(k) or []) for k in LISTAS}

def perfil_corto(am):
    """Lo esencial de perfil_real para galería y plan de pintura: qué es, paleta, lo que NO hay, luz/cielo, condiciones."""
    pr = (am or {}).get('perfil_real') or {}
    if not isinstance(pr, dict) or not pr: return {}
    return {'que_es': pr.get('que_es'), 'paleta_de_colores': pr.get('paleta_de_colores') or [], 'lo_que_no_hay': pr.get('lo_que_no_hay') or [],
            'luz_natural_y_cielo': pr.get('luz_natural_y_cielo'), 'condiciones_fisicas': pr.get('condiciones_fisicas'),
            'escala_y_horizonte': pr.get('escala_y_horizonte')}

def marcar_ascenso(am, objetos, fuente):
    """objetos = [{'id', 'nombre'}] que la historia usa. Marca (no borra) los elementos de ambiente que coinciden. Devuelve la lista de ascensos."""
    idx = {}
    for o in objetos or []:
        if not isinstance(o, dict) or not o.get('id'): continue
        for k in (o.get('nombre'), o['id'], re.sub(r'^(obj|objeto)-', '', str(o['id']))):
            if k: idx.setdefault(_norm_nombre(k), o)
    asc = []
    for q in (am or {}).get('utileria_ambiente') or []:
        if not isinstance(q, dict): continue
        o = idx.get(_norm_nombre(q.get('nombre')))
        if o is not None:
            q['ascender_a_oficial'] = {'objeto_id': o['id'], 'motivo': f"coincide con el objeto oficial «{o.get('nombre') or o['id']}» ({fuente})", 'conserva_datos': True}
            asc.append({'ambiente_id': q.get('ambiente_id'), 'nombre': q.get('nombre'), 'objeto_id': o['id'], 'fuente': fuente})
    return asc
