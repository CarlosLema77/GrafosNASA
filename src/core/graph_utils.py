import math

def euclidean_distance(star_a, star_b):
    """Calcula la distancia euclidiana entre dos estrellas."""
    xa, ya = star_a["coordenates"]["x"], star_a["coordenates"]["y"]
    xb, yb = star_b["coordenates"]["x"], star_b["coordenates"]["y"]
    return math.sqrt((xa - xb)**2 + (ya - yb)**2)

def build_graph_from_loader(loader, blocked_paths):
    """
    Construye el grafo global con aristas bidireccionales,
    respetando los bloqueos y las conexiones reales del JSON.
    """
    nodes, edges = set(), []
    seen_edges = set()

    for constellation in loader.data["constellations"]:
        for star in constellation["starts"]:
            sid = int(star["id"])
            nodes.add(sid)

            for link in star.get("linkedTo", []):
                target_id = int(link["starId"])
                if (sid, target_id) in blocked_paths or (target_id, sid) in blocked_paths:
                    continue

                dist = float(link.get("distance", 1.0))
                edge_key = tuple(sorted((sid, target_id)))

                # Solo agregar si no existe todavía (para evitar duplicados)
                if edge_key not in seen_edges:
                    edges.append((sid, target_id, dist))
                    edges.append((target_id, sid, dist))  # conexión inversa
                    seen_edges.add(edge_key)

    return list(nodes), edges



def get_path_edges(path):
    """Convierte una lista de nodos en pares ordenados (aristas)."""
    return [tuple(sorted((path[i], path[i+1]))) for i in range(len(path)-1)]

