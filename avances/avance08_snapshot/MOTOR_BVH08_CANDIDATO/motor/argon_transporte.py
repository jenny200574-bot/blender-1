"""Transporte SB real, streaming 1800s. Seco por defecto; cero red al cotizar."""
import json,math,copy,os,sys,importlib.util
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from seguridad import leer,sha,guardar
from recetas_proveedor import huella,Ledger

def tarifa(root,cfg,date=None):
 d=leer(Path(root)/'config/tarifas_argon.json');day=date or datetime.now(ZoneInfo('America/Bogota')).date().isoformat();rows=d['tokens'][cfg['model']];rows=[x for x in rows if x['vigente_desde']<=day]
 if not rows:raise ValueError('FALTA tarifa para fecha; no cotizar ni enviar')
 row=max(rows,key=lambda x:x['vigente_desde']);return dict(row,date_bogota=day,source_sha256=d['source_sha256'])

def pedido(query,cfg):
 task=query.get('task','object_recipe');schema={'object_recipe':{'source':'procedencia','parts':[{'id':'id local','shape':'MESH|ELLIPSOID|CYLINDER|CONE','position_m':[0,0,0],'rotation_deg':[0,0,0],'dimensions_m':'del ADN','vertices_m':'si MESH','faces':'si MESH','material':{'rgba':'ADN','roughness':'ADN/biblioteca','metallic':'ADN/biblioteca'},'source':'ADN o biblioteca'}]},'recipe_batch':{'responses':[{'id':'ID EXACTO de cada elemento de entrada','recipe':'receta del contrato correspondiente; o status:FALTA con missing y producer'}]},'entity_recipe':{'source':'fuente explícita','parts':'geometría y materiales por ADN; FALTA si no se puede'},'anatomy_review':{'status':'PROPOSAL_OR_FALTA','source':'ADN','missing':'landmarks/apoyos/ancla que NO se pueden inferir','profile':'Sólo datos acreditados, no certificación inventada'}}[task]
 if task=='recipe_batch':schema['contracts']={k:pedido({'task':k},cfg)['prompt'].split('Contrato: ',1)[1].split('\nEntrada íntegra: ',1)[0] for k in ['object_recipe','anatomy_review','entity_recipe']}
 prompt='Devuelve JSON estricto. Sin Python ejecutable, sin cajas/bbox de acabado. Respeta metros, medidas, material y detalles del ADN. No inventes datos físicos, anclas, lateralidad ni límites certificados. Si faltan, devuelve FALTA con productor. Contrato: '+json.dumps(schema,ensure_ascii=False)+'\nEntrada íntegra: '+json.dumps(query,ensure_ascii=False,sort_keys=True)
 return {'model':cfg['model'],'prompt':prompt,'stream':True,'timeout_s':cfg['timeout_s'],'max_output_tokens':cfg['max_output_tokens'],'thinking_level':cfg['thinking_level'],'response_mime_type':'application/json','query_sha256':huella(query),'task':task}

