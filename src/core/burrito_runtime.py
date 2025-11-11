# src/core/burro_runtime.py
from __future__ import annotations
from dataclasses import dataclass, asdict, replace, is_dataclass
from typing import Callable, Dict, List, Optional, Any, Union
import copy
from src.core.hypergiants import apply_hypergiant_effects, is_hypergiant, list_jump_destinations


# ------------------------------------------------------------
# TIPOS DE DATOS
# ------------------------------------------------------------

@dataclass
class StarEffect:
    """
    Efectos definidos para la estrella visitada.
    Mantiene los campos originales y agrega opcionales
    para cumplir el flujo completo del viaje.

    Orden de aplicación:
      1) Costo por distancia (viaje).
      2) Visita: comer (si energía < 50%, máx 50% del tiempo) e investigar (si se parametriza).
      3) Boost de hipergigante (si hyper_boost=True).
      4) Deltas directos y/o cambio de salud.

    Campos ORIGINALES (no se quitan):
      - vida_ly   : ± años-luz (investigación/enfermedad)
      - energia   : ± energía
      - alimento  : ± pasto/comida (kg)
      - nota      : texto libre para recap

    Campos NUEVOS (opcionales; si la UI no los manda, no afectan):
      - tiempo_visita     : a.l. disponibles en la estrella
      - tiempo_por_kg     : a.l./kg para comer
      - invest_cost_per_x : energía gastada por bloque
      - invest_x_time     : tamaño de bloque temporal (a.l.)
      - set_salud         : string con nuevo estado ("Excelente", "Buena", etc.) o None
      - hyper_boost       : si True, aplica boost de hipergigante
    """
    # Originales
    vida_ly: float = 0.0
    energia: float = 0.0
    alimento: float = 0.0
    nota: str = ""

    # Nuevos opcionales
    tiempo_visita: float = 0.0
    tiempo_por_kg: float = 0.0
    invest_cost_per_x: float = 0.0
    invest_x_time: float = 0.0
    set_salud: Optional[str] = None
    hyper_boost: bool = False


@dataclass
class StepRecap:
    """
    Resumen por paso para UI/tabla.
    Mantiene los campos originales y agrega métricas nuevas sin romper compatibilidad.
    """
    # Originales
    from_star_id: int
    to_star_id: int
    to_star_label: str
    distancia_ly: float
    vida_antes: float
    vida_delta_viaje: float
    vida_delta_estrella: float
    vida_despues: float
    energia_antes: float
    energia_delta: float
    energia_despues: float
    alimento_antes: float
    alimento_delta: float
    alimento_despues: float
    nota: str

    # NUEVOS (opcionales; la UI puede ignorarlos si no los usa)
    kg_comidos: float = 0.0
    energia_investigada: float = 0.0
    hyper_boost_aplicado: bool = False
    salud_antes: Optional[str] = None
    salud_despues: Optional[str] = None


# ------------------------------------------------------------
# ADAPTADOR DEL BURRO (no dependemos de implementación concreta)
# ------------------------------------------------------------

