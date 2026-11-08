import json,sys,shutil,math
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path(__file__).resolve().parents[1];ROOT=B.parent;R=ROOT/'MOTOR_UNICO_20261107';pk=ROOT/'esc1_candidata';sys.path.insert(0,str(R/'motor'));from seguridad import guardar,sha
from orquestador import ejecutar
v=json.loads((B/'evidencias/validacion_planos.json').read_text());accepted=[]
for name in ['iteracion16_cofre_reparado2','iteracion17_cama_reparada2']:
 rec=v['recipes'][name]
 if not rec['passed']:raise ValueError('Recipe failed '+name)
 accepted.append((name,rec))
backup=ROOT/'esc1_antes_objetos';shutil.copytree(pk,backup)
d=json.loads((pk/'entrada_escena.json').read_text());dnafile=pk/'adn_entidades.json';dna=json.loads(dnafile.read_text());inventory=json.loads((pk/'inventario_set_medido.json').read_text());receipt={'fecha_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'applied':[],'values_generated_not_measured':True,'visual_approved':False,'physics_approved':False}
for name,checked in accepted:
 recipe=checked['recipe'];ident=recipe['id'];found=[r for r in dna['records'] if r.get('type')=='OBJECT' and (r['id']==ident or ident in r.get('exact_aliases',[]))]
 if len(found)!=1:raise ValueError('Ambiguous exact identity')
 record=found[0];source_data=record['source_data'];measured=[o for o in inventory['objects'] if o['id']==ident]
 if len(measured)!=1:raise ValueError('No exact measured placement')
 p=measured[0];rotation=[math.degrees(a) for a in p['rotation_euler_rad']]
 geometry={'parts':recipe['parts'],'placement':{'scene_object_id':ident,'position_m':p['position_m'],'rotation_deg':rotation,'source':'inventario_set_medido.json exact object '+ident},'material':recipe['parts'][0]['material'],'source':'Argon_GENERATED validated response '+name,'header_material_policy':'Header default aliases first/body part material; each piece retains its own Argon material. No material numbers are created.'}
 source_data['construction_3d']=geometry
 for f,target in [('respuesta.json','argon_'+ident+'_05_respuesta.json'),('semantic_validacion.json','argon_'+ident+'_05_validacion.json')]:
  shutil.copy2(B/'evidencias'/name/f,pk/target);path=pk/target;d['assets'].append({'path':target,'sha256':sha(path),'bytes':path.stat().st_size,'type':'json'})
 receipt['applied'].append({'id':ident,'record_id':record['id'],'response_sha256':sha(B/'evidencias'/name/'respuesta.json'),'part_count':len(recipe['parts']),'dimensions_m':checked['metrics']['dimensions_m'],'tolerance_m':checked['metrics']['tolerance_m'],'no_generated_number_changed':True,'placement_from_measured_inventory':True})
guardar(dnafile,dna);guardar(pk/'argon_objetos05_recibo.json',receipt)
for a in d['assets']:
 p=pk/a['path'];a.update(sha256=sha(p),bytes=p.stat().st_size)
p=pk/'argon_objetos05_recibo.json';d['assets'].append({'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'type':'json'})
for s in d['sources']:s['sha256']=sha(pk/s['path'])
d['sources'].append({'module':'Argon Vertex GENERATED / object recipe contract','path':'argon_objetos05_recibo.json','sha256':sha(p)});guardar(pk/'entrada_escena.json',d);guardar(B/'evidencias/aplicacion_objetos.json',receipt)
res=ejecutar(pk/'entrada_escena.json',ROOT/'preview_cpu_esc1_objetos',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False)
summary={'fecha_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':res['estado'],'faltantes':len(res['errores']),'errores':res['errores'],'master':res.get('master'),'gpu_used':False,'paid_network_calls_in_preview':0,'production_approved':False};guardar(B/'evidencias/preview_cpu_objetos_resultado.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='errores'},ensure_ascii=False))
