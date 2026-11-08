"""Entrada única estricta. Los adaptadores conservan la fuente, nunca completan prosa."""
from seguridad import *
VERSION='1.0'
OBLIGATORIAS=('rostros_finales','ropa_final')
def desenvolver(value):
 for _ in range(8):
  if isinstance(value,str):value=json.loads(value);continue
  if isinstance(value,list) and len(value)==1 and isinstance(value[0],dict):value=value[0];continue
  if isinstance(value,dict) and set(value)=={'json'}:value=value['json'];continue
  if isinstance(value,dict) and 'stdout' in value and set(value)<= {'stdout','stderr','exitCode'}:
   if value.get('exitCode',0)!=0:raise ValueError('Productor falló')
   value=value['stdout'];continue
  return value
 raise ValueError('Demasiados envoltorios')

def normalizar_heredada(d,referencia):
 # No inferir anatomía/aprobación/voz a partir de un ID. Ausencias quedan None.
 return {'schema_version':VERSION,'scene':d.get('scene'),'clock':{'fps':d.get('fps'),'duration_s':d.get('duration_s'),'rounding':'half_up'},
 'sources':[referencia], 'coordinates':None,'entities':[{'id':a.get('id'),'type':'CHARACTER','anatomy':a.get('anatomy'),'legacy':a} for a in d.get('actors',[])]+[{'id':p.get('id'),'type':'PROP','legacy':p} for p in d.get('props',[])],
 'environment':d.get('environment'),'motion':{'catalog':d.get('catalog'),'assignments':d.get('assignments'),'status':None},'camera':d.get('camera'),'lighting':None,'audio':None,'required_capabilities':list(OBLIGATORIAS),'libraries':[], 'legacy':d,'provisional':d.get('provisional',[])}

def cargar(root):
 p=Path(root)/'entrada_escena.json'
 try:
  d=desenvolver(leer(p))
  if not isinstance(d,dict):raise ValueError('Se esperaba objeto')
  return d,[]
 except (OSError,ValueError,TypeError) as e:return {},[error('entrada_escena.json','exportador n8n',str(e),'JSON_INVALIDO')]

