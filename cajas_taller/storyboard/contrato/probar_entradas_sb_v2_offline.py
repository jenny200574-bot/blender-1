#!/usr/bin/env python3
"""Solo box: pruebas sin red, casos artificiales rotulados y datos reales solo lectura.
Uso --datos TALLER_SNAPSHOT. Imprime JSON; stdout se puede guardar SOLO fuera de capítulos.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import socket
import sys
import tempfile
from pathlib import Path
sys.dont_write_bytecode=True

def no_network(*a,**k):raise RuntimeError('RED_PROHIBIDA_EN_AUTOPRUEBA')
socket.socket.connect=no_network;socket.create_connection=no_network
MODULE=Path(__file__).resolve().parents[1]/'entradas_sb_v2.py'
spec=importlib.util.spec_from_file_location('entradas_sb_v2',MODULE);E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)

def run(root):
    tests=[];real=[]
    def check(name,value):tests.append({'prueba':name,'ok':bool(value)})
    def raises(name,fn,code=None):
        try:fn()
        except (E.InputError,OSError) as ex:check(name,code is None or code in str(ex))
        else:check(name,False)
    def digest_tree(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
    before=digest_tree(root)
    sources=ast.parse(MODULE.read_text());imports={n.names[0].name for n in ast.walk(sources) if isinstance(n,ast.Import)}
    check('Solo importaciones estándar sin motor activo',not imports&{'requests','httpx','subprocess','os','cubo_sb','paso01_pago','personajes','bpy'})
    check('Módulo no tiene primitivas de escritura',not any(isinstance(n,ast.Attribute) and n.attr in {'write_text','write_bytes','mkdir','unlink','rmdir','rename','replace','touch'} for n in ast.walk(sources)))
    check('Escena especial con ID seguro',E.scene_number('POSCREDITOS')=='POSCREDITOS')
    exclusions=[];cl=E.sanitize_01({'parametros_3d':{'actor':{'controles':{'expresion':'respira','colores.piel':'NO_FILTRAR_SENTINELA','gordura':1}}}},exclusions)
    check('Actuación se conserva separada del aspecto',cl['parametros_3d']['actor']['controles_transitorios_fuente01']=={'expresion':'respira'} and len(exclusions)==2)
    t=E.timing24([7.5,11.5]);check('24fps181..276 y96cuadros',t['start_frame']==181 and t['end_frame_inclusive']==276 and t['frame_count']==96)
    check('Redondeo decimal exacto',E.frame_boundary(0.0625)==2)
    raises('Rechaza tiempo negativo',lambda:E.timing24([-1,2]));raises('Rechaza NaN',lambda:E.timing24([0,float('nan')]))
    raises('Rechaza booleano tiempo',lambda:E.timing24([False,2]));raises('Rechaza intervalo cero',lambda:E.timing24([1,1]));raises('Rechaza fuera de duración',lambda:E.timing24([1,3],2))
    raises('Rechaza tiempo menor a cuadro',lambda:E.timing24([0,.001]));raises('Rechaza ID recorrido',lambda:E.safe_id('../x'))
    raises('Rechaza capítulo decimal ambiguo',lambda:E.resolve_chapter(E.Reader(root),'canal-prueba','1.0'))
    raises('Rechaza ruta protegida antes de leer',lambda:E.Reader(root).path('cajas/secrets_argon/oculto'))
    for channel in sorted((root/'trabajo/paso00_cadena').iterdir()):
        for cap in sorted(channel.glob('cap01_*')):
            files=sorted((cap/'cubos/01').glob('esc_*.json'),key=lambda f:int(f.stem.split('_')[-1]))
            for f in files:
                n=f.stem.split('_')[-1];out=E.assemble(root,channel.name,cap.name,n)
                raw=json.loads(f.read_text()) if f.stat().st_size else {};effective=raw.get('respuesta') if not raw.get('acciones') and isinstance(raw.get('respuesta'),dict) else raw
                cov=out['coverage'];real.append({'canal':channel.name,'capitulo':cap.name,'escena':n,'coverage':cov,'blocking_fields_step4':out['blocking_fields_step4'],'contract_input_coverage':out['contract_input_coverage']})
                prefix=channel.name+'/'+n+': '
                check(prefix+'inactivo y13coberturas',out['active'] is False and len(out['contract_input_coverage'])==13)
                check(prefix+'sin modificar fps01',out['accion_01'].get('fps')==effective.get('fps') and out['clock_24fps']['fps']==24 if out['clock_24fps'] else not raw)
                check(prefix+'todas acciones intactas',out['accion_01'].get('acciones',[])==effective.get('acciones',[]))
                check(prefix+'puntos preservados',out['accion_01'].get('puntos',{})==effective.get('puntos',{}))
                check(prefix+'segmentos preservados',[s['source_segment'] for s in out['segments_enriched']]==[s for p in effective.get('personajes',[]) for s in p.get('segmentos',[])])
                check(prefix+'IDs y texto de mirada conservados',all(x['gaze']['mirada_id_source']==a.get('mirada_id') and x['gaze']['mirada_text_source']==a.get('mirada') for x,a in zip(out['actions_enriched'],effective.get('acciones',[]))))
                check(prefix+'guion de escena conservado',bool(out['script_scene_verbatim']))
                check(prefix+'sin inventar huesos mirada',all(x['gaze']['target_bone'] is None for x in out['actions_enriched']))
                check(prefix+'sin looks de fichas ADN',all(not {'description','descripcion','nunca_cambia','never_changes'}&set(x) for x in out['adn']['records']))
                check(prefix+'refs con hashes y orden continuo',[x['slot'] for x in out['adn']['ordered_images']]==list(range(1,len(out['adn']['ordered_images'])+1)) and all(len(x['sha256'])==64 for x in out['adn']['ordered_images']))
                check(prefix+'manifiesto faltante bloquea',out['spatial_manifest']['blocking_step4'] and out['blocked_for_step4'])
            if files:
                n=files[0].stem.split('_')[-1];byint=E.assemble(root,channel.name,1,n);byep=E.assemble(root,channel.name,cap.name.split('_',1)[1],n)
                check(channel.name+': int/ep equivalentes',byint==byep)
    check('Título numerado exacto desde mapa',E.script_scene('1. Inicio\nUno: dato\n2. Fin\nOtro', '1',[{'numero':'1','titulo':'1. Inicio'},{'numero':'2','titulo':'2. Fin'}])=='1. Inicio\nUno: dato')
    parsed=E.script_dialogues('UNO: [calmado] Texto literal.\nDOS:\n—Otra frase.',[{'id':'uno','names':['Uno']},{'id':'dos','names':['Dos']}])
    check('Diálogo inline y multilínea',len(parsed)==2 and parsed[0]['spoken_text_if_unambiguous']=='Texto literal.' and parsed[1]['speaker_id']=='dos')
    check('Acotación se conserva, no se vuelve voz',parsed[0]['stage_direction_prefix_source']=='calmado' and parsed[0]['text_source_with_stage_directions']=='[calmado] Texto literal.')
    check('TODOS los datos reales idénticos antes/después',before==digest_tree(root))
    # Todo lo que sigue se crea en un directorio temporal NUEVO del box; no toca snapshot ni capítulos213.
    T=Path(tempfile.mkdtemp(prefix='sb_v2_SOLO_PRUEBA_'));D=T/'trabajo/paso00_cadena/canal-prueba/cap01_ep-prueba';D.mkdir(parents=True)
    raises('capitulo booleano rechazado',lambda:E.resolve_chapter(E.Reader(T),'canal-prueba',True))
    check('capitulo completo explícito',E.resolve_chapter(E.Reader(T),'canal-prueba',D.name)==D)
    dup=D.parent/'cap01_ep-otro';dup.mkdir();raises('Dos cap01 no elige primero',lambda:E.resolve_chapter(E.Reader(T),'canal-prueba',1),'AMBIGUO')
    check('ep exacto desambigua',E.resolve_chapter(E.Reader(T),'canal-prueba','ep-prueba')==D)
    duplicate_ep=D.parent/'cap02_ep-prueba';duplicate_ep.mkdir();raises('ep duplicado ambiguo',lambda:E.resolve_chapter(E.Reader(T),'canal-prueba','ep-prueba'),'AMBIGUO')
    link=T/'salida';link.symlink_to('/etc',target_is_directory=True);raises('Symlink exterior bloqueado',lambda:E.Reader(T).path('salida/passwd'))
    def put(rel,obj):
        p=T/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False));return p
    rel=str(D.relative_to(T));lib='trabajo/biblioteca/canal-prueba/personajes'
    png=b'\x89PNG\r\n\x1a\nSOLO_PRUEBA_NO_RENDER';h=hashlib.sha256(png).hexdigest();im=T/lib/'uno/frente.png';im.parent.mkdir(parents=True);im.write_bytes(png)
    put(lib+'/personajes.json',{'personajes':[{'id':'actor-uno','nombre':'Uno','nunca_cambia':'NO_FILTRAR_SENTINELA','versiones':[{'forma_id':'forma-uno','estado':'aprobada','refs':['uno/frente.png'],'refs_sha256':[h]}]}]})
    put(rel+'/respuestas/base.json',{'catalogo_oficial':{'personajes':[{'id':'actor-uno','nombre':'Uno'}]},'escenas':[{'numero':'1','personajes':[{'personaje_id':'actor-uno'}]}]})
    put(rel+'/respuestas/personajes.json',{'personajes':[{'personaje_id':'actor-uno','estados':[{'escena':'1','inicio':{'forma_id':'forma-uno'},'fin':{'forma_id':'forma-uno'}}]}]})
    c={'escena':'1','fps':8,'duracion_s':2,'puntos':{'p':[1,2,3]},'personajes':[{'id':'actor-uno','version_personaje':{'description':'NO_FILTRAR_SENTINELA'},'segmentos':[{'t':[0,2],'pos':['p','p'],'rot':10}]}],
       'acciones':[{'id':'a1','actor':'actor-uno','accion':'hablar','t':[0,2],'mirada':'Uno','cita':'Texto literal','pose':'de_pie','gesto':'respira','manos':{'left':'abierta','right':'quieta'}}],
       'parametros_3d':{'colores.piel':'NO_FILTRAR_SENTINELA'},'respuesta':'NO_FILTRAR_SENTINELA'}
    put(rel+'/cubos/01/esc_1.json',c)
    o=E.assemble(T,'canal-prueba',D.name,1);serialized=json.dumps(o)
    check('Identidad textual no pasa a contexto','NO_FILTRAR_SENTINELA' not in serialized)
    check('ADN aprobado con hash verificable',o['coverage']['dna']['characters_with_verified_refs']==1)
    check('Gesto/manos intactos',o['actions_enriched'][0]['gesture_source']=='respira' and o['actions_enriched'][0]['hands_source']==c['acciones'][0]['manos'])
    check('Mirada por nombre exacto con trazabilidad',o['actions_enriched'][0]['gaze']['resolved_entity_id']=='actor-uno' and o['actions_enriched'][0]['gaze']['resolution']=='nombre_exacto_unico')
    im.write_bytes(png+b'ROTO');broken=E.assemble(T,'canal-prueba',D.name,1);check('Imagen alterada bloquea ADN',any(x['code']=='DNA_CHECKSUM_MISMATCH' for x in broken['blocking_fields_step4']))
    put(rel+'/cubos/02/scene_spatial_manifest.json',{'canal':'canal-prueba','escena':'1','TEST_ONLY':True});present=E.assemble(T,'canal-prueba',D.name,1)
    check('Manifiesto presente no se certifica físicamente',present['spatial_manifest']['status']=='presente por validar geometría' and present['spatial_manifest']['blocking_step4'])
    put(rel+'/cubos/02/esc_1_spatial_manifest.json',{'TEST_ONLY':True});amb=E.assemble(T,'canal-prueba',D.name,1)
    check('Dos manifiestos no elige primero',amb['spatial_manifest']['status']=='manifiesto ambiguo')
    ref=T/'cajas/cubo_fijo/hojas/prop_prueba.png';ref.parent.mkdir(parents=True,exist_ok=True);ref.write_bytes(png)
    seal={'id':'prop-prueba','ids_canal':['obj-prueba'],'canal':'canal-prueba','sellado':True,'imagen_ref':str(ref),'imagen_sha256':h}
    put('cajas/cubo_fijo/objetos_pj/prop_prueba.json',seal)
    assets=E.other_asset_refs(E.Reader(T),'canal-prueba',{}, {},[{'objeto':'obj-prueba'}])
    check('Sello lógico no finge aprobación visual',assets['coverage']['approved_with_verified_images']==0 and bool(assets['requested'][0]['images']))
    seal['hoja_aprobada']={'ruta':str(ref),'sha256':h,'aprobado_por':'SOLO_PRUEBA','cuando':'FICTICIO'}
    put('cajas/cubo_fijo/objetos_pj/prop_prueba.json',seal)
    assets=E.other_asset_refs(E.Reader(T),'canal-prueba',{}, {},[{'objeto':'obj-prueba'}])
    check('Referencia visual con prueba explícita y hash',assets['coverage']['approved_with_verified_images']==1)
    assets=E.other_asset_refs(E.Reader(T),'canal-prueba',{}, {},[{'objeto':'../../NO_ABRIR'}])
    check('Nombre inseguro de objeto se conserva sin abrir ruta',assets['requested'][0].get('entity_id_source')=='../../NO_ABRIR' and assets['coverage']['approved_with_verified_images']==0)
    empty=T/rel/'cubos/01/esc_3.json';empty.write_bytes(b'');zero=E.assemble(T,'canal-prueba',D.name,3);check('01 vacío no dispara generación',any(x['code']=='MISSING_UPSTREAM_ACTION' for x in zero['blocking_fields_step4']))
    return {'pasan':sum(t['ok'] for t in tests),'fallan':sum(not t['ok'] for t in tests),'pruebas':tests,'escenas_reales':real,'sin_red_IA_gasto':True,'datos_reales_sin_modificar':before==digest_tree(root),'casos_artificiales':'solo directorio temporal del box, no escenas reales ni salida de Argon'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--datos',required=True,type=Path);a=p.parse_args();out=run(a.datos)
    print(json.dumps(out,ensure_ascii=False,indent=2));return int(out['fallan']>0)
if __name__=='__main__':raise SystemExit(main())
