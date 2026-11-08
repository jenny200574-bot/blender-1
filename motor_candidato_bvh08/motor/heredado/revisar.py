"""Métricas heredadas comparables y física genérica, independientes de identidad."""
import math,json,sys
from pathlib import Path
from entrada import leer,guardar

def revisar(package,output):
 d=leer(Path(package)/'entrada.json');out=Path(output);T=leer(out/'trazas.json');N=min(len(x) for x in T.values());fps=d['fps'];actors={a['id']:a for a in d['actors']};report={'naturalidad':{},'fisica':{},'huesos_max_pct':0.,'vel_ang_max_deg_s':0.,'no_aprobado':bool(d['provisional']),'pendientes':d['provisional']}
 for pid,rows in T.items():
  p=actors[pid]['profile'];L0=rows[0]['largos'];rs=[];hop=0;vz=0
  for i,fr in enumerate(rows):
   report['huesos_max_pct']=max(report['huesos_max_pct'],max(abs(fr['largos'][k]-L0[k])/L0[k]*100 for k in L0))
   if not i:continue
   prev=rows[i-1];a0,a1=prev['plant'],fr['plant']
   if a0 and a1 and a0[0]==a1[0]:rs.append(math.dist(a0[1][:2],a1[1][:2]))
   v=(fr['loc'][2]-prev['loc'][2])*fps;vz=max(vz,v);hop+=v>p['vel_vertical_max_m_s']
   va=max(abs(fr['ang'].get(k,[0,0,0])[j]-prev['ang'].get(k,[0,0,0])[j]) for k in fr['ang'] for j in range(3))*fps;report['vel_ang_max_deg_s']=max(report['vel_ang_max_deg_s'],round(va,1))
  fu=[x['com_fuera'] for x in rows]
  report['naturalidad'][pid]={'equilibrio_cuadros_fuera':sum(x>p['margen_equilibrio_m'] for x in fu),'equilibrio_cuadros_fuera_4cm_fijo':sum(x>.04 for x in fu),'equilibrio_max_fuera_m':round(max(fu),3),'resbale_pie_max_cm_cuadro':round(max(rs or [0])*100,2),'resbale_pie_medio_cm_cuadro':round(sum(rs)/max(1,len(rs))*100,3),'saltitos_cuadros':hop,'vel_subida_cadera_max_m_s':round(vz,2)}
  limits=actors[pid].get('physics')
  if limits:
   com=[x['com'] for x in rows];acc=[math.sqrt(sum((com[i+1][j]-2*com[i][j]+com[i-1][j])**2 for j in range(3)))*fps*fps for i in range(2,N-2)];smooth=[sum(acc[max(0,i-2):i+3])/len(acc[max(0,i-2):i+3]) for i in range(len(acc))]
   report['fisica'][pid]={'acel_com_max_m_s2':round(max(smooth or [0]),2),'cuadros_acel_excesiva':sum(x>limits['aceleracion_max_com_m_s2'] for x in smooth),'limites_entrada':limits}
   if report['fisica'][pid]['cuadros_acel_excesiva']:report['no_aprobado']=True
  else:report['fisica'][pid]={'estado':'FALTA','modulo':'ADN/perfil físico','mensaje':'No se infiere masa ni capacidad de fuerza'};report['no_aprobado']=True
 guardar(out/'revisor_comparable.json',report);return report
if __name__=='__main__':print(json.dumps(revisar(*sys.argv[1:]),ensure_ascii=False)[:500])
