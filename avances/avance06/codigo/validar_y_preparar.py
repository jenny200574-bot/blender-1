import json,sys,math,copy,shutil
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';R=B/'MOTOR_UNICO_20261107';sys.path.insert(0,str(R/'motor'))
from geometria import validar_rig
from vivo_binding import compilar as vivo
from seguridad import guardar
num=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def read(p):return json.loads(p.read_text())
results={};raw=read(E/'evidencias/av06_bird02/respuesta.json');bones=[];radii={}
for b in raw['bones']:
 bone={'id':b['id'],'role':b['role'],'parent':b['parent'] or None,'head':[b['h'+k] for k in 'xyz'],'tail':[b['t'+k] for k in 'xyz'],'limits_deg':[[b['lim_'+k+'_min'],b['lim_'+k+'_max']] for k in 'xyz'],'source':raw['source']};bones.append(bone);radii[b['id']]=b['radius']
rig={'bones':bones};errors=validar_rig(rig);required=set(read(E/'config/bird_roles.json'))
if len(bones)!=19 or {b['role'] for b in bones}!=required:errors.append('19 exact roles required')
if sum(b['parent'] is None for b in bones)!=1:errors.append('one root required')
for b in bones:
 if not b['id'].startswith('ch-piquito-030a.'):errors.append('IDs must be namespaced')
 if not all(num(v) for v in b['head']+b['tail']+sum(b['limits_deg'],[])) or not num(radii[b['id']]) or radii[b['id']]<=0:errors.append('nonfinite/invalid bone value')
 if any(not 0<=v[2]<=.101 for v in [b['head'],b['tail']]):errors.append('bone outside official height')
results['bird_rig']={'passed':not errors,'errors':errors,'bone_count':len(bones),'source':raw['source'],'physics_approved':False,'attachment_approved':False,'missing':raw['missing_physics_and_anchor_source']}
if not errors:guardar(E/'evidencias/bird_rig_canonico.json',{'units':'m','rig':rig,'bone_radii_m':radii,'source':raw['source'],'status':'GENERATED_DESIGN_VALIDATED_TOPOLOGY_ONLY','missing_physics_and_anchor_source':raw['missing_physics_and_anchor_source']})
raw=read(E/'evidencias/av06_light02/respuesta.json');lights=[];errors=[]
for i in range(1,4):
 light={'id':raw[f'l{i}_id'],'type':raw[f'l{i}_type'],'shape':raw[f'l{i}_shape'],'size':raw[f'l{i}_size'],'energy':raw[f'l{i}_energy'],'color':[raw[f'l{i}_{k}'] for k in 'rgb'],'position_m':[raw[f'l{i}_p{k}'] for k in 'xyz'],'rotation_deg':[math.degrees(raw[f'l{i}_r{k}']) for k in 'xyz'],'frame':'WORLD','source':raw['source']}
 if not light['id'].startswith('av06.art.') or light['type']!='AREA' or light['shape'] not in ['SQUARE','DISK'] or not all(num(v) for v in [light['energy'],light['size']]+light['color']+light['position_m']+light['rotation_deg']) or light['energy']<0 or light['size']<=0 or any(not 0<=v<=1 for v in light['color']):errors.append('invalid emitter '+str(i))
 lights.append(light)
profile={'source':raw['source'],'base':lights,'events':[],'exposure':raw['exposure'],'gamma':raw['gamma'],'view_transform':raw['view_transform'],'world':{'id':'av06.art.world','color':[raw['world_'+k] for k in 'rgb'],'strength':raw['world_strength'],'source':raw['source']},'status':'GENERATED_ARTISTIC_DESIGN_NOT_VISUALLY_APPROVED'}
if len(set(l['id'] for l in lights))!=3 or not -5<=profile['exposure']<=5 or not .1<=profile['gamma']<=5 or not 0<=profile['world']['strength']<=5 or any(not 0<=v<=1 for v in profile['world']['color']):errors.append('profile bounds')
results['lighting']={'passed':not errors,'errors':errors,'emitter_count':len(lights),'visual_approved':False,'no_generated_value_changed':True,'rotation_conversion':'radians to degrees only','events':'empty: no invented narrative light keys'}
if not errors:guardar(E/'evidencias/iluminacion_canonica.json',profile)
l=read(E/'evidencias/av06_live01/respuesta.json');data=read(B/'esc1_candidata/entrada_escena.json');proposal=json.loads(l['live_payload_json']);data['environment']['live_data'].update(proposal,status=l['status'].lower());_,errs=vivo(data)
errs.extend([{'semantic':'No cambiar toda la ventana en vez de su arcoíris'}, {'semantic':'Color marrón del libro no demuestra letras temblando'}, {'semantic':'hide_render de Spark no prueba cuatro héroes ni FX'}, {'semantic':'new_parts no tiene dimensiones/receta canónica completa'}])
results['live']={'passed':False,'applied':False,'status':l['status'],'error_count':len(errs),'errors':errs,'missing':json.loads(l['missing_json'])}
fields=read(E/'config/audit_map.json');audit=read(E/'evidencias/av06_audit02/respuesta.json');remaining={x['campo'] for x in read(Path('/opt/myia-motor-v9/avance05_20261107/entrega/evidencias/preview_cpu_objetos_resultado.json'))['errores']};errs=[]
for key,field in fields.items():
 status=audit[key+'_status']
 if status not in ['SOURCE','GENERATED','FALTA']:errs.append({'field':field,'error':'bad status'})
 if field in remaining and status!='FALTA':errs.append({'field':field,'error':'claims missing field resolved without valid receipt','status':status})