def validar(d,root):
 exigir("contrato")
 import jsonschema
 shape=leer(Path(__file__).resolve().parents[1]/"CONTRATO_ENTRADA.schema.json")
 structural=list(jsonschema.Draft202012Validator(shape).iter_errors(d))
 if structural:return [error("/".join(str(p) for p in x.path),"exportador n8n",x.message,"TIPO_INVALIDO",tipo="adaptar formato") for x in structural]
 E=[]
 def need(ok,field,module,msg,**kw):
  if not ok:E.append(error(field,module,msg,**kw))
 for k in ['schema_version','scene','clock','coordinates','sources','assets','entities','environment','motion','camera','lighting','libraries','required_capabilities']:
  need(k in d,k,'preparar entrada','Campo obligatorio ausente')
 if E:return E
 need(d['schema_version']==VERSION,'schema_version','preparar entrada','Versión no soportada')
 cl=d.get('clock') or {};fps=cl.get('fps');dur=cl.get('duration_s')
 need(numero(fps) and fps>0,'clock/fps','01','FPS ausente/inválido');need(numero(dur) and dur>0,'clock/duration_s','01','Duración ausente/inválida')
 need(cl.get('rounding')=='half_up','clock/rounding','motor','Cuantización global explícita requerida')
 need(isinstance(d['coordinates'],dict) and all(k in d['coordinates'] for k in ['unit','up','forward','origin','source']),'coordinates','01/4a2','Ejes y unidades certificados ausentes')
 if isinstance(d['coordinates'],dict):need(d['coordinates'].get('unit')=='m' and d['coordinates'].get('up')=='Z','coordinates','adaptador espacial','Transformar explícitamente a metros/Z antes de construir')
 sources=d['sources'];need(isinstance(sources,list) and bool(sources),'sources','exportador n8n','Fuentes con procedencia requeridas')
 for i,s in enumerate(sources if isinstance(sources,list) else []):
  need(isinstance(s,dict) and all(k in s for k in ['module','path','sha256']),'sources/'+str(i),'exportador n8n','Fuente incompleta')
 assets=d['assets'];need(isinstance(assets,list) and bool(assets),'assets','empaquetador','Manifiesto de archivos obligatorio')
 paths=set()
 for i,a in enumerate(assets if isinstance(assets,list) else []):
  field='assets/'+str(i)
  if not isinstance(a,dict):E.append(error(field,'empaquetador','Asset debe ser objeto'));continue
  try:
   p=ruta(root,a.get('path'));need(a.get('path') not in paths,field,'empaquetador','Ruta de asset repetida');paths.add(a.get('path'))
   need(p.is_file(),field,'empaquetador','Archivo ausente')
   if p.is_file():need(sha(p)==a.get('sha256') and p.stat().st_size==a.get('bytes'),field,'empaquetador','Hash o bytes distintos',codigo='HASH_DISTINTO')
  except (OSError,ValueError,TypeError):E.append(error(field,'empaquetador','Ruta inválida/externa','RUTA_INVALIDA'))
 for i,s in enumerate(sources if isinstance(sources,list) else []):
  if isinstance(s,dict):
   try:need(s.get('path') in paths and sha(ruta(root,s.get('path')))==s.get('sha256'),'sources/'+str(i),'exportador n8n','Fuente no coincide con assets/hash')
   except (OSError,ValueError,TypeError):E.append(error('sources/'+str(i),'exportador n8n','Archivo fuente inválido'))
 entities=d['entities'];need(isinstance(entities,list) and bool(entities),'entities','ADN/01','Entidades obligatorias')
 ids=[]
 for ent in entities if isinstance(entities,list) else []:
  if not isinstance(ent,dict):E.append(error('entities','ADN','Entidad debe ser objeto'));continue
  pid=ent.get('id');field='entities/'+str(pid);ids.append(pid)
  need(isinstance(pid,str) and bool(pid),field,'ADN','ID obligatorio')
  need(ent.get('type') in ['CHARACTER','PROP','FX'],field+'/type','ADN/SELLO','Tipo no válido')
  if ent.get('type')=='PROP':need('spec' not in ent or not any(x in ent['spec'] for x in ['cabezas','altura_referencia_perfil_m']),field,'ADN/puente','PROP no debe exigir anatomía humanoide',codigo='PROP_MAL_CLASIFICADO')
  if ent.get('type')=='CHARACTER':
   need(ent.get('anatomy') in ['humanoid','declarative','avian'],field+'/anatomy','motor/ADN','Anatomía sin backend certificado',codigo='ANATOMIA_NO_SOPORTADA',tipo='crear capacidad')
   app=ent.get('appearance') or {}
   for k in ['rostros_finales','ropa_final']:
    need(isinstance(app.get(k),dict) and bool(app[k].get('asset')) and app[k].get('source') is not None,field+'/appearance/'+k,'ADN/SELLO PJ + constructor','Acabado final no vinculado; cápsula no es final',tipo='crear capacidad')
 need(len(ids)==len(set(x for x in ids if isinstance(x,str))),'entities/id','ADN/01','IDs duplicados/inválidos',codigo='ID_DUPLICADO')
 expected=d.get('requirements',{}).get('entity_ids')
 need(isinstance(expected,list),'requirements/entity_ids','01 integral','Lista de entidades del guion ausente')
 if isinstance(expected,list):
  for pid in expected:need(pid in ids,'entities/'+str(pid),'01/ADN','Entidad requerida omitida',codigo='ENTIDAD_OMITIDA')
 for ref in d.get('requirements',{}).get('object_refs',[]):
  binding=d.get('bindings',{}).get(ref)
  need(isinstance(binding,dict) and bool(binding.get('scene_object_id')),'bindings/'+str(ref),'01 + ADN OBJ + 4a2/02N','Objeto requerido sin binding espacial inequívoco',codigo='OBJETO_SIN_BINDING')
 # Toda omisión provisional sigue bloqueando. No filtrar por gravedad artística.
 for p in d.get('provisional',[]):E.append(error(p.get('campo','provisional'),p.get('modulo','fuentes'),p.get('mensaje','Dato provisional'),codigo='PROVISIONAL'))
 motion=d.get('motion') or {};need(motion.get('status')=='complete','motion/status','2B/Argon','Programa completo no acreditado')
 for key in ['catalog','assignments']:
  path=motion.get(key)
  need(path in paths,'motion/'+key,'2B','Archivo requerido no incluido con hash')
  if path in paths:
   try:leer(ruta(root,path))
   except (OSError,ValueError):E.append(error('motion/'+key,'2B','JSON truncado o inválido','JSON_INVALIDO'))
 camera=d.get('camera') or {};shots=camera.get('shots')
 need(isinstance(shots,list) and bool(shots),'camera/shots','SB','Tomas con tiempos explícitos requeridas; cámara técnica no sustituye SB')
 if numero(fps) and numero(dur) and fps>0 and dur>0 and isinstance(shots,list):
  cursor=0
  for s in shots:
   field='camera/shots/'+str(s.get('id'));a=s.get('t0');b=s.get('t1')
   if not (numero(a) and numero(b) and 0<=a<b<=dur):E.append(error(field,'SB','Tiempo ausente/inválido'));continue
   f0,f1=cuadro(a,fps),cuadro(b,fps)
   need(f0==cursor and f1>f0,field,'SB','Hueco, solape o toma vacía',codigo='COBERTURA_TIEMPO');cursor=f1
   need(b-a<=10+1e-9,field,'SB','Toma excede 10 s; no se divide ni recorta',codigo='TOMA_LARGA')
   need(s.get('transition') is not None,field+'/transition','SB','Transición ausente')
  need(cursor==cuadro(dur,fps),'camera/shots','SB','Tomas no cubren escena completa',codigo='COBERTURA_TIEMPO')
 live=(d.get('environment') or {}).get('live_data')
 need(isinstance(live,dict) and live.get('status')=='complete','environment/live_data','4a/4a4 + puente','Eventos no vinculados a propiedades/tiempos')
 need(isinstance(d.get('lighting'),dict) and all(k in d['lighting'] for k in ['exposure','base','events','source']),'lighting','4a2/4a4','Luz artística base/eventos/exposición requeridos')
 # Cambio de alcance t295: voz/labios los hace Omni DESPUÉS; audio opcional.
 need(set(OBLIGATORIAS)<=set(d.get('required_capabilities',[])),'required_capabilities','contrato','Caras y ropa finales ADN no pueden omitirse')
 return E
