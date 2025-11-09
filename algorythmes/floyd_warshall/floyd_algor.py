from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Iterable, Set
import math

Edge = Tuple[int, int, float]  # (u, v, w)

class NegativeCycleError(Exception):
    """Se detectó un ciclo negativo alcanzable."""
    pass

def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Peso por defecto: distancia euclidiana (puedes cambiarlo si tu JSON trae 'weight')."""
    return math.hypot(x2 - x1, y2 - y1)

def build_graph_from_loader(loader, blocked_paths: Set[Tuple[int, int]]) -> Tuple[List[int], List[Edge]]:
    """
    Construye nodos y aristas desde tu JsonLoader.
    - Respeta aristas bloqueadas (pares ordenados min->max en blocked_paths).
    - Genera aristas en ambos sentidos (el enunciado dice que las vías van en ambos sentidos).
    """
    nodes: Set[int] = set()
    edges: List[Edge] = []
    find = loader.find_star_by_id

    for constellation in loader.get_constellations():
        for star in constellation["starts"]:
            u = int(star["id"])
            nodes.add(u)
            x1, y1 = star["coordenates"]["x"], star["coordenates"]["y"]

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

                # Ambas direcciones
                edges.append((u, v, w))
                edges.append((v, u, w))
                nodes.add(v)

    return sorted(nodes), edges


class FloydWarshall:
    """
    All-Pairs Shortest Paths.
    - Calcula distancias mínimas entre todos los pares.
    - Acepta pesos negativos, pero NO ciclos negativos.
    - Útil si harás muchas consultas (u->v) tras un único pre-cálculo.
    """

    def __init__(self, nodes: Iterable[int], edges: Iterable[Edge]):
        self.nodes: List[int] = list(nodes)
        self.index: Dict[int, int] = {n: i for i, n in enumerate(self.nodes)}  # idNodo -> idx matriz
        n = len(self.nodes)

        # Matrices
        self.dist: List[List[float]] = [[float("inf")] * n for _ in range(n)]
        self.next: List[List[Optional[int]]] = [[None] * n for _ in range(n)]

        # Distancias 0 en diagonal
        for i in range(n):
            self.dist[i][i] = 0.0
            self.next[i][i] = self.nodes[i]

        # Cargar aristas
        for u, v, w in edges:
            if u not in self.index or v not in self.index:
                continue
            i, j = self.index[u], self.index[v]
            if w < self.dist[i][j]:
                self.dist[i][j] = w
                self.next[i][j] = v

    def run(self) -> None:
        """Ejecuta Floyd–Warshall. Lanza NegativeCycleError si detecta ciclo negativo."""
        n = len(self.nodes)
        for k in range(n):
            for i in range(n):
                # micro-optimización: guardar referencias locales
                dik = self.dist[i][k]
                if dik == float("inf"):
                    continue
                row_i = self.dist[i]
                row_k = self.dist[k]
                next_i = self.next[i]
                next_k = self.next[k]
                for j in range(n):
                    alt = dik + row_k[j]
                    if alt < row_i[j]:
                        row_i[j] = alt
                        next_i[j] = next_i[k]  # primer salto i->... para ir hacia j

        # Detección de ciclos negativos (dist[i][i] < 0)
        for i in range(n):
            if self.dist[i][i] < 0:
                raise NegativeCycleError("Ciclo negativo detectado.")

    def distance(self, src: int, dst: int) -> float:
        """Devuelve la distancia mínima entre src y dst (o inf si no hay camino)."""
        i, j = self.index.get(src), self.index.get(dst)
        if i is None or j is None:
            return float("inf")
        return self.dist[i][j]

    def rebuild_path(self, src: int, dst: int) -> List[int]:
        """Reconstruye el camino src->dst usando la matriz next. Retorna [] si no hay camino."""
        if src not in self.index or dst not in self.index:
            return []
        i, j = self.index[src], self.index[dst]
        if self.next[i][j] is None:
            return []
        path = [src]
        while src != dst:
            src = self.next[self.index[src]][j]
            if src is None:
                return []
            path.append(src)
        return path