results['audit']={'passed':not errs,'errors':errs,'no_scene_fields_applied':True}
# Full appearance is separate; do not let the four-piece first attempt replace the existing ADN.
p=E/'evidencias/av06_bird_appearance02/respuesta.json'
if p.exists():
 from recetas_proveedor import validar
 ar=read(p);parts=[];errs=[]
 for a in ar['parts']:
  part={'id':a['id'],'feature':a['feature'],'shape':a['shape'],'bind_role':a['bind_role'],'position_m':[a['p'+k] for k in 'xyz'],'rotation_deg':[a['r'+k] for k in 'xyz'],'dimensions_m':[a['d'+k] for k in 'xyz'],'material':{'rgba':[a[k] for k in ['r','g','b','a']],'metallic':a['metallic'],'roughness':a['roughness']},'resolution':a['resolution'],'tip_ratio':a['tip_ratio'],'source':a['source']};parts.append(part)
  if a['bind_role'] not in required:errs.append('unknown bone role')
  if not a['id'].startswith('ch-piquito-030a.'):errs.append('bad part namespace')
 features=read(E/'config/appearance_features.json')
 if sorted(a['feature'] for a in ar['parts'])!=sorted(features):errs.append('incomplete/duplicate feature set')
 if len(set(a['id'] for a in parts))!=len(parts):errs.append('duplicate part IDs')
 # Use engine validator for exact primitive/material rules without altering any supplied value.
 recipe={'id':'ch-piquito-030a','source':ar['source'],'parts':parts}
 # Generic validator's request envelope requires exact dimensions; use its primitive checks plus actual Blender envelope later.
 for part in parts:
  if any(not num(v) or v<=0 for v in part['dimensions_m']) or part['resolution']<8 or any(not num(v) or not 0<=v<=1 for v in part['material']['rgba']+[part['material']['metallic'],part['material']['roughness'],part['tip_ratio']]):errs.append('invalid primitive/material')
  rx,ry,rz=[math.radians(v) for v in part['rotation_deg']];zvalues=[]
  for sx in [-1,1]:
   for sy in [-1,1]:
    for sz in [-1,1]:
     x,y,z=[v*d/2 for v,d in zip([sx,sy,sz],part['dimensions_m'])];y,z=math.cos(rx)*y-math.sin(rx)*z,math.sin(rx)*y+math.cos(rx)*z;x,z=math.cos(ry)*x+math.sin(ry)*z,-math.sin(ry)*x+math.cos(ry)*z;zvalues.append(z+part['position_m'][2])
  if min(zvalues)<-.001 or max(zvalues)>.101:errs.append({'error':'appearance exceeds official height (rotated conservative box)','id':part['id'],'zmin':min(zvalues),'zmax':max(zvalues)})
 targets={'body':(255,216,77),'beak':(242,121,42)}
 targets.update({f'chest.{i}':(255,241,168) for i in range(1,5)})
 for part in parts:
  feature=part['feature'];target=targets.get(feature)
  if feature.startswith(('leg.','foot.','toe.')):target=(242,121,42)
  if target and any(abs(v-c/255)>1e-7 for v,c in zip(part['material']['rgba'][:3],target)):errs.append('source color mismatch '+feature)
 results['appearance']={'passed':not errs,'errors':errs,'part_count':len(parts),'no_generated_value_changed':True,'visual_approved':False}
 if not errs:guardar(E/'evidencias/bird_apariencia_canonica.json',recipe)
guardar(E/'evidencias/validacion_semantica.json',results);print(json.dumps({k:{a:b for a,b in v.items() if a in ['passed','error_count','part_count','bone_count','emitter_count','errors']} for k,v in results.items()},ensure_ascii=False))
