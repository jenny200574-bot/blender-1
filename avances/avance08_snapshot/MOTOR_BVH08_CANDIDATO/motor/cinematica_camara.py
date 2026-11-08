"""Modos geométricamente distintos; datos ausentes bloquean, nunca amplitud inventada."""
import math
from seguridad import *

def trayectoria(spec,fps):
 exigir("camara")
 mode=spec['mode'];required={'STATIC':['position','target'],'PAN':['position','target','degrees'],'CRANE':['position','target','height_m'],'TRACK':['position','target','end_target'],'ORBIT':['position','target','degrees']}
 if mode not in required:raise ValueError('Modo sin implementar: '+mode)
 for k in required[mode]+['t0','t1','lens_mm']:
  if k not in spec:raise ValueError('SB/02N: falta '+k+' para '+mode)
 a,b=cuadro(spec['t0'],fps),cuadro(spec['t1'],fps)
 if b<=a:raise ValueError('Toma vacía')
 out=[]
 for f in range(a,b):
  u=0 if b-a==1 else (f-a)/(b-a-1);p=list(spec['position']);target=list(spec['target'])
  angle=math.radians(spec.get('degrees',0)*u)
  if mode=='PAN':
   x,y=target[0]-p[0],target[1]-p[1];target[0]=p[0]+math.cos(angle)*x-math.sin(angle)*y;target[1]=p[1]+math.sin(angle)*x+math.cos(angle)*y
  elif mode=='CRANE':p[2]+=spec['height_m']*u
  elif mode=='TRACK':
   delta=[(y-x)*u for x,y in zip(target,spec['end_target'])];p=[x+y for x,y in zip(p,delta)];target=[x+y for x,y in zip(target,delta)]
  elif mode=='ORBIT':
   x,y=p[0]-target[0],p[1]-target[1];p[0]=target[0]+math.cos(angle)*x-math.sin(angle)*y;p[1]=target[1]+math.sin(angle)*x+math.cos(angle)*y
  if math.dist(p,target)<1e-8:raise ValueError('Cámara coincide con objetivo')
  out.append({'frame':f+1,'position':p,'target':target,'lens_mm':spec['lens_mm']})
 return out
