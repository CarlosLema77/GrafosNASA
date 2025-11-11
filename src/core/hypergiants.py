# src/core/hypergiants.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Iterable, Callable

# =============================================================================
#  HIPERGIANTES – utilidades de dominio
# -----------------------------------------------------------------------------
#  • Detección desde el JSON vía flag:          "hypergiant": true/false
#  • Reglas del PDF:
#       - Máximo 2 por galaxia (validación utilitaria incluida).
#       - Permiten “saltar” a otra galaxia (el científico elige el destino).
#       - Al pasar por una hipergigante:
#            +50% de la BURROENERGÍA ACTUAL (cap 100%)
#            Duplica el PASTO en bodega.
#
#  Nota de integración:
#   - No modifica el grafo: el “salto” es una decisión de alto nivel
#     (simulador/UI) y este módulo solo aplica efectos y sugiere destinos.
#   - Espera que 'loader' sea algo tipo JsonLoader con .data (dict) cargado.
#   - Espera un objeto 'burro' con atributos: energia (0-100) y pasto_kg (float).
# =============================================================================


# =============================================================================
#  Modelo base
# =============================================================================

@dataclass(frozen=True)
class Hypergiant:
    """Representa una estrella hipergigante detectada en el JSON."""
    star_id: int
    label: str
    galaxy_id: Optional[int]  # Puede ser None si el JSON no lo trae


# =============================================================================
#  Detección & validación desde JSON
# =============================================================================

def is_hypergiant(star: dict) -> bool:
    """True si la estrella del JSON está marcada como hipergigante."""
    return bool(star.get("hypergiant", False))


def collect_hypergiants(loader) -> List[Hypergiant]:
    """
    Escanea el JSON del loader y regresa todas las hipergigantes como objetos Hypergiant.
    Estructura esperada (ejemplo):
      {
        "id": 42,
        "label": "KrakenGamma",
        "coordenates": { "x": 15, "y": 190 },
        "hypergiant": true,
        "galaxy_id": 1,
        ...
      }
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
    Agrupa hipergigantes por galaxy_id. Útil para reportes/validaciones en UI.
    """
    by_galaxy: Dict[Optional[int], List[Hypergiant]] = {}
    for hg in hgs:
        by_galaxy.setdefault(hg.galaxy_id, []).append(hg)
    return by_galaxy


def check_rule_max_two_per_galaxy(hgs: Iterable[Hypergiant]) -> List[str]:
    """
    Devuelve advertencias si alguna galaxia excede el máximo de 2 hipergigantes.
    (No lanza excepción: deja la decisión a la UI/Simulador).
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


# =============================================================================
#  Efectos en el Burro al tocar una hipergigante
# =============================================================================

def apply_hypergiant_effects(burro) -> None:
    """
    Aplica los efectos cuando el burro llega a una hipergigante:
      - +50% de su energía ACTUAL (cap 100).
      - Duplica el pasto en bodega.
    """
    # +50% de lo que tenga actualmente (ej: 40% → 60%; 80% → 100% por cap)
    burro.energia = min(100.0, burro.energia + 0.5 * burro.energia)
    # Duplicar pasto
    burro.pasto_kg *= 2.0


# =============================================================================
#  Listado de destinos de salto
# =============================================================================

def list_jump_destinations(
    loader,
    current_star_id: int,
    current_galaxy_id: Optional[int],
) -> List[Tuple[int, str, Optional[int]]]:
    """
    Devuelve una lista de posibles destinos de salto en forma de tuplas:
      (star_id, label, galaxy_id)
    Regla base:
      - Proponer estrellas en galaxias DISTINTAS a la actual.
    La UI podrá filtrar/ordenar y dejar elegir al científico.
    """
    options: List[Tuple[int, str, Optional[int]]] = []
    for const in loader.data.get("constellations", []):
        for s in const.get("starts", []):
            sid = int(s["id"])
            if sid == current_star_id:
                continue
            gid = s.get("galaxy_id")
            if gid == current_galaxy_id:
                # Salto intergaláctico: evitar misma galaxia
                continue
            options.append((sid, str(s.get("label", sid)), gid))

    # Orden estable: por (galaxy_id, label) para mostrar bonito en la UI
    options.sort(key=lambda t: (t[2], t[1]))
    return options


# =============================================================================
#  Helper de “salto” (no mueve grafo, solo aplica efectos y notifica)
# =============================================================================

def perform_hyperjump(
    burro,
    destination_star_id: int,
    on_before_jump: Optional[Callable[[], None]] = None,
    on_after_jump: Optional[Callable[[], None]] = None,
) -> int:
    """
    Hook para el simulador/UI:
      - (Opcional) Llama on_before_jump() para loggear/avisar.
      - Aplica efectos de hipergigante (energía y pasto).
      - (Opcional) Llama on_after_jump() para cerrar logs/updates.
      - Retorna el ID de la estrella destino para que el simulador
        sitúe al burro allí y continúe la ruta.

    Importante:
      - Este helper no altera el grafo ni verifica bloqueos.
      - La decisión “a qué estrella saltar” se toma fuera (UI/Sim).
    """
    if callable(on_before_jump):
        on_before_jump()

    apply_hypergiant_effects(burro)

    if callable(on_after_jump):
        on_after_jump()

    return int(destination_star_id)
