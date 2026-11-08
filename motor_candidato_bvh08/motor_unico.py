#!/usr/bin/env python3
"""Única entrada pública. Desarrollo CPU estricto, sin red ni servicios pagos."""
import argparse,sys,subprocess,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'motor'))
from seguridad import *
from contrato import cargar,validar
from movimientos import verificar_programa
from eventos import validar_eventos
from auditar_sb import auditar
from orquestador import ejecutar

def regresion(entrada,out,blender,reference):
 # Herramienta de prueba del MISMO backend, no producción ni resultado completo.
 pk=Path(entrada).resolve().parent;d,E=cargar(pk)
 if E:raise ValueError(str(E))
 for a in d.get('assets',[]):
  p=ruta(pk,a['path'])
  if not p.is_file() or sha(p)!=a['sha256']:raise ValueError('Hash de fixture cambiado: '+a['path'])
 out=Path(out)
 if out.exists():raise ValueError('Usar salida nueva para regresión')
 out.mkdir(parents=True)
 cmd=[blender,'-b','-t','2','--python-exit-code','17','-P',str(ROOT/'motor/nucleo_bueno_cpu.py'),'--',str(pk),str(out),'--habilitar']
 with (out/'blender.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=7200)
 if r.returncode or not (out/'trazas.json').is_file():raise RuntimeError('Armado de regresión falló; ver blender.log')
 oldpath=list(sys.path);sys.path.insert(0,str(ROOT/'motor/heredado'))
 from revisar import revisar
 rv=revisar(pk,out);sys.path[:]=oldpath
 ref=leer(reference);checks=[]
 for pid,values in ref['naturalidad'].items():
  for k,value in values.items():checks.append({'actor':pid,'metric':k,'reference':value,'actual':rv['naturalidad'].get(pid,{}).get(k),'equal':value==rv['naturalidad'].get(pid,{}).get(k)})
 for k in ['huesos_max_pct','vel_ang_max_deg_s']:checks.append({'metric':k,'reference':ref[k],'actual':rv[k],'equal':ref[k]==rv[k]})
 result={'all_equal':all(c['equal'] for c in checks),'count':len(checks),'checks':checks,'production_approved':False,'pixel_regression':'NO_EJECUTADA','package_sha256':sha(entrada),'new_trace_sha256':sha(out/'trazas.json')}
 guardar(out/'metricas_oro.json',result);print(json.dumps({'regression':result['all_equal'],'checks':len(checks)}));return result

def main():
 p=argparse.ArgumentParser();p.add_argument('entrada');p.add_argument('--salida',required=True);p.add_argument('--prueba-cpu',action='store_true');p.add_argument('--regresion',action='store_true');p.add_argument('--blender');p.add_argument('--referencia');a=p.parse_args()
 if Path(a.entrada).name!='entrada_escena.json':p.error('Única entrada pública: entrada_escena.json')
 if a.regresion:
  if not a.blender or not a.referencia:p.error('Regresión requiere runtime y referencia explícitos')
  return 0 if regresion(a.entrada,a.salida,a.blender,a.referencia)['all_equal'] else 3
 r=ejecutar(a.entrada,a.salida,a.prueba_cpu,blender=a.blender);print(json.dumps({'estado':r['estado'],'faltantes':len(r['errores']),'gasto_usd':0}));return 2 if r['errores'] else 0
if __name__=='__main__':sys.exit(main())
