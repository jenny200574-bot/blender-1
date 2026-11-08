// n8n Code node: 00 → SELLO OBJ · lo pintado pasa al sello (gratis)
// disabled: False
// inmi 2-nov-2026 (orden Ricardo 17:33 Bogotá): lo que el paso 00 pinta (4a5 escenarios, 4b2 objetos de la historia, 4c2 objetos del lugar)
// entra a la cadena SELLO OBJ (ADN Maestro 04 escenario / 03 objeto + sello fijo). GENÉRICO: canal sale de la carpeta de la corrida.
// Escenarios: solo los que Ricardo guardó en 4a7. Pago: lo que diga «SELLO OBJ · 1 entrada» (hoy cerrado); y siempre la compuerta de sello_pago.py.
const ID=/^[a-z0-9][a-z0-9_-]{1,79}$/; let cfg={habilitar_pago:false, ok_ricardo:'', tope_usd:0};
try { for(const a of $('SELLO OBJ · 1 entrada imagen de referencia').params.assignments.assignments) if(a.name in cfg && !String(a.value).startsWith('=')) cfg[a.name]=a.value; } catch(e) {}
const out=[];
for(const it of $input.all()){ const r=it.json; let L=r.para_sello||[];
  if(r.caja==='4a7'){ const ok=new Set((r.resultados||[]).filter(x=>x.ok).flatMap(x=>[x.id_en_capitulo,x.escenario_id]).filter(Boolean));
    let P=[]; try { P=$('4a6 · leer').first().json.para_sello||[]; } catch(e) {}
    L=P.filter(x=>ok.has(x.id)); }
  const m=String(r.carpeta||'').match(/paso00_cadena\/([^/]+)\//); if(!m) continue;
  for(const x of L){ if(!ID.test(String(x.id))) continue;
    out.push({json:{canal:m[1], id:String(x.id), clase:x.clase, imagen_ref:x.imagen_ref, nombre:x.nombre||null, origen_caja:r.caja, extra:'',
      habilitar_pago:cfg.habilitar_pago===true, ok_ricardo:String(cfg.ok_ricardo||''), tope_usd:Number(cfg.tope_usd||0)}}); } }
const modo=String((($('Entradas (canal, capítulo, modo)').isExecuted ? $('Entradas (canal, capítulo, modo)').first().json : Object.fromEntries($('Entradas (canal, capítulo, modo)').params.assignments.assignments.filter(a => !String(a.value).startsWith('=')).map(a => [a.name, a.value])))).modo||'cotizar').trim().toLowerCase();
return out.map(x=>({json:{...x.json, modo_pagar:modo==='pagar'}}));