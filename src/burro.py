from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional

#sdd

class health(str, Enum):
    Excelente = "Excelente"
    Buena = "Buena"
    Regular = "Regular"
    Mala = "mala"
    MORIBUNDO = "Moribundo"
    MUERTO = "Muerto"

# Ganancia de burroenergia por kg de pasto segun salud
# Segun pdf 5%(excelente), 3%(regular) y 2&(malo)
# Asumimos BUENA=Regular (3%) por falta de mencion explicita

Energy_PER_KG = {
    health.Excelente: 5.0,
    health.Buena: 4.0,
    health.Regular: 3.0,
    health.Mala: 2.0,
    health.MORIBUNDO: 1.0
}

@dataclass
class Burro:
    energia: float
    salud: health
    pasto_kg: float
    edad_inicial: float
    edad_actual: float
    edad_muerte: float
    vida_restantes: float

    @classmethod
    def from_json(cls, data: dict) -> "Burro":
        start_age = float(data.get("startAge", 0))
        death_age = float(data.get("deathAge", start_age))

        #vida util para viajar = diferenica entre edad inicial y muerte
        vida_restante = max(0.0, death_age - start_age)

        return cls(
            energia = float(data["burroenergiaInicial"]),
            salud = health(str(data["estadoSalud"]).capitalize()),
            pasto_kg = float(data["pasto"]),
            edad_inicial = start_age,
            edad_actual = start_age,
            edad_muerte = death_age,
            vida_restantes = vida_restante
        )
    @property
    def esta_muerto(self) -> bool:
        return self.vida_restantes<-0 or self.salud == health.MUERTO or self.vida_restantes <= 0
    
    def viajar(self, diatancia_ly: float)-> None:
        """reduce vida_restante y aumneta edad_actual"""
        distancia = max(0.0, diatancia_ly)
        self.vida_restantes -= distancia
        self.edad_actual += distancia
        
        if self.vida_restantes <= 0 or self.edad_actual >= self.edad_muerte:
            self.salud = health.MUERTO
    
    def comer_en_estrella(self, tiempo_visita: float, tiempo_por_kg: float) -> float:
        if self.energia >= 50 or tiempo_visita <-0 or tiempo_por_kg <=0 or self.pasto_kg <=0:
            return 0.0
        
        max_tiempo_comer = 0,5 * tiempo_visita
        kg_psoibles = max_tiempo_comer / tiempo_por_kg
        kg_a_comer = min(self.pasto_kg, kg_psoibles)

        if kg_a_comer <=0:
            return 0.0
        
        delta = Energy_PER_KG[self.salud] * kg_a_comer
        self.energia = min(100.0, self.energia + delta)
        self.pasto_kg -= kg_a_comer 
        return kg_a_comer
    
    def investigar(self, tiempo_vsita: float, costo_energia_por_x: float, x_tiempo: float):
        if tiempo_vsita <-0 or costo_energia_por_x <=0 or costo_energia_por_x <=0:
            return 0.0
        
        bloques = tiempo_vsita / x_tiempo
        consumo = costo_energia_por_x * bloques
        consumo_real = min(consumo, self.energia)
        self.energia -= consumo_real
        return consumo_real
    
    def aplicar_evento_salud(self, delta_vida: float = 0.0, nueva_salud: Optional[health] = None):
        self.vida_restantes += float(delta_vida)
        if self.vida_restantes <= 0:
            self.salud = health.MUERTO

        if nueva_salud is not None:
            self.salud = nueva_salud
    
    def hipergigante_boost(self):
        self.energia = min(100.0, self.energia + 5.0 * self.energia)
        self.pasto_kg += 2.0
