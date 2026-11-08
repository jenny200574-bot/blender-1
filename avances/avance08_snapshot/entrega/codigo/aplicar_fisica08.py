import sys,json,copy,math,shutil
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';P=R/'esc1_candidata';M=R/'MOTOR_UNICO_20261107';sys.path.insert(0,str(E/'codigo'));sys.path.insert(0,str(M/'motor'))
from validar_fisica08 import validar
from seguridad import guardar,sha
read=lambda p:json.loads(p.read_text())
source=read(E/'config/physics04_sources.json');items=source['items'];patch=read(E/'evidencias/av08_physics04/respuesta.json');s03=read(E/'config/physics03_sources.json');meshes=s03['compiled_mesh_ids']
assert read(E/'evidencias/av08_physics04/schema_validacion.json')['passed']
assert patch['collider_indices']==list(range(len(items)))
get=lambda i:items[i]['id']
def pairs(name):
 result=[]
 for row in patch[name]:
  assert len(row)==2 and all(isinstance(i,int) and not isinstance(i,bool) and 0<=i<len(items) for i in row) and row[0]!=row[1]
  result.append([get(i) for i in row])
 return result
x=copy.deepcopy(source['previous']);x['physics']['colliders']=[get(i) for i in patch['collider_indices']];x['physics']['allowed_collision_pairs']=pairs('allowed_pair_indices');x['physics']['contact_pairs']=pairs('surface_contact_pair_indices');x['avian']['shoulder_offset_m']=patch['shoulder_offset_m'];x['avian']['support_polygon_offsets_m']=patch['support_polygon_offsets_m'];x['composition08']={'base':'av08_physics03; numeric bounded values only','repair':'av08_physics04 exact selector schema','approval':'No model approval; deterministic sanity plus subsequent actual scene physics required'}
known={o['id'] for o in s03['measured_inventory']['objects'] if o['type']=='MESH'}|{o['id'] for group in meshes.values() for ps in group.values() for o in ps};empty=set(meshes['prop_meshes']);errors=validar(x,known,meshes['character_meshes'],empty)
# No arbitrary inter-character penetrations or floor exemptions; surface contact does not waive depth.
owners={p['id']:p['owner'] for p in items}
for a,b in x['physics']['allowed_collision_pairs']:
 if owners[a]!=owners[b] or a=='piso' or b=='piso':errors.append('UNJUSTIFIED_PENETRATION_EXCEPTION:'+a+'|'+b)
for pair in x['physics']['contact_pairs']:
 if any(q not in x['physics']['colliders'] for q in pair):errors.append('INVALID_CONTACT_PAIR:'+str(pair))
mutationtests=[]
for k,v in [('root_speed_max_m_s',1e9),('bone_length_error_m',1),('joint_speed_max_deg_s',601),('colliders',[])]:
 bad=copy.deepcopy(x);bad['physics'][k]=v;found=validar(bad,known,meshes['character_meshes'],empty);mutationtests.append({'mutation':k,'rejected':bool(found)})
