"""Actualizar sólo informes a partir de evidencias verificadas. Nunca declara la escena completa."""
import json,sys,re,subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import guardar,archivar,sha

def text(path,value):
 p=R/path;archivar(p);p.write_text(value)
def load(path):return json.loads((R/path).read_text())
def main():
 now=datetime.now(ZoneInfo('America/Bogota')).isoformat();result=load('evidencia/guardianes_v4_verificado/resultado.json');A=result['grupo_A'];B=result['grupo_B'];assert len(A)==27 and len(B)==26 and result['estado']=='BLOQUEADO'
 gold=load('evidencia/oro_v4_verificado/metricas_oro.json');assert gold['all_equal'] and gold['count']==23
 suite={}
 for name,path,count in [('cpu','evidencia/pruebas_cpu.json',40),('t307','evidencia/pruebas_t307.json',28),('dev2','evidencia/pruebas_dev2.json',11),('adn','evidencia/pruebas_traductor_adn.json',16),('fisica','evidencia/pruebas_puentes_fisicos.json',14)]:
  d=load(path);assert d['passed'] and not d['failures'] and not d['errors'];assert d.get('tests',d.get('run'))==count;suite[name]={'count':count,'passed':True,'source':path}
 star=load('evidencia/star_v4_verificado/regresiones.json');cat=load('evidencia/catalogo_v4_verificado/regresiones_catalogo.json');assert star['all_passed'] and len(star['checks'])==22 and cat['all_passed'] and len(cat['checks'])==82
 folders=['evidencia/traductor_v4_verificado','evidencia/otro_universo_v4_verificado'];man=[load(f+'/worker_manifiesto.json') for f in folders];rr=[load(f+'/resultado.json') for f in folders];assert man[0]['code']==man[1]['code'] and all(sha(R/x['path'])==x['sha256'] for x in man[0]['code']) and all(r['estado']=='COMPLETO' for r in rr)
 guardar(R/'evidencia/dos_universos_v4_verificado.json',{'same_code_and_libraries':True,'file_count':len(man[0]['code']),'matches_current_files':True,'different_entry_hashes':man[0]['entry_sha256']!=man[1]['entry_sha256'],'results':[r['estado'] for r in rr],'coverage':[r['coverage'] for r in rr],'proofs':folders,'passed':True,'spend_usd':0,'note':'Fixtures sintéticos distintos, no Guardianes ni otra escena real aprobada.'})
 pat=r'guardian|kael|piquito|spark|valentina|don.caos|pintor|\beco\b|novia|prision_octogonal|ch-[a-z0-9_-]+|cn-[a-z0-9_-]+|gdc-[a-z0-9_-]+|/workspace/|/opt/myia|/home/box|217[.]76|32soe7oh2f1gtf'
 cmd=['rg','--line-number','--ignore-case',pat,'motor/','--glob','*.py','--glob','*.json'];p=subprocess.run(cmd,cwd=R,capture_output=True,text=True);assert p.returncode==1 and not p.stdout
 guardar(R/'evidencia/barrido_valores_fijos_v4_verificado.json',{'command':cmd,'returncode':p.returncode,'matches':[],'passed':True,'scope':'Todo motor/ Python y JSON, incluido heredado'})
 old=load('evidencia/fuentes_originales_t307.json');checks=[dict(source=c['source'],expected=c['expected'],current=sha(c['source']),unchanged=sha(c['source'])==c['expected']) for c in old['checks']];assert len(checks)==53 and all(c['unchanged'] for c in checks);guardar(R/'evidencia/fuentes_originales_v4_verificado.json',{'checks':checks,'all_unchanged':True,'count':53})
 remote=[load('evidencia/reintento_213_adn_cierre_'+str(i)+'.json') for i in [1,2]];assert all(not x['connection_ok'] and x['timeout'] for x in remote)
 result['fecha_informe_bogota']=now;result['servidor_213']='NO_SUBIDO / dos reintentos de lectura con timeout / no probado CPU remoto';result['servidor_213_evidencias']=['evidencia/reintento_213_adn_cierre_1.json','evidencia/reintento_213_adn_cierre_2.json'];result['nota_alcance_traductor']='La construcción paramétrica se probó en fixture; la reconstrucción semántica de los seis ADN reales sigue A. No se pide a Ricardo que modele perfiles.';guardar(R/'resultado.json',result)
 for group,entries in [('A',A),('B',B)]:
  rows=['# Grupo '+group+' — '+str(len(entries))+' entradas vigentes','', 'Actualizado: '+now+' Bogotá (UTC−5).','', '| Campo | Código | Productor/módulo | Qué falta |','|---|---|---|---|']
  for e in entries:rows.append('| '+' | '.join(str(e.get(k,'')).replace('|','/').replace('\n',' ') for k in ['campo','codigo','modulo','mensaje'])+' |')
  if group=='B':rows+=['','La prosa y las siete imágenes están disponibles. Las doce entradas de cotas NO eliminan ninguna A del traductor. No se pide a Ricardo que dibuje los patrones ni se afirma que exista un exportador de medidas.','Los límites bloqueados encontrados (COM 20 m/s², articulación 600°/s, resbale 5 cm/cuadro, equilibrio 0,06 m/2 cuadros, cero saltitos) ya se cotejaron; no pedirlos de nuevo. Los tres últimos aún necesitan integración A.','Voz/labios: Omni posterior; no son bloqueos.']
  text('FALTANTES_GRUPO_'+group+'.md','\n'.join(rows)+'\n')
 text('FALTANTES.md','# Faltantes vigentes\n\nBLOQUEADO: **27 A + 26 B**. No se llegó al objetivo sólo B.\n\n- [Capacidades A](FALTANTES_GRUPO_A.md)\n- [Datos B](FALTANTES_GRUPO_B.md)\n- Detalle ejecutable: `resultado.json`.\n- Informe: `RESULTADO_FASES_0a6.md`.\n')
 clas=load('CLASIFICACION_56.json');clas['fecha_bogota']=now;clas['nota_estado_actual']='Las 56 entradas originales son historia. Diagnóstico actual: 27 A + 26 B, no sólo B; las doce faltas de cotas no sustituyen las A de geometría final.';guardar(R/'CLASIFICACION_56.json',clas)
 oldmd=(R/'CLASIFICACION_56.md').read_text();oldmd=re.sub(r'Diagnóstico actual: 28 A \+ 12 B', 'Diagnóstico actual: 27 A + 26 B',oldmd);text('CLASIFICACION_56.md',oldmd+'\n\nActualización v4: **27 A + 26 B**; consultar las listas vigentes. La tabla histórica no es el conteo actual.\n')
 inv=load('INVENTARIO_CAPACIDADES.json');inv.update(version='20261107-dev4-cpu',fecha_bogota=now,pending_A=27,pending_B=26,scene_state='BLOQUEADO',spend_usd=0)
 for c in inv['capabilities']:
  if c['id']=='caras_rasgos_ropa_ADN':c.update(state='SUPERFICIES_PARAMETRICAS_REALES_PROBADAS; RECONSTRUCCION_SEMANTICA_REAL_A',proof='evidencia/traductor_v4_verificado/verificacion_independiente.json',pending='Caras/ropa finales de seis ADN reales aún no construidas; capturar hechos y recibir perfiles no resuelve esa obligación.')
  if c['id']=='escalera_retarget_pulida':c['pending']='Contactos: puente estructurado programado; lista íntegra real falta B. Caché no validada B. Kimodo/CMU completo no certificado.'
  if c['id']=='213':c.update(proof='evidencia/reintento_213_adn_cierre_1.json; evidencia/reintento_213_adn_cierre_2.json',state='DOS_TIMEOUT; NO_SUBIDO_NO_PROBADO')
  if c['id']=='universalidad_t300':c['proof']='evidencia/barrido_valores_fijos_v4_verificado.json; evidencia/dos_universos_v4_verificado.json'
  if c['id']=='star_rot_ancla_jerarquia':c['proof']='evidencia/star_v4_verificado/regresiones.json'
 inv['capabilities'] += [{'id':'superficies_adn_medidas','state':'COMPILADOR_CPU_PROBADO_POR_ENTRADA_UNICA','proof':'evidencia/traductor_v4_verificado/resultado.json; evidencia/pruebas_traductor_adn.json','note':'Malla de cara, cobertura con espesor/aberturas, materiales y SSS; no confundir con seis identidades terminadas.'},{'id':'puentes_fisicos_estructurados','state':'CONTACTOS_Y_REGLAS_NORMALIZADOS; DATOS_REALES_B_Y_BINDING_COMPLETO_A','proof':'evidencia/pruebas_puentes_fisicos.json; evidencia/guardianes_v4_verificado/puentes_fisicos.json','note':'Hash obligatorio para programa, inventario collider explícito, negativos sin crash y sin lista vacía inventada.'},{'id':'moldes_sin_doble_escala','state':'REGRESION_BLENDER_PASADA','proof':'evidencia/star_v4_verificado/regresiones.json','note':'Archiva malla anterior, raíz escala unidad; no reemplaza armatures por props.'}];guardar(R/'INVENTARIO_CAPACIDADES.json',inv)
 guardar(R/'evidencia/resumen_pruebas_v4_verificado.json',{'suite':suite,'unit_tests':sum(v['count'] for v in suite.values()),'star':22,'catalog':82,'gold_exact':23,'two_universes':True,'fixed_values':0,'original_sources_unchanged':53,'guardianes_A':27,'guardianes_B':26,'guardianes_state':'BLOQUEADO','spend_usd':0})
 guardar(R/'evidencia/hoja_contacto_guardianes_estado.json',{'state':'NO_GENERADA','reason':'27 capacidades A aún pendientes; no renderizar una escena parcial para disfrazar la aceptación','real_frames':0,'comparison_with_Star_ESC6':'PENDIENTE','reference':'/workspace/videos_star/ENTREGA_AKO_MOTOR_FONDOS_20261107/salida/esc6/hoja_fondos_v2.png','spend_usd':0})
 text('motor_unico.off','BLOQUEADO — 27 A + 26 B. Sólo pruebas CPU locales explícitas. Sin promoción, n8n ni producción. US$0.\n')
 text('README.md','# Motor único — desarrollo CPU v4\n\n**BLOQUEADO: 27 A + 26 B; NO listo ni subido al 213.**\n\nUna entrada `entrada_escena.json` y paquete por hashes. Voz/labios: Omni después.\n\nEstado real e instrucciones: `RESULTADO_FASES_0a6.md`. Listas exactas: `FALTANTES_GRUPO_A.md`, `FALTANTES_GRUPO_B.md`. Contrato: `CONTRATO_MOTOR_UNICO.md`. Regresión del oro: `evidencia/oro_v4_verificado/metricas_oro.json`. US$0.\n')
 print('Informes estructurados actualizados: 27 A /26 B; pruebas109 +Star22 +catálogo82 +oro23.')
if __name__=='__main__':main()
