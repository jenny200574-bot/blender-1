// n8n Code node: SELLO OBJ · 1b armar pedido (gratis)
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const e=$input.item.json;
if(!e.canal||!e.id) throw new Error('Falta canal o id (no hay ejemplo fijo: vienen del formulario o de la lista del paso 00)');
const clase=['objeto','poder','escenario'].includes(e.clase)?e.clase:'objeto';
const ped={id:String(e.id),canal:String(e.canal),clase}; if(e.imagen_ref) ped.imagenes=[String(e.imagen_ref)];
return {json:{...e, clase, extraer_b64:'b64.'+b64u(ped)}};