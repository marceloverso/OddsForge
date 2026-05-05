"""Cliente para TheSportsDB (resultados)."""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import httpx

from config import CONFIG

logger = logging.getLogger(__name__)
COLOMBIA_TZ = timezone(timedelta(hours=-5))


class SportsDBClient:
    def __init__(self):
        self.api_key = CONFIG.SPORTSDB_API_KEY
        self.base_url = CONFIG.SPORTSDB_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_events_by_date(self, sport_name: str, date_str: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{self.api_key}/eventsday.php"
        params = {"d": date_str, "s": sport_name}
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("events", []) or []
            logger.info(f"TheSportsDB {sport_name} {date_str}: {len(events)} eventos.")
            return events
        except Exception as e:
            logger.error(f"Error consultando TheSportsDB ({sport_name}): {e}")
            return []

    def find_match(self, picks: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not events:
            return None
        for event in events:
            home_db = self._normalize(event.get("strHomeTeam", ""))
            away_db = self._normalize(event.get("strAwayTeam", ""))
            for pick in picks:
                home_pick = self._normalize(pick["local"])
                away_pick = self._normalize(pick["visitante"])
                if (home_db in home_pick or home_pick in home_db) and \
                   (away_db in away_pick or away_pick in away_db):
                    return event
        return None

    def determine_winner(self, event: Dict[str, Any], pick_team: str) -> tuple:
        home_score = event.get("intHomeScore")
        away_score = event.get("intAwayScore")
        if home_score is None or away_score is None:
            return ("N/A", "⏳ PENDIENTE")
        try:
            h = int(home_score)
            a = int(away_score)
        except (ValueError, TypeError):
            return (f"{home_score}-{away_score}", "⏳ PENDIENTE")
        score_str = f"{h}-{a}"
        pick_norm = self._normalize(pick_team)
        home_norm = self._normalize(event.get("strHomeTeam", ""))
        away_norm = self._normalize(event.get("strAwayTeam", ""))
        if h > a:
            winner = home_norm
        elif a > h:
            winner = away_norm
        else:
            winner = "draw"
        if winner == "draw":
            return (score_str, "❌ PERDIDA")
        if pick_norm in winner or winner in pick_norm:
            return (score_str, "✅ GANADA")
        else:
            return (score_str, "❌ PERDIDA")

    @staticmethod
    def _normalize(name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r"[^a-z0-9]", "", name)
        return name
