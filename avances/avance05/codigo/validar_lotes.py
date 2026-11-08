import json,sys,math
from pathlib import Path
B=Path(__file__).resolve().parents[1];ENGINE=B.parent/'MOTOR_UNICO_20261107';sys.path.insert(0,str(ENGINE/'motor'))
from recetas_proveedor import validar

def read(p):return json.loads(p.read_text())
def report(name):
 out=B/'evidencias'/name
 return read(out/'respuesta.json') if (out/'respuesta.json').exists() and read(out/'schema_validacion.json')['passed'] else None

def run():
 src=B.parent/'esc1_antes';sb=read(src/'storyboard_camara.json');dna=read(src/'adn_entidades.json');checks={};accepted={};fail=[]
 audit=report('iteracion04_inventario')
 if audit:
  expected=set(read(B/'config/repair.schema.json')['properties']['resolutions']['properties']);rows=audit['resolutions'];fields=[r['field'] for r in rows];errs=[]
  if len(fields)!=24 or set(fields)!=expected or len(set(fields))!=24:errs.append('Must cover exactly all 24 fields once')
  checks['inventory']={'passed':not errs,'errors':errs,'source_count':sum(r['status']=='SOURCE' for r in rows),'falta_count':sum(r['status']=='FALTA' for r in rows)}
 cam=report('iteracion05_camaras')
 if cam:
  errs=[];by={s['id']:s for s in cam['shots']};orig={s['vineta']:s for s in sb['vinetas']}
  if len(cam['shots'])!=12 or set(by)!=set(orig):errs.append('Camera IDs duplicated/missing')
  for ident,s in by.items():
   if ident not in orig:continue
   o=orig[ident]
   if [s['t0'],s['t1']]!=o['t_abs']:errs.append(ident+': altered time')
   keys=s['keyframes'];oldkeys=o['keyframes']
   if len(keys)!=len(oldkeys):errs.append(ident+': changed keyframe count')
   for k,old in zip(keys,oldkeys):
    if k['t']!=old['t'] or k['lente_mm']!=old['lente_mm']:errs.append(ident+': keyframe time/lens mismatch')
    if not all(math.isfinite(k[f]) for f in ['t','giro_grados','inclinacion_grados','lente_mm','altura_m','distancia_m']):errs.append(ident+': nonfinite numeric value')
    if not k['source'].startswith('Argon_GENERATED'):errs.append(ident+': design source not labeled GENERATED')
   oldsegments=o['segmentos'];segments=s['segments'];indices=[x['index'] for x in segments]
   if len(indices)!=len(oldsegments) or set(indices)!=set(range(len(oldsegments))):errs.append(ident+': segment indices mismatch')
   for seg in segments:
    if seg['index']>=len(oldsegments):continue
    movement=oldsegments[seg['index']]['movimiento']
    if seg['movement']!=movement:errs.append(ident+': movement changed')
    if movement=='PAN' and (not isinstance(seg.get('degrees'),(int,float)) or seg['degrees']<=0):errs.append(ident+': PAN needs positive degrees')
    if movement=='CRANE' and (not isinstance(seg.get('distance'),(int,float)) or seg['distance']<=0):errs.append(ident+': CRANE needs positive distance metres')
  checks['camera']={'passed':not errs,'errors':errs}
  if not errs:accepted['camera']=cam
 for name,label,ident in [('iteracion06_cofre','chest','obj-cofre-dorado'),('iteracion07_cama','bed','obj-cama'),('iteracion08_cofre_reparado','chest','obj-cofre-dorado'),('iteracion09_cama_reparada','bed','obj-cama')]:
  data=report(name)
  if not data:continue
  errs=[];params=read(B/'config'/str(label+'_sources.json'))
  if data['id']!=ident:errs.append('Wrong identity')
  if data['status']=='GENERATED':
   try:metrics=validar(data,{'dimensions_m':params['dimensions_m_exact']})
   except (ValueError,KeyError,TypeError) as e:errs.append(str(e));metrics=None
   for p in data['parts']:
    if not p['source'].startswith('Argon_GENERATED') or params['record']['id'] not in p['source']:errs.append('Part source must label generated design and actual ADN ID')
  else:
   metrics=None
   if data['parts']:errs.append('FALTA must not contain proposed parts')
  checks[name]={'passed':not errs,'status':data['status'],'errors':errs,'metrics':metrics}
  if not errs and data['status']=='GENERATED':accepted[ident]=data
 output={'checks':checks,'accepted_sections':list(accepted),'accepted_data':accepted,'production_approved':False,'all_scene_fields_resolved':False}
 (B/'evidencias/validacion_lotes.json').write_text(json.dumps(output,ensure_ascii=False,indent=2));print(json.dumps({'checks':checks,'accepted_sections':list(accepted)},ensure_ascii=False))
if __name__=='__main__':run()