bad=copy.deepcopy(x);bad['avian']['balance_margin_m']=1;mutationtests.append({'mutation':'avian_margin1m','rejected':bool(validar(bad,known,meshes['character_meshes'],empty))})
guardar(E/'evidencias/physics08_sanity_final.json',{'passed':not errors,'errors':errors,'negative_tests':mutationtests,'bounds_source':'AV08 conservative deterministic engineering sanity bounds, NOT modified oro thresholds','scene_physics_approved':False,'colliders':len(x['physics']['colliders']),'model_approved_flag_used':False})
assert not errors,errors;assert all(t['rejected'] for t in mutationtests)
# Invoke native rule validator too, before touching candidate.
from puentes_fisicos import reglas
canonical,rule_errors=reglas(x['physics']);assert canonical is not None and not rule_errors
shutil.copytree(P,R/'esc1_antes_fisica08');d=read(P/'entrada_escena.json');eco=next(e for e in d['entities'] if e['id']=='ch-eco-eff3');bird=next(e for e in d['entities'] if e['id']=='ch-piquito-030a');a=x['avian'];measure=read(E/'evidencias/hombro_medido08.json');rot=measure['inverse_rotation_rows'];transform=lambda v:[sum(rot[i][j]*v[j] for j in range(3)) for i in range(3)];assert a['rotation_relative_eco_deg']==[0,0,0]
point_source={'method':'ARGON_PROPOSED_SCENE_PARAMETERS; REST frame conversion from measured native Eco clavicle','measurement_sha256':sha(E/'evidencias/hombro_medido08.json'),'proposal_sha256':sha(E/'evidencias/av08_physics04/respuesta.json'),'not_certified_until_actual_scene_review':True}
points=[{'id':'hombro_L_aviar','bone':'clavicula_L','position_m':transform(a['shoulder_offset_m']),'rotation_deg':measure['inverse_rotation_euler_deg'],'frame':'LOCAL','source':point_source}]
for i,v in enumerate(a['support_polygon_offsets_m']):points.append({'id':'soporte_piquito_'+str(i),'bone':'clavicula_L','position_m':transform(v),'rotation_deg':measure['inverse_rotation_euler_deg'],'frame':'LOCAL','source':point_source})
assert not eco.get('points');eco['points']=points
profile=bird['anatomy_profile'];profile['physics']={'balance_margin_m':a['balance_margin_m'],'support_intervals':a['support_intervals'],'proposal_source':'argon08_physics_canonica.json','not_physically_certified':True};profile['attachment']=a['attachment'];profile['source']='Argon08 proposed physics + measured native Eco left shoulder; engine checks mandatory'
bird['anatomy_profile']=profile;bird['dna_record']['source_data']['anatomy_profile']=copy.deepcopy(profile)
d['rules_source']=canonical;program=read(P/'programa_2b.json');program.update(contacts=x['contacts'],contacts_complete=True,contact_design_source='argon08_physics_canonica.json; attachment is explicit rigid parent binding, not external IK',physics_validated=False)
# Deterministic native geometry/phase prevalidation admits only CPU validation; final review cannot be skipped.
pre=read(E/'evidencias/movimientos08_prevalidacion_cpu.json');assert pre['passed'] and pre['unique_used_movements']==15
cat=read(P/'catalogo_poses_escena.json');used={r['movimiento'] for r in read(P/'asignacion_para_motor.json')}
for mid in used:
 checks=[q for q in pre['checks'] if q['movement']==mid];assert checks and all(q['passed'] for q in checks)
 cat['movimientos'][mid]['validado']=True
 cat['movimientos'][mid]['approval_ref']={'path':'movimientos08_prevalidacion_cpu.json','sha256':sha(E/'evidencias/movimientos08_prevalidacion_cpu.json'),'scope':'NATIVE_CPU_POSE_AND_PHASE_SANITY_FOR_CPU_TRIAL_ONLY; scene dynamics/collision/balance NOT approved','production_approved':False,'issued_by':'deterministic native rig test, not model'}
for name,value in [('argon08_physics_canonica.json',x),('programa_2b.json',program),('catalogo_poses_escena.json',cat),('physics08_sanity_final.json',read(E/'evidencias/physics08_sanity_final.json')),('movimientos08_prevalidacion_cpu.json',pre),('hombro_medido08.json',measure)]:guardar(P/name,value)
# Complete canonical reconstruction tracks final catalog, while original truncation stays in archive.
raw=read(P/'respuesta_2b.json');raw['movimientos']=cat['movimientos'];raw['program']=program;raw['physics_proposal']='argon08_physics_canonica.json';guardar(P/'respuesta_2b.json',raw)
for name in ['argon08_physics_canonica.json','physics08_sanity_final.json','movimientos08_prevalidacion_cpu.json','hombro_medido08.json']:
 if not any(z['path']==name for z in d['assets']):d['assets'].append({'path':name,'sha256':sha(P/name),'bytes':(P/name).stat().st_size,'type':'json'})
d['sources'].append({'module':'Argon08 per-scene proposed physics; native sanity validated, physical review pending','path':'argon08_physics_canonica.json','sha256':sha(P/'argon08_physics_canonica.json')})
for z in d['assets']:z.update(sha256=sha(P/z['path']),bytes=(P/z['path']).stat().st_size)
for z in d['sources']:z['sha256']=sha(P/z['path'])
guardar(P/'entrada_escena.json',d);guardar(E/'evidencias/aplicacion_fisica08.json',{'candidate_backup':str(R/'esc1_antes_fisica08'),'source_2b_complete':True,'physics_proposed_by_argon':True,'sanity_passed':True,'fixed_rules_unchanged':True,'no_T317_values_imported':True,'native_measured_left_shoulder_frame':True,'external_ik_contacts':len(x['contacts']),'explicit_rigid_attachment':True,'movements_admitted_for_cpu_trial':len(used),'scene_physics_approved':False})
print('Physics sanity passed, native rule binding passed; ready for full native preflight and mandatory actual review')
