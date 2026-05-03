"""Cliente async para The Odds API v4."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import httpx

from config import CONFIG

logger = logging.getLogger(__name__)
COLOMBIA_TZ = timezone(timedelta(hours=-5))


class OddsClient:
    """Wrapper alrededor de The Odds API."""

    def __init__(self):
        self.api_key = CONFIG.ODDS_API_KEY
        self.base_url = CONFIG.ODDS_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0, headers={"Accept": "application/json"})
        self.requests_used = 0
        self.requests_remaining = 500

    async def close(self):
        await self.client.aclose()

    async def get_in_season_sports(self) -> List[str]:
        """Retorna solo los sport_keys que están en temporada y en nuestra lista prioritaria."""
        url = f"{self.base_url}/sports"
        params = {"apiKey": self.api_key, "all": "false"}

        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            # Actualizar quota (aunque /sports no cuenta, por si acaso)
            self._update_quota(resp.headers)

            active = {s["key"] for s in data if s.get("active") and not s.get("has_outrights", False)}
            prioritized = set(CONFIG.SPORTS_PRIORITY)
            return list(active & prioritized)

        except Exception as e:
            logger.error(f"Error obteniendo deportes: {e}")
            return []

    async def get_odds_for_sport(self, sport_key: str) -> List[Dict[str, Any]]:
        """Obtiene odds h2h en decimal para un deporte. Consume 1 request."""
        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": CONFIG.REGIONS,
            "markets": CONFIG.MARKETS,
            "oddsFormat": CONFIG.ODDS_FORMAT,
            "dateFormat": CONFIG.DATE_FORMAT,
        }

        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            self._update_quota(resp.headers)
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                logger.warning(f"{sport_key} no tiene mercado h2h disponible.")
            else:
                logger.error(f"HTTP {e.response.status_code} en {sport_key}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error en odds {sport_key}: {e}")
            return []

    async def get_all_odds(self, sport_keys: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Consulta odds de todos los deportes en paralelo (concurrency limitada)."""
        semaphore = asyncio.Semaphore(5)  # Máximo 5 requests concurrentes
        results = {}

        async def fetch(sport):
            async with semaphore:
                odds = await self.get_odds_for_sport(sport)
                return sport, odds

        tasks = [fetch(sk) for sk in sport_keys]
        for coro in asyncio.as_completed(tasks):
            sport, odds = await coro
            if odds:
                results[sport] = odds

        return results

    def _update_quota(self, headers: httpx.Headers):
        """Actualiza contadores de quota desde headers de respuesta."""
        try:
            self.requests_used = int(headers.get("x-requests-used", self.requests_used))
            self.requests_remaining = int(headers.get("x-requests-remaining", self.requests_remaining))
        except ValueError:
            pass

    def is_today(self, commence_time: str) -> bool:
        """Verifica si el partido es hoy en hora Colombia."""
        try:
            dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            dt_col = dt.astimezone(COLOMBIA_TZ)
            today_col = datetime.now(COLOMBIA_TZ)
            return dt_col.date() == today_col.date()
        except Exception:
            return True  # Si falla el parseo, incluirlo por defecto
