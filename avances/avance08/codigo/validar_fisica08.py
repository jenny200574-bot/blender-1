import math
BOUNDS={'bone_length_error_m':(1e-7,.001),'root_speed_max_m_s':(.01,10),'root_accel_max_m_s2':(.1,100),'penetration_tolerance_m':(1e-6,.01)}
FIXED={'com_accel_max_m_s2':20,'joint_speed_max_deg_s':600,'slip_max_m_per_frame':.05}
def validar(proposal,known_meshes,character_meshes,empty_roots):
 e=[];p=proposal['physics'];a=proposal['avian']
 for k,(lo,hi) in BOUNDS.items():
  v=p.get(k)
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:e.append('OUT_OF_SANITY_BOUND:'+k)
 for k,v in FIXED.items():
  if p.get(k)!=v:e.append('FIXED_RULE_CHANGED:'+k)
 if p.get('reject_surface_intersections') is not True:e.append('SURFACE_INTERSECTION_REJECTION_DISABLED')
 cs=p.get('colliders',[]);cset=set(cs)
 if not cs or len(cs)!=len(cset):e.append('COLLIDER_EMPTY_OR_DUPLICATE')
 for x in cs:
  if x not in known_meshes or x in empty_roots or x.startswith(('marca_','flecha_','rej_')):e.append('NOT_ACTUAL_PHYSICAL_MESH:'+x)
 if 'piso' not in cset or not any(x.startswith('muro_') for x in cs):e.append('NO_FLOOR_OR_WALLS')
 for who,parts in character_meshes.items():
  primary=[x['id'] for x in parts if x.get('role') in ['body','body_cover','head','face']]
  if not any(x in cset for x in primary):e.append('CHARACTER_COLLISION_OMITTED:'+who)
 for pair in p.get('allowed_collision_pairs',[]):
  if len(pair)!=2 or pair[0]==pair[1] or any(x not in cset for x in pair):e.append('INVALID_ALLOWED_PAIR:'+str(pair))
 margin=a.get('balance_margin_m')
 if not isinstance(margin,(int,float)) or not math.isfinite(margin) or not 0<=margin<=.01:e.append('AVIAN_MARGIN_ABSURD')
 offset=a['shoulder_offset_m'];poly=a['support_polygon_offsets_m']
 if len(offset)!=3 or any(not math.isfinite(v) for v in offset) or any(abs(v)>.04 for v in offset):e.append('ANCHOR_OUTSIDE_SHOULDER_ENVELOPE')
 if len(poly)<4 or any(len(x)!=3 or any(not math.isfinite(v) or abs(v)>.04 for v in x) for x in poly):e.append('SUPPORT_POLYGON_ABSURD')
 elif any(abs(x[2]-offset[2])>p['penetration_tolerance_m'] for x in poly):e.append('FLOATING_BIRD_FOOT_SUPPORT_GAP')
 if a['attachment']['target_point']!='ch-eco-eff3.hombro_L_aviar':e.append('WRONG_SHOULDER')
 if [(x['t0'],x['t1']) for x in a['support_intervals']]!=[(0,18),(18,30),(30,33),(33,44),(44,46),(46,55)]:e.append('INCOMPLETE_SOURCE_SUPPORT_INTERVALS')
 if any(x.get('mode')!='supported' for x in a['support_intervals']):e.append('UNSOURCED_BIRD_FLIGHT')
 return e
