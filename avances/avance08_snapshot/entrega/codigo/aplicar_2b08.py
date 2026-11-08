import json,copy,re,hashlib,shutil,sys
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';P=R/'esc1_candidata';M=R/'MOTOR_UNICO_20261107';sys.path.insert(0,str(M/'motor'));from seguridad import guardar,sha
read=lambda p:json.loads(p.read_text());x=read(E/'evidencias/av08_2b03/respuesta.json');source=read(E/'config/2b_sources.json');d=read(P/'entrada_escena.json');cat=read(P/'catalogo_poses_escena.json');rows=read(P/'asignacion_para_motor.json')
assert read(E/'evidencias/av08_2b03/schema_validacion.json')['passed'];assert [q['index'] for q in x['rows']]==list(range(52))
def texts(v):
 if isinstance(v,str):yield v
 elif isinstance(v,dict):
  for a in v.values():yield from texts(a)
 elif isinstance(v,list):
  for a in v:yield from texts(a)
norm=lambda s:re.sub(r'\s+',' ',s).casefold();corpus=norm(' '.join(texts(source['source_01']))+' '+source['chapter'])
for q,old in zip(x['rows'],rows):
 assert norm(q['evidence_quote']) in corpus
 assert q['movement_id']==('m_hablar_visor_sin_toque' if old['movimiento']=='m_hablar_visor' else old['movimiento'])
newangles={};oldpose=cat['poses']['p_visor_toque']['angulos'];base=cat['poses']['p_de_pie_base']['angulos'];armkeys={'brazo_R','antebrazo_R','mano_R','brazo_L','antebrazo_L','mano_L'}
assert {v['bone'] for v in x['visor_pose_sources']}==set(oldpose)
for v in x['visor_pose_sources']:
 bone=v['bone'];expected='p_de_pie_base' if bone in armkeys else 'p_visor_toque';assert v['source_pose']==expected;newangles[bone]=copy.deepcopy(cat['poses'][expected]['angulos'][bone])
shutil.copytree(P,R/'esc1_antes_2b08')
cat['poses']['p_visor_sin_toque']={'angulos':newangles,'source':'Argon08 selected source angles; no new numeric angles','validado':False,'source_selection':'argon08_2b_propuesta.json#/visor_pose_sources'}
v=copy.deepcopy(cat['movimientos']['m_hablar_visor']);v['descripcion']='Mira el visor sin crear contacto físico de mano; brazos base, mirada del diseño existente.'
for f in v['fases']:
 if f['pose']=='p_visor_toque':f['pose']='p_visor_sin_toque'
v['validado']=False;v.pop('approval_ref',None);cat['movimientos']['m_hablar_visor_sin_toque']=v
for q,row in zip(x['rows'],rows):
 row['movimiento']=q['movement_id'];row['_source08']={'proposal_row':q['index'],'quote':q['evidence_quote'],'source_kind':q['source_kind'],'scope':'Narrative/source01 mapping confirmed; not physical approval'}
initials={}
for row in rows:
 if row.get('accion_plan','').startswith('segmento_01_') and row.get('t0')==0:initials[row['personaje']]=cat['movimientos'][row['movimiento']]['fases'][0]['pose']
assert len(initials)==5
shutil.copy2(P/'respuesta_2b.json',P/'archivo/respuesta_2b_truncada_pre08.json')
program={'status':'complete','narrative_source_complete':True,'physics_validated':False,'iniciales':initials,'anclas_semanticas':x['contact_intents'],'coverage':{'needed':52,'covered':52,'missing':[]},'producer':'Argon08 + deterministic exact-source compiler','source_zip_sha256':'9e7f7f91c915aff858fb144da0399063ab2543f17dde94df85d95c88770b12bb','notes':['New reconstruction from complete authorized chapter and01; NOT recovered original truncated API tail.','All52rows cited literally;15movement technical validation pending; visor touch removed without new angles.']}
newraw={'status':'complete','finish_reason':'STOP','reconstruction08':True,'poses':cat['poses'],'movimientos':cat['movimientos'],'asignacion':rows,'program':program,'source_response':'argon08_2b_propuesta.json'}
for name,value in [('catalogo_poses_escena.json',cat),('asignacion_para_motor.json',rows),('programa_2b.json',program),('respuesta_2b.json',newraw),('argon08_2b_propuesta.json',x)]:guardar(P/name,value)
d['motion']['status']='complete';notes=[a for a in d['provisional'] if a.get('campo')=='2B'];d['provisional']=[a for a in d['provisional'] if a not in notes];d.setdefault('normalization_history',[]).extend({'resolved_note':n,'reason':'Complete authorized narrative reconstruction, exact52tuples and literal source quotes; physical approval remains separate mandatory gate.'} for n in notes)
for name in ['argon08_2b_propuesta.json','archivo/respuesta_2b_truncada_pre08.json']:
 if not any(a['path']==name for a in d['assets']):d['assets'].append({'path':name,'sha256':sha(P/name),'bytes':(P/name).stat().st_size,'type':'json'})
d['sources'].append({'module':'Argon08 complete narrative-source proposal','path':'argon08_2b_propuesta.json','sha256':sha(P/'argon08_2b_propuesta.json')})
for a in d['assets']:a.update(sha256=sha(P/a['path']),bytes=(P/a['path']).stat().st_size)
for a in d['sources']:a['sha256']=sha(P/a['path'])
guardar(P/'entrada_escena.json',d);guardar(E/'evidencias/2b08_validacion_fuente.json',{'passed':True,'rows':52,'all_quotes_literal':True,'ids_times_layers_unchanged':True,'one_movement_replaced_to_remove_unsourced_touch':True,'new_numeric_pose_angles':0,'original_truncated_preserved':True,'physics_or_production_approved':False})
print('2B52complete, literal source verified; movements still require deterministic validation')
