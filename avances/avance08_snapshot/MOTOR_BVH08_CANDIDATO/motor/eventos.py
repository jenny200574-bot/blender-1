"""Un reloj global, curvas explícitas, continuidad verificable en cortes."""
from seguridad import *
CURVAS={'LINEAR':lambda u:u,'CONSTANT':lambda u:0.0,'SMOOTH':lambda u:u*u*(3-2*u)}
MATERIALES={'material.base_color':'Base Color','material.metallic':'Metallic','material.roughness':'Roughness','material.emission_color':'Emission Color','material.emission_strength':'Emission Strength'}
PROPIEDADES=set(MATERIALES)|{'location','rotation_euler','scale','energy','color','hide_render','world.background_color','world.background_strength','scene.exposure','scene.gamma'}

def validar_eventos(events,duration):
 E=[];tracks={}
 for i,e in enumerate(events):
  field='events/'+str(i)
  if not isinstance(e,dict) or not all(k in e for k in ['object','property','keys','source']):E.append(error(field,'4a/4a4/01','Binding incompleto'));continue
  if e['property'] not in PROPIEDADES:E.append(error(field,'motor vivo','Propiedad no soportada','CAPACIDAD_PENDIENTE',tipo='crear capacidad'))
  if e['property'] in MATERIALES and not e.get('material'):E.append(error(field,'4a2/4a4','Evento de material necesita ID inequívoco de material'))
  if e['property']=='hide_render' and any(k.get('curve')!='CONSTANT' for k in e['keys']):E.append(error(field,'4a/01','Visibilidad booleana necesita curva CONSTANT'))
  last=-1
  for k in e['keys']:
   if not all(x in k for x in ['t','value','curve']) or not numero(k.get('t')) or not 0<=k['t']<=duration or k['t']<=last or k.get('curve') not in CURVAS:
    E.append(error(field,'4a/4a4/01','Tiempo/curva/valor de evento inválido'));continue
   last=k['t']
  key=('material',e.get('material'),e['property']) if e['property'] in MATERIALES else (e['object'],e['property'])
  if key in tracks:E.append(error(field,'motor temporal','Dos escritores para la misma propiedad','CONFLICTO',tipo='conflicto'))
  tracks[key]=e
 return E

def valor(keys,t):
 if t<=keys[0]['t']:return keys[0]['value']
 for a,b in zip(keys,keys[1:]):
  if t<=b['t']:
   if t==b['t']:return b['value']
   if isinstance(a['value'],bool):
    if a['curve']!='CONSTANT':raise ValueError('Booleano requiere CONSTANT')
    return a['value']
   u=CURVAS[a['curve']]((t-a['t'])/(b['t']-a['t']))
   if isinstance(a['value'],list):return [x+(y-x)*u for x,y in zip(a['value'],b['value'])]
   return a['value']+(b['value']-a['value'])*u
 return keys[-1]['value']

