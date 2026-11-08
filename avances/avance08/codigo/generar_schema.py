import json,sys,fcntl,os,hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path(__file__).resolve().parents[1]
def now():return datetime.now(ZoneInfo('America/Bogota')).isoformat()
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False));os.replace(tmp,p)
def vertex_schema(d):
 if isinstance(d,list):return [vertex_schema(x) for x in d]
 if isinstance(d,dict):return {k:(v.upper() if k=='type' else vertex_schema(v)) for k,v in d.items()}
 return d
def standard(d):
 if isinstance(d,list):return [standard(v) for v in d]
 if isinstance(d,dict):
  out={k:standard(v) for k,v in d.items() if k!='nullable'}
  if d.get('nullable'):return {'anyOf':[out,{'type':'null'}]}
  return out
 return d

def main():
 if (B/'config/generador.off').exists():raise ValueError('AV08 closed before network/ledger')
 name=sys.argv[1]
 if not name.replace('_','').isalnum():raise ValueError('Invalid iteration name')
 out=B/'evidencias'/name
 if out.exists():raise ValueError('Iteration must be new')
 out.mkdir(parents=True)
 selected=lambda env,default:B/'config'/os.environ.get(env,default)
 schema=json.loads(selected('MYIA_SCHEMA','repair.schema.json').read_text());prompt=selected('MYIA_PROMPT','repair_prompt.txt').read_text()+'\nFUENTES\n'+selected('MYIA_SOURCES','repair_source_pack.json').read_text()
 if len(sys.argv)>2:prompt+='\nERRORES A REPARAR\n'+Path(sys.argv[2]).read_text()
 nbytes=len(prompt.encode())+len(json.dumps(schema).encode()); imagepaths=json.loads(selected('MYIA_SOURCES','repair_source_pack.json').read_text()).get('_image_paths',[]); nbytes+=len(imagepaths)*24000;reserve=round(((nbytes+2048)*.5+32768*3)/1e6,8)
 ledger=B/'evidencias/ledger.json'
 with (B/'evidencias/ledger.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=json.loads(ledger.read_text()) if ledger.exists() else {'step_cap_usd':10,'plan_cap_usd':50,'preventive_plan_stop_usd':45,'previous_plan_gross_usd':.669088,'step_gross_usd':0,'reserved_usd':0,'entries':[]}
  if d['step_gross_usd']+d['reserved_usd']+reserve>d['step_cap_usd'] or d['previous_plan_gross_usd']+d['step_gross_usd']+d['reserved_usd']+reserve>45:raise ValueError('Budget rejected')
  ref=str(len(d['entries'])+1);d['entries'].append({'id':ref,'purpose':name,'date_bogota':now(),'state':'RESERVED_BEFORE_NETWORK','reserve_usd':reserve,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'schema_sha256':hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest(),'model':'gemini-3-flash-preview'});d['reserved_usd']+=reserve;save(ledger,d)
 from google import genai
 from google.genai import types
 from google.oauth2 import service_account
 cred=service_account.Credentials.from_service_account_file(__import__('os').environ['VERTEX_SA_FILE'],scopes=['https://www.googleapis.com/auth/cloud-platform'])
 schema_mode=os.environ.get('MYIA_SCHEMA_MODE','vertex')
 schema_kwargs={'response_json_schema':standard(schema)} if schema_mode=='json' else {'response_schema':vertex_schema(schema)}
 client=genai.Client(vertexai=True,project='${GCP_PROJECT_ID}',location='global',credentials=cred,http_options=types.HttpOptions(api_version='v1',base_url='https://aiplatform.googleapis.com',timeout=900000,retry_options=types.HttpRetryOptions(attempts=1)))
 parts=[types.Part.from_text(text=prompt)]
 for ip in imagepaths:
  import mimetypes
  p=Path(ip).resolve()
  if not str(p).startswith(('/opt/myia-taller-n8n/trabajo/','/opt/myia-taller-n8n/cajas/FIJOS_TALLER/','/opt/myia-taller-n8n/cajas/cubo_fijo/hojas/')) or p.suffix.lower() not in ['.png','.jpg','.jpeg','.webp'] or p.stat().st_size>8000000:raise ValueError('Image not allowed')
  parts.append(types.Part.from_bytes(data=p.read_bytes(),mime_type=mimetypes.guess_type(str(p))[0]))
 text='';usage=None;finish=None;code=None;phase='network';cost=None
 try:
  for chunk in client.models.generate_content_stream(model='gemini-3-flash-preview',contents=[types.Content(role='user',parts=parts)],config=types.GenerateContentConfig(response_mime_type='application/json',**schema_kwargs,max_output_tokens=32768,thinking_config=types.ThinkingConfig(thinking_level='LOW'))):
   if chunk.usage_metadata:usage=chunk.usage_metadata
   for c in chunk.candidates or []:
    if c.finish_reason:finish=str(c.finish_reason)
    for p in (c.content.parts if c.content else []) or []:
     if p.text and not p.thought:text+=p.text
  (out/'respuesta_raw.json').write_text(text);phase='parse'
  if usage is None:raise ValueError('No usage; reservation retained')
  tin=usage.prompt_token_count or 0;cached=usage.cached_content_token_count or 0;tout=(usage.candidates_token_count or 0)+(usage.thoughts_token_count or 0);cost=((tin-cached)*.5+cached*.05+tout*3)/1e6
  save(out/'consumo.json',{'date_bogota':now(),'input_tokens':tin,'output_including_thoughts_tokens':tout,'cached_tokens':cached,'gross_usd':cost,'net_expected_credits_usd':0,'invoice_verified':False,'finish':finish,'usage':usage.model_dump(mode='json')})
  obj=json.loads(text)
  import jsonschema
  errors=[{'path':'/'.join(map(str,e.path)),'message':e.message} for e in jsonschema.Draft202012Validator(standard(schema)).iter_errors(obj)]
  if 'STOP' not in str(finish):errors.append({'path':'finish','message':'Not complete STOP'})
  save(out/'schema_validacion.json',{'passed':not errors,'errors':errors,'response_mime_type':'application/json','response_schema_sent':schema_mode=='vertex','response_json_schema_sent':schema_mode=='json','schema_mode':schema_mode});save(out/'respuesta.json',obj)
  print(json.dumps({'iteration':name,'schema_passed':not errors,'errors':len(errors),'gross_usd':cost}))
 except Exception as exc:
  sys.path.insert(0,'/opt/myia-motor-v9/avance07_20261107/MOTOR_UNICO_20261107/motor');from errores_seguro import mensaje_seguro
  code=getattr(exc,'code',None);save(out/'error.json',{'date_bogota':now(),'phase':phase,'type':type(exc).__name__,'code':str(code),'usage_received':usage is not None,'safe_message':mensaje_seguro(exc)[:4000]});print(json.dumps({'iteration':name,'phase':phase,'error_type':type(exc).__name__,'code':str(code)}))
 finally:
  client.close()
  if cost is not None or str(code) in ['400','401','403','404','429','500','503']:
   with (B/'evidencias/ledger.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);d=json.loads(ledger.read_text());entry=next(e for e in d['entries'] if e['id']==ref);entry.update(state='SETTLED' if cost is not None else 'NON200_NO_TOKEN_CHARGE',gross_usd=cost or 0,settled_bogota=now());d['step_gross_usd']+=cost or 0;d['reserved_usd']=round(d['reserved_usd']-reserve,10);save(ledger,d)
if __name__=='__main__':main()
