# core/models.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


# ---------------------------------------------------------------------
# Salud del burro (normalizada a capitalización consistente)
# ---------------------------------------------------------------------
class Health(str, Enum):
    Excelente   = "Excelente"
    Buena       = "Buena"
    Regular     = "Regular"
    Mala        = "Mala"
    Moribundo   = "Moribundo"
    Muerto      = "Muerto"


# ---------------------------------------------------------------------
# Ganancia de burroenergía por kg de pasto SEGÚN SALUD
# PDF: 5%(excelente), 3%(regular) y 2%(malo).
# Añadimos:
#  - Buena: 4% (intermedio).
#  - Moribundo: 1% (mínimo).
#  - Muerto: 0% (no aplica, seguridad).
# ---------------------------------------------------------------------
ENERGY_PER_KG: Dict[Health, float] = {
    Health.Excelente: 5.0,
    Health.Buena:     4.0,
    Health.Regular:   3.0,
    Health.Mala:      2.0,
    Health.Moribundo: 1.0,
    Health.Muerto:    0.0,
}


@dataclass
class Burro:
    """Estado del burro durante el viaje/simulación."""
    energia: float          # 0..100
    salud: Health
    pasto_kg: float
    edad_inicial: float     # años luz
    edad_actual: float      # años luz
    edad_muerte: float      # años luz
    vida_restante: float    # años luz (tiempo de vida que queda)

    # -----------------------------------------------------------------
    # Fábrica desde JSON (claves esperadas del JSON del burro)
    # - burroenergiaInicial (0..100)
    # - estadoSalud ("Excelente"/"Buena"/"Regular"/"Mala"/"Moribundo"/"Muerto")
    # - pasto (kg)
    # - startAge / deathAge (años luz)
    # -----------------------------------------------------------------
    @classmethod
    def from_json(cls, data: dict) -> "Burro":
        start_age  = float(data.get("startAge", 0.0))
        death_age  = float(data.get("deathAge", start_age))
        energia    = float(data.get("burroenergiaInicial", 0.0))
        salud_raw  = str(data.get("estadoSalud", "Regular")).strip().capitalize()
        pasto_kg   = float(data.get("pasto", 0.0))

        # Normaliza salud a Enum (acepta varias capitalizaciones)
        salud_map = {h.value.lower(): h for h in Health}
        salud = salud_map.get(salud_raw.lower(), Health.Regular)

        vida_restante = max(0.0, death_age - start_age)

        return cls(
            energia=max(0.0, min(100.0, energia)),
            salud=salud,
            pasto_kg=max(0.0, pasto_kg),
            edad_inicial=start_age,
            edad_actual=start_age,
            edad_muerte=death_age,
            vida_restante=vida_restante,
        )

    # -----------------------------------------------------------------
    @property
    def esta_muerto(self) -> bool:
        return (
            self.vida_restante <= 0.0 or
            self.edad_actual >= self.edad_muerte or
            self.salud == Health.Muerto
        )

    # -----------------------------------------------------------------
    def viajar(self, distancia_ly: float) -> None:
        """Avanza en años luz y descuenta vida."""
        if self.esta_muerto:
            return
        d = max(0.0, float(distancia_ly))
        self.vida_restante -= d
        self.edad_actual   += d
        if self.vida_restante <= 0.0 or self.edad_actual >= self.edad_muerte:
            self.salud = Health.Muerto

    # -----------------------------------------------------------------
    def comer_en_estrella(self, tiempo_visita: float, tiempo_por_kg: float) -> float:
        """
        El burro COME solo si su energía < 50%.
        Máximo 50% del tiempo de visita dedicado a comer.
        Devuelve kg consumidos.
        """
        if self.esta_muerto:
            return 0.0
        if self.energia >= 50.0:
            return 0.0
        if tiempo_visita <= 0.0 or tiempo_por_kg <= 0.0 or self.pasto_kg <= 0.0:
            return 0.0

        max_tiempo_comer = 0.5 * tiempo_visita
        kg_posibles = max_tiempo_comer / tiempo_por_kg
        kg_a_comer = max(0.0, min(self.pasto_kg, kg_posibles))

        if kg_a_comer <= 0.0:
            return 0.0

        delta = ENERGY_PER_KG.get(self.salud, 0.0) * kg_a_comer
        self.energia = min(100.0, self.energia + delta)
        self.pasto_kg -= kg_a_comer
        return kg_a_comer

    # -----------------------------------------------------------------
    def investigar(self, tiempo_visita: float, costo_energia_por_x: float, x_tiempo: float) -> float:
        """
        Consume energía por bloques de 'x_tiempo' durante 'tiempo_visita'.
        Devuelve energía efectivamente consumida.
        Si la energía llega a 0, marca al burro como muerto.
        """
        if self.esta_muerto:
            return 0.0
        if tiempo_visita <= 0.0 or costo_energia_por_x <= 0.0 or x_tiempo <= 0.0:
            return 0.0

        bloques = tiempo_visita / x_tiempo
        consumo = costo_energia_por_x * bloques
        consumo_real = min(consumo, max(0.0, self.energia))
        self.energia -= consumo_real
        # asegurar límites
        if self.energia <= 0.0:
            self.energia = 0.0
            # cuando la energía llega a cero, considerar muerte inmediata
            self.salud = Health.Muerto

        self.energia = max(0.0, self.energia)
        return consumo_real


    # -----------------------------------------------------------------
    def aplicar_evento_salud(self, delta_vida: float = 0.0, nueva_salud: Optional[Health] = None):
        """
        Aplica variación de vida (± años luz) y/o cambio de estado de salud.
        """
        if self.esta_muerto:
            return
        self.vida_restante += float(delta_vida)
        if self.vida_restante <= 0.0:
            self.salud = Health.Muerto
        elif nueva_salud is not None:
            self.salud = nueva_salud

    # -----------------------------------------------------------------
    def hipergigante_boost(self) -> None:
        """
        Efecto al pasar por estrella hipergigante:
        +50% de la energía actual (tope 100) y duplica pasto.
        """
        if self.esta_muerto:
            return
        self.energia  = min(100.0, self.energia + 0.5 * self.energia)
        self.pasto_kg = self.pasto_kg * 2.0
