import sys,json,math,copy
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';sys.path.insert(0,str(B/'MOTOR_UNICO_20261107/motor'));sys.path.insert(0,str(E/'codigo'))
from canonizar07 import canon_part
from recetas_proveedor import validar
from seguridad import guardar
from eventos import validar_eventos,valor
from vivo_binding import compilar
read=lambda p:json.loads(p.read_text())

def main():
 templates=read(E/'evidencias/av07_live02/respuesta.json');features=read(E/'evidencias/av07_liveparts02/respuesta.json');patch=read(E/'evidencias/av07_liveparts03/respuesta.json');features['fx_dimensions_m']=patch['fx_dimensions_m'];assert len(features['fx_dimensions_m'])==3;
 for part in features['cofre_additional_parts']:
  if part['id'] in ['av07.lock.number.glyph','av07.lock.letter.glyph']:part['py']=patch['glyph_py']
 landing=read(E/'evidencias/av07_fxland01/respuesta.json')['keys'];assert len(landing)==2 and [k['t'] for k in landing]==[18,21] and all(k['dx']==k['dy']==0 for k in landing);assert landing[0]['dz']>landing[1]['dz'] and abs(landing[1]['dz']-(-.45))<1e-7
 old=read(E/'evidencias/av07_live01/respuesta.json');source='argon07_vivo_plantillas.json + argon07_vivo_geometria.json; GENERATED design; action intervals source01 exact; not visual/physics certification'
 records=read(E/'evidencias/adn_canonico_final.json')['records'];book=next(r for r in records if r['id']=='obj-libro-cuentos__e1-8')['source_data']['construction_3d']['parts'];window=next(r for r in records if r['id']=='Ventana con vista al arcoíris')['source_data']['construction_3d']['parts'];p0=read(B/'esc1_candidata/entrada_escena.json');dna=read(B/'esc1_candidata/adn_entidades.json');cofre=copy.deepcopy(next(r for r in dna['records'] if r['id']=='gdc-cofre-abecedario'));g=cofre['source_data']['construction_3d'];newparts=[canon_part(p,source) for p in features['cofre_additional_parts']]
 ids={'av07.lock.'+a+'.'+b for a,b in [('color','shackle'),('number','shackle'),('letter','shackle'),('number','glyph'),('letter','glyph')]};assert {p['id'] for p in newparts}==ids and len(newparts)==5,'Require3U+number+letter, no duplicated bodies'
 assert all(p['shape']=='MESH' for p in newparts)
 metrics=validar({'source':source,'parts':g['parts']+newparts},{'dimensions_m':[cofre['source_data']['medidas_cm'][k]/100 for k in ['ancho_cm','fondo_cm','alto_cm']]},tolerance=.001);g['parts']+=newparts
 for p in newparts:assert all(v>=0 for v in p['material']['rgba'])
 # Four FX retain literal original model materials/positions; only dimensions corrected by next model output.
 fx=[];fx_raw=[o for o in old['new_objects'] if o['id'].startswith('av07.fx.')];assert len(fx_raw)==4
 points=read(B/'esc1_candidata/source_01.json')['puntos'];pointkeys=dict(blue='spark_aterrizaje',magenta='valentina_aterrizaje',green='eco_aterrizaje',yellow='pintor_aterrizaje')
 for o in fx_raw:
  assert len(o['parts'])==1;raw=copy.deepcopy(o['parts'][0]);raw.update(dict(zip(['dx','dy','dz'],features['fx_dimensions_m'])));part=canon_part(raw,source);assert part['material']['emission_strength']>0
  c=o['id'].split('.')[-1];assert o['position_m'][:2]==points[pointkeys[c]][:2]
  v=validar({'source':source,'parts':[part]},{'dimensions_m':features['fx_dimensions_m']},tolerance=.001)
  fx.append(dict(id=o['id'],position_m=o['position_m'],rotation_deg=o['rotation_deg'],geometry=[part],source=source,scope='New visual FX design, color-to-hero assignment is design not a literal source assertion'))
 assert templates['letter_selector']=='all_book_parts_role_letter' and templates['rainbow_selector']=='all_seven_window_parts_role_rainbow';assert templates['hero_selector']=='all_source01_aparecer_actors_a6_to_a10' and templates['fx_selector']=='all_four_new_fx'
 letters=[p for p in book if p['role']=='letter'];bands=[p for p in window if p['role']=='rainbow'];actors=[a['actor'] for a in p0['actions'] if a['id'] in ['a6','a7','a8','a9','a10']];assert len(letters)==3 and len(bands)==7 and len(set(actors))==5
 offsets=templates['letter_offsets'];assert offsets[0]['t']==0 and offsets[-1]['t']==3 and offsets[0]['offset_m']==[0,0,0]
 jitter=[k for k in offsets if 0<k['t']<2];assert len(jitter)>=2 and math.dist(jitter[0]['offset_m'],jitter[1]['offset_m'])>1e-5
 assert len(offsets[-1]['offset_m'])==3 and math.dist(offsets[-1]['offset_m'],[0,0,0])>.1
 assert templates['rainbow_t0']==9 and templates['rainbow_t1']==11;gray=templates['rainbow_gray_rgba'];assert len(gray)==4 and gray[0]==gray[1]==gray[2] and gray[3]==1
 events=[];states=[];bind={t:[] for t in p0['environment']['live_data']['state_for_scene']['inicio']+p0['environment']['live_data']['state_for_scene']['fin']};texts=list(bind)
 def track(ident,prop,keys,material=None,recursive=False,action=None):
  q={'object':ident,'property':prop,'keys':copy.deepcopy(keys),'source':source}
  if material:q['material']=material
  if recursive:q['recursive']=True
  if action:q['action_id']=action
  events.append(q);return q
 def assertion(claim,ident,prop,t,value,material=None):
  item={'id':'av07.state.'+str(len(states)),'object':ident,'property':prop,'t':t,'value':value,'tolerance':1e-5,'source':source}
  if material:item['material']=material
  states.append(item);bind[claim].append(item['id'])
 def isbool(keys,t,expected):assert isinstance(valor(keys,t),bool) and valor(keys,t)==expected
 for keys in [templates['letter_visibility'],templates['hero_visibility'],templates['fx_visibility'],templates['cofre_visibility']]:
  assert all(isinstance(k['value'],bool) and k['curve']=='CONSTANT' for k in keys)
 isbool(templates['letter_visibility'],0,False);isbool(templates['letter_visibility'],3,True);isbool(templates['letter_visibility'],55,True)
 for p in letters:
  keys=[dict(t=k['t'],value=[a+b for a,b in zip(p['position_m'],k['offset_m'])],curve=k['curve']) for k in offsets];track(p['id'],'location',keys,action='a1');track(p['id'],'hide_render',templates['letter_visibility'],action='a1')
  assertion(texts[0],p['id'],'hide_render',0,False)
  for k in jitter[:2]:assertion(texts[0],p['id'],'location',k['t'],valor(keys,k['t']))
  assertion(texts[2],p['id'],'hide_render',55,True)
 pages=[p for p in book if p['id'] in ['av07.book.page_left','av07.book.page_right']];assert len(pages)==2
 for p in pages:assertion(texts[2],p['id'],'hide_render',55,False)
 for p in bands:
  rgba=p['material']['rgba'];assert max(rgba[:3])-min(rgba[:3])>.1
  keys=[dict(t=templates['rainbow_t0'],value=rgba,curve=templates['rainbow_curve']),dict(t=templates['rainbow_t1'],value=gray,curve=templates['rainbow_curve'])];mat=p['id']+'_material';track(p['id'],'material.base_color',keys,material=mat,action='a3');assertion(texts[1],p['id'],'material.base_color',0,rgba,mat);assertion(texts[3],p['id'],'material.base_color',55,gray,mat)
 isbool(templates['hero_visibility'],0,True);isbool(templates['hero_visibility'],18,True);isbool(templates['hero_visibility'],21,False);isbool(templates['hero_visibility'],55,False)
 for ident in actors:track(ident,'hide_render',templates['hero_visibility'],recursive=True);assertion(texts[4],ident,'hide_render',55,False)
 probe=templates['fx_probe_t'];assert 18<probe<21;isbool(templates['fx_visibility'],0,True);isbool(templates['fx_visibility'],probe,False);isbool(templates['fx_visibility'],21,True)
 for p in fx:
  track(p['id'],'hide_render',templates['fx_visibility'],recursive=True);assertion(texts[4],p['id'],'hide_render',probe,False);assertion(texts[4],p['id'],'hide_render',55,True)
  keys=[dict(t=k['t'],value=[p['position_m'][i]+k[a] for i,a in enumerate(['dx','dy','dz'])],curve=k['curve']) for k in landing];assert .1<keys[0]['value'][2]<2.7 and abs(keys[1]['value'][2]-.05)<1e-7;track(p['id'],'location',keys)
  for k in keys:assertion(texts[4],p['id'],'location',k['t'],k['value'])
 isbool(templates['cofre_visibility'],0,True);isbool(templates['cofre_visibility'],30,True);isbool(templates['cofre_visibility'],33,False);isbool(templates['cofre_visibility'],55,False);track('obj-cofre-dorado','hide_render',templates['cofre_visibility'],recursive=True,action='a13');assertion(texts[5],'obj-cofre-dorado','hide_render',55,False)
 for ident in ['obj-cofre-dorado.candado_color','obj-cofre-dorado.candado_numero','obj-cofre-dorado.candado_letra']+sorted(ids):assertion(texts[5],ident,'hide_render',55,False)
 lid=next(p for p in g['parts'] if p['id']=='obj-cofre-dorado.tapa');assertion(texts[5],lid['id'],'rotation_euler',55,[math.radians(v) for v in lid['rotation_deg']])
 errors=validar_eventos(events,p0['clock']['duration_s']);assert not errors,str(errors)
 allowed={p['id'] for p in book+window+g['parts']}|{p['id'] for p in fx}|set(actors)|{'obj-cofre-dorado'}
 assert all(q['object'] in allowed for q in events+states)
 live={'status':'complete','source':source,'state_for_scene':p0['environment']['live_data']['state_for_scene'],'changes':events,'expected_states':states,'state_bindings':bind,'missing':[],'scope':'Complete parameterized data; full esc1 build/physics/visual validation NOT done, still gated by 2B/anatomy/rules'}
 test=copy.deepcopy(p0);test['environment']['events']=[];test['environment']['live_data']=live;receipt,errs=compilar(test);assert not errs,str(errs)
 out={'passed':True,'tracks':len(events),'assertions':len(states),'six_states_bound':len(bind),'three_letter_parts':len(letters),'seven_rainbow_bands':len(bands),'five_source_actors':len(actors),'four_real_fx':len(fx),'four_actual_landing_tracks':len(fx),'lock_additions':len(newparts),'cofre_geometry_validation':metrics,'live_bridge':receipt,'twoB_or_rules_approval':False,'full_scene_cpu_passed':False,'production_approved':False}
 guardar(E/'evidencias/live_canonico07.json',live);guardar(E/'evidencias/live_fx_canonico07.json',{'props':fx});guardar(E/'evidencias/cofre_con_candados07.json',cofre);guardar(E/'evidencias/validacion_live07.json',out);print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as ex:
  guardar(E/'evidencias/live_rechazo_compilacion07.json',{'passed':False,'error':str(ex),'applied':False});raise
