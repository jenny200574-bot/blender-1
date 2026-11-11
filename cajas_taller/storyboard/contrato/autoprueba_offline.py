#!/usr/bin/env python3
"""Prueba offline de especificacion SB. No importa el motor, no usa red/IA ni escribe datos.
Requiere jsonschema (draft2020-12). NO sustituye Gate1, ADN ni contexto real.
"""
import copy, json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from jsonschema import Draft202012Validator
P=Path(__file__).resolve().parent
SCHEMA=json.loads((P/'contrato_vineta_v1.schema.json').read_text())
RULES=json.loads((P/'reglas_sb_v1.json').read_text())
V=Draft202012Validator(SCHEMA)
B1='1_narrative_and_emotion'; B2='2_visible_action_dialogue_reaction'; B3='3_subjects_and_hierarchy'
B6='6_set_and_time'; B7='7_shot_size_and_framing'; B8='8_camera_optics_and_geometry'; B9='9_camera_movement_and_motive'
def rnd(t):return int((Decimal(str(t))*24).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
def panel_checks(p,ctx=None):
    ctx=ctx or {}; err=[]
    t=p[B6]['scene_timecode_sec']; fr=p[B6]['frame_range_24fps']
    if t['end']<=t['start'] or abs(t['end']-t['start']-t['duration'])>1e-9:err.append('SB_TIME')
    if fr['frame_start']!=rnd(t['start'])+1 or fr['frame_end']!=rnd(t['end']) or fr['frame_end']<fr['frame_start']:err.append('SB_CLOCK')
    if p[B8]['keyframe_start']['frame']!=fr['frame_start'] or p[B8]['keyframe_end']['frame']!=fr['frame_end']:err.append('SB_KEYFRAME_CLOCK')
    w=p[B3]['utility_weights']
    if abs(sum(w.values())-1)>1e-9:err.append('SB_WEIGHTS_SUM')
    ids=[c['character_id'] for c in p['4_characters_dna_and_state']]
    if len(ids)!=len(set(ids)):err.append('SB_DUPLICATE_CHARACTER')
    d=p[B2]['dialogue']; primary=p[B3]['primary_subject']
    face_needed=d is not None or p[B1]['target_emotion']['arousal_level']>=.45
    if face_needed and (w['w_emo']<.75 or primary['entity_type']!='CHARACTER' or primary['target_bone']!='eye_target' or not p['12_tolerances_and_validations']['require_both_eyes_visible']):err.append('SB_FACE_PRIORITY')
    if d and d['timing_sec']['end_offset']<=d['timing_sec']['start_offset']:err.append('SB_AUDIO_TIME')
    if d and d['speaker_id'] not in ids and d['speaker_id'] not in ctx.get('voice_only_ids',[]):err.append('SB_SPEAKER_ID')
    # Pre-roll may occur in the previous panel. Do not clip audio to image bounds.
    if d and t['start']+d['timing_sec']['start_offset']-d['pre_roll_sec']<0:err.append('SB_PRE_ROLL_BEFORE_SCENE')
    reaction=p[B2]['reaction']
    if reaction and reaction['reactor_id'] not in ids:err.append('SB_REACTOR_ID')
    mov=p[B9]['movement_type']; canonical=mov.replace('_','')
    if 'DOLLYIN' in canonical:
        if 'previous_arousal' not in ctx:err.append('SB_DOLLY_MISSING_CONTEXT')
        else:
            delta=p[B1]['target_emotion']['arousal_level']-ctx['previous_arousal']
            if delta<.15-1e-9 or abs(delta-p[B1].get('arousal_delta',-99))>1e-9:err.append('SB_DOLLY_DELTA')
    if mov in ('LOCK','STATIC'):
        a=p[B8]['keyframe_start'];b=p[B8]['keyframe_end']
        if a['camera_location_xyz']!=b['camera_location_xyz'] or a['aim_target_xyz']!=b['aim_target_xyz'] or a['roll_deg']!=b['roll_deg'] or p[B8]['focal_length_mm']['start']!=p[B8]['focal_length_mm']['end'] or p[B8]['path_length_m'] or p[B9]['speed_m_per_sec'] or p[B9]['handheld_shake']['enabled']:err.append('SB_LOCK')
    if p[B7]['shot_size_code']=='PD':
        pf=p[B3].get('prop_focus') or {}
        if not pf.get('is_narrative_catalyst') or not pf.get('requires_visual_readability') or pf.get('consecutive_prop_shots')!=0:err.append('SB_PD_FLAGS')
        if ctx.get('previous_shot')=='PD':err.append('SB_PD_CONSECUTIVE')
    return err

def scene_checks(codes,genre='DRAMA',measured_displacement=None):
    # Unit-check of sequence policy, not acceptance of incomplete panel objects.
    err=[];n=len(codes)
    if not n:return ['SB_EMPTY_SCENE']
    exception=genre in RULES['quotas']['exception']['genres'] and measured_displacement is not None and measured_displacement>2
    limit=.35 if exception else .20
    if sum(c in ('GPG','PG') for c in codes)/n>limit+1e-9:err.append('SB_WIDE_QUOTA')
    if any(sum(c in ('GPG','PG') for c in codes[i:i+5])>1 for i in range(max(0,n-4))):err.append('SB_WIDE_WINDOW')
    if codes.count('GPP')>1:err.append('SB_GPP_QUOTA')
    if any(a==b=='PD' for a,b in zip(codes,codes[1:])):err.append('SB_PD_CONSECUTIVE')
    g=[i for i,c in enumerate(codes) if c=='GPG']
    if any(b-a<6 for a,b in zip(g,g[1:])):err.append('SB_GPG_SPACING')
    return err

def main():
    Draft202012Validator.check_schema(SCHEMA)
    raw=json.loads((P/'ejemplo_informe_original.json').read_text())
    good=json.loads((P/'ejemplo_v1_solo_prueba.json').read_text())
    ctx={'previous_arousal':.56,'previous_shot':'PMC'} # FICTICIO: .78-.22; no es dato de ningun capitulo.
    out=[]
    def test(name,condition):
        out.append({'prueba':name,'ok':bool(condition)})
        if not condition:raise AssertionError(name)
    test('schema draft2020-12 valido',True)
    rawerrs=list(V.iter_errors(raw))
    test('original informe2.0.0 detectado incompatible sin migracion silenciosa',bool(rawerrs))
    test('fixture2.1.0 solo prueba cumple schema',not list(V.iter_errors(good)))
    test('fixture cumple chequeos logicos disponibles con contexto ficticio rotulado',not panel_checks(good,ctx))
    test('sin contexto anterior Dolly queda bloqueado','SB_DOLLY_MISSING_CONTEXT' in panel_checks(good))
    cases=[('arousal fuera0..1',[B1,'target_emotion','arousal_level'],1.1),('ADN override prohibido',['4_characters_dna_and_state',0,'dna_override_allowed'],True),('apariencia nueva prohibida',['4_characters_dna_and_state',0,'hair_color'],'azul'),('pre-roll0.6 rechazado',[B2,'dialogue','pre_roll_sec'],.6),('Dolly REVEAL sin delta suficiente',[B1,'arousal_delta'],.10),('r_head PMC fuera rango',[B7,'expected_head_height_ratio'],.10),('flag lectura falso en PD',[B3,'prop_focus'],{'entity_id':'PROP_BROKEN_KEY','is_narrative_catalyst':True,'requires_visual_readability':False,'consecutive_prop_shots':0,'script_evidence':'solo prueba'})]
    for name,path,value in cases:
        bad=copy.deepcopy(good);d=bad
        for k in path[:-1]:d=d[k]
        d[path[-1]]=value
        if name=='flag lectura falso en PD':bad[B7]['shot_size_code']='PD'
        test(name,bool(list(V.iter_errors(bad))))
    bad=copy.deepcopy(good);bad[B6]['frame_range_24fps']['frame_end']+=1
    test('cuadro final incoherente bloqueado','SB_CLOCK' in panel_checks(bad,ctx))
    bad=copy.deepcopy(good);bad[B3]['utility_weights']['w_emo']=.75
    test('pesos no normalizados bloqueados','SB_WEIGHTS_SUM' in panel_checks(bad,ctx))
    test('GPP duplicado bloqueado','SB_GPP_QUOTA' in scene_checks(['GPP','GPP','PMC']))
    test('PD consecutivos bloqueados','SB_PD_CONSECUTIVE' in scene_checks(['PD','PD','PMC']))
    test('35% sin movimiento medido no se presume','SB_WIDE_QUOTA' in scene_checks(['PG','PMC','PMC'],'COMEDIA'))
    test('35% solo global con traslado medido','SB_WIDE_QUOTA' not in scene_checks(['PG','PMC','PMC'],'COMEDIA',2.1))
    test('excepcion no permite dos amplios en ventana5','SB_WIDE_WINDOW' in scene_checks(['PG','PG','PMC','PMC','PMC','PMC'],'ACCION',3))
    test('clock ejemplo181..276 =96cuadros',rnd(11.5)-rnd(7.5)==96)
    print(json.dumps({'pasan':len(out),'fallan':0,'pruebas':out,'original_informe_errores_schema':[{'ruta':'/'.join(map(str,e.absolute_path)),'mensaje':e.message} for e in rawerrs],'fixture':'SOLO PRUEBA; sin aprobacion artistica ni datos de capitulo','pendiente_para_operar':['ADN/catalogo y checksums reales','continuidad de escena completa','manifest espacial y rig','Blender Gate1','voz medida si aplica'],'sin_red_ia_gasto_y_sin_escribir_datos':True},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
