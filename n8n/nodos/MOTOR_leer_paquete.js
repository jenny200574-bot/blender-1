// n8n Code node: MOTOR · leer paquete
// disabled: True
// Fase 4 (6-nov-2026): lee la respuesta de «MOTOR · preparar entrada». US$0.
const it=$input.first();const txt=String(it.json.stdout||'').trim().split('\n').pop();let r;
try{r=JSON.parse(txt);}catch(e){throw new Error('preparar entrada no devolvió JSON. stdout: '+String(it.json.stdout||'').slice(0,300)+' | stderr: '+String(it.json.stderr||'').slice(0,300));}
if(!r.ok) throw new Error('preparar entrada: '+r.error);
if(r.llamadas_pagas||r.gasto_usd) throw new Error('preparar entrada no debía gastar');
return [{json:{modulo:'MOTOR · preparar entrada',...r,aviso:r.apto_previa?(r.camara_sb?'':'Sin cámara del SB: el motor usará cámara automática (ver faltantes.json)'):'El paquete no pasa ni para previa: el motor no armará; ver faltantes.json'}}];