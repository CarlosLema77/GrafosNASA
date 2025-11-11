# src/core/hypergiants.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Iterable

# ---------------------------------------------------------------------------
#  Hipergigantes – utilidades de dominio
#  - Se detectan por el flag JSON:  "hypergiant": true
#  - Reglas del PDF:
#       • Máximo 2 por galaxia.
#       • Permiten "saltar" a otra galaxia (elige el científico el destino).
#       • Al pasar por una hipergigante:
#             +50% de la burroenergía actual (cap 100%)
#             duplica el pasto en bodega
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Hypergiant:
    star_id: int
    label: str
    galaxy_id: Optional[int]  # puede venir None si no está en el JSON
    # puedes guardar más campos si quieres mostrarlos en la UI


# ----- Detección & validación ------------------------------------------------

def is_hypergiant(star: dict) -> bool:
    """True si la estrella del JSON está marcada como hipergigante."""
    return bool(star.get("hypergiant", False))


def collect_hypergiants(loader) -> List[Hypergiant]:
    """
    Escanea el JSON cargado por el JsonLoader y regresa todas
    las hipergigantes como objetos Hypergiant.
    """
    result: List[Hypergiant] = []
    for const in loader.data.get("constellations", []):
        for s in const.get("starts", []):
            if is_hypergiant(s):
                result.append(
                    Hypergiant(
                        star_id=int(s["id"]),
                        label=str(s.get("label", s["id"])),
                        galaxy_id=s.get("galaxy_id"),
                    )
                )
    return result


def validate_by_galaxy(hgs: Iterable[Hypergiant]) -> Dict[Optional[int], List[Hypergiant]]:
    """
    Agrupa por galaxy_id y sirve para validar que no haya más de 2
    hipergigantes por galaxia (regresa el índice por galaxia).
    """
    by_galaxy: Dict[Optional[int], List[Hypergiant]] = {}
    for hg in hgs:
        by_galaxy.setdefault(hg.galaxy_id, []).append(hg)
    return by_galaxy


def check_rule_max_two_per_galaxy(hgs: Iterable[Hypergiant]) -> List[str]:
    """
    Devuelve una lista de advertencias (strings) si alguna galaxia
    excede el máximo de 2 hipergigantes.
    """
    warnings: List[str] = []
    grouped = validate_by_galaxy(hgs)
    for gid, items in grouped.items():
        if len(items) > 2:
            names = ", ".join(f"{i.label}#{i.star_id}" for i in items)
            warnings.append(
                f"[Advertencia] Galaxia {gid} tiene {len(items)} hipergigantes (>2): {names}"
            )
    return warnings


# ----- Efecto de pasar por una hipergigante ----------------------------------

def apply_hypergiant_effects(burro) -> None:
    """
    Aplica los efectos cuando el burro llega a una hipergigante:
      - +50% de su energía ACTUAL (cap 100)
      - Duplica el pasto en bodega
    """
    # +50% de lo que tenga actualmente
    burro.energia = min(100.0, burro.energia + 0.5 * burro.energia)
    burro.pasto_kg *= 2.0


# ----- Listado de destinos para el salto -------------------------------------

def list_jump_destinations(
    loader,
    current_star_id: int,
    current_galaxy_id: Optional[int],
) -> List[Tuple[int, str, Optional[int]]]:
    """
    Devuelve (star_id, label, galaxy_id) de posibles destinos de salto.
    Por defecto lista **todas** las estrellas en galaxias DISTINTAS
    a la actual (no limita a dos galaxias; si necesitas otra regla, cámbiala
    aquí cuando integres el simulador).
    """
    options: List[Tuple[int, str, Optional[int]]] = []
    for const in loader.data.get("constellations", []):
        for s in const.get("starts", []):
            gid = s.get("galaxy_id")
            if int(s["id"]) == current_star_id:
                continue
            if gid == current_galaxy_id:
                # salto debe ir a una galaxia distinta
                continue
            options.append((int(s["id"]), str(s.get("label", s["id"])), gid))
    # ordénalo por (galaxy_id, label) para que la UI lo muestre ordenado
    options.sort(key=lambda t: (t[2], t[1]))
    return options


# ----- Helper de “saltar” (sin mover el grafo) --------------------------------

def perform_hyperjump(
    burro,
    destination_star_id: int,
    on_before_jump=None,
    on_after_jump=None,
) -> int:
    """
    Hook para el simulador/UI:
      - Llama on_before_jump() si se provee (para registrar/loggear).
      - Aplica efectos de hipergigante.
      - Retorna el ID de la estrella destino (para que el simulador
        sitúe al burro ahí y continúe el recorrido).
    Nota: no modifica el grafo; sólo devuelve el destino acordado.
    """
    if callable(on_before_jump):
        on_before_jump()

    apply_hypergiant_effects(burro)

    if callable(on_after_jump):
        on_after_jump()

    return int(destination_star_id)
