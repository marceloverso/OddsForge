"""Configuración central del Parlay Bot."""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class Config:
    """Todas las variables de entorno y reglas de negocio."""

    # API Keys
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # The Odds API
    ODDS_BASE_URL: str = "https://api.the-odds-api.com/v4"
    REGIONS: str = "eu"           # Cuotas decimales europeas
    MARKETS: str = "h2h"          # Solo moneyline
    ODDS_FORMAT: str = "decimal"  # Forzar decimal
    DATE_FORMAT: str = "iso"

    # Reglas del Parlay
    MIN_PICKS: int = 10
    MAX_PICKS: int = 14
    MAX_PER_SPORT: int = 4
    STAKE_COP: int = 2000

    # Filtro de cuotas (sweet spot para favoritos moderados)
    MIN_ODD: float = 1.35
    MAX_ODD: float = 2.30
    TARGET_ODD: float = 1.65      # Cuota ideal que buscamos

    # Deportes a monitorear (priorizados, se ignora si no están en temporada)
    SPORTS_PRIORITY: List[str] = None

    def __post_init__(self):
        self.SPORTS_PRIORITY = [
            # Fútbol
            "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
            "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_uefa_champs_league",
            "soccer_brazil_campeonato", "soccer_argentina_primera_division",
            "soccer_usa_mls", "soccer_mexico_ligamx", "soccer_colombia",

            # Americanos
            "americanfootball_nfl", "basketball_nba", "baseball_mlb",
            "icehockey_nhl", "americanfootball_ncaaf",

            # Otros
            "basketball_euroleague", "tennis_atp_french_open", "tennis_wta_french_open",
            "mma_mixed_martial_arts", "cricket_ipl", "aussierules_afl",
            "rugbyleague_nrl", "rugbyunion_six_nations",
        ]

CONFIG = Config()
