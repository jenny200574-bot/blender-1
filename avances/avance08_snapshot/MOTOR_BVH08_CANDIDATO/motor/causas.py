"""Consolidación diagnóstica por causa/contrato productor; conserva cada fila original."""
def consolidar(errors):
 truncated=any(e.get('codigo')=='JSON_TRUNCADO' for e in errors);groups={}
 for e in errors:
  if e.get('grupo')!='B':continue
  field=e['campo'];code=e.get('codigo');producer=e['modulo'];cause=e.get('causa')
  if code=='ADN_COTA_NO_DEFINIDA':cause='ADN_3D:'+field.split('/')[1];producer='ADN Maestro 03/04 / SELLO PJ'
  elif field in ['2B','motion/status'] or field.startswith('motion/respuesta_2b') or truncated and field=='motion/contacts':cause='programa_2B_integro_y_contactos';producer='2B/Argon + 01/Star'
  elif field in ['coordinates','ejes']:cause='marco_espacial';producer='01/4a2'
  elif field in ['luces','iluminacion','lighting']:cause='iluminacion_de_variante';producer='4a2/4a4 + configuración técnica'
  elif field in ['environment/live_data','environment/live_source']:cause='escenario_vivo';producer='4a4 + 01 + 4a2'
  elif field=='motion/semantic_index/approval':cause='calidad_tecnica_biblioteca';producer='Biblioteca de movimientos + 2B/revisor'
  elif field=='rules/source_parameters':cause='reglas_y_manifiesto_colision';producer='Biblioteca reglas vigentes + 4a2/manifiesto'
  cause=cause or field;key=(cause,producer)
  g=groups.setdefault(key,{'cause':cause,'producer':producer,'on_hold_ADN':code=='ADN_COTA_NO_DEFINIDA','diagnostics':[]})
  g['diagnostics'].append({'field':field,'code':code,'message':e['mensaje'],'original_producer':e['modulo']})
 rows=list(groups.values());A=[e for e in errors if e.get('grupo')=='A'];hold=[e for e in A if '/appearance/' in e['campo']]
 return {'A_diagnostic_rows':len(A),'A_on_hold_faces_clothes':len(hold),'A_other':len(A)-len(hold),'B_diagnostic_rows':sum(len(g['diagnostics']) for g in rows),'B_causes':len(rows),'B_on_hold_ADN_causes':sum(g['on_hold_ADN'] for g in rows),'B_other_causes':sum(not g['on_hold_ADN'] for g in rows),'B_on_hold_ADN_diagnostic_rows':sum(len(g['diagnostics']) for g in rows if g['on_hold_ADN']),'causes':rows,'note':'Una causa no es un campo ni una fila: se preservan todas las referencias; consolidar no resuelve el dato.'}
