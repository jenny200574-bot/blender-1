"""Plan de montaje estricto. Sin master parcial; transiciones no implementadas bloquean."""
from seguridad import *
def planificar(shots,fps,duration):
 exigir("montaje")
 cursor=0;out=[]
 for i,shot in enumerate(shots):
  a,b=cuadro(shot['t0'],fps),cuadro(shot['t1'],fps)
  if a!=cursor or b<=a:raise ValueError('Hueco/solape temporal')
  if shot.get('state')!='APROBADA':raise ValueError('No se monta toma bloqueada: '+str(shot['id']))
  transition=shot.get('transition')
  if transition=='FIN_ESCENA' and i!=len(shots)-1:raise ValueError('FIN_ESCENA antes de última toma')
  if transition not in ['CORTE','CORTE_SECO','CUT','FIN_ESCENA']:raise ValueError('Transición pendiente de implementar: '+str(transition))
  out.append({'id':shot['id'],'start':a,'stop_exclusive':b,'frames':b-a});cursor=b
 if cursor!=cuadro(duration,fps):raise ValueError('Montaje no cubre duración completa')
 return out
