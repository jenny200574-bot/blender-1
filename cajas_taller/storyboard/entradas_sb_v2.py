#!/usr/bin/env python3
"""SB entradas2.0: ensamblador UNIVERSAL INACTIVO. Solo lectura, biblioteca estándar.
No importa código activo, no accede a red, no guarda archivos ni decide cámaras.
CLI imprime JSON a stdout. La salida es CONTEXTO, nunca contrato de viñeta aprobado.
"""
import argparse
import copy
import hashlib
import json
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

VERSION = "entradas_sb_v2.0.0_inactivo"
DEFAULT_ROOT = Path('/opt/myia-taller-n8n')
VIEW_ORDER = ('frente', 'espalda')

class InputError(ValueError):
    pass

def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,119}', value) or '..' in value:
        raise InputError('ID_INSEGURO')
    return value

def number(value):
    if isinstance(value, bool): raise InputError('NUMERO_BOOLEANO')
    try: d=Decimal(str(value))
    except Exception as ex: raise InputError('NUMERO_INVALIDO') from ex
    if not d.is_finite(): raise InputError('NUMERO_NO_FINITO')
    return d

def frame_boundary(seconds):
    d=number(seconds)
    if d<0: raise InputError('TIEMPO_NEGATIVO')
    return int((d*24).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def timing24(t, duration=None):
    if not isinstance(t, (list,tuple)) or len(t)!=2: raise InputError('INTERVALO_INVALIDO')
    a,b=map(number,t)
    if a<0 or b<=a or (duration is not None and b>number(duration)): raise InputError('INTERVALO_FUERA_DE_ESCENA')
    lo,hi=frame_boundary(a)+1,frame_boundary(b)
    if hi<lo: raise InputError('INTERVALO_MENOR_DE_UN_CUADRO')
    return {'fps':24,'start_frame':lo,'end_frame_inclusive':hi,'frame_count':hi-lo+1,
            'source_seconds':list(t),'quantized_seconds':[float(Decimal(lo-1)/24),float(Decimal(hi)/24)],
            'source_kind':'tiempo_01_no_voz_medida','conversion':'ROUND_HALF_UP; base1; fin inclusivo; NO cambia fuente ni duración'}

def norm(text):
    t=''.join(c for c in unicodedata.normalize('NFKD',str(text or '')) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+',t.lower()))

def gaze_norm(text):
    return ' '.join(x for x in norm(text).split() if x not in {'a','al','el','la','los','las','hacia'})

def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

class Reader:
    def __init__(self, root):
        self.root=Path(root).resolve();self.audit={}
    def path(self, value):
        p=Path(value)
        if p.is_absolute():
            try: p=p.relative_to(self.root)
            except ValueError:
                try:p=p.relative_to(DEFAULT_ROOT)
                except ValueError as e:raise InputError('RUTA_FUERA_DEL_TALLER') from e
        parts=p.parts
        if '..' in parts or any(x.lower() in {'secrets_argon','.secrets','claves','.myia_taller'} or x.lower().startswith(('claves_','secrets_')) or x.lower().startswith('.env') or (x.lower().startswith('vertex') and x.lower().endswith('.json')) for x in parts):
            raise InputError('RUTA_PROTEGIDA')
        q=self.root/p
        if not q.resolve().is_relative_to(self.root):raise InputError('SYMLINK_FUERA_DEL_TALLER')
        return q
    def bytes(self, value):
        p=self.path(value);b=p.read_bytes();self.audit[str(p.relative_to(self.root))]=hashlib.sha256(b).hexdigest();return b
    def json(self,value,default=None):
        p=self.path(value)
        if not p.exists():return copy.deepcopy(default)
        try:return json.loads(self.bytes(value).decode('utf8'),parse_constant=lambda s:(_ for _ in ()).throw(InputError('JSON_NO_FINITO')))
        except (UnicodeError,json.JSONDecodeError) as ex:raise InputError('JSON_INVALIDO:'+str(p.relative_to(self.root))) from ex
    def image_digest(self,value):
        p=self.path(value)
        if p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:raise InputError('REFERENCIA_NO_ES_IMAGEN')
        if not p.is_file():return None
        b=self.bytes(p)
        if not (b.startswith(b'\x89PNG') or b.startswith(b'\xff\xd8\xff') or (b.startswith(b'RIFF') and b[8:12]==b'WEBP')):raise InputError('IMAGEN_FORMATO_INVALIDO')
        return hashlib.sha256(b).hexdigest()
    def logical(self,value):return str(DEFAULT_ROOT/self.path(value).relative_to(self.root))

def resolve_chapter(reader, canal, capitulo):
    safe_id(canal);base=reader.path(Path('trabajo/paso00_cadena')/canal)
    if isinstance(capitulo,bool):raise InputError('CAPITULO_INVALIDO')
    if isinstance(capitulo,int) or (isinstance(capitulo,str) and capitulo.isdigit()):
        n=int(capitulo)
        if n<0:raise InputError('CAPITULO_INVALIDO')
        choose=lambda name,m:int(m.group(1))==n
    elif isinstance(capitulo,str) and re.fullmatch(r'ep-[A-Za-z0-9-]+',capitulo):
        choose=lambda name,m:m.group(2)==capitulo
    elif isinstance(capitulo,str) and re.fullmatch(r'cap[0-9]+_ep-[A-Za-z0-9-]+',capitulo):
        choose=lambda name,m:name==capitulo
    else:raise InputError('CAPITULO_INVALIDO')
    matches=[]
    for p in sorted(base.iterdir()) if base.is_dir() else []:
        m=re.fullmatch(r'cap([0-9]+)_(ep-[A-Za-z0-9-]+)',p.name)
        if m and p.is_dir() and choose(p.name,m):matches.append(reader.path(p))
    if len(matches)!=1:raise InputError('CAPITULO_AMBIGUO' if matches else 'CAPITULO_NO_ENCONTRADO')
    return matches[0]

def scene_number(value):
    if isinstance(value,bool):raise InputError('ESCENA_INVALIDA')
    if str(value).isdigit():
        if int(value)<1:raise InputError('ESCENA_INVALIDA')
        return str(int(value))
    if isinstance(value,str):return safe_id(value)
    raise InputError('ESCENA_INVALIDA')

def sanitize_01(value, exclusions, path=''):
    """Conserva todos los campos de acción; excluye solo identidad y respuestas opacas.
    Las rutas excluidas quedan auditadas, sin volcar su contenido. El JSON fuente no cambia.
    No pretende borrar rasgos semánticos del diálogo literal ni del guion.
    """
    if isinstance(value,list):return [sanitize_01(v,exclusions,f'{path}/{i}') for i,v in enumerate(value)]
    if not isinstance(value,dict):return copy.deepcopy(value)
    out={}
    for k,v in value.items():
        q=path+'/'+k;key=k.lower()
        if key in {'respuesta','version_personaje','never_changes','nunca_cambia','refs_personajes'} or key.startswith('colores'):
            exclusions.append(q);continue
        if key=='parametros_3d':
            # No perder actuación junto con colores/gordura: separar controles transitorios acreditados.
            allowed={'expresion','expresion_valor','pose','postura','mirada','mirada_id','gesto','gestos','manos','mano_izquierda','mano_derecha'}
            transient={}
            for pid,record in (v.items() if isinstance(v,dict) else []):
                if not isinstance(record,dict):exclusions.append(q+'/'+pid);continue
                kept={}
                for ck,cv in (record.get('controles') or {}).items():
                    if ck in allowed:kept[ck]=copy.deepcopy(cv)
                    else:exclusions.append(q+'/'+pid+'/controles/'+ck)
                if kept:transient[pid]={'controles_transitorios_fuente01':kept}
            out[k]=transient
            continue
        out[k]=sanitize_01(v,exclusions,q)
    return out

def source_script(reader,D):
    # base.txt es el pedido que produjo el mapa base; NO usar el primer recorte de investigación.
    primary=D/'pedidos/base.txt'
    files=[primary] if primary.is_file() else sorted((D/'pedidos').glob('*.txt'))
    texts={};sources=[]
    for f in files:
        raw=reader.bytes(f).decode('utf8',errors='replace')
        for m in re.finditer(r'^=== GUION_COMPLETO ===\r?\n(.*?)\r?\n=== FIN GUION ===\s*$',raw,re.S|re.M):
            txt=m.group(1);texts[hashlib.sha256(txt.encode()).hexdigest()]=txt;sources.append(reader.logical(f))
    if len(texts)>1:return None,{'status':'ambiguo','sources':sources}
    return (next(iter(texts.values())) if texts else None),{'status':'disponible' if texts else 'falta','sources':sources,
            'selection':'pedido base.txt del mapa; si falta, solo aceptar guion idéntico único entre pedidos, nunca primero arbitrario'}

def script_scene(script,n,scene_map=None):
    if not script:return None
    markers=list(re.finditer(r'(?im)^\s*ESCENA\s+([0-9]+)\b',script))
    hits=[(i,m) for i,m in enumerate(markers) if str(int(m[1]))==n]
    if len(hits)==1:
        i,m=hits[0];end=markers[i+1].start() if i+1<len(markers) else len(script)
        return script[m.start():end].strip()
    if hits:return None
    # Otro formato real: títulos numerados del mapa. Solo coincidencia literal, no adivinar por número.
    title_ids={str(e.get('titulo') or '').strip():str(e.get('numero')) for e in scene_map or [] if e.get('titulo')}
    found=[];offset=0
    for line in script.splitlines(keepends=True):
        title=line.strip()
        if title in title_ids:found.append((offset,title_ids[title]))
        offset+=len(line)
    targets=[i for i,x in enumerate(found) if x[1]==n]
    if len(targets)!=1:return None
    i=targets[0];return script[found[i][0]:found[i+1][0] if i+1<len(found) else len(script)].strip()

def script_dialogues(text, names):
    out=[];speaker=None
    def emit(name,line,payload):
        ids=sorted({e['id'] for e in names if gaze_norm(name) in {gaze_norm(x) for x in e['names']}})
        lead=re.match(r'^\[([^]]+)\]\s*(.*)$',payload)
        rest=lead[2] if lead else payload
        out.append({'order':len(out)+1,'speaker_name_source':name,
                    'speaker_id':ids[0] if len(ids)==1 else ('NARRADOR' if norm(name) in {'narrador','narradora'} else None),
                    'script_line_verbatim':line,'text_source_with_stage_directions':payload,
                    'stage_direction_prefix_source':lead[1] if lead else None,
                    'spoken_text_if_unambiguous':rest if '[' not in rest and ']' not in rest else None,
                    'timing_sec':None,'voice_measured':False})
    for line in (text or '').splitlines():
        h=re.fullmatch(r"\s*([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9 .'()-]{0,60}):\s*(.*?)\s*",line)
        if h:
            speaker=h[1].strip()
            if h[2]:emit(speaker,line,h[2]);speaker=None
            continue
        value=line.strip()
        if not value:continue
        if speaker and value.startswith(('—','-','«','"')):emit(speaker,line,value.lstrip('—-').strip())
        speaker=None
    return out


def entity_catalog(base,lib):
    entities={}
    for kind,key in [('CHARACTER','personajes'),('PROP','objetos'),('ENVIRONMENT','escenarios')]:
        for p in (base.get('catalogo_oficial') or {}).get(key) or []:
            if isinstance(p,dict) and p.get('id'):
                names=[x for x in [p.get('nombre'),p.get('id')]+(p.get('alias') or []) if isinstance(x,str) and x]
                entities[p['id']]={'id':p['id'],'entity_type':kind,'names':list(dict.fromkeys(names))}
    for p in lib.get('personajes') or []:
        for pid in [p.get('id')]+(p.get('ids_mapa') or []):
            if pid in entities:
                entities[pid]['names']=list(dict.fromkeys(entities[pid]['names']+[x for x in [p.get('nombre')]+(p.get('alias') or []) if isinstance(x,str) and x]))
    return list(entities.values())

def mapped_library(lib,pid):
    hits=[p for p in lib.get('personajes') or [] if p.get('id')==pid or pid in (p.get('ids_mapa') or [])]
    if len(hits)>1:raise InputError('ADN_PERSONA_AMBIGUA:'+pid)
    return hits[0] if hits else None

def form_ids(states,pid,n):
    ids=[]
    for p in states.get('personajes') or []:
        if p.get('personaje_id')!=pid:continue
        for st in p.get('estados') or []:
            if str(st.get('escena'))!=n:continue
            for k in ['inicio','fin']:
                f=(st.get(k) or {}).get('forma_id')
                if isinstance(f,str) and f and f.lower() not in {'falta','desconocido'} and f not in ids:ids.append(f)
    return ids

def spatial_manifest(reader,D,n,canal,explicit=None):
    candidates=[]
    if explicit:
        q=reader.path(explicit)
        if not q.is_relative_to(D/'cubos'):raise InputError('MANIFIESTO_FUERA_DE_CUBOS_DEL_CAPITULO')
        candidates=[q] if q.is_file() else []
    else:
        # Solo nombres explícitos de manifiesto actual, nunca moldes, backups ni estimaciones del01.
        for sub in ['02','02N','escena','SB']:
            B=D/'cubos'/sub
            for rel in [f'esc_{n}/scene_spatial_manifest.json',f'esc_{n}/spatial_manifest.json',f'scene_spatial_manifest_esc_{n}.json',f'esc_{n}_spatial_manifest.json','scene_spatial_manifest.json','spatial_manifest.json',f'esc_{n}/manifiesto_espacial.json',f'manifiesto_espacial_esc_{n}.json','manifiesto_espacial.json']:
                p=reader.path(B/rel)
                if p.is_file():candidates.append(p)
    candidates=list(dict.fromkeys(candidates))
    if not candidates:return {'status':'falta manifiesto','blocking_step4':True,'data':None,'candidates':[]}
    if len(candidates)!=1:return {'status':'manifiesto ambiguo','blocking_step4':True,'data':None,'candidates':[reader.logical(p) for p in candidates]}
    obj=reader.json(candidates[0]);valid=isinstance(obj,dict)
    if valid:
        if obj.get('canal') not in (None,canal):valid=False
        if obj.get('escena') is not None and str(obj['escena'])!=n:valid=False
    return {'status':'presente por validar geometría' if valid else 'identidad/formato manifiesto no coincide','blocking_step4':True,
            'data':obj if valid else None,'path':reader.logical(candidates[0]),'sha256':reader.audit[str(candidates[0].relative_to(reader.root))],
            'note':'Existir no prueba bounds, rig, medidas ni Gate1: validación física corresponde a paso posterior.'}

def dna_refs(reader,canal,D,n,ids,base,states,lib,issues):
    seals=[]
    for f in sorted(reader.path('cajas/cubo_fijo/personajes').glob('*.json')):
        e=reader.json(f)
        if isinstance(e,dict) and e.get('canal') in (None,canal) and e.get('sellado') is True:seals.append((f,e))
    records=[];slots=[];libroot=Path('trabajo/biblioteca')/canal/'personajes'
    cfg=reader.json('cajas/personajes_config.json',{})
    order=(((cfg.get('hoja') or {}).get('vistas') or {}).get('refs_por_lado') or {}).get('sin_lado') or list(VIEW_ORDER)
    for pid in sorted(ids):
        pm=mapped_library(lib,pid);aliases={pid}|set((pm or {}).get('ids_mapa') or [])|{(pm or {}).get('id')}
        matches=[(f,e) for f,e in seals if aliases&({e.get('id')}|set(e.get('ids_canal') or []))]
        if len(matches)>1:issues.append({'code':'ADN_SELLO_AMBIGUO','entity_id':pid});continue
        requested=form_ids(states,pid,n);chosen=[]
        if matches:
            f,e=matches[0];ha=e.get('hoja_aprobada') or {};images=[]
            if not (ha.get('ruta') and ha.get('aprobado_por') and ha.get('cuando') and re.fullmatch(r'[a-fA-F0-9]{64}',str(ha.get('sha256') or ''))):
                issues.append({'code':'ADN_APROBACION_INCOMPLETA','entity_id':pid});continue
            im=reader.path(ha['ruta'])
            if not im.is_file() or reader.image_digest(im)!=ha['sha256'].lower():
                issues.append({'code':'DNA_CHECKSUM_MISMATCH','entity_id':pid});continue
            if len(requested)>1:issues.append({'code':'SELLO_UNICO_NO_MAPEA_CAMBIO_DE_FORMA','entity_id':pid});continue
            images=[{'view':'hoja_aprobada','path':reader.logical(im),'sha256':ha['sha256'].lower()}]
            chosen=[{'character_id':pid,'dna_ref_id':e['id'],'dna_checksum_sha256':reader.audit[str(f.relative_to(reader.root))],
                     'checksum_scope':'bytes completos del registro sellado; hash calculado, no selo ficticio','source':reader.logical(f),
                     'requested_form_ids':requested,'approval_kind':'sello_con_hoja_aprobada_y_hash_verificado','height_m':e.get('altura_m'),
                     'eye_height_standing_m':e.get('eye_height_standing_m'),'dna_override_allowed':False,'images':images}]
        else:
            versions=(pm or {}).get('versiones') or []
            if not requested:
                issues.append({'code':'ADN_FORMA_NO_IDENTIFICADA','entity_id':pid});continue
            for fid in requested:
                vs=[v for v in versions if v.get('forma_id')==fid or fid in (v.get('ids_mapa') or [])]
                # El mismo fallback conservador existente: una versión y una forma TOTAL en el capítulo.
                allforms={f for p in states.get('personajes') or [] if p.get('personaje_id')==pid for st in p.get('estados') or [] for k in ['inicio','fin'] if (f:=(st.get(k) or {}).get('forma_id'))}
                if not vs and len(versions)==1 and len(allforms)==1:vs=versions
                if len(vs)!=1 or vs[0].get('estado')!='aprobada':issues.append({'code':'ADN_FALTA_NO_APROBADO_O_AMBIGUO','entity_id':pid,'form_id':fid});continue
                v=vs[0];vis=v.get('vistas') or {};refs=v.get('refs') or [];expected=v.get('refs_sha256') or []
                declared=list(zip(refs,expected)) if len(refs)==len(expected) else []
                hashes=dict(declared)
                rels=[(k,vis[k]) for k in list(order)+sorted(set(vis)-set(order)) if k in vis] if vis else [(f'ref_{i+1}',r) for i,r in enumerate(refs)]
                ims=[];bad=False
                for view,rel in rels:
                    q=reader.path(libroot/rel)
                    if not q.is_relative_to(reader.path(libroot)):raise InputError('IMAGEN_FUERA_BIBLIOTECA')
                    sha=reader.image_digest(q)
                    if not sha or not hashes.get(rel) or sha.lower()!=str(hashes[rel]).lower():bad=True;break
                    ims.append({'view':view,'path':reader.logical(q),'sha256':sha})
                if bad or not ims:issues.append({'code':'DNA_CHECKSUM_MISMATCH','entity_id':pid,'form_id':fid});continue
                chosen.append({'character_id':pid,'dna_ref_id':v.get('forma_id') or fid,'dna_checksum_sha256':canonical_hash({'personaje':pm,'version':v}),
                               'checksum_scope':'JSON canónico del registro personaje+versión, UTF8, claves ordenadas; no texto para el prompt',
                               'source':reader.logical(libroot/'personajes.json'),'requested_form_ids':[fid],'approval_kind':'version_biblioteca_aprobada_con_hash_refs',
                               'height_m':pm.get('altura_m') or v.get('altura_m'),'eye_height_standing_m':v.get('eye_height_standing_m'),
                               'dna_override_allowed':False,'images':ims})
        for rec in chosen:
            records.append(rec)
            for im in rec['images']:
                slots.append({'slot':len(slots)+1,'character_id':pid,'dna_ref_id':rec['dna_ref_id'],**im})
    return {'records':records,'ordered_images':slots,'canonical_order':'character_id ascendente; forma inicio luego fin; vistas según config sin_lado, otras por nombre; refs fallback en orden declarado. Slots por viñeta se ordenarán por roles cuando Argon elija sujeto.',
            'identity_text_included':False,'coverage':{'characters_requested':len(ids),'characters_with_verified_refs':len({r['character_id'] for r in records}),'images':len(slots)}}

def other_asset_refs(reader,canal,scene,effective,actions):
    """Set/props: inventario por ID exacto, no convertir ficha descriptiva en ADN visual."""
    requested=[];set_id=effective.get('escenario_id') or scene.get('escenario_id')
    if set_id:requested.append(('ENVIRONMENT',set_id))
    props=sorted({a.get('objeto') for a in actions if isinstance(a.get('objeto'),str) and a.get('objeto')})
    requested.extend(('PROP',pid) for pid in props)
    seals=[]
    for category in ['objetos_pj','objetos_escenario']:
        for p in sorted(reader.path('cajas/cubo_fijo/'+category).glob('*.json')):
            x=reader.json(p)
            if isinstance(x,dict) and x.get('canal') in (None,canal):seals.append((p,x))
    rows=[];approved=[]
    for kind,pid in requested:
        try:safe_id(pid)
        except InputError:
            rows.append({'entity_id_source':pid,'entity_type':kind,'approved_for_prompt':False,'images':[],'status':'fuente trae nombre/no ID seguro; no se usa como ruta ni se inventa correspondencia'})
            continue
        matches=[]
        for p,x in seals:
            aliases={x.get('id')}|set(x.get('ids_canal') or [])|set(x.get('ids_capitulo') or [])
            if pid in aliases:matches.append((p,x))
        row={'entity_id':pid,'entity_type':kind,'approved_for_prompt':False,'images':[]}
        if len(matches)>1:row['status']='sello ambiguo, no elegir primero'
        elif matches:
            p,x=matches[0];ha=x.get('hoja_aprobada') or {};path=ha.get('ruta') or x.get('imagen_ref');sha=ha.get('sha256') or x.get('imagen_sha256')
            row.update({'dna_ref_id':x.get('id'),'dna_checksum_sha256':reader.audit[str(p.relative_to(reader.root))],'source':reader.logical(p),'status':'sello sin referencia visual aprobada/verificable'})
            # Una imagen generada o un sellado lógico NO certifica aprobación visual.
            if x.get('sellado') is True and path and sha:
                q=reader.path(path)
                if q.is_file() and reader.image_digest(q)==str(sha).lower():
                    row['images']=[{'view':'referencia','path':reader.logical(q),'sha256':str(sha).lower()}]
                    if ha.get('aprobado_por') and ha.get('cuando'):
                        row['approved_for_prompt']=True;row['status']='hoja visual aprobada y hash verificado';approved.append(copy.deepcopy(row))
                    else:row['status']='hash de imagen verificado; falta prueba explícita de aprobación visual'
        else:
            category='escenarios' if kind=='ENVIRONMENT' else 'objetos'
            p=reader.path(Path('trabajo/biblioteca')/canal/category/pid/'ficha.json')
            if p.is_file():
                x=reader.json(p);row.update({'status':'ficha existente, sin catálogo de imagen aprobada/hash en este formato','source':reader.logical(p),'source_sha256':reader.audit[str(p.relative_to(reader.root))],'metadata_state':x.get('estado')})
            else:row['status']='falta referencia exacta del activo; no se adivinan alias ni sufijos'
        rows.append(row)
    return {'requested':rows,'approved_records':approved,'coverage':{'requested':len(rows),'approved_with_verified_images':len(approved)},
            'note':'Candidatos NO aprobados no se adjuntan como referencias aprobadas; no se inventan fotos ni se copian descripciones de ficha. Un prop casual puede no requerir insert; el contrato posterior determinará refs necesarias por viñeta.'}


def assemble(root,canal,capitulo,escena,manifest=None):
    r=Reader(root);D=resolve_chapter(r,canal,capitulo);n=scene_number(escena);issues=[]
    def issue(code,**kw):issues.append({'code':code,**kw})
    base=r.json(D/'respuestas/base.json',{});states=r.json(D/'respuestas/personajes.json',{})
    lib=r.json(Path('trabajo/biblioteca')/canal/'personajes/personajes.json',{})
    scene_matches=[e for e in base.get('escenas') or [] if str(e.get('numero'))==n]
    if len(scene_matches)!=1:issue('ESCENA_MAPA_FALTA_O_AMBIGUA')
    scene=scene_matches[0] if len(scene_matches)==1 else {}
    p01=D/'cubos/01'/f'esc_{n}.json';raw={}
    if not p01.is_file():issue('MISSING_UPSTREAM_ACTION',reason='falta archivo01')
    elif p01.stat().st_size==0:issue('MISSING_UPSTREAM_ACTION',reason='archivo01 vacío')
    else:
        try:raw=r.json(p01,{})
        except InputError as ex:issue('MISSING_UPSTREAM_ACTION',reason=str(ex))
    if not isinstance(raw,dict):raw={};issue('MISSING_UPSTREAM_ACTION',reason='01 no es objeto')
    effective=raw
    if not raw.get('acciones') and isinstance(raw.get('respuesta'),dict):effective=raw['respuesta']
    actions=effective.get('acciones') or [];characters=effective.get('personajes') or []
    if not isinstance(actions,list):raise InputError('ACCIONES01_NO_ES_LISTA')
    if not isinstance(characters,list):raise InputError('PERSONAJES01_NO_ES_LISTA')
    if not actions:issue('MISSING_UPSTREAM_ACTION',reason='legacy01 sin acciones accion_v1')
    if effective.get('escena') is not None and str(effective['escena'])!=n:issue('ESCENA01_NO_COINCIDE')
    duration=effective.get('duracion_s');clock=None
    try:
        if number(duration)<=0:raise InputError('DURACION_INVALIDA')
        clock=timing24([0,duration])
    except InputError as ex:issue('TIEMPO_INVALIDO',reason=str(ex))
    exclusions=[];clean=sanitize_01(effective,exclusions)
    ids={x.get('id') for x in characters if x.get('id')}
    ids|={x.get('personaje_id') for x in scene.get('personajes') or [] if x.get('personaje_id')}
    ids|={x.get('actor') for x in actions if x.get('actor') and x.get('actor')!='NARRADOR'}
    names=entity_catalog(base,lib)
    for pid in sorted(ids):
        if not any(x['id']==pid for x in names):names.append({'id':pid,'entity_type':'CHARACTER','names':[pid]})
    enriched=[];action_ids=set();speeches=[]
    for i,a in enumerate(actions):
        if not isinstance(a,dict):issue('ACCION_TIPO_INVALIDO',index=i);continue
        aid=a.get('id')
        if not aid or aid in action_ids:issue('BEAT_ID_FALTA_O_DUPLICADO',index=i)
        action_ids.add(aid)
        t24=None
        try:t24=timing24(a.get('t'),duration)
        except InputError as ex:issue('ACCION_TIEMPO_INVALIDO',beat_id=aid,reason=str(ex))
        gid=a.get('mirada_id');matches=[x for x in names if x['id']==gid] if gid else [x for x in names if gaze_norm(a.get('mirada')) and gaze_norm(a['mirada']) in {gaze_norm(v) for v in x['names']}]
        target=matches[0] if len(matches)==1 else None
        # Si un ID existe pero no aparece en catálogo, conservarlo NO significa verificarlo.
        derived=target['id'] if target else None
        e={'source_action':copy.deepcopy(a),'timing_24fps':t24,'actor_names':next((x['names'] for x in names if x['id']==a.get('actor')),[]),
           'gaze':{'mirada_id_source':gid,'mirada_text_source':a.get('mirada'),'resolved_entity_id':derived,'target_names':target['names'] if target else [],
                   'resolution':'id_exacto' if target and gid else ('nombre_exacto_unico' if target else 'sin_resolver_no_inventado'),'target_bone':None},
           'pose_source':a.get('pose'),'gesture_source':a.get('gesto',a.get('gestos')),'hands_source':a.get('manos',a.get('hands_state'))}
        enriched.append(e)
        if norm(a.get('accion')) in {'hablar','decir','dialogo','susurrar','gritar','narrar'}:
            speeches.append({'beat_id':aid,'speaker_id':a.get('actor'),'speaker_names':e['actor_names'],'cita_source_verbatim':a.get('cita'),
                             'action_interval_seconds':copy.deepcopy(a.get('t')),'timing_24fps':t24,'delivery_tone_source':a.get('tono'),
                             'voice_measured':False,'warning':'cita es evidencia01; no se declara transcripción literal completa sin cotejar guion'})
    segment_times=[]
    for ch in characters:
        for i,seg in enumerate(ch.get('segmentos') or []):
            try:segtime=timing24(seg.get('t'),duration)
            except InputError as ex:segtime=None;issue('SEGMENTO_TIEMPO_INVALIDO',character_id=ch.get('id'),index=i,reason=str(ex))
            segment_times.append({'character_id':ch.get('id'),'segment_index':i,'source_segment':copy.deepcopy(seg),'timing_24fps':segtime})
    script,script_meta=source_script(r,D);piece=script_scene(script,n,base.get('escenas'));dialogues=script_dialogues(piece,names)
    if not piece:issue('GUION_ESCENA_FALTA_O_AMBIGUO')
    filler=r.json(D/'personajes_relleno.json',{})
    extras=filler.get('personajes') or []
    if isinstance(extras,dict):extras=[dict(v,id=k) for k,v in extras.items() if isinstance(v,dict)]
    voice_only={p.get('personaje_id') for p in scene.get('personajes') or [] if norm(p.get('presencia')) in {'solo voz','voz','fuera de cuadro solo voz'}}
    voice_only|={p.get('id') or p.get('personaje_id') for p in extras if isinstance(p,dict) and p.get('tipo')=='solo_voz'}
    visual_ids=ids-voice_only
    refs=dna_refs(r,canal,D,n,visual_ids,base,states,lib,issues)
    other_refs=other_asset_refs(r,canal,scene,effective,actions)
    spatial=spatial_manifest(r,D,n,canal,manifest)
    if spatial['blocking_step4']:issue('MISSING_SET_OR_RIG_BONES',reason=spatial['status'])
    coverage={
      '01_actions':len(actions),'01_segments':len(segment_times),'01_points':len(effective.get('puntos') or {}),
      'gaze_id_source':sum(bool(x['gaze']['mirada_id_source']) for x in enriched),'gaze_resolved_entity':sum(bool(x['gaze']['resolved_entity_id']) for x in enriched),
      'gaze_bone_measured':0,'actions_with_gesture_field':sum(x['gesture_source'] is not None for x in enriched),
      'actions_with_hands_field':sum(x['hands_source'] is not None for x in enriched),'speech_actions':len(speeches),'script_dialogues_parsed':len(dialogues),
      'transient_controls_preserved':sum(len(p.get('controles_transitorios_fuente01') or {}) for p in (clean.get('parametros_3d') or {}).values()),'fps_source':effective.get('fps'),'fps_context':24,'dna':refs['coverage'],'set_prop_refs':other_refs['coverage'],'manifest':spatial['status']}
    contract_inputs=[
      {'block':1,'status':'parcial' if actions else 'falta','input':'acciones, citas y emociones cualitativas01; beat cinematográfico/arousal/valence y propósito los decide Argon con fuente'},
      {'block':2,'status':'parcial','input':'guion literal si existe, citas/intervalos de habla01; no voz medida, tono completo, pre-roll ni reacción estructurada garantizados'},
      {'block':3,'status':'pendiente_Argon','input':'catálogo IDs disponible; U, pesos y sujeto los decide SB, no este programa'},
      {'block':4,'status':'parcial','input':'referencias/hash aprobados según cobertura; postura/mirada01; manos/huesos/ojos medidos pueden faltar'},
      {'block':5,'status':'parcial' if segment_times else 'falta','input':'puntos y segmentos01 intactos, no equivalen a transforms/rig Blender medidos'},
      {'block':6,'status':'parcial','input':'escenario_ID, duración y reloj24; bounds/luz física requieren manifiesto'},
      {'block':7,'status':'pendiente_Argon','input':'tamaño/encuadre corresponde a SB; no heredar tomas del01 como mandato'},
      {'block':8,'status':'falta' if spatial['data'] is None else 'parcial','input':'geometría exacta exige manifiesto y solver; no se inventa XYZ'},
      {'block':9,'status':'pendiente_Argon','input':'movimiento y motivo son decisión SB, LOCK por defecto'},
      {'block':10,'status':'parcial','input':'ejes y posiciones01 como fuente; continuidad geométrica todavía por comprobar'},
      {'block':11,'status':'sí' if refs['coverage']['characters_with_verified_refs']==len(visual_ids) and visual_ids and other_refs['coverage']['requested']==other_refs['coverage']['approved_with_verified_images'] else 'parcial','input':'catálogo ordenado de refs verificadas; roles por viñeta los decide Argon'},
      {'block':12,'status':'falta','input':'sin resultados Gate1/Gate2; jamás se certifica aceptación por preparar contexto'},
      {'block':13,'status':'parcial','input':'bloqueos de entrada explícitos; faltan validación de contrato y aceptación física'}]
    return {'version':VERSION,'active':False,'canal':canal,'capitulo_folder':D.name,'capitulo_id':D.name.split('_',1)[1],'escena':n,
            'blocked_for_step4':bool(issues),'blocking_fields_step4':issues,'clock_24fps':clock,
            'accion_01':clean,'actions_enriched':enriched,'segments_enriched':segment_times,'dialogue_evidence_01':speeches,
            'script_scene_verbatim':piece,'script_source':script_meta,'script_dialogues':dialogues,
            'entity_names':sorted(names,key=lambda x:x['id']),'voice_only_entity_ids':sorted(voice_only & ids),'adn':refs,'other_asset_adn':other_refs,'spatial_manifest':spatial,
            'coverage':coverage,'contract_input_coverage':contract_inputs,
            'source_audit_sha256':dict(sorted(r.audit.items())),
            'excluded_identity_paths':exclusions,'legacy_01_camera_advisory_only':True,
            'note':'Contexto inactivo y parcial, NO contrato de viñeta ni aprobación de gasto/ejecución. Identidad textual excluida; guion/acción/citas literales pueden nombrar rasgos y son datos, no instrucciones para ADN.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--taller',default=str(DEFAULT_ROOT));p.add_argument('--canal',required=True);p.add_argument('--capitulo',required=True);p.add_argument('--escena',required=True);p.add_argument('--manifest')
    a=p.parse_args()
    try:out=assemble(a.taller,a.canal,a.capitulo,a.escena,a.manifest)
    except (InputError,OSError,TypeError,KeyError) as ex:
        print(json.dumps({'version':VERSION,'active':False,'blocked_for_step4':True,'error':str(ex)},ensure_ascii=False));return 2
    print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False));return 0
if __name__=='__main__':raise SystemExit(main())
