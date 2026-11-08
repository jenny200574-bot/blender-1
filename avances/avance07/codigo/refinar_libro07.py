import json,sys,copy,bisect
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';sys.path.insert(0,str(B/'MOTOR_UNICO_20261107/motor'))
from seguridad import guardar
from recetas_proveedor import validar
read=lambda p:json.loads(p.read_text());source=read(E/'evidencias/av07_bookmesh01/respuesta.json');canon=read(E/'evidencias/adn_canonico_final.json');record=next(r for r in canon['records'] if r['id']=='obj-libro-cuentos__e1-8');parts=record['source_data']['construction_3d']['parts'];assert len(source['pages'])==2 and {p['id'] for p in source['pages']}=={'av07.book.page_left','av07.book.page_right'}
profiles={}
for page in source['pages']:
 p=next(p for p in parts if p['id']==page['id']);rows=page['sections'];assert 6<=len(rows)<=9 and rows[0]['x']==-.09 and rows[-1]['x']==.09 and all(a['x']<b['x'] for a,b in zip(rows,rows[1:]));assert abs(max(r['half_y'] for r in rows)-.12)<1e-8 and all(0<r['half_y']<=.12 and -.01<=r['z_bottom']<r['z_top']<=.01 for r in rows);assert rows[0]['half_y']<.12 and rows[-1]['half_y']<.12
 vs=[]
 for r in rows:vs.extend([[r['x'],-r['half_y'],r['z_bottom']],[r['x'],r['half_y'],r['z_bottom']],[r['x'],-r['half_y'],r['z_top']],[r['x'],r['half_y'],r['z_top']]])
 faces=[[0,2,3,1]]
 for i in range(len(rows)-1):
  a=4*i;b=a+4;faces.extend([[a,a+1,b+1,b],[a+2,b+2,b+3,a+3],[a,b,b+2,a+2],[a+1,a+3,b+3,b+1]])
 a=4*(len(rows)-1);faces.append([a,a+1,a+3,a+2]);p.update(shape='MESH',vertices_m=vs,faces=faces,dimensions_m=[max(v[k] for v in vs)-min(v[k] for v in vs) for k in range(3)],source='argon07_libro_perfiles.json#/'+page['id']+'; deterministic closed4vertices-per-section shell, not box');profiles[p['id']]=rows
# Literal existing glyph geometry must not be buried under the newly designed page surface.
clearances=[]
for glyph in [p for p in parts if p.get('role')=='letter']:
 for v in glyph['vertices_m']:
  x=v[0]+glyph['position_m'][0];z=v[2]+glyph['position_m'][2];page=next(p for p in parts if p['id']==('av07.book.page_left' if x<0 else 'av07.book.page_right'));rows=profiles[page['id']];local=x-page['position_m'][0];i=max(0,min(len(rows)-2,bisect.bisect_right([r['x'] for r in rows],local)-1));a,b=rows[i:i+2];u=(local-a['x'])/(b['x']-a['x']);top=page['position_m'][2]+a['z_top']+(b['z_top']-a['z_top'])*u;clearances.append(z-top)
assert min(clearances)>1e-6,'Glyph still buried in page: '+str(min(clearances))
v=validar({'source':'Argon07 visual refinement','parts':parts},{'dimensions_m':record['source_data']['dimensions_m']},tolerance=.001);record['source']+=' + argon07_libro_perfiles.json';record['source_data']['shape_query']={'required_features':[p['id'] for p in parts]}
guardar(E/'evidencias/adn_canonico_refinado07.json',canon);guardar(E/'evidencias/libro_refinado07_validacion.json',{'passed':True,'metrics':v,'minimum_glyph_clearance_m':min(clearances),'old_visual_rejection':'Two white ellipsoids looked like plates, so old shape NOT presented as approved book','shape_new':'Closed point-profile shells, rounded/chamfered corners + crease profile, not box','measured_or_original_ADN_dimensions_changed':False,'visual_production_approved':False});print(json.dumps({'passed':True,'min_glyph_clearance_m':min(clearances),'metrics':v}))
