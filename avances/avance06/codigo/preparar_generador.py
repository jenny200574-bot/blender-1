from pathlib import Path
import json
B=Path('/workspace/avance06');src=Path('/workspace/avance05/codigo/generar_schema.py').read_text()
src=src.replace("'step_cap_usd':3","'step_cap_usd':10").replace("'previous_plan_gross_usd':.0759895","'previous_plan_gross_usd':.2042645").replace("+reserve>3 or","+reserve>d['step_cap_usd'] or")
src=src.replace("nbytes=len(prompt.encode())+len(json.dumps(schema).encode());reserve=", "nbytes=len(prompt.encode())+len(json.dumps(schema).encode()); imagepaths=json.loads(selected('MYIA_SOURCES','repair_source_pack.json').read_text()).get('_image_paths',[]); nbytes+=len(imagepaths)*24000;reserve=")
src=src.replace("text='';usage=None;finish=None;code=None;phase='network';cost=None", "parts=[types.Part.from_text(text=prompt)]\n for ip in imagepaths:\n  import mimetypes\n  p=Path(ip).resolve()\n  if not str(p).startswith(('/opt/myia-taller-n8n/trabajo/','/opt/myia-taller-n8n/cajas/FIJOS_TALLER/','/opt/myia-taller-n8n/cajas/cubo_fijo/hojas/')) or p.suffix.lower() not in ['.png','.jpg','.jpeg','.webp'] or p.stat().st_size>8000000:raise ValueError('Image not allowed')\n  parts.append(types.Part.from_bytes(data=p.read_bytes(),mime_type=mimetypes.guess_type(str(p))[0]))\n text='';usage=None;finish=None;code=None;phase='network';cost=None")
src=src.replace('contents=prompt,config=','contents=[types.Content(role=\'user\',parts=parts)],config=')
src=src.replace('/opt/myia-motor-v9/avance05_20261107/MOTOR_UNICO_20261107/motor','/opt/myia-motor-v9/avance06_20261107/MOTOR_UNICO_20261107/motor')
(B/'codigo/generar_schema.py').write_text(src)
props={'schema':{'type':'string','enum':['ako_json/v1']},'id':{'type':'string'},'clase':{'type':'string','enum':['personaje','objeto','escenario','poder','estilo']},**{f'bloque_{i}':{'type':'string'} for i in range(1,6)}}
(B/'config/ako.schema.json').write_text(json.dumps({'type':'object','properties':props,'required':list(props)}))
(B/'config/registry.json').write_text('{}')
