"""Silhuetas y vistas de hojas aprobadas. CPU, sin identidades codificadas.
No genera un personaje distinto: conserva píxeles y hash de la referencia.
La reconstrucción por silueta NO acredita por sí sola relieve facial ni ropa separada.
"""
import json,sys,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

def extraer(path,policy):
    im=np.asarray(Image.open(path).convert('RGB'),dtype=float)
    # Fondo mayoritario por fila; ruido estimado con MAD, no paletas por personaje.
    bg=[]
    for row in im:
        chroma=np.ptp(row,axis=1);grey=row[chroma<=np.quantile(chroma,policy['background_quantile'])];levels=(grey.mean(axis=1)/policy['background_bin_pixels']).astype(int);mode=np.argmax(np.bincount(levels));bg.append(np.median(grey[levels==mode],axis=0))
    bg=np.asarray(bg)[:,None,:];distance=np.linalg.norm(im-bg,axis=2)
    noise=distance[distance<=np.quantile(distance,policy['background_quantile'])];med=np.median(noise);mad=np.median(np.abs(noise-med));threshold=med+policy['background_mad_multiplier']*max(mad,1)
    chroma=np.ptp(im,axis=2);noise_chroma=chroma[chroma<=np.quantile(chroma,policy['background_quantile'])];cm=np.median(noise_chroma);ct=cm+policy['background_mad_multiplier']*max(1,np.median(np.abs(noise_chroma-cm)));mask=chroma>ct
    mask=ndimage.binary_closing(mask,iterations=policy['closing_pixels'])
    mask=ndimage.binary_fill_holes(mask)
    if policy.get('view_boxes_px'):
        views=[]
        for role in ['front','side','back']:
            bx0,by0,bx1,by1=policy['view_boxes_px'][role];m=mask[by0:by1,bx0:bx1];ys,xs=np.nonzero(m)
            if not len(xs):raise ValueError('Máscara vacía en '+role)
            x0,x1=int(xs.min()),int(xs.max())+1;y0,y1=int(ys.min()),int(ys.max())+1;m=m[y0:y1,x0:x1]
            views.append({'box':[bx0+x0,by0+y0,bx0+x1,by0+y1],'height':y1-y0,'width':x1-x0,'area':int(m.sum()),'mask':m,'image':im[by0+y0:by0+y1,bx0+x0:bx0+x1].astype(np.uint8)})
        return views,{'method':'recortes anotados de hoja aprobada + máscara cromática CPU; no inferencia de medidas ocultas','selected':[{k:v for k,v in x.items() if k not in ('mask','image')} for x in views],'policy_source':policy['source']}
    labels,n=ndimage.label(mask);slices=ndimage.find_objects(labels)
    components=[]
    for i,sl in enumerate(slices):
        if sl is None:continue
        y,x=sl;h=y.stop-y.start;w=x.stop-x.start
        if h<policy['minimum_component_height_fraction']*im.shape[0]:continue
        area=int(np.sum(labels[sl]==i+1));components.append({'box':[x.start,y.start,x.stop,y.stop],'height':h,'width':w,'area':area,'label':i+1})
    candidates=sorted(components,key=lambda c:c['height'],reverse=True)[:policy['full_body_views']]
    if len(candidates)!=policy['full_body_views']:raise ValueError('ADN imagen: no se aíslan vistas completas; '+str({'threshold':threshold,'components':components}))
    candidates.sort(key=lambda c:c['box'][0])
    views=[]
    for c in candidates:
        x0,y0,x1,y1=c['box'];m=labels[y0:y1,x0:x1]==c['label'];score=np.sum(m & m[:,::-1])/max(1,np.sum(m | m[:,::-1]));views.append(dict(c,mask=m,image=im[y0:y1,x0:x1].astype(np.uint8),mirror_iou=float(score)))
    # La hoja debe declarar orden; sin él no adjudicar frente/perfil por un nombre.
    order=policy.get('view_order')
    if order is None:raise ValueError('ADN imagen: falta orden de vistas certificado o detector de poses aprobado')
    if order=='front_then_back_or_side':
        # El frente es el primer cuerpo completo del formato de hoja declarado.
        sides=views[1:];profile=min(sides,key=lambda v:v['mirror_iou']);back=next(v for v in sides if v is not profile)
        views=[views[0],profile,back]
    else:
        if sorted(order)!=['back','front','side']:raise ValueError('Orden de vistas inválido')
        views=[views[order.index(k)] for k in ['front','side','back']]
    return views,{'method':'row-median / MAD / connected-components','threshold_rgb_distance':float(threshold),'candidates':components,'selected':[ {k:v for k,v in x.items() if k not in ('mask','image')} for x in views]}

def main():
    request=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);receipts=[]
    for record in request['references']:
        views,receipt=extraer(record['path'],record['policy']);receipt.update(entity=record['entity'],source_sha256=record['sha256']);dest=out/record['sha256'];dest.mkdir(exist_ok=True)
        for name,v in zip(['front','side','back'],views):
            Image.fromarray(v['image']).save(dest/(name+'.png'));Image.fromarray((v['mask']*255).astype(np.uint8)).save(dest/(name+'_mask.png'))
        (dest/'recibo.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));receipts.append(receipt)
    (out/'recibos.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
