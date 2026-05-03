"""Entry point del Parlay Bot."""
import asyncio
import logging
import sys

from config import CONFIG
from odds_client import OddsClient
from selector import ParlaySelector
from telegram import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("parlay_bot")


async def main():
    logger.info("🚀 Iniciando Parlay Bot...")

    if not CONFIG.ODDS_API_KEY:
        logger.error("❌ Falta ODDS_API_KEY en variables de entorno.")
        sys.exit(1)

    client = OddsClient()
    selector = ParlaySelector()
    notifier = TelegramNotifier()

    try:
        logger.info("Consultando deportes en temporada...")
        sports = await client.get_in_season_sports()
        logger.info(f"Deportes activos encontrados: {len(sports)}")

        if not sports:
            await notifier.send_parlay(selector.build_parlay([]))
            return

        logger.info("Descargando odds...")
        all_odds = await client.get_all_odds(sports)
        logger.info(f"Deportes con odds disponibles: {len(all_odds)}")

        today_odds = {}
        for sport, events in all_odds.items():
            today_events = [e for e in events if client.is_today(e.get("commence_time", ""))]
            if today_events:
                today_odds[sport] = today_events
                logger.info(f"  {sport}: {len(today_events)} eventos hoy")

        candidates = selector.extract_picks(today_odds)
        parlay = selector.build_parlay(candidates)

        logger.info(f"Enviando parlay con {len(parlay.picks)} picks (cuota: {parlay.total_odd})...")
        await notifier.send_parlay(parlay)

        logger.info(
            f"✅ Listo. Requests usados este mes: {client.requests_used}, "
            f"restantes: {client.requests_remaining}"
        )

    finally:
        await client.close()
        await notifier.close()


if __name__ == "__main__":
    asyncio.run(main())
