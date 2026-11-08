"""Salida de tiempos para Omni; NO genera voz, audio, visemas ni lip-sync.
01 aporta actuación y tiempos; SB aporta pertenencia a tomas. No se prorratea texto.
"""
from seguridad import *

def compilar(actions,shots,fps,duration,entity_ids,source,transition_convention="outgoing"):
    lines=[];errors=[];seen=set()
    for i,a in enumerate(actions):
        action=a.get('accion',a.get('action'))
        if action not in {'hablar','speak','dialogue'}:continue
        ident=a.get('id');speaker=a.get('actor',a.get('speaker'));text=a.get('texto',a.get('text',a.get('dialogo',a.get('cita'))));times=a.get('t',[a.get('t0'),a.get('t1')]);pointer=source+'#/acciones/'+str(i)
        base={'id':ident,'hablante':speaker,'texto':text,'fuente':pointer}
        if not isinstance(ident,str) or ident in seen or speaker not in entity_ids or not isinstance(text,str) or not text.strip() or not isinstance(times,list) or len(times)!=2 or not all(numero(t) for t in times) or not 0<=times[0]<times[1]<=duration:
            errors.append(error('dialogue/'+str(ident),'guion/01','Hablante, texto, ID o intervalo de diálogo ausente/inválido',fuente=pointer));continue
        seen.add(ident);t0,t1=times;f0,f1=cuadro(t0,fps),cuadro(t1,fps);pieces=[]
        for s in shots:
            a0,b0=cuadro(s['t0'],fps),cuadro(s['t1'],fps);start,end=max(a0,f0),min(b0,f1)
            if end>start:pieces.append({'toma':s['id'],'inicio_s':max(t0,s['t0']),'fin_s':min(t1,s['t1']),'inicio_cuadro':start+1,'fin_cuadro':end,'intervalo_cuadros_base0':[start,end]})
        if sum(p['fin_cuadro']-p['inicio_cuadro']+1 for p in pieces)!=f1-f0:errors.append(error('dialogue/'+ident+'/tomas','SB/01','Diálogo fuera de cobertura de tomas',fuente=pointer))
        lines.append(dict(base,inicio_s=t0,fin_s=t1,inicio_cuadro=f0+1,fin_cuadro=f1,intervalo_cuadros_base0=[f0,f1],toma=pieces[0]['toma'] if len(pieces)==1 else None,tomas=[p['toma'] for p in pieces],por_toma=pieces))
    handoff=[]
    for shot in shots:
        tr=shot.get('transition');kind=tr.get('type') if isinstance(tr,dict) else tr
        if kind in {'J_CUT','L_CUT'}:handoff.append({'toma':shot['id'],'tiempo_s':shot['t1'] if transition_convention=='outgoing' else shot['t0'],'directiva_original':tr,'destino':'Omni después del motor','fuente':'SB/entrada_escena.json#/camera/shots'})
    return {'audio_edit_handoff':handoff,'version':'dialogos_omni/1','estado':'BLOQUEADO' if errors else 'COMPLETO','destino':'omni posterior al motor','genera_voz':False,'genera_lipsync':False,'fps':fps,'duracion_s':duration,'convencion_cuadros':'inicio/fin 1-based inclusivos; intervalo_cuadros_base0 [inicio,fin); HALF_UP global','dialogos':lines,'errores':errors,'nota':'Los intervalos son planificación 01, no alineación de una grabación. El texto aparece una sola vez aunque cruce un corte. Las intervenciones simultáneas conservan un hablante por registro.'}
