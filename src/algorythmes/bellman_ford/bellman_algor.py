from typing import Dict, List, Tuple, Optional, Iterable, Set
import math

Edge = Tuple[int, int, float]  # (source, destination, weight)


class NegativeCycleError(Exception):
    """Se lanza cuando hay un ciclo de peso negativo alcanzable desde el origen."""
    pass


class BellmanFord:
    """
    Caminos mínimos desde un origen hacia TODOS los nodos.
    - Acepta pesos negativos.
    - Detecta ciclos negativos.
    - Útil cuando no puedes garantizar que todos los pesos sean >= 0.
    """

    def __init__(self, nodes: Iterable[int], edges: Iterable[Edge]):
        self.nodes: List[int] = list(nodes)
        self.edges: List[Edge] = list(edges)

    def run(self, source: int) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
        """
        Ejecuta Bellman-Ford desde 'source'.

        :param source: nodo origen.
        :return: (distancias, predecesores)
        :raises NegativeCycleError: si hay ciclo negativo.
        """
        # inf, no 'info'
        dist: Dict[int, float] = {n: float('inf') for n in self.nodes}
        prev: Dict[int, Optional[int]] = {n: None for n in self.nodes}

        if source not in dist:
            raise ValueError(f"Origen {source} no está en el grafo.")
        dist[source] = 0.0

        # |V| - 1 iteraciones de relajación
        for _ in range(len(self.nodes) - 1):
            changed = False
            for u, v, w in self.edges:
                if dist[u] != float('inf') and dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    changed = True
            if not changed:
                break

        # Detección de ciclo negativo alcanzable
        for u, v, w in self.edges:
            if dist[u] != float('inf') and dist[u] + w < dist[v]:
                raise NegativeCycleError("Ciclo negativo alcanzable desde el origen.")

        return dist, prev

    @staticmethod
    def rebuild_path(prev: Dict[int, Optional[int]], target: int) -> List[int]:
        """Reconstruye el camino origen→target usando el mapa de predecesores."""
        path: List[int] = []
        cur: Optional[int] = target
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path


# ---------- Helpers para integrarse con tu JSON/Canvas ----------

def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Peso por defecto: distancia euclidiana."""
    return math.hypot(x2 - x1, y2 - y1)


def build_graph_from_loader(loader, blocked_paths: Set[Tuple[int, int]]) -> Tuple[List[int], List[Edge]]:
    """
    Construye (nodes, edges) a partir del JsonLoader.
    - Respeta aristas bloqueadas: `blocked_paths` contiene pares (min_id, max_id).
    - Si el link trae 'weight', se usa; si no, distancia euclidiana.
    - Se agregan aristas en ambos sentidos (bidireccional).
    """
    nodes: Set[int] = set()
    edges: List[Edge] = []
    find = loader.find_star_by_id

    for constellation in loader.get_constellations():
        for star in constellation["starts"]:
            u = int(star["id"])
            nodes.add(u)
            x1, y1 = star["coordenates"]["x"], star["coordenates"]["y"]

            # usar .get para evitar KeyError
            for link in star.get("linkedTo", []):
                v = int(link["starId"])
                target = find(v)
                if not target:
                    continue

                pair = tuple(sorted((u, v)))
                if pair in blocked_paths:
                    continue

                x2, y2 = target["coordenates"]["x"], target["coordenates"]["y"]
                w = float(link.get("weight", euclidean_distance(x1, y1, x2, y2)))

                edges.append((u, v, w))
                edges.append((v, u, w))
                nodes.add(v)

    return sorted(nodes), edges
