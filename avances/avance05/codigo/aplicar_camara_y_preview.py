import json,sys,math,shutil,hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path(__file__).resolve().parents[1];ROOT=B.parent;R=ROOT/'MOTOR_UNICO_20261107';pk=ROOT/'esc1_candidata';sys.path.insert(0,str(R/'motor'))
from seguridad import guardar,sha
from orquestador import ejecutar
out=B/'evidencias/iteracion08_camara_escalar';schema=json.loads((out/'schema_validacion.json').read_text());value=json.loads((out/'respuesta.json').read_text())
if not schema['passed']:raise ValueError('Schema failed')
for key in ['pan_v3_degrees','crane_v5_distance_m','pan_v7_degrees']:
 if not isinstance(value[key],(int,float)) or not math.isfinite(value[key]) or value[key]<=0:raise ValueError('Invalid camera amplitude '+key)
if not value['source'].startswith('Argon_GENERATED'):raise ValueError('Must identify new generated design')
receipt={'fecha_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'semantic_passed':True,'source_response_sha256':sha(out/'respuesta.json'),'source':value['source'],'changes':[],'production_approved':False}
d=json.loads((pk/'entrada_escena.json').read_text());sbfile=pk/'storyboard_camara.json';sb=json.loads(sbfile.read_text());commandsfile=pk/'camara_4g/commands.json';commands=json.loads(commandsfile.read_text())
if (pk/'storyboard_antes_argon05.json').exists():raise ValueError('Already patched')
shutil.copy2(sbfile,pk/'storyboard_antes_argon05.json')
for shot,key,mode,arg in [('v3','pan_v3_degrees','PAN','degrees'),('v5','crane_v5_distance_m','CRANE','distance'),('v7','pan_v7_degrees','PAN','degrees')]:
 a=next(s for s in sb['vinetas'] if s['vineta']==shot);segment=a['segmentos'][0]
 if segment['movimiento']!=mode:raise ValueError('Unexpected source camera movement')
 segment['args'][arg]=value[key]
 row=commands[shot]['movimiento'][0]
 if row[2]!=mode:raise ValueError('Commands movement differs')
 row[3][arg]=value[key]
 source_data=next(s for s in d['camera']['shots'] if s['id']==shot)['source_data'];source_data['segmentos'][0]['args'][arg]=value[key]
 receipt['changes'].append({'field':'camera/'+shot+'/0/'+mode,'argument':arg,'value':value[key],'original_direction':segment['args'].get('dir_lr',segment['args'].get('dir_ud'))})
guardar(sbfile,sb);guardar(commandsfile,commands)
for name,p in [('argon_camara05_respuesta.json',out/'respuesta.json'),('argon_camara05_schema_validacion.json',out/'schema_validacion.json'),('argon_camara05_schema.json',B/'config/camera_scalars.schema.json')]:shutil.copy2(p,pk/name)
guardar(pk/'argon_camara05_recibo.json',receipt)
newnames=['storyboard_antes_argon05.json','argon_camara05_respuesta.json','argon_camara05_schema_validacion.json','argon_camara05_schema.json','argon_camara05_recibo.json']
for a in d['assets']:
 p=pk/a['path'];a.update(sha256=sha(p),bytes=p.stat().st_size)
for name in newnames:
 p=pk/name;d['assets'].append({'path':name,'sha256':sha(p),'bytes':p.stat().st_size,'type':'json'})
for s in d['sources']:s['sha256']=sha(pk/s['path'])
d['sources'].extend([{'module':'SB original antes Argon05','path':'storyboard_antes_argon05.json','sha256':sha(pk/'storyboard_antes_argon05.json')},{'module':'Argon Vertex gemini-3-flash-preview / SB numérico GENERATED','path':'argon_camara05_respuesta.json','sha256':sha(pk/'argon_camara05_respuesta.json')}]);d['camera']['numeric_amplitudes_provenance']='argon_camara05_recibo.json';guardar(pk/'entrada_escena.json',d);guardar(B/'evidencias/aplicacion_camara.json',receipt)
# No implicit external generation: preserve dry_run and .off; additionally disable automatic discovery on this isolated copy.
policy=R/'config/politica_ejecucion.json';shutil.copy2(policy,ROOT/'politica_antes_preview.json');pol=json.loads(policy.read_text());pol['argon_automatico']=False;guardar(policy,pol)
res=ejecutar(pk/'entrada_escena.json',ROOT/'preview_cpu_esc1',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False)
summary={'fecha_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':res['estado'],'faltantes':len(res['errores']),'errores':res['errores'],'master':res.get('master'),'gpu_used':False,'paid_network_calls_in_preview':0,'production_approved':False};guardar(B/'evidencias/preview_cpu_resultado.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='errores'},ensure_ascii=False))
