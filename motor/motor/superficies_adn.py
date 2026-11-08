"""Superficie de sección variable: cara/ropa reales, no cápsulas.
Perfiles en metros y costuras/huecos por datos. Pure Python CPU.
"""
import math

def loft(spec):
    sections=spec['sections_m'];n=spec['radial_segments'];thickness=spec['thickness_m']
    if isinstance(n,bool) or not isinstance(n,int) or n<8:raise ValueError('Resolución radial inválida')
    if len(sections)<2 or thickness<0:raise ValueError('Perfil o grosor inválido')
    if any(len(row)!=5 or any(not math.isfinite(v) for v in row) for row in sections):raise ValueError('Sección necesita z, centro_x, centro_y, radio_x y radio_y finitos')
    if any(row[3]<=thickness or row[4]<=thickness for row in sections):raise ValueError('Grosor excede radio del patrón')
    if any(b[0]<=a[0] for a,b in zip(sections,sections[1:])):raise ValueError('Perfil z no creciente')
    vertices=[];faces=[];rows=len(sections)
    for layer in range(2 if thickness else 1):
        inset=layer*thickness
        for z,cx,cy,rx,ry in sections:
            for i in range(n):
                angle=2*math.pi*i/n;vertices.append([cx+(rx-inset)*math.cos(angle),cy+(ry-inset)*math.sin(angle),z])
    cuts=spec.get('cutouts',[])
    for cut in cuts:
        if not all(k in cut for k in ['angle_start_deg','angle_end_deg','z_min_m','z_max_m','source']):raise ValueError('Hueco sin definición/fuente')
    def cutout(row,i):
        z=(sections[row][0]+sections[row+1][0])/2;angle=(i+.5)*360/n
        return any(c['z_min_m']<=z<c['z_max_m'] and c['angle_start_deg']<=angle<c['angle_end_deg'] for c in cuts)
    outer=[]
    for row in range(rows-1):
        for i in range(n):
            if cutout(row,i):continue
            a=row*n+i;b=row*n+(i+1)%n;c=b+n;d=a+n;outer.append([a,b,c,d])
    faces+=outer
    if thickness:
        offset=rows*n;faces += [[v+offset for v in reversed(face)] for face in outer]
        # Todo borde del patrón (incluidos huecos) se cierra con su canto, no con un relleno.
        edges={}
        for face in outer:
            for a,b in zip(face,face[1:]+face[:1]):
                key=tuple(sorted((a,b)));edges.setdefault(key,[]).append((a,b))
        for edge,uses in edges.items():
            if len(uses)==1:
                a,b=uses[0];faces.append([b,a,a+offset,b+offset])
    else:
        if spec['cap_bottom']:faces.append(list(reversed(range(n))))
        if spec['cap_top']:faces.append(list(range((rows-1)*n,rows*n)))
    if not vertices or not faces:raise ValueError('Perfil no construible')
    return vertices,faces
