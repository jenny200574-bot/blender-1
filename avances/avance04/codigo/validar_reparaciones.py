import sys,json
from pathlib import Path
B=Path(__file__).resolve().parents[1];R=Path(sys.argv[1]);sys.path.insert(0,str(R/'motor'))
from recetas_proveedor import validar
from geometria import validar_rig
from eventos import PROPIEDADES
raw=json.loads((B/'evidencias/respuesta_esc1_raw.json').read_text());d=raw[0] if isinstance(raw,list) and len(raw)==1 else raw
errors=[];missing=json.loads((B/'config/faltantes_antes.json').read_text());expected={x['campo'] for x in missing};actual={x.get('campo') for x in d.get('resolutions',[])}
for field in sorted(expected-actual):errors.append({'field':field,'reason':'No exact resolution supplied'})
for recipe in d.get('object_recipes',[]):
 try:validar(recipe['recipe'],recipe['query'])
 except (ValueError,KeyError,TypeError) as e:errors.append({'field':'object_recipes/'+recipe.get('id',''),'reason':str(e)})
for row in d.get('resolutions',[]):
 value=row.get('value') or {}
 if value.get('rig'):
  errors.extend({'field':row['campo'],'reason':e['mensaje']} for e in validar_rig(value['rig']))
  roles={b.get('role') for b in value['rig']['bones']};required={'root','neck','head','beak','tail','wing.L','wing.R','leg.L','leg.R','foot.L','foot.R'}|{f'toe.{s}.{n}' for s in ['L','R'] for n in ['front1','front2','front3','back']}
  if not required<=roles:errors.append({'field':row['campo'],'reason':'Incomplete avian rig; missing '+','.join(sorted(required-roles))})
for state in d.get('live_scenery',{}).get('expected_states',[]):
 if state.get('property') not in PROPIEDADES:errors.append({'field':'live_scenery','reason':'Unsupported property '+str(state.get('property'))})
 if not {'tolerance','source','id','object','property','t','value'}<=set(state):errors.append({'field':'live_scenery','reason':'Expected-state contract incomplete'})
source=json.loads((R/'paquetes/guardianes_t316/entrada_escena.json').read_text());expected_shots={s['id'] for s in source['camera']['shots']};received={s.get('id') for s in d.get('camera_numeric',{}).get('shots',[])}
if received!=expected_shots:errors.append({'field':'camera_numeric','reason':'Missing shots '+','.join(sorted(expected_shots-received))})
for row in d.get('equivalences',[]):
 if not {'source','spatial_pointer','dna_pointer'}<=set(row):errors.append({'field':'equivalences','reason':'No verifiable JSON-pointer evidence; fuzzy normalization is not identity proof'})
result={'api_generation_succeeded':True,'root_normalized_from_single_list':isinstance(raw,list),'ready_to_apply':not errors,'expected_missing_fields':len(expected),'exact_fields_addressed':len(expected&actual),'error_count':len(errors),'errors':errors,'applied_fields':0,'production_approved':False,'model_used':'gemini-3-flash-preview','not_gemini_4_argon':True}
(B/'evidencias/validacion_respuesta.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(B/'evidencias/respuesta_normalizada.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='errors'}))
