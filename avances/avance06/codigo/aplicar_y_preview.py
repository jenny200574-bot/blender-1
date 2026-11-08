import json,sys,shutil,copy
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';R=B/'MOTOR_UNICO_20261107';P=B/'esc1_candidata';sys.path.insert(0,str(R/'motor'));from seguridad import guardar,sha
from orquestador import ejecutar
read=lambda p:json.loads(p.read_text());v=read(E/'evidencias/validacion_semantica.json');bl=read(E/'evidencias/blender_diseno_world_resultado.json');assert all(v[k]['passed'] for k in ['bird_rig','appearance','lighting','audit']) and bl['passed']
shutil.copytree(P,B/'esc1_antes_aplicar06');d=read(P/'entrada_escena.json');dna=read(P/'adn_entidades.json');anatomy=read(E/'evidencias/bird_rig_canonico.json');appearance=read(E/'evidencias/bird_apariencia_canonica.json');light=read(E/'evidencias/iluminacion_canonica.json');ent=next(e for e in d['entities'] if e['id']=='ch-piquito-030a');record=next(e for e in dna['records'] if e['id']==ent['id']);record['source_data']['anatomy_profile']=copy.deepcopy(anatomy);record['source_data']['generated_geometry_candidate']=copy.deepcopy(appearance);record['source_data']['generation06_scope']='Generated static design, validated build. NOT certified physics, attachment, facial animation or final visual approval.'
ent['anatomy_profile']=copy.deepcopy(anatomy);ent['dna_record']=copy.deepcopy(record)
# Native declarative appearance contract; never declare the physical/attachment source complete.
app=ent.setdefault('appearance',{});app['geometry']={'parts':appearance['parts'],'source':appearance['source'],'required_roles':sorted({p['feature'] for p in appearance['parts']}),'final_appearance_ref':{'scope':'GENERATED_STATIC_CPU_CONSTRUCTION_ONLY; no facial/visual/physics approval','response':'argon_piquito06_apariencia.json','visual_approved':False}}
for field in ['rostros_finales','ropa_final']:app[field]={'asset':'argon_piquito06_apariencia.json','source':appearance['source'],'scope':'Legacy contract slot links supplied geometry; NOT a final visual or facial approval'}
guardar(B/'respaldos/iluminacion_y_notas_antes06.json',{'lighting':d.get('lighting'),'provisional':d.get('provisional')});d['lighting']=light
oldnotes=[n for n in d.get('provisional',[]) if n.get('campo') in ['luces','iluminacion']];d['provisional']=[n for n in d.get('provisional',[]) if n not in oldnotes];d.setdefault('normalization_history',[]).extend({'resolved_note':n,'reason':'Previous technical light profile replaced by explicit generated artistic AREA+World profile, independently built on CPU; no visual-production approval claimed.'} for n in oldnotes)
guardar(P/'adn_entidades.json',dna)
assets=[('bird_rig_canonico.json','argon_piquito06_rig.json'),('bird_apariencia_canonica.json','argon_piquito06_apariencia.json'),('bird_apariencia_procedencia.json','argon_piquito06_procedencia.json'),('iluminacion_canonica.json','argon_luces06.json'),('blender_diseno_world_resultado.json','argon06_construccion_validada.json')]
for src,dst in assets:
 shutil.copy2(E/'evidencias'/src,P/dst);d['assets'].append({'path':dst,'sha256':sha(P/dst),'bytes':(P/dst).stat().st_size,'type':'json'});d['sources'].append({'module':'Argon GENERATED validated design AVANCE06; not production approval','path':dst,'sha256':sha(P/dst)})
for a in d['assets']:a.update(sha256=sha(P/a['path']),bytes=(P/a['path']).stat().st_size)
for s in d['sources']:s['sha256']=sha(P/s['path'])
guardar(P/'entrada_escena.json',d);guardar(E/'evidencias/aplicacion06.json',{'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'applied':['Piquito 19-bone design, anatomy incomplete without physical/anchor sources','40 static geometry parts, not facial approval','3 AREA lights + World/exposure/gamma'],'live_applied':False,'twoB_changed':False,'physics_rules_changed':False,'equivalences_invented':False,'production_approved':False})
r=ejecutar(P/'entrada_escena.json',B/'preview_cpu_esc1',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False);summary={'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':r['estado'],'faltantes':len(r['errores']),'errores':r['errores'],'master':r.get('master'),'gpu_used':False,'paid_network_calls_in_preview':0,'production_approved':False};guardar(E/'evidencias/preview_cpu_resultado.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='errores'}))
