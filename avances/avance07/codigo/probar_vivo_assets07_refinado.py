import json,sys,math
from pathlib import Path
import bpy,bmesh
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';sys.path.insert(0,str(B/'MOTOR_UNICO_20261107/motor'))
from apariencia_3d import construir_parte
from seguridad import guardar
from eventos import aplicar,verificar_estados
read=lambda p:json.loads(p.read_text());live=read(E/'evidencias/live_canonico07_integrado.json');canon=read(E/'evidencias/adn_canonico_refinado07.json');cofre=read(E/'evidencias/cofre_con_candados07.json');fx=read(E/'evidencias/live_fx_canonico07.json')['props'];d=read(B/'esc1_candidata/entrada_escena.json');fps=d['clock']['fps'];dur=d['clock']['duration_s'];sc=bpy.context.scene
for ob in sc.objects:ob.hide_render=True
objects={};specs=[]
for r in canon['records']+[cofre]:
 g=r['source_data']['construction_3d'];specs.append({'id':r['id'] if r['id']!='gdc-cofre-abecedario' else 'obj-cofre-dorado','position_m':g['placement']['position_m'],'rotation_deg':g['placement']['rotation_deg'],'geometry':g['parts']})
specs+=fx
for spec in specs:
 root=bpy.data.objects.new(spec['id'],None);sc.collection.objects.link(root);root.location=spec['position_m'];root.rotation_euler=[math.radians(x) for x in spec['rotation_deg']];objects[root.name]=root
 for part in spec['geometry']:construir_parte(part,root,objects)
sc.render.fps=fps;sc.frame_start=1;sc.frame_end=round(fps*dur)
actors=[e['id'] for e in d['entities']];skip_events=[e for e in live['changes'] if e['object'] in actors];events=[e for e in live['changes'] if e['object'] not in actors];skip_states=[s for s in live['expected_states'] if s['object'] in actors];states=[s for s in live['expected_states'] if s['object'] not in actors]
assert len(skip_events)==len(skip_states)==5,'Actor assertions must never be faked by EMPTY substitutes'
nonmanifold=[]
for ob in objects.values():
 if ob.type!='MESH':continue
 bm=bmesh.new();bm.from_mesh(ob.data)
 if any(not edge.is_manifold for edge in bm.edges):nonmanifold.append(ob.name)
 bm.free()
assert not nonmanifold,str(nonmanifold)
receipts=aplicar(sc,events,fps,dur);checks=verificar_estados(sc,states,fps);result={'passed':checks['all_passed'],'checks':checks,'mesh_count':sum(o.type=='MESH' for o in objects.values()),'nonmanifold':nonmanifold,'data_tracks_verified':len(events),'assertions_verified':len(states),'not_built_actors':actors,'skipped_actor_assertions':skip_states,'full_esc1_preview_passed':False,'physics_or_2B_approved':False,'production_approved':False,'gpu_used':False,'scope':'REAL CPU Blender mesh/material/animation assertions for assets only; no fake actor placeholders; full scene remains gated'};guardar(E/'evidencias/vivo_assets_cpu_refinado07.json',result)
if not checks['all_passed']:raise ValueError(str(checks['errors']))
p=E/'modelos_refinados/assets_vivo07_refinado.blend';assert not p.exists();bpy.ops.wm.save_as_mainfile(filepath=str(p));print(json.dumps({k:v for k,v in result.items() if k not in ['checks','skipped_actor_assertions']}))
