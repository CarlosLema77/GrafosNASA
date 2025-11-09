from __future__ import annotations
from typing import Iterable, Dict, List, Tuple, Optional, Deque, Set
from collections import deque, defaultdict

Edge = Tuple[int, int, float]  # (u, v, capacity)


class InvalidPathError(Exception):
    """Capacidad inválida (negativa o no numérica)."""
    pass


class MaxFlow:
    """
    Ford-Fulkerson (variante Edmonds-Karp) para flujo máximo entre source y sink.
    - BFS para encontrar caminos aumentantes (O(V·E^2)).
    - Soporta multigrafo: capacidades se acumulan si hay varias (u,v).
    - Puedes excluir aristas bloqueadas al construir edges (ver helper).
    """

    def __init__(self, nodes: Iterable[int], edges: Iterable[Edge]) -> None:
        # Lista de nodos (sin duplicados, preservando orden)
        self.nodes: List[int] = list(dict.fromkeys(nodes))

        # Capacidad residual dirigida: cap[u][v] = capacidad disponible u->v
        self.cap: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))

        for u, v, c in edges:
            if c is None:
                raise InvalidPathError(f"Capacidad None en ({u}->{v}).")
            try:
                c = float(c)
            except (TypeError, ValueError):
                raise InvalidPathError(f"Capacidad no numérica en ({u}->{v}): {c}")
            if c < 0:
                raise InvalidPathError(f"Capacidad negativa en ({u}->{v}): {c}")

            self.cap[u][v] += c  # acumula si hay múltiples aristas

        # Asegura que existan entradas para todos los nodos (aunque no tengan salidas)
        for n in self.nodes:
            _ = self.cap[n]

    def _bfs(self, s: int, t: int, parent: Dict[int, Optional[int]]) -> float:
        """BFS en la red residual. Devuelve el cuello de botella del camino aumentante (0 si no hay)."""
        for n in self.nodes:
            parent[n] = None
        parent[s] = -1  # marca origen

        q: Deque[int] = deque([s])
        flow_to: Dict[int, float] = {s: float("inf")}

        EPS = 1e-12
        while q:
            u = q.popleft()
            for v, cap_uv in self.cap[u].items():
                if cap_uv > EPS and parent[v] is None:  # aún no visitado y hay capacidad
                    parent[v] = u
                    flow_to[v] = min(flow_to[u], cap_uv)
                    if v == t:
                        return flow_to[v]
                    q.append(v)
        return 0.0

    def run(self, source: int, sink: int) -> Tuple[float, Dict[int, Dict[int, float]], Set[int]]:
        """
        Ejecuta Edmonds-Karp desde 'source' a 'sink'.
        :return:
          - max_flow: valor de flujo máximo
          - residual: red residual final (self.cap)
          - S: conjunto de nodos alcanzables desde 'source' en la residual (define corte mínimo S, V−S)
        """
        if source not in self.nodes or sink not in self.nodes:
            raise ValueError("source o sink no están en los nodos del grafo.")

        parent: Dict[int, Optional[int]] = {}
        max_flow = 0.0

        while True:
            aug = self._bfs(source, sink, parent)
            if aug <= 1e-12:
                break  # no hay más caminos aumentantes

            max_flow += aug

            # Retrocede por 'parent' y actualiza la residual
            v = sink
            while v != source:
                u = parent[v]
                # hacia adelante disminuye
                self.cap[u][v] -= aug
                # hacia atrás aumenta
                self.cap[v][u] += aug
                v = u

        S = self._reachable_in_residual(source)
        return max_flow, self.cap, S

    def _reachable_in_residual(self, s: int) -> Set[int]:
        """Nodos alcanzables desde s en la residual (cap > 0). Útil para obtener el corte mínimo (S, V−S)."""
        EPS = 1e-12
        seen: Set[int] = set([s])
        q: Deque[int] = deque([s])

        while q:
            u = q.popleft()
            for v, cap_uv in self.cap[u].items():
                if cap_uv > EPS and v not in seen:
                    seen.add(v)
                    q.append(v)
        return seen

    # ----------------- Helpers de integración con tu proyecto -----------------

    @staticmethod
    def build_flow_graph_from_loader(
        loader,
        blocked_paths: Set[Tuple[int, int]],
        capacity_key: str = "capacity",
        default_capacity: float = 1.0,
        undirected: bool = True,
    ) -> Tuple[List[int], List[Edge]]:
        """
        Construye nodos y aristas DIRIGIDAS con capacidad desde el JsonLoader.
        - Respeta caminos bloqueados (pares normalizados: tuple(sorted((u,v)))).
        - Si el link trae `capacity_key`, lo usa; si no, usa `default_capacity`.
        - Si `undirected` es True, añade (u->v) y (v->u) con la misma capacidad.
        """
        nodes_set: Set[int] = set()
        edges: List[Edge] = []

        find = loader.find_star_by_id
        for constellation in loader.get_constellations():
            for star in constellation["starts"]:
                u = int(star["id"])
                nodes_set.add(u)

                for link in star.get("linkedTo", []):
                    v = int(link["starId"])
                    if find(v) is None:
                        continue

                    pair = tuple(sorted((u, v)))
                    if pair in blocked_paths:
                        continue

                    cap = float(link.get(capacity_key, default_capacity))
                    if cap < 0:
                        raise InvalidPathError(f"Capacidad negativa en link {u}->{v}: {cap}")

                    edges.append((u, v, cap))
                    if undirected:
                        edges.append((v, u, cap))
                    nodes_set.add(v)

        return sorted(nodes_set), edges
