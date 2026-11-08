"""Monta renders reales con rótulo BLOQUEADO; nunca genera una aprobación."""
from pathlib import Path
import sys,json
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import leer,guardar,archivar,sha
folder,reference,result=map(Path,sys.argv[1:4]);rec=leer(folder/'recibo.json');state=leer(result)
assert state['estado']=='BLOQUEADO' and rec['state']=='DIAGNOSTICO_BLOQUEADO_NO_ACEPTACION'
images=rec['images'];assert len(images)==state['coverage']['requested_shots']
font=ImageFont.truetype('DejaVuSans.ttf',11);small=ImageFont.truetype('DejaVuSans.ttf',9)
w,h,header,footer,cols=320,180,90,24,4
canvas=Image.new('RGB',(cols*w,header+((len(images)+cols-1)//cols)*(h+footer)),(24,25,29));draw=ImageDraw.Draw(canvas)
lines=['DIAGNÓSTICO REAL CPU — BLOQUEADO, NO ESCENA FINAL',f"{len(images)} imágenes reales; {rec['subject_count']}/{state['coverage']['requested_entities']} sujetos colocados. Ave sin rig/ancla y objetos sin receta NO se inventan.",'Posturas de base y luz técnica declarada. Cámara/actuación/estado del entorno NO aprobados.',f"Cotas de biblioteca autorizadas t314. Esta hoja NO cambia A={len(state['grupo_A'])} / B={len(state['grupo_B'])}."]
for i,line in enumerate(lines):draw.text((10,8+i*19),line,font=font,fill=(255,196,75) if i==0 else 'white')
for i,image in enumerate(images):
 path=folder/image['image'];assert sha(path)==image['sha256'];im=Image.open(path).convert('RGB');im.thumbnail((w,h));x=(i%cols)*w;y=header+(i//cols)*(h+footer);canvas.paste(im,(x,y));draw.text((x+5,y+h+4),f"{image['shot']} · cuadro {image['frame']} · cámara {image['camera_status']}",font=small,fill='white')
p=folder/'hoja_contacto_REAL_DIAGNOSTICO_BLOQUEADO.png';archivar(p);canvas.save(p)
ref=Image.open(reference).convert('RGB');left=Image.new('RGB',(cols*w,canvas.height),(20,20,24));ref.thumbnail((left.width,left.height-30));left.paste(ref,((left.width-ref.width)//2,30));ImageDraw.Draw(left).text((10,8),'REFERENCIA STAR — ESC6 (otra escena)',font=font,fill='white')
comparison=Image.new('RGB',(left.width+canvas.width,max(left.height,canvas.height)),(20,20,24));comparison.paste(left,(0,0));comparison.paste(canvas,(left.width,0));cp=folder/'comparacion_Star_ESC6_vs_diagnostico.png';archivar(cp);comparison.save(cp)
guardar(folder/'comparacion.json',{'reference':str(reference),'reference_sha256':sha(reference),'contact_sheet':str(p),'contact_sha256':sha(p),'comparison':str(cp),'scope':'COMPARACION_CUALITATIVA_ESCENAS_DISTINTAS_NO_EQUIVALENCIA','observations':['Star ESC6 contiene oficina/mobiliario detallado y variantes de luz.','El diagnóstico actual contiene bases ADN y entorno fuente; objetos sin receta ocultos y ave omitida.','No hay paridad visual acreditada con Star ni escena final aprobada. No procede comparar píxeles de escenas distintas.'],'blocked_shots':[i['shot'] for i in images if i['camera_status']!='pasa'],'spend_usd':0})
print(p)