class Transport:
 def __init__(self,root,client_factory=None):self.root=Path(root);self.cfg=leer(self.root/'config/argon_transporte.json');self.client_factory=client_factory
 def quote(self,query):
  p=pedido(query,self.cfg);rate=tarifa(self.root,self.cfg);n=math.ceil(len(p['prompt'].encode('utf-8'))/self.cfg['chars_per_token']);reserve_n=len(p['prompt'].encode('utf-8'))+256
  cost=lambda tin:(tin*rate['entrada']+p['max_output_tokens']*rate['salida'])/1e6
  return {'request':p,'tariff':rate,'estimated_input_tokens':n,'reserve_input_tokens_upper_bound':reserve_n,'output_tokens_ceiling_including_thoughts':p['max_output_tokens'],'estimated_usd':round(cost(n),8),'reserve_usd':round(cost(reserve_n),8),'count_method':'offline bytes/3 estimate; reserve byte upper bound +256; no count_tokens HTTP','network_sent':False}
 def prepare(self,query):
  q=self.quote(query);ledger=Ledger(self.root/'evidencia/ledger.json');ref=ledger.before(q['reserve_usd'],'argon_transport_dry_run',mock=True);ledger.settle(ref,0);q['ledger']=ref;q['state']='DRY_RUN_RESERVED_AND_RELEASED_ZERO_SPEND';q['credential_file_present']=any(Path(os.environ[n]).is_file() for n in ['MYIA_ARGON_CRED','VERTEX_CRED','GOOGLE_APPLICATION_CREDENTIALS'] if os.environ.get(n)) or Path(self.cfg.get('existing_file','')).is_file();return q
 def __call__(self,query,receipt):
  cache=self.root/'bibliotecas/argon_respuestas'/query.get('task','object_recipe')/(huella(query)+'.json')
  if cache.exists():
   saved=leer(cache)
   if saved.get('query_sha256')!=huella(query) or saved.get('response_sha256')!=huella(saved['response']):raise ValueError('Caché transporte alterada')
   return dict(saved['response'],_usage_usd=0)
  # Safety checks BEFORE credentials, client construction, count_tokens or network.
  if self.cfg.get('dry_run',True) or (self.root/'config/argon_envio.off').exists():raise ValueError('ENVIO_REAL_APAGADO; preparar/cotizar sí; no se envía')
  q=self.quote(query)
  if not receipt.get('authorized') or receipt.get('reserved_usd',-1)<q['reserve_usd']:raise ValueError('Reserva previa insuficiente')
  if self.client_factory:client=self.client_factory()
  else:
   source=Path(self.cfg['client_module'])
   if sha(source)!=self.cfg['client_sha256']:raise ValueError('Cliente SB cambió de hash')
   # Sólo el cliente existente autentica; no se leen ni guardan claves aquí.
   if not os.environ.get('MYIA_ARGON_CRED'):
    selected=next((os.environ[n] for n in ['VERTEX_CRED','GOOGLE_APPLICATION_CREDENTIALS'] if os.environ.get(n)),self.cfg.get('existing_file'))
    if selected:os.environ['MYIA_ARGON_CRED']=selected
   spec=importlib.util.spec_from_file_location('motor_argon_sb_reused',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);client=m._cliente()
  from google.genai import types
  config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=self.cfg['thinking_level'],include_thoughts=True),max_output_tokens=self.cfg['max_output_tokens'],response_mime_type='application/json');text='';usage=None;finish=None
  for chunk in client.models.generate_content_stream(model=self.cfg['model'],contents=q['request']['prompt'],config=config):
   for cand in chunk.candidates or []:
    for part in (cand.content.parts if cand.content else []) or []:
     if not getattr(part,'thought',False) and getattr(part,'text',None):text+=part.text
    if cand.finish_reason:finish=str(cand.finish_reason)
   if chunk.usage_metadata:usage=chunk.usage_metadata
  if usage is None or 'MAX_TOKENS' in str(finish):raise ValueError('FALTA uso íntegro o respuesta truncada; mantener reserva')
  tin=usage.prompt_token_count or 0;tout=(usage.candidates_token_count or 0)+(usage.thoughts_token_count or 0);rate=q['tariff'];cost=(tin*rate['entrada']+tout*rate['salida'])/1e6;obj=json.loads(text)
  if query.get('task','object_recipe')=='object_recipe':
   from recetas_proveedor import validar
   validar(obj,query)
  elif query.get('task')=='recipe_batch':
   if not isinstance(obj.get('responses'),list):raise ValueError('Lote sin responses')
  elif obj.get('status') not in ['PROPOSAL_OR_FALTA','FALTA','PROPOSAL']:raise ValueError('Anatomía sólo admite propuesta/FALTA, no certificación inventada')
  if query.get('task')=='recipe_batch':obj['_usage_usd']=cost;return obj
  guardar(cache,{'query_sha256':huella(query),'response_sha256':huella(obj),'response':obj,'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'origin':'argon_stream_sb','usage_usd':cost});obj['_usage_usd']=cost;return obj
