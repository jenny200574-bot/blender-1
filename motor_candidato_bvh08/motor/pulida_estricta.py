"""Adaptador de pulida: firma verificada, interruptor respetado, sin continuar sin pulir."""
from pathlib import Path
import importlib.util
from seguridad import *

def cargar_backend():
 p=Path(__file__).parent/'heredado/pulida.py';spec=importlib.util.spec_from_file_location('pulida_numerica',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def pulir(src,dst,*,unit_scale,footlock,npz=None,backend=None,switch=None,effector_map=None):
 exigir("movimiento")
 if switch and Path(switch).exists():raise ValueError('Pulida desactivada por .off: candidato bloqueado')
 if not numero(unit_scale) or unit_scale<=0:raise ValueError('Escala BVH explícita requerida')
 if footlock and not npz:raise ValueError('Footlock requiere FK/NPZ y mapa de efectores; no se omite')
 if footlock:
  import numpy as np
  if not isinstance(effector_map,dict) or effector_map.get('unit')!='m' or effector_map.get('up')!='Y' or not effector_map.get('ids'):raise ValueError('Mapa de efectores/unidades/ejes explícitos requerido')
  with np.load(npz,allow_pickle=False) as data:
   posed=data['posed_joints'];contacts=data['foot_contacts'];count=len(effector_map['ids'])
   if count>8 or posed.ndim!=3 or posed.shape[1:]!=(count,3) or contacts.shape!=posed.shape[:2]:raise ValueError('NPZ no coincide con mapa de efectores; no adivinar índices')
 if Path(dst).exists():raise ValueError('Salida ya existe; archivar antes de pulir')
 pm=backend or cargar_backend()
 options={'use_npz_contacts':True} if footlock else {}
 report=pm.polish_bvh(Path(src),Path(dst),do_smooth=True,do_footlock=footlock,npz=npz,unit_scale=unit_scale,**options)
 report['effector_map']=effector_map
 if footlock and not report.get('footlock_applied'):raise ValueError('Backend no aplicó footlock; candidato bloqueado')
 return report
