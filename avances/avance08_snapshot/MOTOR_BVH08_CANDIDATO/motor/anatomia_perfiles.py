"""ADN/perfil estructural→esqueleto/masa relativa/apoyos/ancla. Sin cotas ni hombro inventados."""
import copy,math
from seguridad import error,numero
from geometria import validar_rig

def compilar(d):
 receipts=[];errors=[];status=d.setdefault('_anatomy_bridge',{})
 for e in d.get('entities',[]):
  if e.get('type')!='CHARACTER' or e.get('legacy'):continue
  if e.get('rig') and e.get('physics') and not e.get('attachment'):status[e['id']]='READY';continue
  base='entities/'+e['id'];data=(e.get('dna_record') or {}).get('source_data') or {};p=e.get('anatomy_profile') or data.get('anatomy_profile');source=(e.get('dna_record') or {}).get('source',e.get('source'))
  if not p and e.get('rig') and e.get('physics'):p={'units':'m','rig':e['rig'],'physics':e['physics'],'attachment':e.get('attachment'),'source':'entrada_escena.json: contrato métrico canónico'}
  if e.get('anatomy') not in ['avian','declarative']:
   errors.append(error(base+'/anatomy','motor/ADN→esqueleto','Perfil anatómico sin constructor','ANATOMIA_NO_SOPORTADA',tipo='crear capacidad'));status[e['id']]='UNSUPPORTED';continue
  if not isinstance(p,dict):
   errors.append(error(base+'/anatomy_profile','ADN Maestro 03/04 + 01/Star puntos','Faltan landmarks/proporciones estructurales y límites articulares certificados; altura y cabezas no determinan longitudes de alas/patas. Faltan también apoyos/ancla explícitos cuando va acoplado. No se escala un rig de otra identidad.','PERFIL_ANATOMICO_DATOS',fuente=source,causa='perfil_anatomico:'+e['id']));status[e['id']]='WAITING_DATA';continue
  try:
   rig=copy.deepcopy(e.get('rig') or p['rig']);unit=p['units']
   if unit=='height_fraction':
    height=data.get('height_m')
    if not numero(height) or height<=0:raise ValueError('Falta altura ADN para landmark normalizado')
    for b in rig['bones']:
     for k in ['head','tail']:b[k]=[v*height for v in b[k]]
   elif unit!='m':raise ValueError('Unidades del perfil no admitidas: deben declararse m o height_fraction')
   if not isinstance(rig,dict) or not isinstance(rig.get('bones'),list) or any(not isinstance(b,dict) or any(not isinstance(b.get(k),list) or len(b[k])!=3 or any(not numero(v) for v in b[k]) for k in ['head','tail']) for b in rig['bones']):raise ValueError('Landmarks óseos deben ser vectores métricos numéricos')
   if any(not isinstance(b.get('id'),str) or not b['id'] or not isinstance(b.get('role'),str) or not isinstance(b.get('limits_deg'),list) or len(b['limits_deg'])!=3 or any(not isinstance(v,list) or len(v)!=2 or any(not numero(x) for x in v) or v[0]>v[1] for v in b['limits_deg']) for b in rig['bones']):raise ValueError('IDs, roles y límites óseos explícitos no válidos')
   missing=validar_rig(rig)
   if missing:raise ValueError('Rig incompleto: '+str(missing))
   if e['anatomy']=='avian':
    required={'root','neck','head','beak','tail','wing.L','wing.R','leg.L','leg.R','foot.L','foot.R'}|{f'toe.{s}.{n}' for s in ['L','R'] for n in ['front1','front2','front3','back']}
    if not required<={b['role'] for b in rig['bones']}:raise ValueError('Faltan roles aviares completos, incluidos dedos')
   physics=copy.deepcopy(e.get('physics') or p.get('physics') or {})
   if not (physics.get('bone_mass_kg') or physics.get('bone_mass_weights')):
    weights={}
    for b in rig['bones']:
     radius=p['bone_radii_m'][b['id']]
     if not numero(radius) or radius<=0:raise ValueError('Radio estructural debe ser positivo')
     weights[b['id']]=math.pi*radius**2*math.dist(b['head'],b['tail'])
    physics.update(bone_mass_weights=weights,mass_model='volumen cilíndrico relativo de radios/longitudes fuente; NO kg medidos')
   mass=physics.get('bone_mass_kg',physics.get('bone_mass_weights'))
   if set(mass)!={b['id'] for b in rig['bones']} or any(not numero(v) or v<=0 for v in mass.values()):raise ValueError('Masas/pesos deben cubrir todos los huesos y ser positivos')
   if not numero(physics.get('balance_margin_m')) or physics['balance_margin_m']<0:raise ValueError('Falta margen físico vigente')
   intervals=physics['support_intervals'];end=0
   for x in intervals:
    if not numero(x.get('t0')) or not numero(x.get('t1')) or x['t0']!=end or x['t1']<=end:raise ValueError('Cobertura temporal de apoyos incompleta')
    if x['mode']=='supported' and not x.get('support_points'):raise ValueError('Faltan puntos de apoyo')
    if x['mode'] not in ['supported','airborne','flight','suspended']:raise ValueError('Modo anatómico de apoyo desconocido')
    if x['mode']!='supported' and not any(a['id']==x.get('action_ref') for a in d.get('actions',[])):raise ValueError('Vuelo/suspensión sin acción fuente')
    end=x['t1']
   if end!=d['clock']['duration_s']:raise ValueError('Apoyos no cubren toda la escena')
   attachment=copy.deepcopy(p.get('attachment',e.get('attachment')))
   coupled=any(s.get('tipo')=='acoplarse' for s in e.get('source_data',{}).get('segmentos',[]))
   if coupled and not attachment:raise ValueError('Acoplamiento sin target_point/marco/offset y autoridad del hombro')
   if attachment:
    if not all(k in attachment for k in ['target_point','offset_m','rotation_deg','source']) or len(attachment['offset_m'])!=3 or len(attachment['rotation_deg'])!=3 or any(not numero(v) for v in attachment['offset_m']+attachment['rotation_deg']):raise ValueError('Ancla sin ID/offset/rotación/procedencia medidos')
   e['rig']=rig;e['physics']=physics
   if attachment:e['attachment']=attachment
   status[e['id']]='READY';receipts.append({'entity':e['id'],'bones':len(rig['bones']),'anatomy':e['anatomy'],'attachment':attachment,'source':p.get('source',source)})
  except (KeyError,TypeError,ValueError) as exc:
   status[e['id']]='WAITING_DATA';errors.append(error(base+'/anatomy_profile','ADN Maestro 03/04 + 01/Star puntos',str(exc),'PERFIL_ANATOMICO_DATOS',fuente=source,causa='perfil_anatomico:'+e['id']))
 return receipts,errors

def aplicar_anclas(entities,rigs,objects):
 from mathutils import Vector,Euler
 result=[]
 for e in entities:
  a=e.get('attachment')
  if not a:continue
  target=objects.get(a['target_point'])
  if target is None:raise ValueError('Punto de ancla no construido: '+a['target_point'])
  rig=rigs[e['id']];rig.parent=target;rig.location=a['offset_m'];rig.rotation_euler=[math.radians(v) for v in a['rotation_deg']];result.append({'entity':e['id'],'target_point':a['target_point'],'source':a['source']})
 return result
