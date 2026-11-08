// n8n Code node: SELLO ESTILO · PARA: pago cerrado (cotización)
// disabled: False
const j=$input.first().json;
return [{json:{para:true, donde:'SELLO ESTILO · 2 (llamada paga cerrada: habilitar_pago=false / tope_usd=0 / sin OK de Ricardo)', id:j.id, canal:j.canal,
 costo_por_llamada:j.cotizacion, total_usd_si_se_abre:j.cotizado_usd, gastado_usd:0, avisos:j.avisos,
 para_abrir:'Ricardo da OK → habilitar_pago=true, ok_ricardo=<su OK>, tope_usd ≥ total; y el ingeniero crea /opt/myia-taller-n8n/cajas/HABILITAR_PAGO_ADN (monto + desde=ISO). La llamada YA está conectada a sello_pago.py (compuerta + tope + ledger); sin la compuerta no llama a nada.'}}];