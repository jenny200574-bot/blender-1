"""ADN OBJ→buscador real→mismo contrato de geometría/puntos/bisagras."""
import copy
from seguridad import leer,ruta,error,numero,sha
from buscador_formas import buscar

def compilar(d,root,catalog,policy,runtime=None):
 if 'props' in d and not any(p.get('dna_ref') for p in d['props']):return {'state':'EXPLICIT','count':len(d['props'])},[]
 refs=[p['id'] for p in d.get('props',[]) if p.get('dna_ref')] if 'props' in d else d.get('requirements',{}).get('object_refs',[]);path=d.get('adn_entities_source','adn_entidades.json');asset=next((a for a in d.get('assets',[]) if a['path']==path),None);records=leer(ruta(root,path)) if asset and ruta(root,path).is_file() and sha(ruta(root,path))==asset['sha256'] else {'records':[]};props=copy.deepcopy([p for p in d.get('props',[]) if not p.get('dna_ref')]);errors=[];receipts=[]
 for ident in refs:
  found=[r for r in records.get('records',[]) if r.get('type')=='OBJECT' and (r.get('id')==ident or ident in r.get('exact_aliases',[]))]
  gaze=any(a.get('mirada_id')==ident or a.get('mirada')==ident for a in d.get('actions',[]));physical=any(a.get('objeto')==ident for a in d.get('actions',[]));binding=d.get('bindings',{}).get(ident,{})
  if gaze and not physical and not found:
   if binding.get('reference_kind')=='POINT' and isinstance(binding.get('position_m'),list) and len(binding['position_m'])==3:
    props.append({'id':binding['scene_object_id'],'position_m':binding['position_m'],'geometry':[],'points':[],'reference_kind':'POINT','source':binding.get('source')});receipts.append({'object':ident,'state':'SPATIAL_TARGET','source':binding.get('source'),'not_a_visible_prop':True});continue
   errors.append(error('bindings/'+ident+'/reference_kind','4a2/manifiesto espacial','Referencia sólo usada para mirar: falta declarar POINT u OBJECT. No pedir ADN de un lugar ni ocultar un mueble como si fuera un punto. Posición/bbox ya disponibles.','REFERENCIA_ESPACIAL_DATOS',causa='tipo_referencia:'+ident));continue
  field='props/'+ident
  if len(found)!=1:errors.append(error(field+'/dna_ref','ADN OBJ/SELLO + 4a2','Falta asociación exacta y única entre objeto espacial y ficha ADN; no aproximar nombres','OBJETO_ADN_DATOS',causa='objeto:'+ident));continue
  rec=found[0];data=rec['source_data'];metrics=data.get('medidas_cm',{});dims=data.get('dimensions_m')
  if dims is None and all(k in metrics for k in ['ancho_cm','fondo_cm','alto_cm']):dims=[metrics[k]/100 for k in ['ancho_cm','fondo_cm','alto_cm']]
  if not isinstance(dims,list) or len(dims)!=3 or any(not numero(x) or x<=0 for x in dims):errors.append(error(field+'/dimensions_m','ADN OBJ/SELLO','Faltan medidas reales del objeto','OBJETO_ADN_DATOS',causa='objeto:'+ident));continue
  geometry=data.get('construction_3d') or {};query=copy.deepcopy(data.get('shape_query') or {});query.update(id=ident,dimensions_m=dims,source=rec.get('source'),producer='ADN OBJ/SELLO + 4a2',text=data.get('frase_sello',data.get('text','')))
  if geometry.get('parts'):query['parts']=geometry['parts']
  result=buscar(query,catalog,policy,runtime=runtime);receipts.append(result)
  if result['state']!='FOUND':errors.append(error(field+'/recipe','ADN OBJ/SELLO + catálogo de formas','Escalera agotada sin receta compatible ni despiece medido. ADN/medidas/referencia están conservados; faltan receta/despiece/puntos de la forma descrita. Proveedor Argon por defecto activo, sin gasto real en programación.','OBJETO_ADN_DATOS',causa='objeto:'+ident,source_record=rec['id'],search_receipt=result));continue
  bind=d.get('bindings',{}).get(ident);placement=geometry.get('placement') or bind
  material=geometry.get('material') or data.get('material')
  if not placement or not material:errors.append(error(field+'/placement_material','ADN OBJ/SELLO + 4a2','Falta transformación/material inequívoco por dato; no usar color de bbox','OBJETO_ADN_DATOS',causa='objeto:'+ident));continue
  rotation=placement.get('rotation_deg')
  if rotation is None:errors.append(error(field+'/rotation_deg','4a2/manifiesto espacial','Falta rotación del objeto; posición/bbox no determinan su orientación','OBJETO_ADN_DATOS',causa='objeto:'+ident));continue
  recipe=result['recipe'];parts=copy.deepcopy(recipe.get('parts'))
  if parts is None:
   required=['ancla_z','materials_catalog']
   if any(k not in geometry for k in required):errors.append(error(field+'/recipe_parameters','ADN OBJ/SELLO + catálogo de materiales','Receta encontrada; faltan ancla/materiales explícitos para ejecutarla','OBJETO_ADN_DATOS',causa='objeto:'+ident));continue
   parts=[dict(id=ident+'.formula',shape='STAR_FORMULA',formula=recipe['formula'],dimensions_m=dims,position_m=[0,0,0],rotation_deg=[0,0,0],ancla_z=geometry['ancla_z'],material=material,materials_catalog=geometry['materials_catalog'],source=rec.get('source'))]
  props.append({'id':placement.get('scene_object_id',ident),'position_m':placement['position_m'],'rotation_deg':rotation,'geometry':parts,'points':copy.deepcopy(geometry.get('points',[])),'hinges':copy.deepcopy(geometry.get('hinges',[])),'source':rec.get('source'),'shape_provenance':result['provenance']})
 d['props']=props
 from eje_objetos import enlazar
 cam=d.get('camera') or {};refs=cam.get('resolver_inputs') or {};sb_path=refs.get('sb_scene')
 if sb_path:
  asset=next((a for a in d.get('assets',[]) if a.get('path')==sb_path),None)
  try:
   p=ruta(root,sb_path)
   if not asset or not p.is_file() or sha(p)!=asset.get('sha256'):raise ValueError('hash')
   sb=leer(p)
  except (ValueError,OSError,KeyError,TypeError):
   errors.append(error('camera/sb_scene','SB + constructor','El storyboard del eje no es legible o no coincide con su hash; no se inventa el objeto del eje','EJE_SIN_OBJETO'))
  else:
   personajes=[e['id'] for e in d.get('entities',[]) if e.get('type')=='CHARACTER']
   aliases,eje_err=enlazar(sb.get('vinetas') or [],[x['id'] for x in props],personajes);errors+=eje_err
   by_id={x['id']:x for x in props}
   for eje,prop_id in aliases.items():
    prop=by_id.get(prop_id)
    if prop is None:continue
    prop.setdefault('axis_ids',[])
    if eje not in prop['axis_ids']:prop['axis_ids'].append(eje)
 d['_props_bridge']={'state':'WAITING_DATA' if errors else 'READY','objects':receipts};return d['_props_bridge'],errors