class BurroAdapter:
    """
    Envuelve una instancia de 'Burro' y expone getters/setters normalizados.
    Compatible con tu burro.py (energia, pasto_kg, vida_restante, salud, viajar(),
    comer_en_estrella(), investigar(), aplicar_evento_salud(), hipergigante_boost()).
    """

    def __init__(self, burro_real: Any):
        self._orig = burro_real
        # Clon profundo seguro
        if is_dataclass(burro_real):
            try:
                self._copy = replace(burro_real)
            except Exception:
                self._copy = copy.deepcopy(burro_real)
        elif isinstance(burro_real, dict):
            # Permite dicts si el Burro expone from_json
            from src.core.burro import Burro
            self._copy = Burro.from_json(burro_real)
        else:
            self._copy = copy.deepcopy(burro_real)

        # Validación mínima
        for attr in ("energia", "pasto_kg", "vida_restante"):
            if not hasattr(self._copy, attr):
                raise AttributeError(f"Burro no tiene atributo requerido: '{attr}'")

    # --- acceso a la copia ---
    @property
    def model(self) -> Any:
        return self._copy

    # --- getters ---
    def get_vida(self) -> float:
        return float(getattr(self._copy, "vida_restante"))

    def get_energia(self) -> float:
        return float(getattr(self._copy, "energia"))

    def get_alimento(self) -> float:
        return float(getattr(self._copy, "pasto_kg"))

    def get_salud(self) -> Optional[str]:
        s = getattr(self._copy, "salud", None)
        # Enum Health o string; devolvemos .value si existe
        try:
            return s.value if hasattr(s, "value") else (str(s) if s is not None else None)
        except Exception:
            return None

    # --- setters (clamp a rangos válidos) ---
    def set_vida(self, value: float) -> None:
        setattr(self._copy, "vida_restante", max(0.0, float(value)))

    def set_energia(self, value: float) -> None:
        setattr(self._copy, "energia", max(0.0, min(100.0, float(value))))

    def set_alimento(self, value: float) -> None:
        setattr(self._copy, "pasto_kg", max(0.0, float(value)))

    def set_salud(self, salud_str: Optional[str]) -> None:
        if not salud_str:
            return
        try:
            from src.core.burro import Health
            # Normaliza capitalización según tu Enum
            mapping = {h.value.lower(): h for h in Health}
            new = mapping.get(salud_str.strip().lower())
            if new is not None:
                # usar API del modelo si existe
                if hasattr(self._copy, "aplicar_evento_salud"):
                    self._copy.aplicar_evento_salud(0.0, new)
                else:
                    setattr(self._copy, "salud", new)
            else:
                # si no matchea, intenta asignar string
                setattr(self._copy, "salud", salud_str)
        except Exception:
            setattr(self._copy, "salud", salud_str)

    # --- acciones del modelo ---
    def viajar(self, distancia_ly: float) -> float:
        """Resta vida por viaje. Retorna delta de vida (normalmente negativo)."""
        distancia_ly = max(0.0, float(distancia_ly))
        vida_antes = self.get_vida()
        if hasattr(self._copy, "viajar") and callable(self._copy.viajar):
            self._copy.viajar(distancia_ly)
        else:
            self.set_vida(vida_antes - distancia_ly)
        return self.get_vida() - vida_antes

    def comer(self, tiempo_visita: float, tiempo_por_kg: float) -> float:
        """Come usando la propia lógica del burro (solo si energía < 50% y máx 50% del tiempo)."""
        if tiempo_visita <= 0.0 or tiempo_por_kg <= 0.0:
            return 0.0
        if hasattr(self._copy, "comer_en_estrella"):
            return float(self._copy.comer_en_estrella(tiempo_visita, tiempo_por_kg))
        return 0.0

    def investigar(self, tiempo_visita: float, cost_per_x: float, x_time: float) -> float:
        """Investiga consumiendo energía por bloques."""
        if tiempo_visita <= 0.0 or cost_per_x <= 0.0 or x_time <= 0.0:
            return 0.0
        if hasattr(self._copy, "investigar"):
            return float(self._copy.investigar(tiempo_visita, cost_per_x, x_time))
        return 0.0

    def aplicar_evento_salud(self, delta_vida: float = 0.0, set_salud: Optional[str] = None) -> None:
        """Aplica delta de vida y/o cambio de salud."""
        if hasattr(self._copy, "aplicar_evento_salud"):
            # Mapea string->Enum si aplica
            if set_salud:
                from src.core.burro import Health
                mapping = {h.value.lower(): h for h in Health}
                enum_target = mapping.get(set_salud.strip().lower())
            else:
                enum_target = None
            self._copy.aplicar_evento_salud(delta_vida=float(delta_vida), nueva_salud=enum_target)
        else:
            self.set_vida(self.get_vida() + float(delta_vida))
            if set_salud:
                self.set_salud(set_salud)

    def hipergigante_boost(self) -> None:
        """Boost de hipergigante (+50% energía actual, duplica pasto)."""
        if hasattr(self._copy, "hipergigante_boost"):
            self._copy.hipergigante_boost()


# ------------------------------------------------------------
# MOTOR DE EFECTOS EN TIEMPO REAL (PASO A PASO)
# ------------------------------------------------------------

