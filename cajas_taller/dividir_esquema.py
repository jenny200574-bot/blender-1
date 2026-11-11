"""MYIA · Taller · DIVIDIR ESQUEMA (orden t331u, Ricardo: «pártelo en dos llamadas estratégicas que no cambien los resultados»).
GENÉRICO, cualquier paso y cualquier canal. Vertex/Argon rechaza con 400 los esquemas de salida estructurada de más de ~205
propiedades (medido t326u). Si el esquema de un paso pasa de `limite_propiedades` y el paso tiene grupos declarados en
llamadas_config.json → «dividir_esquema.pasos.<paso>», el pedido se parte en N llamadas (una por parte, en orden):
  - cada parte pide SOLO sus campos (raíz + campos de cada registro de la lista), con el MISMO texto de entrada completo;
  - una parte con «contexto_de» recibe además, como CONTEXTO FIJO, los campos declarados de la salida de la parte anterior
    (por id del registro), para que lo que pide quede coherente con ella;
  - al final se UNEN en la MISMA estructura del esquema completo (por id del registro) y se VALIDA de nuestro lado contra el
    esquema COMPLETO original (tipos, obligatorios, enum, conteos y que no sobre nada que no esté en el esquema).
Sin red, sin pagos: solo arma esquemas, contexto, unión y validación."""
import json, copy
from pathlib import Path
import llamada_segura as LS

def config(paso):
    """(limite, cfg_del_paso o None) desde llamadas_config.json → dividir_esquema."""
    try: d = (json.loads(LS.CONFIG_LLAMADAS.read_text(encoding='utf-8')).get('dividir_esquema') or {})
    except Exception: d = {}
    return int(d.get('limite_propiedades') or 180), (d.get('pasos') or {}).get(paso)

def contar(x):
    """Propiedades totales del esquema (lo que cuenta Vertex)."""
    if isinstance(x, dict): return len(x.get('properties') or {}) + sum(contar(v) for v in x.values())
    if isinstance(x, list): return sum(contar(v) for v in x)
    return 0

def _item(esq, lista):
    return esq['properties'][lista]['items']

def sub_esquema(esq, cfg, parte):
    """Esquema de UNA parte: raíz = parte['raiz'] (+ la lista), registro = clave + parte['campos'] (o todos menos parte['excluir'])."""
    e = copy.deepcopy(esq); lista, clave = cfg['lista'], cfg['clave']
    it = _item(e, lista); props = it['properties']
    if 'campos' in parte: keep = [clave] + [k for k in parte['campos'] if k != clave]
    else: keep = [k for k in props if k not in set(parte.get('excluir') or [])]
    it['properties'] = {k: props[k] for k in props if k in keep}
    if 'required' in it: it['required'] = [k for k in it['required'] if k in keep]
    if 'propertyOrdering' in it: it['propertyOrdering'] = [k for k in it['propertyOrdering'] if k in keep]
    rz = parte.get('raiz', 'todo')
    raiz = list(e['properties']) if rz == 'todo' else [lista] + [k for k in rz if k != lista]
    e['properties'] = {k: v for k, v in e['properties'].items() if k in raiz}
    if 'required' in e: e['required'] = [k for k in e['required'] if k in raiz]
    if 'propertyOrdering' in e: e['propertyOrdering'] = [k for k in e['propertyOrdering'] if k in raiz]
    if e.get('title'): e['title'] = f"{e['title']} · parte {parte['nombre']}"
    return e

def plan(paso, esq):
    """None si no hay que dividir (cabe o no hay grupos declarados). Si hay: dict con las partes y sus esquemas.
    Revisa que las partes cubran TODOS los campos del esquema completo, sin repetir (salvo la clave) → la unión es exacta."""
    limite, cfg = config(paso)
    n = contar(esq)
    if not cfg or n <= limite: return None
    lista, clave = cfg['lista'], cfg['clave']
    todos_it = list(_item(esq, lista)['properties']); todos_rz = list(esq['properties'])
    partes, vistos_it, vistos_rz = [], {}, {}
    for pt in cfg['partes']:
        s = sub_esquema(esq, cfg, pt); m = contar(s)
        if m > limite: raise ValueError(f'dividir_esquema {paso}: la parte {pt["nombre"]} tiene {m} propiedades (> {limite})')
        for k in _item(s, lista)['properties']:
            if k != clave: vistos_it.setdefault(k, []).append(pt['nombre'])
        for k in s['properties']:
            if k != lista: vistos_rz.setdefault(k, []).append(pt['nombre'])
        partes.append(dict(pt, esquema=s, propiedades=m))
    falta = [k for k in todos_it if k != clave and k not in vistos_it] + [k for k in todos_rz if k != lista and k not in vistos_rz]
    doble = [k for k, v in list(vistos_it.items()) + list(vistos_rz.items()) if len(v) > 1]
    if falta or doble: raise ValueError(f'dividir_esquema {paso}: partes mal declaradas (faltan {falta}, repetidos {doble})')
    return {'paso': paso, 'lista': lista, 'clave': clave, 'limite': limite, 'propiedades_completo': n, 'partes': partes,
            'orden_raiz': todos_rz, 'orden_item': todos_it}

