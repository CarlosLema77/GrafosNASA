# src/core/planner.py
from __future__ import annotations
from dataclasses import replace
from typing import List, Dict, Tuple, Set, Optional
import random
import copy

from src.core.graph_utils import build_graph_from_loader
from src.core.hypergiants import (
    is_hypergiant,
    collect_hypergiants,
    apply_hypergiant_effects,
)

class MaxRoutePlanner:
    """
    Planificador de ruta máxima:
    - No toca el burro real.
    - Prioriza alcanzar hipergigantes y saltar a galaxias no visitadas.
    - Salto con costo 0 ly y buff sugerido (+50% energía, duplica pasto) en el CLON.
    - Devuelve estructura de recap para UI.
    """

    def __init__(self, loader):
        self.loader = loader
        self._star_index: Dict[int, dict] = {}
        for const in self.loader.data.get("constellations", []):
            for s in const.get("starts", []):
                self._star_index[int(s["id"])] = s

        self._hgs_by_galaxy: Dict[Optional[int], List[int]] = {}
        for hg in collect_hypergiants(self.loader):
            self._hgs_by_galaxy.setdefault(hg.galaxy_id, []).append(hg.star_id)

    def plan_max_route(
        self,
        start_star_id: int,
        real_burro,
        blocked_paths: Set[Tuple[int, int]],
        rng: Optional[random.Random] = None,
        max_hops: int = 10_000,
    ) -> Dict:
        if rng is None:
            rng = random

        # 1) Clon del burro
        try:
            burro = copy.deepcopy(real_burro)
        except Exception:
            burro = replace(real_burro)

        # 2) Grafo respetando bloqueos
        nodes, edges = build_graph_from_loader(self.loader, blocked_paths)
        adj: Dict[int, List[Tuple[int, float]]] = {}
        for u, v, w in edges:
            adj.setdefault(u, []).append((v, float(w)))

        # 3) Estado
        current = int(start_star_id)
        if current not in self._star_index:
            raise ValueError(f"start_star_id {current} no existe.")

        visited_stars: Set[int] = set()
        visited_galaxies: Set[Optional[int]] = set()

        current_galaxy = self._galaxy_of(current)
        visited_galaxies.add(current_galaxy)
        visited_stars.add(current)

        # Estructuras de salida
        itinerary: List[Dict] = []
        recap_rows: List[Dict] = []
        segment = {
            "galaxy_id": current_galaxy,
            "entry_star": current,
            "path": [current],
            "exit_hypergiant": None,
            "jump_to": None,
        }

        hops = 0
        while hops < max_hops:
            hops += 1

            next_star = self._choose_next_in_galaxy(
                current=current,
                current_galaxy=current_galaxy,
                adj=adj,
                visited_stars=visited_stars,
                burro=burro
            )

            if next_star is None:
                if is_hypergiant(self._star_index[current]):
                    jump_info = self._try_hyperjump(rng, current_galaxy, visited_galaxies)
                    if not jump_info:
                        itinerary.append(segment)
                        break

                    before = self._snapshot(burro)
                    apply_hypergiant_effects(burro)
                    after = self._snapshot(burro)
                    recap_rows.append(self._mk_recap_row_buff(
                        galaxy_id=current_galaxy,
                        from_star=current,
                        to_star=None,
                        note="Buff de hipergigante aplicado (siguiente tramo)",
                        before=before, after=after
                    ))

                    segment["exit_hypergiant"] = current
                    segment["jump_to"] = {"galaxy_id": jump_info["dest_galaxy"], "landing_hg": jump_info["landing_hg"]}
                    itinerary.append(segment)

                    current_galaxy = jump_info["dest_galaxy"]
                    visited_galaxies.add(current_galaxy)
                    current = jump_info["landing_hg"]
                    if current not in visited_stars:
                        visited_stars.add(current)
                    segment = {
                        "galaxy_id": current_galaxy,
                        "entry_star": current,
                        "path": [current],
                        "exit_hypergiant": None,
                        "jump_to": None,
                    }
                    continue

                itinerary.append(segment)
                break

            dist = self._edge_distance(adj, current, next_star)
            if dist is None:
                itinerary.append(segment)
                break

            if burro.vida_restante <= 0 or (burro.vida_restante - dist) < 0:
                itinerary.append(segment)
                break

            before = self._snapshot(burro)
            burro.viajar(dist)
            after = self._snapshot(burro)

            recap_rows.append(self._mk_recap_row_move(
                galaxy_id=current_galaxy,
                from_star=current,
                to_star=next_star,
                distance=dist,
                before=before, after=after
            ))

            current = next_star
            visited_stars.add(current)
            segment["path"].append(current)

            if is_hypergiant(self._star_index[current]):
                jump_info = self._try_hyperjump(rng, current_galaxy, visited_galaxies)
                if jump_info:
                    before = self._snapshot(burro)
                    apply_hypergiant_effects(burro)
                    after = self._snapshot(burro)
                    recap_rows.append(self._mk_recap_row_buff(
                        galaxy_id=current_galaxy,
                        from_star=current,
                        to_star=None,
                        note="Buff de hipergigante aplicado (siguiente tramo)",
                        before=before, after=after
                    ))

                    segment["exit_hypergiant"] = current
                    segment["jump_to"] = {"galaxy_id": jump_info["dest_galaxy"], "landing_hg": jump_info["landing_hg"]}
                    itinerary.append(segment)

                    current_galaxy = jump_info["dest_galaxy"]
                    visited_galaxies.add(current_galaxy)
                    current = jump_info["landing_hg"]
                    if current not in visited_stars:
                        visited_stars.add(current)
                    segment = {
                        "galaxy_id": current_galaxy,
                        "entry_star": current,
                        "path": [current],
                        "exit_hypergiant": None,
                        "jump_to": None,
                    }

        if itinerary and itinerary[-1] is not segment:
            itinerary.append(segment)
        elif segment["path"]:
            itinerary.append(segment)

        return {
            "per_galaxy": itinerary,
            "visited_stars": [sid for seg in itinerary for sid in seg["path"]],
            "visited_galaxies": list(visited_galaxies),
            "life_left_ly": float(burro.vida_restante),
            "sim_burro": {
                "energia": float(burro.energia),
                "pasto_kg": float(burro.pasto_kg),
                "edad_actual": float(burro.edad_actual),
                "vida_restante": float(burro.vida_restante),
            },
            "recap": recap_rows
        }

    # ---------------- utilitarios & helpers ----------------

    def _choose_next_in_galaxy(self, current, current_galaxy, adj, visited_stars, burro) -> Optional[int]:
        neighbors = adj.get(current, [])
        candidates: List[Tuple[float, int, bool]] = []
        for v, d in neighbors:
            if v in visited_stars:
                continue
            if self._galaxy_of(v) != current_galaxy:
                continue
            if d > burro.vida_restante:
                continue
            star = self._star_index.get(v)
            if not star:
                continue
            candidates.append((d, v, is_hypergiant(star)))

        if not candidates:
            return None

        hgs = [c for c in candidates if c[2]]
        if hgs:
            hgs.sort(key=lambda x: x[0])
            return hgs[0][1]

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _try_hyperjump(self, rng, current_galaxy, visited_galaxies) -> Optional[Dict]:
        candidates = [
            gid for gid, stars in self._hgs_by_galaxy.items()
            if gid != current_galaxy and gid not in visited_galaxies and len(stars) > 0
        ]
        if not candidates:
            return None
        dest_galaxy = rng.choice(candidates)
        landing_list = self._hgs_by_galaxy.get(dest_galaxy, [])
        if not landing_list:
            return None
        landing_hg = rng.choice(landing_list)
        return {"dest_galaxy": dest_galaxy, "landing_hg": landing_hg}

    def _galaxy_of(self, star_id: int) -> Optional[int]:
        s = self._star_index.get(star_id)
        return s.get("galaxy_id") if s else None

    def _edge_distance(self, adj, u, v) -> Optional[float]:
        for w, d in adj.get(u, []):
            if w == v:
                return d
        return None

    # ----- recap helpers -----

    def _snapshot(self, burro):
        return {
            "energia": float(burro.energia),
            "pasto_kg": float(burro.pasto_kg),
            "vida": float(burro.vida_restante),
            "edad": float(burro.edad_actual),
        }

    def _mk_recap_row_move(self, galaxy_id, from_star, to_star, distance, before, after):
        to_info = self._star_index.get(to_star, {})
        lab = to_info.get("label", f"Star {to_star}")
        is_hg = bool(to_info.get("hypergiant", False))
        return {
            "galaxy_id": galaxy_id,
            "paso": "tramo",
            "estrella": lab,
            "es_hipergigante": is_hg,
            "detalle": f"Llegó a {lab} (−vida {distance:.1f} ly)",
            "delta_energia": after["energia"] - before["energia"],
            "delta_pasto": after["pasto_kg"] - before["pasto_kg"],
            "delta_vida": after["vida"] - before["vida"],
        }

    def _mk_recap_row_buff(self, galaxy_id, from_star, to_star, note, before, after):
        from_info = self._star_index.get(from_star, {})
        lab = from_info.get("label", f"Star {from_star}")
        return {
            "galaxy_id": galaxy_id,
            "paso": "buff",
            "estrella": lab,
            "es_hipergigante": True,
            "detalle": f"{lab}: {note}",
            "delta_energia": after["energia"] - before["energia"],
            "delta_pasto": after["pasto_kg"] - before["pasto_kg"],
            "delta_vida": after["vida"] - before["vida"],
        }
