"""Puente local universal desde el paquete anterior. No ejecuta productores externos."""
import shutil
from contrato import normalizar_heredada,OBLIGATORIAS
from seguridad import *

def preparar(origen,destino,sb=None):
 origen=Path(origen);destino=Path(destino)
 if destino.exists():raise ValueError('Destino debe ser nuevo; archivar antes')
 destino.mkdir(parents=True)
 # Copiar sólo datos de entrada; nada de scripts, resultados viejos ni credenciales.
 old_source=leer(origen/'entrada.json')
 allow={'entrada.json','source_01_integral.json','source_01.json','adn_entidades.json','adn_manifest.json','programa_2b.json','respuesta_2b.json'}
 for field in ['catalog','assignments','adn_entities']:
  if old_source.get(field):allow.add(old_source[field])
 for field in ['path','catalog','live']:
  if old_source.get('environment',{}).get(field):allow.add(old_source['environment'][field])
 for prop in old_source.get('props',[]):
  if prop.get('formula'):allow.add(prop['formula'])
 for name in sorted(allow):
  p=ruta(origen,name)
  if p.is_file():
   if p.suffix not in ['.json','.blend']:raise ValueError('Tipo de asset no admitido en puente')
   q=ruta(destino,name);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 old=leer(destino/'entrada.json');src={'module':'preparar legado','path':'entrada.json','sha256':sha(destino/'entrada.json')}
 d=normalizar_heredada(old,src);d['job_id']=destino.name
 d['requirements']={'entity_ids':[]};d['assets']=[]
 source=destino/'source_01_integral.json'
 if not source.exists():source=destino/'source_01.json'
 if source.exists():
  x=leer(source);d['requirements']['entity_ids']=[q['id'] for q in x.get('personajes',[])]
  d['actions']=x.get('acciones',[]);d['points']=x.get('puntos',{});d['facts']=x.get('hechos',[])
  d['segments']=[dict(actor=p['id'],source_data=seg) for p in x.get('personajes',[]) for seg in p.get('segmentos',[])]
  refs=[]
  for action in d['actions']:
   for field in ['objeto','mirada_id']:
    value=action.get(field)
    if isinstance(value,str) and value and value not in d['requirements']['entity_ids'] and value not in refs:refs.append(value)
  d['requirements']['object_refs']=refs
  d['sources'].append({'module':'01','path':source.name,'sha256':sha(source)})
  # Conservar entidades antes omitidas SIN asignarles humanoide ni geometría genérica.
  current={a['id'] for a in d['entities']}
  for a in x.get('personajes',[]):
   if a['id'] not in current:d['entities'].append({'id':a['id'],'type':'CHARACTER','anatomy':None,'source':source.name,'source_data':a})
 if (destino/'adn_entidades.json').exists():
  dna=leer(destino/'adn_entidades.json');lookup={e['id']:e for e in d['entities']}
  for rec in dna['records']:
   if rec['id'] in lookup:lookup[rec['id']]['dna_record']=rec
 live=d.get('environment',{}).get('live')
 if live and ruta(destino,live).exists():d['environment']['live_data']=leer(ruta(destino,live))
 if sb:
  shutil.copy2(sb,destino/'storyboard_camara.json');sc=leer(destino/'storyboard_camara.json')
  d['camera']={'source':'storyboard_camara.json','transition_semantics':'outgoing','shots':[{'id':q['vineta'],'t0':q['t_abs'][0],'t1':q['t_abs'][1],'transition':q.get('transicion_salida'),'source_data':q} for q in sc['vinetas']]}
  d['sources'].append({'module':'SB','path':'storyboard_camara.json','sha256':sha(destino/'storyboard_camara.json')})
 if d.get('motion',{}).get('catalog'):
  cat=d['motion']['catalog'];d['libraries']=[{'id':'catalogo_escena','path':cat,'sha256':sha(destino/cat),'approval_status':'SIN_VERIFICAR'}]
 for p in sorted(destino.rglob("*")):
  if p.is_file():d['assets'].append({'path':str(p.relative_to(destino)),'sha256':sha(p),'bytes':p.stat().st_size,'type':p.suffix[1:]})
 from adn_inspeccion import enriquecer
 from perfiles_puente import adaptar
 d=adaptar(enriquecer(d))
 guardar(destino/'entrada_escena.json',d);return d
