// n8n Code node: 02T · validar esquema y faltantes (gratis)
// disabled: False
const out=[];
for(const item of $input.all()){
 let r;try{r=JSON.parse(String(item.json.stdout||'').trim().split('\n').pop());}catch(e){throw new Error('02T: respuesta no JSON; revisar el puente restringido');}
 if(r.ok!==true)throw new Error('02T: '+String(r.error||'respuesta no válida'));
 if(r.gasto_usd!==0||r.llamadas_pagas!==0||r.renderizado!==false||r.network_paid!==false)throw new Error('02T violó la política gratuita');
 if(typeof r.paquete_id!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(r.paquete_id)||r.paquete_id.includes('..'))throw new Error('02T: paquete_id no seguro');
 if(!Array.isArray(r.datos_faltantes)||!Number.isInteger(r.faltantes)||r.faltantes!==r.datos_faltantes.length)throw new Error('02T: faltantes sin trazabilidad');
 for(const f of r.datos_faltantes)if(!f.campo||!f.modulo_productor||!f.que_falta)throw new Error('02T: campo o productor ausente');
 out.push({json:r});
}return out;