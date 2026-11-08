"""Escalera de formas por datos. Sin nombres de objeto/canal en las reglas.
Exacta→similar con umbral→composición explícita→Argon autorizado/off→FALTA.
"""
import re,unicodedata,math
from pathlib import Path

def tokens(text,synonyms,stop):
    text=unicodedata.normalize('NFKD',str(text)).encode('ascii','ignore').decode().lower();words=re.findall(r'[a-z0-9]+',text);out=set()
    for word in words:
        seen=set()
        while word in synonyms and word not in seen:seen.add(word);word=synonyms[word]
        if word not in stop:out.add(word)
    return out

def similitud(query,recipe,policy):
    sy=policy['synonyms'];stop=set(policy['stop_words']);q=tokens(' '.join(query.get('words',[]))+' '+query.get('text',''),sy,stop);c=tokens(' '.join(recipe.get('words',[])),sy,stop);qt=tokens(query.get('use',''),sy,stop);ct=tokens(' '.join(recipe.get('uses',[])),sy,stop)
    shape=1.0 if query.get('shape') and query.get('shape') in recipe.get('shapes',[]) else 0.0
    lexical=len(q&c)/max(1,len(q|c));use=len(qt&ct)/max(1,len(qt|ct));dimensions=0.0
    if query.get('dimensions_m') and recipe.get('reference_dimensions_m'):
        a=query['dimensions_m'];b=recipe['reference_dimensions_m']
        if min(a+b)<=0:raise ValueError('Dimensiones no positivas')
        ratios=[x/y for x,y in zip(a,b)];g=math.exp(sum(math.log(x) for x in ratios)/len(ratios));dimensions=math.exp(-sum(abs(math.log(x/g)) for x in ratios)/len(ratios))
    elif query.get('dimensions_m') and recipe.get('scale_policy')=='independent_axes':dimensions=1.0
    scores={'shape':shape,'dimensions':dimensions,'use':use,'words':lexical};weights=policy['weights'];total=sum(weights[k]*scores[k] for k in weights)/sum(weights.values())
    conflict=not set(query.get('required_features',[]))<=set(recipe.get('features',[]))
    return {'score':total,'components':scores,'conflict':conflict}

def guardar_receta(recipe,path):
    """Biblioteca declarativa versionada; no guardar ni ejecutar código del proveedor."""
    from seguridad import leer,guardar,sha
    if not isinstance(recipe,dict) or not recipe.get('id') or not recipe.get('source'):raise ValueError('Receta sin identidad/procedencia')
    parts=recipe.get('parts')
    if not isinstance(parts,list) or not parts:raise ValueError('Receta nueva debe traer despiece declarativo; no código o bbox')
    required={'id','shape','dimensions_m','position_m','rotation_deg','material','source'}
    if any(not required<=set(p) or p['shape'] not in {'BOX','ELLIPSOID','CYLINDER','CONE','TORUS','MESH','CURVE'} or len(p['dimensions_m'])!=3 or min(p['dimensions_m'])<=0 for p in parts):raise ValueError('Despiece nuevo incompleto o no admitido')
    if any(not {'rgba','metallic','roughness'}<=set(p['material']) for p in parts):raise ValueError('Material nuevo incompleto')
    path=Path(path);library=leer(path) if path.exists() else {'recipes':[]}
    if any(x['id']==recipe['id'] for x in library['recipes']):raise ValueError('ID de receta ya existe: no sustituir aprobaciones')
    library['recipes'].append(recipe);guardar(path,library)
    return {'path':str(path),'sha256':sha(path),'recipe_id':recipe['id'],'archived_previous':True}

def buscar(query,catalog,policy,*,switch=None,paid_ok=False,argon_provider=None,ledger_before=None,recipe_library_path=None,runtime=None):
    if not 0<=policy['minimum_score']<=1:raise ValueError('Umbral inválido')
    recipes=catalog['recipes'];byid={r['id']:r for r in recipes};log=[];exact=query.get('formula') or catalog.get('por_id',{}).get(query['id'])
    def accepted(recipe,step,score):
        return {'state':'FOUND','object':query['id'],'step':step,'score':score,'recipe':recipe,'dimensions_m':query['dimensions_m'],'provenance':{'query_source':query['source'],'recipe_source':recipe['source'],'step':step,'score':score},'attempts':log}
    if exact in byid and not byid[exact].get('bbox_only'):
        recipe=byid[exact]
        if set(query.get('required_features',[]))<=set(recipe.get('features',[])):return accepted(recipe,1,1.0)
        log.append({'step':1,'recipe':exact,'state':'INCOMPATIBLE_FEATURES'})
    else:log.append({'step':1,'recipe':exact,'state':'NOT_FOUND_OR_BBOX'})
    ranked=[]
    for recipe in recipes:
        if recipe.get('bbox_only'):continue
        score=similitud(query,recipe,policy);ranked.append((score['score'],recipe,score))
    ranked.sort(key=lambda row:(-row[0],row[1]['id']))
    for score,recipe,details in ranked:
        log.append({'step':2,'recipe':recipe['id'],**details,'minimum':policy['minimum_score']})
        if not details['conflict'] and score>=policy['minimum_score']:return accepted(recipe,2,score)
    parts=query.get('parts')
    if parts:
        required={'id','shape','dimensions_m','position_m','rotation_deg','material','source'}
        bad=[p.get('id') for p in parts if not required<=set(p) or p['shape'] not in policy['primitive_shapes'] or min(p['dimensions_m'])<=0]
        if not bad:
            recipe={'id':query['id']+'.composition','parts':parts,'source':query['source'],'features':query.get('required_features',[])};return accepted(recipe,3,1.0)
        log.append({'step':3,'state':'INCOMPLETE_PARTS','parts':bad})
    else:log.append({'step':3,'state':'NO_DECLARED_PARTS'})
    if runtime is not None:
        recipe,receipt=runtime.generate(query);log.append({'step':4,**receipt})
        if recipe is not None:
            result=accepted(recipe,4,1.0);result['provider_receipt']=receipt;return result
        return {'state':'FALTA','object':query['id'],'step':5,'score':None,'producer':query.get('producer','ADN OBJ + catálogo'),'missing':[receipt.get('reason','Proveedor sin receta válida')],'attempts':log,'spent_usd':receipt.get('spent_usd',0)}
    disabled=switch is None or Path(switch).exists()
    if disabled or not paid_ok or argon_provider is None or ledger_before is None or recipe_library_path is None:log.append({'step':4,'state':'OFF_OR_NOT_AUTHORIZED','spent_usd':0})
    else:
        # El llamador de confianza debe registrar autorización/tope ANTES de usar un proveedor.
        receipt=ledger_before(query)
        if not receipt.get('authorized') or receipt.get('remaining_usd',0)<=0:raise ValueError('No hay ledger/autorización previa de gasto')
        recipe=argon_provider(query,receipt)
        if not isinstance(recipe,dict) or not recipe.get('source') or not recipe.get('validated'):raise ValueError('Receta nueva sin validación/procedencia')
        stored=guardar_receta(recipe,recipe_library_path);result=accepted(recipe,4,1.0);result['library_receipt']=stored;return result
    return {'state':'FALTA','object':query['id'],'step':5,'score':None,'producer':query.get('producer','4a2/escenario vivo + ADN objeto'),'missing':['receta detallada compatible o partes/medidas/materiales verificables'],'attempts':log,'spent_usd':0}
