# core/report_generator.py
import json
import os
from datetime import datetime
from typing import Optional


class ReportGenerator:
    """
    Genera el reporte final de toda la simulación en formato JSON.
    El archivo se almacena en una carpeta especificada por el usuario.

    Estructura del JSON resultante:
      {
        "start_time": "...",
        "visited_stars": [...],
        "hops": [...],
        "totals": {
            "total_grass_kg": ...,
            "total_energy_used_%": ...,
            "total_time_x": ...,
            "total_distance_ly": ...
        },
        "end_reason": "...",
        "life_left_ly": ...
      }
    """

    def __init__(self, output_dir: str):
        # Crear carpeta para los reportes si no existe
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Plantilla inicial del reporte
        self.data = {
            "start_time": datetime.now().isoformat(),
            "visited_stars": [],         # Lista de dicts por cada visita
            "hops": [],                  # Movimientos entre estrellas
            "totals": {
                "total_grass_kg": 0.0,
                "total_energy_used_%": 0.0,
                "total_time_x": 0.0,
                "total_distance_ly": 0.0
            },
            "end_reason": None,          # "finished", "dead", "aborted", etc.
            "life_left_ly": None
        }

    # ----------------------------------------------------------------------
    # Registrar VISITA a una estrella
    # ----------------------------------------------------------------------
    def log_visit(
        self,
        star_id: int,
        label: str,
        galaxy_id: Optional[int],
        hypergiant: bool,
        grass_kg: float,
        time_x: float,
        energy_in_pct: float,
        energy_out_pct: float
    ):
        """
        Registra todo lo ocurrido al visitar una estrella:
          - Identificación de la estrella
          - Si era hipergigante
          - Cuánto pasto se comió
          - Tiempo invertido
          - Energía antes y después
        """
        self.data["visited_stars"].append({
            "star_id": int(star_id),
            "label": label,
            "galaxy_id": galaxy_id,
            "hypergiant": bool(hypergiant),
            "grass_eaten_kg": float(grass_kg),
            "invest_time_x": float(time_x),
            "energy_in_%": float(energy_in_pct),
            "energy_out_%": float(energy_out_pct)
        })

        # Totales acumulados
        self.data["totals"]["total_grass_kg"] += float(grass_kg)
        self.data["totals"]["total_time_x"] += float(time_x)

    # ----------------------------------------------------------------------
    # Registrar SALTO entre estrellas
    # ----------------------------------------------------------------------
    def log_hop(self, origin: int, target: int, distance_ly: float, energy_used_pct: float):
        """
        Registra un salto normal entre estrellas (no hipersalto).
        """
        self.data["hops"].append({
            "from": int(origin),
            "to": int(target),
            "distance_ly": float(distance_ly),
            "energy_used_%": float(energy_used_pct),
        })

        # Totales acumulados
        self.data["totals"]["total_distance_ly"] += float(distance_ly)
        self.data["totals"]["total_energy_used_%"] += float(energy_used_pct)

    # ----------------------------------------------------------------------
    # Finalizar el reporte y guardar a disco
    # ----------------------------------------------------------------------
    def finalize(self, life_left_ly: float, end_reason: str = "finished") -> str:
        """
        Cierra el reporte indicando cómo terminó la simulación y
        la vida restante del burro en años luz.
        Devuelve la ruta completa del archivo JSON generado.
        """
        self.data["end_reason"] = end_reason
        self.data["life_left_ly"] = float(life_left_ly)

        # Nombre elegante y único por ejecución
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Guardar el JSON final
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

        return filepath
