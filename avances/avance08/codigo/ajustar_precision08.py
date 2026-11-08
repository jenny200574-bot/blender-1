from pathlib import Path
r=Path("/opt/myia-motor-v9/avance08_20261107")
p=r/"entrega/codigo/fisica_final_offset_publico_prueba08.py"
s=(r/"respaldos/fisica_final_antes_avance_float32.py").read_text()
old="                count+=1;origin=hit[0]+ray*1e-7"
new="""                count+=1
                # Numeric ray-origin progress only; physical tolerances unchanged.
                advance=max(1e-7,max(1.0,*(abs(v) for v in hit[0]))*(2**-20))
                if advance>rules['penetration_tolerance_m']/16:
                    raise ValueError('PRECISION_FLOAT32_INSUFICIENTE para tolerancia suministrada')
                origin=hit[0]+ray*advance"""
assert s.count(old)==1
s=s.replace(old,new)
assert s.count("names=rules['colliders'];trees={};verts={}")==1
s=s.replace("names=rules['colliders'];trees={};verts={}","names=rules['colliders'];trees={};verts={};surface_probes={}")
needle="            obj=objects[name].evaluated_get(dg);mesh=obj.to_mesh();vs=[obj.matrix_world@v.co for v in mesh.vertices];fs=[list(p.vertices) for p in mesh.polygons];trees[name]=BVHTree.FromPolygons(vs,fs);verts[name]=vs;obj.to_mesh_clear()"
replacement="""            obj=objects[name].evaluated_get(dg);mesh=obj.to_mesh();vs=[obj.matrix_world@v.co for v in mesh.vertices];fs=[list(p.vertices) for p in mesh.polygons]
            trees[name]=BVHTree.FromPolygons(vs,fs);verts[name]=vs
            # Evaluated triangle centroids and unique edge midpoints lie ON the
            # supplied surface; no invented geometry or relaxed penetration limit.
            # Vertices alone miss coaxial/interlocked solid penetration.
            mesh.calc_loop_triangles();triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
            edges={tuple(sorted((a,b))) for tri in triangles for a,b in zip(tri,tri[1:]+tri[:1])}
            surface_probes[name]=vs+[sum((vs[i] for i in t),Vector())/3 for t in triangles]+[(vs[a]+vs[b])/2 for a,b in sorted(edges)]
            obj.to_mesh_clear()"""
assert s.count(needle)==1;s=s.replace(needle,replacement)
assert s.count("for v in verts[source]:")==1;s=s.replace("for v in verts[source]:","for v in surface_probes[source]:")
p.write_text(s)
print("Scale-aware candidate only; fail closed at inadequate float32 precision")
