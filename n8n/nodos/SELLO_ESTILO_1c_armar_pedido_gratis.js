// n8n Code node: SELLO ESTILO · 1c armar pedido (gratis)
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const e=$('SELLO ESTILO · 1 entrada imagen de referencia').first().json; const s=J($('SELLO ESTILO · 1a fijar sello de estilo del canal (gratis)').first().json); const c=J($input.first().json);
if(!e.canal) throw new Error('Falta canal');
const L=((c.cubo||{}).estilo||[]).filter(x=>x.canal===e.canal||(x.ids_canal||[]).includes(e.canal));
if(!L.length) throw new Error('El canal no tiene entrada de estilo en el cubo: correr 1a (estilo fijar)');
const ped={id:L[0].id,canal:e.canal,clase:'estilo'}; if(e.imagen_ref) ped.imagenes=[e.imagen_ref];
return [{json:{...e, id:L[0].id, sello_estilo:{imagen:s.imagen_ruta||null, existe:!!s.imagen_existe, avisos:s.avisos||[], resumen:s.resumen||null}, extraer_b64:'b64.'+b64u(ped)}}];