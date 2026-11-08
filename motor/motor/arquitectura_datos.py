"""Paredes locales arbitrarias y unión de huecos rectangulares múltiples.
Sin cuarto, pared, cielo ni IDs impuestos. El exterior es geometría de la entrada.
"""
def paneles(spec):
    w,h,t=spec['width_m'],spec['height_m'],spec['thickness_m']
    if min(w,h,t)<=0:raise ValueError('Arquitectura: dimensiones no positivas')
    holes=[o['rect_m'] for o in spec['openings']]
    if any(not (0<=a<c<=w and 0<=b<d<=h) for a,b,c,d in holes):raise ValueError('Hueco fuera de pared o degenerado')
    xs=sorted({0,w}|{q for o in holes for q in [o[0],o[2]]});zs=sorted({0,h}|{q for o in holes for q in [o[1],o[3]]});out=[]
    for z0,z1 in zip(zs,zs[1:]):
        spans=[]
        for x0,x1 in zip(xs,xs[1:]):
            x,z=(x0+x1)/2,(z0+z1)/2
            if any(a<=x<=c and b<=z<=d for a,b,c,d in holes):continue
            if spans and spans[-1][1]==x0:spans[-1][1]=x1
            else:spans.append([x0,x1])
        for x0,x1 in spans:out.append({'dimensions_m':[x1-x0,t,z1-z0],'position_m':[(x0+x1)/2,0,(z0+z1)/2],'source_rect_m':[x0,z0,x1,z1]})
    return out
