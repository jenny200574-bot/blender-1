"""Typed Argon design -> deterministic closed geometry; no artistic numbers invented here."""
import json,math,sys,copy
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';R=B/'MOTOR_UNICO_20261107';sys.path.insert(0,str(R/'motor'))
from seguridad import guardar
from recetas_proveedor import validar
read=lambda p:json.loads(p.read_text())
IDS={'obj-libro-cuentos__e1-8':[.4,.26,.04],'obj-visor-spark':[.16,.12,.06],'Ventana con vista al arcoíris':[1.6,.15,1.3],'Centro de la habitación':[2.2,2.2,.02]}
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):
 d=math.sqrt(dot(a,a))
 if d<1e-12:raise ValueError('Zero tube tangent/normal')
 return [x/d for x in a]
def tube(p):
 pts=[[q[k] for k in ['x','y','z']] for q in p['points']];rad=p['radius_m'];n=p['resolution'];normal=norm(p['plane_normal'])
 if len(pts)<2 or not 8<=n<=64 or rad<=0:raise ValueError('Invalid closed tube')
 if any(math.dist(a,b)<1e-10 for a,b in zip(pts,pts[1:])):raise ValueError('Repeated consecutive tube point')
 vs=[]
 for i,q in enumerate(pts):
  t=norm([b-a for a,b in zip(pts[max(0,i-1)],pts[min(len(pts)-1,i+1)])])
  if abs(dot(t,normal))>1e-5:raise ValueError('Plane normal not perpendicular to tube')
  v=cross(t,normal)
  for j in range(n):vs.append([q[k]+rad*(math.cos(2*math.pi*j/n)*normal[k]+math.sin(2*math.pi*j/n)*v[k]) for k in range(3)])
 faces=[list(reversed(range(n)))]+[[i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j] for i in range(len(pts)-1) for j in range(n)]+[list(range((len(pts)-1)*n,len(pts)*n))]
 return vs,faces

def canon_part(p,source):
 part=dict(id=p['id'],role=p['role'],shape=p['shape'],position_m=[p[k] for k in ['px','py','pz']],rotation_deg=[p[k] for k in ['rx','ry','rz']],dimensions_m=[p[k] for k in ['dx','dy','dz']],resolution=p['resolution'],material=dict(rgba=[p[k] for k in ['r','g','b','a']],metallic=p['metallic'],roughness=p['roughness'],transmission=p['transmission'],source=source),source=source,normals='SMOOTH')
 if p['emission']>0:part['material'].update(emission_rgba=part['material']['rgba'],emission_strength=p['emission'])
 if p['shape']=='CONE':part['tip_ratio']=p['tip_ratio']
 if p['shape']=='POINT_TUBE':
  vs,fs=tube(p);part.update(shape='MESH',vertices_m=vs,faces=fs,dimensions_m=[max(v[k] for v in vs)-min(v[k] for v in vs) for k in range(3)],generated_from_points=True)
 return part

def main():
 name=sys.argv[1];src=read(E/'evidencias'/name/'respuesta.json');assert read(E/'evidencias'/name/'schema_validacion.json')['passed']
 assert len(src['objects'])==4 and {x['id'] for x in src['objects']}==set(IDS)
 measured=read(B/'esc1_candidata/inventario_set_medido.json');sources=read(E/'config/adn_sources.json');assert measured['scale_length']==1
 canonical=[];errors=[];metrics=[];used=set()
 for i,x in enumerate(src['objects']):
  try:
   assert x['dimensions_m']==IDS[x['id']], 'Source dimensions changed'
   source='argon07_adn_respuesta.json#/objects/'+str(i)+'; generated design from exact current inventory IDs, NOT equivalence to legacy gdc seals'
   parts=[canon_part(p,source) for p in x['parts']]
   assert all(p['id'].startswith('av07.') and p['id'] not in used for p in parts), 'Reused or unnamespaced ID'
   assert len({p['id'] for p in parts})==len(parts),'Duplicate parts'
   recipe={'source':source,'parts':parts};v=validar(recipe,{'dimensions_m':IDS[x['id']]},tolerance=.001)
   m=next(o for o in measured['objects'] if o['id']==x['id']);assert all(abs(a-b)<.001 for a,b in zip(m['dimensions_m'],x['dimensions_m']))
   placement={'scene_object_id':x['id'],'position_m':m['position_m'],'rotation_deg':[math.degrees(t) for t in m['rotation_euler_rad']],'source':'inventario_set_medido.json: exact matching id, measured transform preserved'}
   c={'id':x['id'],'type':'OBJECT','exact_aliases':[],'source':source,'association':'NEW LOCAL spatial-source-specific design, NOT rename/alias or overwrite of existing sealed gdc records','source_data':{'id':x['id'],'dimensions_m':x['dimensions_m'],'frase_sello':x['frase_sello'],'source_inventory_origin':'deducido in source 4b1/4a2, not measured ADN approval','construction_3d':{'parts':parts,'placement':placement,'material':parts[0]['material']},'generated_scope':'Parametric design only; NOT global seal, visual approval or physics certification'}}
   used.update(p['id'] for p in parts)
   canonical.append(c);metrics.append({'id':x['id'],'passed':True,'metrics':v,'parts':len(parts),'role_ids':{p['id']:p['role'] for p in parts}})
  except Exception as ex:errors.append({'object':x['id'],'error':str(ex)})
 axes=src['axes'];axis_ok=axes['status']=='SOURCE' and axes['unit']=='m' and axes['up'] in ['Z','+Z'] and axes['forward'] in ['Y','+Y']
 out={'passed':not errors,'objects_validated':len(canonical),'errors':errors,'metrics':metrics,'axes_validated':axis_ok,'production_approved':False,'global_seals_modified':False}
 guardar(E/'evidencias'/('validacion_'+name+'.json'),out)
 guardar(E/'evidencias'/('adn_canonico_'+name+'.json'),{'records':canonical,'axes':axes,'axes_validated':axis_ok})
 print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
