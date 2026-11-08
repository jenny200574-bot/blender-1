#!/usr/bin/env python3
"""Puente restringido n8n/T317. preparar/traducir son gratuitos y no renderizan."""
import argparse,copy,fcntl,hashlib,json,re,shutil,sys,uuid,datetime,os
from pathlib import Path
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parent;ENGINE=BASE/'MOTOR_UNICO_20261107'
sys.path.insert(0,str(ENGINE/'motor'))
from seguridad import leer,guardar,sha,ruta

def ident(s):
 if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',s) or '..' in s:raise ValueError('Identificador inválido')
 return s

def contexto(a):
 t=Path('/opt/myia-taller-n8n');sys.path.insert(0,str(t/'cajas/storyboard'))
 import entradas_sb_v2 as e
 ctx=e.assemble(t,a.canal,a.capitulo,a.escena)
 d=t/'trabajo/paso00_cadena'/a.canal/ctx['capitulo_folder']
 return ctx,d

def paquete(a):
 ctx,d=contexto(a);home=BASE/'trabajo'/a.canal/ctx['capitulo_folder']/('esc_'+str(ctx['escena']))
 if a.paquete:
  p=ruta(home,ident(a.paquete))
  if not (p/'entrada_escena.json').is_file():raise ValueError('Paquete no encontrado para este canal/capítulo/escena')
  return p,ctx,d
 src=d/'cubos/01'/('esc_'+str(ctx['escena'])+'.json');raw=leer(src)
 sb=d/'cubos/SB/blender'/('esc_'+str(ctx['escena'])+'_camara.json')
 molde=d/'ramas/moldes'/ident(str(raw.get('escenario_id','')))/'molde.blend'
 required={sha(src),sha(sb),sha(molde)};matches=[]
 for candidate in sorted((ENGINE/'paquetes').glob('*/entrada_escena.json')):
  data=leer(candidate);hashes={x.get('sha256') for x in data.get('assets',[])}|{x.get('sha256') for x in data.get('sources',[])}
  if required<=hashes:matches.append((candidate,data))
 # Un paquete canónico previo sólo se reutiliza si coinciden las TRES fuentes actuales.
 if not matches:raise ValueError('FALTA_ADAPTADOR_CANONICO: no hay paquete con los hashes exactos de 01, SB y molde actuales; no usar datos de otra escena')
 candidate,data=matches[0];source=candidate.parent
 name=datetime.datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d_%H%M%S_')+uuid.uuid4().hex[:8];out=home/name;out.mkdir(parents=True,exist_ok=False)
 for asset in data['assets']:
  origin=ruta(source,asset['path'])
  if sha(origin)!=asset['sha256'] or origin.stat().st_size!=asset['bytes']:raise ValueError('Hash de asset canónico alterado')
  target=ruta(out,asset['path']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,target)
 fresh={'source_01':str(src),'source_01_sha256':sha(src),'source_sb':str(sb),'source_sb_sha256':sha(sb),'molde':str(molde),'molde_sha256':sha(molde),'canonical_template':str(candidate),'canonical_template_sha256':sha(candidate),'method':'exact_source_hash_match','canal':a.canal,'capitulo':ctx['capitulo_folder'],'escena':ctx['escena']}
 guardar(out/'procedencia_n8n.json',fresh);data['assets'].append({'path':'procedencia_n8n.json','sha256':sha(out/'procedencia_n8n.json'),'bytes':(out/'procedencia_n8n.json').stat().st_size,'type':'json'})
 data['sources'].append({'module':'02T/n8n actual','path':'procedencia_n8n.json','sha256':sha(out/'procedencia_n8n.json')})
 policy=leer(ENGINE/'config/funciones_produccion.json')
 for key in policy['solver_keys']:data.setdefault('legacy',{}).setdefault('solver',{})[key]=policy['features'][key]
 data.setdefault('render',{}).update(engine=policy['render']['engine'],samples=policy['render']['samples'],resolution=policy['render']['resolution'])
 data['render']['source_policy_sha256']=sha(ENGINE/'config/funciones_produccion.json')
 data['requested_features']=policy['features']
 data['job_id']=name;guardar(out/'entrada_escena.json',data)
 return out,ctx,d

def traducir(a):
 pk,ctx,src=paquete(a)
 from orquestador import ejecutar
 run=pk/('validacion_'+uuid.uuid4().hex[:8]);result=ejecutar(pk/'entrada_escena.json',run,prueba_cpu=True,solo_validar=True)
 missing=[{'campo':e['campo'],'modulo_productor':e['modulo'],'que_falta':e['mensaje'],'bloqueante':True,'codigo':e['codigo'],'accion':e.get('accion')} for e in result['errores']]
 guardar(pk/'faltantes.json',{'faltantes':missing,'bloqueantes':len(missing)})
 report={'ok':True,'estado':result['estado'],'paquete_id':pk.name,'paquete_dir':str(pk),'entrada_escena':str(pk/'entrada_escena.json'),'canal':a.canal,'capitulo':ctx['capitulo_folder'],'escena':str(ctx['escena']),'apto_entrada':not missing,'apto_produccion':False,'apto_previa':False,'camara_sb':True,'faltantes':len(missing),'bloqueantes':len(missing),'gasto_usd':0,'llamadas_pagas':0,'network_paid':False,'renderizado':False,'validacion_dir':str(run),'faltantes_archivo':str(pk/'faltantes.json'),'datos_faltantes':missing,'fuentes_sha256':leer(pk/'procedencia_n8n.json')}
 guardar(pk/'traduccion_informe.json',report);return report

def main():
 p=argparse.ArgumentParser();p.add_argument('accion',choices=['preparar','traducir','armar']);p.add_argument('--canal',required=True,type=ident);p.add_argument('--capitulo',required=True,type=ident);p.add_argument('--escena',required=True,type=ident);p.add_argument('--paquete',type=ident);a=p.parse_args()
 if a.accion in ['preparar','traducir']:r=traducir(a)
 else:
  # Nunca caer al motor anterior ni producir un vídeo parcial.
  r=traducir(a)
  if r['bloqueantes']:r.update(ok=False,error='DATOS_BLOQUEANTES: ver faltantes.json')
  elif (ENGINE/'motor_unico.off').exists():r.update(ok=False,error='PRODUCCION_APAGADA: falta completar promoción validada')
  else:r.update(ok=False,error='EJECUTOR_GPU_PENDIENTE: no renderizar en el VPS sin espacio')
 print(json.dumps(r,ensure_ascii=False));return 0
if __name__=='__main__':
 try:sys.exit(main())
 except (ValueError,OSError,KeyError,TypeError) as e:
  print(json.dumps({'ok':False,'error':str(e),'gasto_usd':0,'llamadas_pagas':0},ensure_ascii=False));sys.exit(1)
