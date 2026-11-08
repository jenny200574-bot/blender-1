// n8n Code node: 00 → SELLO OBJ · marcar aprobación
// disabled: False
const ok=String(($input.first().json||{})['Decisión']||'')==='Aprobar'; const L=$('00 → SELLO OBJ · lo pintado pasa al sello (gratis)').all();
const tope=Number((L.length*0.1).toFixed(4));
return L.map(x=>({json:{...x.json, habilitar_pago:ok, ok_ricardo:ok?'n8n-ejecucion-'+$execution.id:'', tope_usd:ok?tope:0}}));