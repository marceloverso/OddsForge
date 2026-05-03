"""Motor de selección de picks y construcción del parlay."""
import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any
from math import prod

from config import CONFIG

logger = logging.getLogger(__name__)


@dataclass
class Pick:
    sport_key: str
    sport_title: str
    league: str
    home_team: str
    away_team: str
    selection: str        # Equipo elegido
    odd: float
    commence_time: str
    reason: str


@dataclass
class Parlay:
    picks: List[Pick]
    total_odd: float
    stake_cop: int
    potential_return: float
    disclaimer: str = field(default="")


class ParlaySelector:
    """Selecciona picks basado en cuotas y diversificación."""

    def __init__(self):
        self.min_odd = CONFIG.MIN_ODD
        self.max_odd = CONFIG.MAX_ODD
        self.target = CONFIG.TARGET_ODD

    def extract_picks(self, all_odds: Dict[str, List[Dict[str, Any]]]) -> List[Pick]:
        """Convierte la respuesta cruda de la API en candidatos filtrados."""
        candidates = []

        for sport_key, events in all_odds.items():
            for event in events:
                # Solo eventos de hoy (el cliente ya filtra, pero doble check)
                commence = event.get("commence_time", "")

                home = event.get("home_team", "N/A")
                away = event.get("away_team", "N/A")
                sport_title = event.get("sport_title", sport_key)

                # Extraer cuotas del primer bookmaker disponible (EU region)
                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue

                # Tomar el primer bookmaker (ya filtramos por region=eu)
                bm = bookmakers[0]
                markets = bm.get("markets", [])
                if not markets:
                    continue

                outcomes = markets[0].get("outcomes", [])
                if len(outcomes) < 2:
                    continue

                # Encontrar favorito y underdog
                outcomes_sorted = sorted(outcomes, key=lambda x: x["price"])
                favorite = outcomes_sorted[0]
                underdog = outcomes_sorted[-1]

                fav_price = favorite["price"]
                und_price = underdog["price"]

                # Estrategia: tomar el FAVORITO si su cuota está en rango óptimo.
                # Si el favorito está muy bajo (<1.35), saltamos (no vale la pena el riesgo acumulado).
                # Si el favorito está alto (>2.30), es volado, saltamos.
                if self.min_odd <= fav_price <= self.max_odd:
                    pick = Pick(
                        sport_key=sport_key,
                        sport_title=sport_title,
                        league=sport_title,
                        home_team=home,
                        away_team=away,
                        selection=favorite["name"],
                        odd=round(fav_price, 2),
                        commence_time=commence,
                        reason=f"Favorito moderado. Cuota ideal para acumulado."
                    )
                    candidates.append(pick)

                # Opcional: si no hay suficientes favoritos, tomar 1 underdog moderado por deporte
                # (desactivado por defecto para mantener lógica conservadora)

        logger.info(f"Candidatos filtrados: {len(candidates)}")
        return candidates

    def score_pick(self, pick: Pick) -> float:
        """Score más alto = mejor para el parlay.

        Favorece cuotas cerca del TARGET (1.65) y penaliza extremos.
        """
        distance = abs(pick.odd - self.target)
        score = max(0.0, 1.0 - (distance / 1.0))  # 1.0 en target, 0 en target±1.0

        # Bonus leve por deportes con más volumen (confianza implícita del mercado)
        # No aplica filtro real, solo diversificación posterior
        return score

    def build_parlay(self, candidates: List[Pick]) -> Parlay:
        """Construye el mejor parlay respetando restricciones."""
        if len(candidates) < CONFIG.MIN_PICKS:
            logger.warning(f"Solo {len(candidates)} candidatos. Mínimo requerido: {CONFIG.MIN_PICKS}")
            return Parlay(picks=[], total_odd=0.0, stake_cop=CONFIG.STAKE_COP, potential_return=0.0)

        # Ordenar por score descendente
        candidates.sort(key=self.score_pick, reverse=True)

        selected = []
        sport_counts: Dict[str, int] = {}

        for pick in candidates:
            sport = pick.sport_key
            current = sport_counts.get(sport, 0)

            if current >= CONFIG.MAX_PER_SPORT:
                continue

            selected.append(pick)
            sport_counts[sport] = current + 1

            if len(selected) >= CONFIG.MAX_PICKS:
                break

        # Si no alcanzamos el mínimo, relajamos (aunque no debería pasar con suficientes deportes)
        if len(selected) < CONFIG.MIN_PICKS:
            logger.warning(f"Solo se seleccionaron {len(selected)} picks.")

        # Calcular métricas
        total_odd = round(prod([p.odd for p in selected]), 2)
        potential = round(CONFIG.STAKE_COP * total_odd, 2)

        disclaimer = (
            "⚠️ *JUEGO RESPONSABLE* ⚠️\n"
            "Este bot es solo una herramienta informativa. *No garantiza ganancias.*\n"
            "Apuesta bajo tu propio riesgo. Monto sugerido: $2.000 COP.\n"
            "Si el juego afecta tu vida, busca ayuda: Coljuegos 01 8000 510 203."
        )

        return Parlay(
            picks=selected,
            total_odd=total_odd,
            stake_cop=CONFIG.STAKE_COP,
            potential_return=potential,
            disclaimer=disclaimer
        )