def texto_formato(pl, parte):
    """Instrucción que reemplaza el FORMATO del esquema completo en el texto de UNA parte."""
    s = json.dumps(parte['esquema'], ensure_ascii=False, indent=1)
    otras = [p['nombre'] for p in pl['partes'] if p['nombre'] != parte['nombre']]
    return (f"\n\nPEDIDO DIVIDIDO (parte {parte['nombre']} de {len(pl['partes'])}: {parte.get('nota', '')}). El análisis es el MISMO de siempre "
            f"(misma entrada completa, mismo método, mismas reglas); solo cambia QUÉ campos devuelves en esta llamada. Los demás campos "
            f"van en la(s) parte(s) {', '.join(otras)} y el código los une por «{pl['clave']}».\n"
            f"FORMATO DE SALIDA OBLIGATORIO (JSON Schema, parte {parte['nombre']}; la respuesta debe validar contra él):\n" + s)

def contexto(pl, parte, obj_prev):
    """JSON del contexto fijo para una parte con «contexto_de»: por registro, la clave + los campos declarados de la parte anterior."""
    lista, clave = pl['lista'], pl['clave']; campos = parte.get('contexto_campos') or []
    regs = [{k: v[k] for k in [clave] + campos if k in v} for v in ((obj_prev or {}).get(lista) or []) if isinstance(v, dict)]
    return json.dumps({lista: regs}, ensure_ascii=False, separators=(',', ':'))

def rotulos_contexto(parte):
    return (f"\n=== CONTEXTO_FIJO_PARTE_{parte['contexto_de']}_JSON (ya decidido en la parte {parte['contexto_de']}: NO lo cambies; "
            f"todo lo que devuelvas debe ser coherente con estas medidas, planta, aberturas, muebles y objetos) ===\n", '\n=== FIN CONTEXTO FIJO ===\n')

def unir(pl, objs):
    """Une las salidas de las partes (en orden) en la estructura del esquema completo. Registros por clave, en el orden de la 1.ª parte."""
    lista, clave = pl['lista'], pl['clave']
    out, orden, regs = {}, [], {}
    for pt, o in zip(pl['partes'], objs):
        o = o or {}
        for k, v in o.items():
            if k == lista: continue
            if k in (pt['esquema'].get('properties') or {}): out[k] = v
        for r in (o.get(lista) or []):
            if not isinstance(r, dict): continue
            i = r.get(clave)
            if i not in regs: regs[i] = {}; orden.append(i)
            for k, v in r.items():
                if k == clave or k in _item(pt['esquema'], lista)['properties']: regs[i][k] = v
    out[lista] = [regs[i] for i in orden]
    def ordenar(d, claves): return {**{k: d[k] for k in claves if k in d}, **{k: v for k, v in d.items() if k not in claves}}
    out[lista] = [ordenar(r, pl.get('orden_item') or []) for r in out[lista]]
    return ordenar(out, pl.get('orden_raiz') or [])   # mismo orden de campos que el esquema completo

def sobrantes(obj, esq, ruta='$', out=None):
    """Campos que NO están en el esquema (validar_esquema no los mira)."""
    out = [] if out is None else out
    if isinstance(esq, dict) and isinstance(obj, dict) and 'properties' in esq:
        for k, v in obj.items():
            if k not in esq['properties']: out.append(f'{ruta}.{k}: no está en el esquema')
            else: sobrantes(v, esq['properties'][k], f'{ruta}.{k}', out)
    elif isinstance(esq, dict) and isinstance(obj, list) and isinstance(esq.get('items'), dict):
        for n, v in enumerate(obj): sobrantes(v, esq['items'], f'{ruta}[{n}]', out)
    elif isinstance(esq, dict) and 'anyOf' in esq:
        pass
    return out

def validar(obj, esq_completo):
    """Errores (vacío = válido) de la UNIÓN contra el esquema COMPLETO original: tipos, obligatorios, enum, conteos y sobrantes."""
    return LS.validar_esquema(obj, esq_completo) + sobrantes(obj, esq_completo)
