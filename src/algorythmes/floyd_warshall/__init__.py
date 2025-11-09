from __future__ import annotations
from typing import Iterable,Dict, List, Tuple
import math

Edge = Tuple[int, int, float]  # (u, v, w)

class FloydWarshall:
    def __init__(self, nodes: Iterable[int], edges: Iterable[Edge]):
        """
        Prepara las matrices base del algoritmo Floyd-Warshall.
        nodes: iterable con ids de estrellas
        edges: iterable con aristas (u, v, weight)
        """
        #lista de nodos
        self.nodes: List[int] = list(nodes)

        #mapa de id-> indice en matriz
        self.index: Dict[int, int] = {n: i for i, n in enumerate(self.nodes)}  # idNodo -> idx matriz

        n = len(self.nodes)

        # matriz de distancias
        self.dist = [[float("inf")] * n for _ in range(n)]

        # matriz de seguimiento nodo para reconstruir camino
        self,next= [[float("inf")] * n for _ in range(n)]

        # distancia de un nodo a sí mismo es 0
        for i in range(n):
            self.dist[i][i] = 0.0
            self.next[i][i] = self.nodes[i]
        
        # cargar aristas del grafo 
        for u, v, w in edges:
            if u not in self.index or v not in self.index:
                continue
            i, j = self.index[u], self.index[v]

            #floyd se queda con el menor si hay duplicados
            if w < self.dist[i][j]:
                self.dist[i][j] = w
                self.next[i][j] = v