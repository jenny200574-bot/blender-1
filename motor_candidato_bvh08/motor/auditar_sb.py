"""Revisa amplitudes explícitas sin convertir izquierda/derecha o velocidad a grados."""
from seguridad import error

def auditar(storyboard):
 E=[];commands=[]
 for v in storyboard.get('vinetas',[]):
  for i,s in enumerate(v.get('segmentos',[])):
   mode=s['movimiento'];args=s.get('args') or {};field='camera/'+v['vineta']+'/'+str(i)+'/'+mode;commands.append({'shot':v['vineta'],'mode':mode,'args':args})
   if mode=='PAN' and not any(k in args for k in ['degrees','giro_grados','anchors','extremos']):E.append(error(field,'SB + 02N/4a2','Faltan grados o extremos inequívocos; dir_lr y speed no determinan amplitud','CAMARA_DATO_FALTANTE'))
   if mode=='CRANE' and not any(k in args for k in ['height_m','metros','distance','anchors','extremos']):E.append(error(field,'SB + 02N/4a2','Faltan metros o extremos verticales; dir_ud y speed no determinan altura','CAMARA_DATO_FALTANTE'))
 return {'commands':commands,'errors':E,'shots':len(storyboard.get('vinetas',[]))}
