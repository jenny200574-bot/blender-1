import json,sys,math
from pathlib import Path
B=Path(__file__).resolve().parents[1];R=B.parent/'MOTOR_UNICO_20261107';sys.path.insert(0,str(R/'motor'));from recetas_proveedor import validar

def read(p):return json.loads(p.read_text())
def main():
 report={'recipes':{},'inventory':{},'production_approved':False}
 for iteration,label,n,ident in [('iteracion10_cofre_plano','chest',5,'obj-cofre-dorado'),('iteracion12_cama_plana','bed',8,'obj-cama'),('iteracion13_cofre_reparado','chest',5,'obj-cofre-dorado'),('iteracion14_cama_reparada','bed',8,'obj-cama')]:
  out=B/'evidencias'/iteration
  if not (out/'respuesta.json').is_file():continue
  d=read(out/'respuesta.json');params=read(B/'config'/str(label+'_sources.json'));parts=[];errors=[]
  if not read(out/'schema_validacion.json')['passed']:errors.append('Schema failed')
  for i in range(1,n+1):
   p={k:d[f'p{i}_{field}'] for k,field in [('id','id'),('shape','shape'),('source','source'),('resolution','resolution'),('tip_ratio','tip_ratio')]}
   p.update(position_m=[d[f'p{i}_{v}'] for v in ['px','py','pz']],rotation_deg=[d[f'p{i}_{v}'] for v in ['rx','ry','rz']],dimensions_m=[d[f'p{i}_{v}'] for v in ['dx','dy','dz']],material={'rgba':[d[f'p{i}_{v}'] for v in ['r','g','b','a']],'metallic':d[f'p{i}_metallic'],'roughness':d[f'p{i}_roughness']});parts.append(p)
   if not p['source'].startswith('Argon_GENERATED') or params['record']['id'] not in p['source']:errors.append('Part provenance incomplete')
  recipe={'id':ident,'source':d['source'],'parts':parts};metrics=None
  try:metrics=validar(recipe,{'dimensions_m':params['dimensions_m_exact']})
  except (ValueError,TypeError,KeyError) as e:errors.append(str(e))
  if d['status']!='GENERATED':errors.append('Not GENERATED')
  receipt={'passed':not errors,'errors':errors,'metrics':metrics,'recipe':recipe,'expected_dimensions_m':params['dimensions_m_exact'],'no_values_modified':True,'assembly':'Only grouping named scalar components into vectors/materials'}
  (out/'semantic_validacion.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));report['recipes'][iteration]=receipt
 inventory=B/'evidencias/iteracion11_inventario_plano/respuesta.json'
 if inventory.is_file():
  d=read(inventory);mapping=read(B/'config/inventory_flat_map.json');pending={e['campo'] for e in read(B/'evidencias/preview_cpu_resultado.json')['errores']};errors=[];rows=[]
  for k,f in mapping.items():
   s=d[k+'_status'];rows.append({'campo':f,'status':s,'source':d[k+'_source'],'reason':d[k+'_reason']})
   if s not in ['SOURCE','FALTA']:errors.append({'campo':f,'error':'Invalid status'})
   if s=='SOURCE' and f in pending:errors.append({'campo':f,'error':'SOURCE is a false completeness claim: the actual engine still blocks this exact field. Narrative/alias/hash/proportions are not a complete executable contract.'})
  report['inventory']={'passed':not errors,'errors':errors,'rows':rows}
 (B/'evidencias/validacion_planos.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'recipes':{k:{'passed':v['passed'],'errors':v['errors']} for k,v in report['recipes'].items()},'inventory_errors':len(report['inventory'].get('errors',[]))},ensure_ascii=False))
if __name__=='__main__':main()
