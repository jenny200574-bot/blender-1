// n8n Code node: PUENTE · PJ+voz → CUBO
// disabled: False
// PUENTE · crear PJ+voz → CUBO (real): arma registro para disco cajas/cubo_fijo/personajes/<id>.json
// Sin ids por defecto: solo el PJ creado (+ ids_pedidos si llegan). El registro trae canal, imágenes y voz_adn del perfil.
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const j=$input.first().json;
const id=String(j.pj_id||'').toLowerCase().replace(/[^a-z0-9_-]/g,'_');
if(!id) throw new Error('PUENTE PJ: falta pj_id (viene de crear PJ)');
const ids=[...new Set([id,...(j.ids_pedidos||[])].filter(Boolean))];
const reg={id,clase:'personaje',nombre:j.nombre||null,canal:j.canal||null,imagenes:j.imagenes||[],descripcion:(j.adn_personaje||{}).descripcion_visual||null,
  nunca_cambia:(j.adn_personaje||{}).nunca_cambia||null,origen_flujo:'crear_pj_voz',sello_hash_perfil:j.sello_hash||null,voz_motor:j.motor||null,voz_adn:j.voz_adn||null,
  prompt_modulo_pj:j.prompt||null,sellado:false,nota:'ADN real vía cubo_fijo extraer (Maestro Ako 02: FASE 1 hoja + FASE 2 ADN, cotizado, PAGO CERRADO); altura solo Blender'};
return [{json:{...j, ids_pedidos:ids, registro_b64:b64u(reg), desde:'crear_pj_voz'}}];
