"""Motor de selección de picks y construcción del parlay."""
import logging
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
    selection: str
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
    def __init__(self):
        self.min_odd = CONFIG.MIN_ODD
        self.max_odd = CONFIG.MAX_ODD
        self.target = CONFIG.TARGET_ODD

    def extract_picks(self, all_odds: Dict[str, List[Dict[str, Any]]]) -> List[Pick]:
        candidates = []
        for sport_key, events in all_odds.items():
            for event in events:
                commence = event.get("commence_time", "")
                home = event.get("home_team", "N/A")
                away = event.get("away_team", "N/A")
                sport_title = event.get("sport_title", sport_key)
                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue
                bm = bookmakers[0]
                markets = bm.get("markets", [])
                if not markets:
                    continue
                outcomes = markets[0].get("outcomes", [])
                if len(outcomes) < 2:
                    continue
                outcomes_sorted = sorted(outcomes, key=lambda x: x["price"])
                favorite = outcomes_sorted[0]
                fav_price = favorite["price"]
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
                        reason="Favorito moderado. Cuota ideal para acumulado."
                    )
                    candidates.append(pick)
        logger.info(f"Candidatos filtrados: {len(candidates)}")
        return candidates

    def score_pick(self, pick: Pick) -> float:
        distance = abs(pick.odd - self.target)
        score = max(0.0, 1.0 - (distance / 1.0))
        return score

    def _select_with_limit(self, candidates: List[Pick], max_per_sport: int) -> List[Pick]:
        candidates.sort(key=self.score_pick, reverse=True)
        selected = []
        sport_counts: Dict[str, int] = {}
        for pick in candidates:
            sport = pick.sport_key
            current = sport_counts.get(sport, 0)
            if current >= max_per_sport:
                continue
            selected.append(pick)
            sport_counts[sport] = current + 1
            if len(selected) >= CONFIG.MAX_PICKS:
                break
        return selected

    def build_parlay(self, candidates: List[Pick]) -> Parlay:
        if len(candidates) < CONFIG.MIN_PICKS:
            logger.warning(f"Solo {len(candidates)} candidatos. Mínimo requerido: {CONFIG.MIN_PICKS}")
            return Parlay(picks=[], total_odd=0.0, stake_cop=CONFIG.STAKE_COP, potential_return=0.0)

        # Intento 1: diversificación (max 4 por deporte)
        selected = self._select_with_limit(candidates, CONFIG.MAX_PER_SPORT)
        logger.info(f"Selección diversificada: {len(selected)} picks.")

        # Intento 2 (FALLBACK): si no alcanza 10, relajamos a 14 por deporte
        if len(selected) < CONFIG.MIN_PICKS:
            logger.info(f"Fallback activado: solo {len(selected)} con diversificación. Tomando más del deporte mayoritario...")
            selected = self._select_with_limit(candidates, CONFIG.MAX_PICKS)
            logger.info(f"Selección fallback: {len(selected)} picks.")

        if len(selected) < CONFIG.MIN_PICKS:
            logger.warning(f"Aún con fallback solo hay {len(selected)} picks.")
            return Parlay(picks=[], total_odd=0.0, stake_cop=CONFIG.STAKE_COP, potential_return=0.0)

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