def aplicar(scene,events,fps,duration):
 exigir("eventos")
 import bpy
 # Expandir jerarquías reales sin resucitar cápsulas/moldes archivados.
 expanded=[];unique={}
 for event in events:
  original=bpy.data.objects.get(event['object']);members=[original] if original is not None else []
  if event.get('recursive'):
   if original is None:raise ValueError('Raíz de evento jerárquico ausente')
   members=[original]+list(original.children_recursive)
  if not members:members=[None]
  for member in members:
   if member is not None and member.get('motor_preserve_hidden'):continue
   e=dict(event,object=member.name if member is not None else event['object']);e.pop('recursive',None);key=(e['object'],e['property'],e.get('material'))
   if key in unique and unique[key]['keys']==e['keys']:continue
   unique[key]=e;expanded.append(e)
 E=validar_eventos(expanded,duration)
 if E:raise ValueError(str(E))
 events=expanded;receipts=[]
 for e in events:
  attr=e['property'];obj=None
  if attr.startswith('world.'):
   world=bpy.data.worlds.get(e['object'])
   if world is None or not world.use_nodes:raise ValueError('World explícito no existe o no usa nodos')
   nodes=[x for x in world.node_tree.nodes if x.type=='BACKGROUND']
   if len(nodes)!=1:raise ValueError('World requiere binding inequívoco de Background')
   target=nodes[0].inputs['Color' if attr=='world.background_color' else 'Strength'];keypath='default_value'
  elif attr.startswith('scene.'):
   if e['object']!=scene.name:raise ValueError('Estado de exposición apunta a otra escena')
   target=scene.view_settings;keypath=attr.split('.',1)[1]
  else:
   obj=bpy.data.objects.get(e['object'])
   if obj is None:raise ValueError('ID de objeto no encontrado: '+e['object'])
  if attr in MATERIALES:
   mat=next((m for m in obj.data.materials if m and m.name==e['material']),None) if obj.type=='MESH' else None
   if mat is None or not mat.use_nodes:raise ValueError('Binding de material no existe: '+str(e.get('material')))
   nodes=[n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
   if len(nodes)!=1:raise ValueError('Shader material ambiguo: necesita binding de nodo')
   target=nodes[0].inputs[MATERIALES[attr]];keypath='default_value'
  elif obj is not None:target=obj.data if attr in ['energy','color'] and obj.type=='LIGHT' else obj;keypath=attr
  if not hasattr(target,keypath):raise ValueError('Propiedad incompatible: '+attr)
  for k in e['keys']:
   setattr(target,keypath,k['value']);target.keyframe_insert(keypath,frame=1+cuadro(k['t'],fps))
  # Horneado por cuadro con nuestro reloj y curva: no defaults Bezier ni reinicio por toma.
  for f in range(cuadro(duration,fps)):
   setattr(target,keypath,valor(e['keys'],f/fps));target.keyframe_insert(keypath,frame=f+1)
  receipts.append({'object':e['object'],'property':attr,'frames':cuadro(duration,fps),'source':e['source']})
 return receipts


def verificar_estados(scene,states,fps):
 """Mide valores finales/iniciales exigidos por 4a4; no basta un recibo de keyframes."""
 import bpy
 errors=[];checks=[]
 for state in states:
  scene.frame_set(1+cuadro(state['t'],fps));bpy.context.view_layer.update();prop=state['property'];obj=bpy.data.objects.get(state['object'])
  if prop in MATERIALES:
   if obj is None or obj.type!='MESH':raise ValueError('Estado apunta a malla/material no construido')
   mats=[m for m in obj.data.materials if m and m.name==state.get('material')]
   if len(mats)!=1:raise ValueError('Estado material sin binding único')
   nodes=[n for n in mats[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED']
   if len(nodes)!=1:raise ValueError('Estado material sin shader único')
   value=nodes[0].inputs[MATERIALES[prop]].default_value
  elif prop.startswith('world.'):
   w=bpy.data.worlds.get(state['object']);nodes=[n for n in w.node_tree.nodes if n.type=='BACKGROUND'] if w and w.use_nodes else []
   if len(nodes)!=1:raise ValueError('Estado World sin Background único')
   value=nodes[0].inputs['Color' if prop=='world.background_color' else 'Strength'].default_value
  elif prop.startswith('scene.'):
   if state['object']!=scene.name:raise ValueError('Estado apunta a otra escena')
   value=getattr(scene.view_settings,prop.split('.',1)[1])
  else:
   if obj is None:raise ValueError('Objeto exigido por estado no construido')
   target=obj.data if obj.type=='LIGHT' and prop in ['energy','color'] else obj
   value=getattr(target,prop)
  expected=state['value'];actual=list(value) if isinstance(expected,list) else value
  if isinstance(expected,bool):passed=actual==expected
  elif isinstance(expected,list):passed=len(actual)==len(expected) and all(abs(x-y)<=state['tolerance'] for x,y in zip(actual,expected))
  else:passed=abs(actual-expected)<=state['tolerance']
  check={'id':state['id'],'frame':1+cuadro(state['t'],fps),'object':state['object'],'property':prop,'actual':actual,'expected':expected,'passed':passed};checks.append(check)
  if not passed:errors.append(dict(type='ESTADO_ENTORNO',**check))
 return {'all_passed':not errors,'checks':checks,'errors':errors}


def separar_por_dependencias(events,light_ids):
 """Entorno material/geométrico primero; emisores y World tras crearlos.
 La validación de escritores se hace sobre el conjunto, no por partición.
 """
 before=[];after=[];ids=set(light_ids)
 for event in events:
  attr=event['property']
  deferred=event['object'] in ids or attr in ['energy','color'] or attr.startswith(('world.','scene.'))
  (after if deferred else before).append(event)
 return before,after
