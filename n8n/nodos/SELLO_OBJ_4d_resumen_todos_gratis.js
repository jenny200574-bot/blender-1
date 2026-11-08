// n8n Code node: SELLO OBJ · 4d resumen (todos, gratis)
// disabled: False
const L=$input.all().map(x=>x.json);
return [{json:{sellados:L.length, ids:L.map(x=>x.id), versiones:L.map(x=>x.id+' v'+x.version), ver_fails:L.flatMap(x=>(x.ver_fails||[]).map(f=>x.id+': '+f))}}];