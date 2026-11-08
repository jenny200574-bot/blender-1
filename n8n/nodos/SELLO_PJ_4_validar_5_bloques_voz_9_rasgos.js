// n8n Code node: SELLO PJ · 4 validar (5 bloques + voz 9 rasgos)
// disabled: False
const j=$input.first().json; const f=[];
const a=j.adn_ako||{}; const t=String(j.adn_ako_texto||a.texto||'');
if(!t) f.push('sin ADN (Fase 2 no corrió)');
for(let n=1;n<=5;n++) if(t&&!new RegExp('^[ \\t>#*_\\-]*'+n+'[.)]','m').test(t)) f.push('falta bloque '+n+' del Maestro 02');
if(/\[GAP/.test(t)) f.push('GAP en ADN');
if(j.en_disco&&a.status&&a.status!=='PASS_SELLABLE') f.push('ADN en disco no pasa: '+(a.fails||[]).join(','));
const v=j.voz_adn; const R=['timbre','tono','ritmo','acento','idioma','edad_aparente','energia','textura','diccion'];
if(!v) f.push('voz: el perfil no tiene voz_adn'); else {
 if(v.schema!=='voz_adn/v1_universal') f.push('voz: schema');
 if(v.motor!==null) f.push('voz: motor debe ser null (universal)');
 for(const r of R) if(!String((v.rasgos||{})[r]||'').trim()) f.push('voz: falta '+r);
 if(String(v.descriptor_universal_en||'').split(',').length<4) f.push('voz: descriptor_universal_en < 4 rasgos'); }
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const sel={id:j.id,clase:'personaje',canal:j.canal}; if(j.adn_ako_texto) sel.adn_ako_texto=j.adn_ako_texto;
// hoja aprobada (inmi 2-nov-2026): solo si Ricardo la aprobó en la entrada 1; si no, la hoja nueva queda «pendiente de aprobación».
const e1=$('SELLO PJ · 1 entrada imagen de referencia').first().json; const ruta=j.hoja||e1.hoja_aprobada_ruta||'';
if(String(e1.hoja_aprobada_por||'').trim()&&String(e1.hoja_aprobada_cuando||'').trim()){ if(!ruta) f.push('hoja aprobada sin ruta'); else sel.hoja_aprobada={ruta:String(ruta),aprobado_por:String(e1.hoja_aprobada_por),cuando:String(e1.hoja_aprobada_cuando),origen:'n8n SELLO PJ (entrada 1)'}; }
const hoja_pendiente_aprobacion=(ruta&&!sel.hoja_aprobada)?String(ruta):null;
return [{json:{...j, hoja_pendiente_aprobacion, ok:f.length===0, fails:f, sellar_b64:'b64.'+b64u(sel)}}];