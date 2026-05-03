"""Configuración central del Parlay Bot."""
import os
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Config:
    """Todas las variables de entorno y reglas de negocio."""

    # API Keys
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
    SPORTSDB_API_KEY: str = os.getenv("SPORTSDB_API_KEY", "3")  # "3" es la demo key pública
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Google Sheets
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    # El JSON de credenciales de la Service Account se lee desde un archivo o variable
    GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

    # The Odds API
    ODDS_BASE_URL: str = "https://api.the-odds-api.com/v4"
    REGIONS: str = "eu"
    MARKETS: str = "h2h"
    ODDS_FORMAT: str = "decimal"
    DATE_FORMAT: str = "iso"

    # TheSportsDB
    SPORTSDB_BASE_URL: str = "https://www.thesportsdb.com/api/v1/json"

    # Reglas del Parlay
    MIN_PICKS: int = 10
    MAX_PICKS: int = 14
    MAX_PER_SPORT: int = 4
    STAKE_COP: int = 2000

    # Filtro de cuotas
    MIN_ODD: float = 1.35
    MAX_ODD: float = 2.30
    TARGET_ODD: float = 1.65

    SPORTS_PRIORITY: List[str] = field(default_factory=list)

    # Mapeo de sport_key (Odds API) -> nombre de deporte en TheSportsDB
    SPORTSDB_SPORT_MAP: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.SPORTS_PRIORITY = [
            "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
            "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_uefa_champs_league",
            "soccer_brazil_campeonato", "soccer_argentina_primera_division",
            "soccer_usa_mls", "soccer_mexico_ligamx", "soccer_colombia",
            "americanfootball_nfl", "basketball_nba", "baseball_mlb",
            "icehockey_nhl", "americanfootball_ncaaf",
            "basketball_euroleague", "mma_mixed_martial_arts",
        ]

        self.SPORTSDB_SPORT_MAP = {
            "soccer_epl": "Soccer",
            "soccer_spain_la_liga": "Soccer",
            "soccer_germany_bundesliga": "Soccer",
            "soccer_italy_serie_a": "Soccer",
            "soccer_france_ligue_one": "Soccer",
            "soccer_uefa_champs_league": "Soccer",
            "soccer_brazil_campeonato": "Soccer",
            "soccer_argentina_primera_division": "Soccer",
            "soccer_usa_mls": "Soccer",
            "soccer_mexico_ligamx": "Soccer",
            "soccer_colombia": "Soccer",
            "americanfootball_nfl": "American Football",
            "basketball_nba": "Basketball",
            "baseball_mlb": "Baseball",
            "icehockey_nhl": "Ice Hockey",
            "americanfootball_ncaaf": "American Football",
            "basketball_euroleague": "Basketball",
            "mma_mixed_martial_arts": "Fighting",
        }

CONFIG = Config()
