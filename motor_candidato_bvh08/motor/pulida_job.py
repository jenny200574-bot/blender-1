"""Worker numérico de pulida, sin red, comandos externos del paquete ni GPU."""
import sys
from pathlib import Path
from seguridad import *
from pulida_estricta import pulir
pk=Path(sys.argv[1]);request=leer(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=False)
r=pulir(ruta(pk,request['raw_bvh']),out/'pulido.bvh',unit_scale=request['unit_scale'],footlock=request['footlock'],npz=ruta(pk,request['raw_npz']) if request.get('raw_npz') else None,effector_map=request.get('effector_map'))
r.update(input_sha256=sha(ruta(pk,request['raw_bvh'])),output_sha256=sha(out/'pulido.bvh'));guardar(out/'recibo.json',r)
