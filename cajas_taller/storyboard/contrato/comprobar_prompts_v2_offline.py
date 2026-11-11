#!/usr/bin/env python3
"""Solo box: pruebas estáticas y conteo local; imprime JSON, no escribe ni llama APIs."""
import argparse
import hashlib
import json
import re
import socket
from pathlib import Path

def no_network(*args, **kwargs):
    raise RuntimeError("Comprobación offline: red deshabilitada; precargue el tokenizador antes")
socket.socket.connect = no_network
socket.create_connection = no_network
from google.genai.local_tokenizer import LocalTokenizer

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a.add_argument('--contrato',type=Path);a.add_argument('--tablas',type=Path);args=a.parse_args()
    s=args.root;c=args.contrato or s/'contrato'
    tokenizer=[REDACTED]
    count=lambda text:tokenizer.count_tokens(text).total_tokens
    mp=json.loads((s/'config/perfiles_argon_cine_v2.propuesta.json').read_text())
    rules=json.loads((c/'reglas_sb_v1.json').read_text());schema=json.loads((c/'contrato_vineta_v1.schema.json').read_text())
    results=[]
    def check(name,ok):results.append({'prueba':name,'ok':bool(ok)})
    required={'BASE_COMUN_V2','BLOQUE_GENERO_V2','REGLAS_SB_V1_JSON','CONTRATO_VINETA_V1_SCHEMA_JSON','CONTEXTO_ESCENA_JSON','CONTEXTO_CONTINUIDAD_JSON','REFERENCIAS_ADN_JSON','MANIFIESTO_ESPACIAL_JSON','NIVELES_CANAL_JSON'}
    ph=lambda t:set(re.findall(r'{{([A-Z_0-9]+)}}',t))
    bad=re.compile(r'(?im)^\s*(?:reescribe|rediseña|inventa|cambia|describe de nuevo)\s+(?:la apariencia|el color|los colores|la piel|el rostro|el vestuario|la ropa|el peinado|las proporciones)\b')
    base=(s/mp['base']).read_text();direct=(s/mp['direction']).read_text();repair=(s/mp['repair']).read_text()
    check('Propuesta inactiva',mp['activation_approved'] is False and mp['status']=='INACTIVO_NO_CARGADO_POR_MOTOR')
    expected={'drama','emocion','intriga','suspenso','terror','comedia','accion','fantasia','ternura','misterio'}
    check('Diez géneros exactos',set(mp['profiles'])==expected)
    check('Versiones aprobadas',rules['rules_version']=='1.0.0' and rules['contract_version']=='2.1.0' and schema['properties']['version']['const']=='2.1.0')
    check('Placeholders dirección',ph(direct)==required)
    check('Placeholders reparación',ph(repair)==required|{'CONTRATOS_ANTERIORES_JSON','ERRORES_VALIDACION_JSON','ALCANCE_REPARACION_JSON'})
    check('Base sin placeholders inesperados',ph(base)==set())
    base_terms=['director principal','ADN INMUTABLE','PROHIBIDO reescribir colores','dna_ref_id','dna_override_allowed=false','24fps','delta arousal>=+0.15','REVEAL por sí solo no exime','pre-roll.8-1.5s','GPG+PG<=20%','hasta35% global','ventana de5','GPP máximo1','Nunca dos PD seguidos','reglas_sb_v1.json','round_half_up','Schema válido no equivale','U=w_emo','>=30','<=8%']
    for term in base_terms:check('Base conserva '+term,term in base)
    for key in schema['properties']:
        if re.match(r'^\d+_',key):check('Bloque contrato '+key,key in base)
    for name,text in [('base',base),('dirección',direct),('reparación',repair)]:check('Sin instrucción afirmativa de rediseño ADN '+name,bad.search(text) is None)
    check('Reparación solo autorizadas','SOLO las viñetas' in repair and 'hash debe permanecer intacto' in repair and 'ambas fronteras' in repair)
    check('Canales/capítulos no fijados',not re.search(r'cn-[a-z0-9]|ep-[a-z0-9]|Guardianes|Génesis',base+direct+repair))
    report=json.loads((s/'contrato/PROMPTS_V2_TOKENS.json').read_text())
    for name,p in mp['profiles'].items():
        text=(s/p['block_file']).read_text();n=count(text)
        check('Tokens700..1000 '+name,700<=n<=1000)
        check('Conteo registrado '+name,n==report['genres'][name]['tokens'])
        check('Género enum '+name,p['contract_genre'] in schema['properties']['1_narrative_and_emotion']['properties']['genre_profile']['enum'] and p['contract_genre'] in text)
        check('Matriz íntegra '+name,all(v in text for v in p['report_preferences'].values()))
        check('Reglas/contrato y ADN '+name,all(v in text for v in ['reglas1.0.0','contrato2.1.0','dna_ref_id','24fps','LOCK']))
        check('Sin rediseño afirmativo '+name,bad.search(text) is None)
        check('Sin placeholders género '+name,ph(text)==set())
    if args.tablas:
        raw=args.tablas.read_bytes();check('Hash tablas fuente',hashlib.sha256(raw).hexdigest()==mp['sources']['report_tables_sha256'])
        rows=[x for x in raw.decode().splitlines() if x[:1].isdigit() and ' | ' in x][:10]
        for p in mp['profiles'].values():check('Fila matriz fuente '+p['contract_genre'],list(p['report_preferences'].values())==[v.strip() for v in rows[p['source_row']-1].split(' | ')])
    check('Detecta pérdida de placeholder',ph(direct.replace('{{MANIFIESTO_ESPACIAL_JSON}}',''))!=required)
    check('Detecta orden peligrosa de ADN',bad.search(base+'\nReescribe la apariencia de todos los personajes.') is not None)
    check('Detecta pérdida de reloj','24fps' not in base.replace('24fps','RELOJ_OMITIDO'))
    check('Tamaño base registrado',count(base)==report['fixed_components']['base_tokens'])
    check('Hashes textos registrados',all(hashlib.sha256((s/k).read_bytes()).hexdigest()==v for k,v in report['file_sha256'].items()))
    out={'pasan':sum(x['ok'] for x in results),'fallan':sum(not x['ok'] for x in results),'pruebas':results,'offline':True,'sin_IA_ni_gasto':True,'tokenizer':'Google GenAI LocalTokenizer/Gemma3, texto; referencia Gemini2.5-Pro; NO conteo certificado de alias Argon','limite':'Check estático y auditoría textual, no prueba de obediencia de IA ni aceptación física'}
    print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if out['fallan']==0 else 1
if __name__=='__main__':raise SystemExit(main())
