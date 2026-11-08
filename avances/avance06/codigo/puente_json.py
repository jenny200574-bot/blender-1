import os,sys,json,re,base64,subprocess,hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance06_20261107/entrega');ROOT=B.parent
SAFE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')
def output(d,code=0):print(json.dumps(d,ensure_ascii=False));raise SystemExit(code)
def legacy():
 p=Path('/opt/myia-taller-n8n/cajas/sello_pago.py');ns={'__name__':'sello_legacy'};exec(compile(p.read_text().split("if __name__ == '__main__':")[0],str(p),'exec'),ns);return ns

def ako_text(obj,cl,ident):
 if isinstance(obj,str):
  try:obj=json.loads(obj)
  except json.JSONDecodeError:return obj
 if not isinstance(obj,dict) or obj.get('schema')!='ako_json/v1' or obj.get('id')!=ident or obj.get('clase')!=cl:raise ValueError('Wrong schema/id/class')
 if any(not isinstance(obj.get(f'bloque_{i}'),str) for i in range(1,6)):raise ValueError('Missing Ako block')
 return '\n\n'.join(obj[f'bloque_{i}'] for i in range(1,6))

def runjob(name,entry):
 if not SAFE.fullmatch(name):raise ValueError('Invalid job')
 if (ROOT/'generador.off').exists():output({'ok':False,'error':'generador.off','llamadas_hechas':0},1)
 for k in ['schema','prompt','sources']:
  if not re.fullmatch(r'[A-Za-z0-9_-]+(?:\.schema)?\.(json|txt)',entry[k]):raise ValueError('Config outside registry')
  p=B/'config'/entry[k]
  if p.is_symlink() or p.stat().st_uid!=0 or p.stat().st_mode&0o022:raise ValueError('Untrusted job config')
 env={k:v for k,v in os.environ.items() if k in ['PATH','LANG','HOME']};env.update(MYIA_SCHEMA=entry['schema'],MYIA_PROMPT=entry['prompt'],MYIA_SOURCES=entry['sources'])
 r=subprocess.run([sys.executable,'-I',str(B/'codigo/generar_schema.py'),name],env=env,capture_output=True,text=True)
 p=B/'evidencias'/name;v=json.loads((p/'schema_validacion.json').read_text()) if (p/'schema_validacion.json').exists() else {'passed':False}
 if r.returncode or not v['passed']:return {'ok':False,'job':name,'error':'generation/schema failed; see root-only evidence','llamadas_hechas':1}
 return {'ok':True,'job':name,'schema_valid':True,'resultado':json.loads((p/'respuesta.json').read_text()),'production_approved':False,'salida':str(p/'respuesta.json')}

def main():
 import argparse
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='op',required=True);sub.add_parser('estado');j=sub.add_parser('ejecutar');j.add_argument('job');a=sub.add_parser('adn');a.add_argument('pedido');a.add_argument('--ok',type=float,required=True);a.add_argument('--aprobado',required=True);args=ap.parse_args()
 if args.op=='estado':
  d=json.loads((B/'evidencias/ledger.json').read_text());output({'ok':True,'gross_usd':d['step_gross_usd'],'reserved_usd':d['reserved_usd'],'cap_usd':d['step_cap_usd'],'off':(ROOT/'generador.off').exists()})
 if args.op=='ejecutar':
  registry=json.loads((B/'config/registry.json').read_text())
  if args.job not in registry:output({'ok':False,'error':'job not approved'},1)
  output(runjob(args.job,registry[args.job]))
 if len(args.pedido)>50000 or not re.fullmatch(r'b64\.[A-Za-z0-9_-]+',args.pedido) or not SAFE.fullmatch(args.aprobado):raise ValueError('Bad request')
 text=args.pedido[4:];d=json.loads(base64.urlsafe_b64decode(text+'='*(-len(text)%4)))
 if d.get('formato')!='ako_json/v1' or not SAFE.fullmatch(str(d.get('id',''))) or not SAFE.fullmatch(str(d.get('canal',''))):raise ValueError('Invalid format/identity')
 # Separate live-payment gate remains closed until explicit live call approval; operator registry jobs are scoped separately.
 if (ROOT/'pago_adn_json.off').exists():output({'ok':False,'error':'pago_adn_json.off: adapted but live payment closed','llamadas_hechas':0})
 L=legacy();K=L['_cubo']();cl=K['ncl'](d.get('clase','personaje'));imgs=d.get('imagenes',[])
 if cl not in L['MAESTRO'] or not imgs or len(imgs)>8 or not all(L['ruta_ok'](x) for x in imgs):raise ValueError('Class/images invalid')
 if cl!='personaje':
  cat=K['catalogo']()
  if any(K['foto_de_personaje'](str(x),cat) for x in imgs):raise ValueError('Character image prohibited for object')
 prompt=K['llenar'](L['texto_fijo'](cl),K['canal_info'](d['canal'],d))[0]+'\nReturn schema ako_json/v1, with each bloque_N containing its full original numbered title and body; conserve the exact source identity. JSON only, no certificate/approval invented.\n'+str(d.get('extra',''))
 name='adn_'+datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d_%H%M%S')+'_'+hashlib.sha256(args.pedido.encode()).hexdigest()[:8]
 sources={'id':d['id'],'clase':cl,'_image_paths':imgs,'identity_reference':'Images supplied by caller, not a technical approval'}
 cfg={'schema':'ako.schema.json','prompt':name+'.txt','sources':name+'.json'}
 # Same conservative reservation formula as generator; legacy gate and per-call --ok enforced before network.
 reserve=((len((prompt+'\nFUENTES\n'+json.dumps(sources,ensure_ascii=False)).encode())+len((B/'config/ako.schema.json').read_text())+2048+len(imgs)*24000)*.5+32768*3)/1e6
 if reserve>args.ok:output({'ok':False,'error':'reserve exceeds --ok','llamadas_hechas':0})
 _,err=L['revisar'](args,reserve)
 if err:output({'ok':False,'error':err,'llamadas_hechas':0})
 for fn,data in [(cfg['prompt'],prompt),(cfg['sources'],json.dumps(sources,ensure_ascii=False))]:(B/'config'/fn).write_text(data)
 result=runjob(name,cfg)
 if not result['ok']:output(result)
 t=ako_text(result['resultado'],cl,d['id']);pa=K['parse_ako'](t,cl)
 result.update(ok=pa['status']=='PASS_SELLABLE',id=d['id'],clase=cl,adn_ako_texto=t,adn_json=result.pop('resultado'),inyeccion=pa.get('inyeccion'),fails=pa['fails'],formato='ako_json/v1')
 output(result)
if __name__=='__main__':
 try:main()
 except SystemExit:raise
 except Exception as e:output({'ok':False,'error_type':type(e).__name__,'error':'Invalid request or runtime error; inspect root-only evidence'},1)
