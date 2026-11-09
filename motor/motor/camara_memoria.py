"""Memoria etapa 11 cámara: purga de mallas evaluadas, compactación de cachés y diagnóstico."""
import gc
import resource


def rss_mb():
    try:
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except Exception:
        return None


def compactar_puntos(puntos, maxn):
    if not puntos or len(puntos) <= maxn:
        return puntos
    paso = max(1, (len(puntos) + maxn - 1) // maxn)
    return puntos[::paso][:maxn]


def objeto_animado(o):
    ad = getattr(o, 'animation_data', None)
    if not ad:
        return False
    return bool(ad.action or ad.nla_tracks)


def purga_mallas_huérfanas(bpy):
    eliminados = 0
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
            eliminados += 1
    return eliminados


def diagnostico_meshes(bpy):
    meshes = list(bpy.data.meshes)
    return {
        'rss_mb': rss_mb(),
        'meshes_total': len(meshes),
        'meshes_sin_usuarios': sum(1 for m in meshes if m.users == 0),
    }


def es_bvh_compartido_estatico(bv, estatico_slot):
    """True si bv es el mismo wrapper que el BVH estático de escenario (no invalidar al evictar ENVC)."""
    return (
        bv is not None
        and estatico_slot is not None
        and len(estatico_slot) >= 1
        and bv is estatico_slot[0]
    )


def descartar_bvh(bv, estatico_slot=None):
    """Obsoleto a propósito: no mutar _BV in-place (del .t rompe referencias compartidas en ENVC)."""
    return


def evictar_entrada_bvh(caja, clave, estatico_slot=None):
    """Quita una entrada de caché sin tocar el wrapper si es el BVH estático compartido."""
    return caja.pop(clave, None)


def purgar_caches_bvh(entorno, otros, estatico=None):
    (entorno or {}).clear()
    (otros or {}).clear()
    if estatico is not None and len(estatico) >= 2:
        estatico[0] = None
        estatico[1] = None


def ciclo_purga_post_toma(bpy, entorno, otros, estatico=None):
    purgar_caches_bvh(entorno, otros, estatico)
    purga_mallas_huérfanas(bpy)
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    gc.collect()
    return diagnostico_meshes(bpy)
