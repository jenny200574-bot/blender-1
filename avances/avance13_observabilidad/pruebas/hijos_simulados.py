#!/usr/bin/env python3
"""Hijos CPU simulados. No Blender, no GPU, no red, no rutas VPS."""
import os,sys,time
cmd=sys.argv[1] if len(sys.argv)>1 else 'ok'
if cmd=='ok':
 sys.stdout.write('hijo_ok stdout\n');sys.stdout.flush();sys.exit(0)
if cmd=='stderr_tb':
 try:
  raise RuntimeError('error_simulado_observabilidad')
 except RuntimeError:
  import traceback;traceback.print_exc();sys.exit(1)
if cmd=='exit':
 code=int(sys.argv[2]) if len(sys.argv)>2 else 7
 sys.stderr.write('salida_no_cero=%s\n'%code);sys.stderr.flush();sys.exit(code)
if cmd=='signal':
 sys.stdout.write('esperando_senal pid=%s\n'%os.getpid());sys.stdout.flush();time.sleep(60);sys.exit(0)
if cmd=='silencio':
 sys.exit(0)
sys.stderr.write('hijo_desconocido\n');sys.exit(2)