class BurroRuntimeEngine:
    """
    Aplica, en tiempo real y paso a paso, los efectos de cada estrella al burro COPIA.
    No modifica al burro original. Conecta perfecto con la UI: si no ingresan datos,
    los campos nuevos valen 0; si los ingresan, se aplican.

    Orden exacto:
      1) Costo por distancia (viajar).
      2) Visita: comer (si energía<50%, máx 50% del tiempo) e investigar (si parametrizado).
      3) Boost de hipergigante (si hyper_boost=True).
      4) Deltas directos y/o cambio de salud (vida_ly, energia, alimento, set_salud).
      5) Recap (tabla) + callback on_update(state) si existe.
    """

    def __init__(
        self,
        real_burro: Union[Any, Dict[str, Any]],
        *,
        on_update: Optional[Callable[[Dict[str, float]], None]] = None
    ) -> None:
        self._adapter = BurroAdapter(real_burro)
        self._on_update = on_update
        self._history: List[StepRecap] = []

    # --- estado actual (para la UI) ---
    def state(self) -> Dict[str, Any]:
        b = self._adapter
        # Incluimos salud por conveniencia de UI
        return {
            "vida_restante": b.get_vida(),
            "energia": b.get_energia(),
            "pasto_kg": b.get_alimento(),
            "salud": b.get_salud(),
        }

    # --- historial ---
    def recap_history(self) -> List[StepRecap]:
        return list(self._history)

    def recap_as_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for r in self._history:
            rows.append({
                "De → A": f"{r.from_star_id} → {r.to_star_id} ({r.to_star_label})",
                "Distancia (ly)": r.distancia_ly,
                "Vida (−viaje)": r.vida_delta_viaje,
                "Vida (±estrella)": r.vida_delta_estrella,
                "Vida (final)": r.vida_despues,
                "Energía (±estrella)": r.energia_delta,
                "Energía (final)": r.energia_despues,
                "Alimento (±estrella)": r.alimento_delta,
                "Alimento (final)": r.alimento_despues,
                "Nota": r.nota,
                # Extras informativos (la UI puede ignorarlos si no los quiere)
                "Kg comidos": r.kg_comidos,
                "Energía gastada investigando": r.energia_investigada,
                "Boost hipergigante": "Sí" if r.hyper_boost_aplicado else "No",
                "Salud (antes)": r.salud_antes or "",
                "Salud (después)": r.salud_despues or "",
            })
        return rows

    # --- aplicación de un paso completo ---
    def apply_step(
        self,
        *,
        from_star_id: int,
        to_star_id: int,
        to_star_label: str,
        distancia_ly: float,
        effect: Optional[StarEffect] = None
    ) -> StepRecap:
        effect = effect or StarEffect()
        b = self._adapter

        # --- snapshot antes ---
        vida_antes = b.get_vida()
        energia_antes = b.get_energia()
        alimento_antes = b.get_alimento()
        salud_antes = b.get_salud()

        # 1) Costo por distancia
        vida_delta_viaje = b.viajar(distancia_ly)  # negativo normalmente

        # 2) Visita: comer / investigar (si hay parámetros)
        kg_comidos = 0.0
        energia_investigada = 0.0
        if effect.tiempo_visita > 0.0:
            # Comer (usa reglas de tu burro.py)
            if effect.tiempo_por_kg > 0.0 and b.get_alimento() > 0.0:
                kg_comidos = b.comer(effect.tiempo_visita, effect.tiempo_por_kg)
            # Investigar
            if effect.invest_cost_per_x > 0.0 and effect.invest_x_time > 0.0:
                energia_investigada = b.investigar(effect.tiempo_visita, effect.invest_cost_per_x, effect.invest_x_time)

        # 3) Boost hipergigante (si procede)
        hyper_applied = False
        if effect.hyper_boost:
            # Usa la función central de hypergiants.py
            apply_hypergiant_effects(b.model)
            hyper_applied = True


        # 4) Deltas directos + estado de salud
        # Vida por estrella
        if effect.vida_ly != 0.0 or effect.set_salud:
            b.aplicar_evento_salud(delta_vida=float(effect.vida_ly), set_salud=effect.set_salud)

        # Energía
        if effect.energia != 0.0:
            b.set_energia(b.get_energia() + float(effect.energia))

        # Alimento
        if effect.alimento != 0.0:
            b.set_alimento(b.get_alimento() + float(effect.alimento))

        # --- snapshot después ---
        vida_despues = b.get_vida()
        energia_despues = b.get_energia()
        alimento_despues = b.get_alimento()
        salud_despues = b.get_salud()

        recap = StepRecap(
            # originales
            from_star_id=int(from_star_id),
            to_star_id=int(to_star_id),
            to_star_label=str(to_star_label),
            distancia_ly=float(distancia_ly),
            vida_antes=float(vida_antes),
            vida_delta_viaje=float(vida_delta_viaje),
            vida_delta_estrella=float(effect.vida_ly),
            vida_despues=float(vida_despues),
            energia_antes=float(energia_antes),
            energia_delta=float(effect.energia),
            energia_despues=float(energia_despues),
            alimento_antes=float(alimento_antes),
            alimento_delta=float(effect.alimento),
            alimento_despues=float(alimento_despues),
            nota=str(effect.nota or "").strip(),
            # nuevos
            kg_comidos=float(kg_comidos),
            energia_investigada=float(energia_investigada),
            hyper_boost_aplicado=bool(hyper_applied),
            salud_antes=salud_antes,
            salud_despues=salud_despues,
        )

        self._history.append(recap)

        # Callback a la UI (barras, labels, etc.)
        if self._on_update is not None:
            self._on_update(self.state())

        return recap