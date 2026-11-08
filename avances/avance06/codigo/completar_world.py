from pathlib import Path
import json,sys,math
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';sys.path.insert(0,str(B/'MOTOR_UNICO_20261107/motor'));from seguridad import guardar
p=E/'evidencias/iluminacion_canonica.json';d=json.loads(p.read_text());r=json.loads((E/'evidencias/av06_lightworld03/respuesta.json').read_text());a=r['world_a'];assert isinstance(a,(float,int)) and math.isfinite(a) and 0<=a<=1 and r['world_id'].startswith('av06.art.world');d['world']['id']=r['world_id'];d['world']['color_rgba']=d['world']['color']+[a];d['world']['alpha_source']='av06_lightworld03/respuesta.json#/world_a';guardar(p,d);print('World contract completed from validated model output')
