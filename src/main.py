"""Entry point del Parlay Bot."""
import asyncio
import logging
import sys

from config import CONFIG
from src.odds_client import OddsClient
from src.selector import ParlaySelector
from src.telegram import TelegramNotifier

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
        # 1. Obtener deportes en temporada
        logger.info("Consultando deportes en temporada...")
        sports = await client.get_in_season_sports()
        logger.info(f"Deportes activos encontrados: {len(sports)}")

        if not sports:
            await notifier.send_parlay(selector.build_parlay([]))
            return

        # 2. Obtener odds de todos los deportes
        logger.info("Descargando odds...")
        all_odds = await client.get_all_odds(sports)
        logger.info(f"Deportes con odds disponibles: {len(all_odds)}")

        # 3. Filtrar solo eventos de hoy
        today_odds = {}
        for sport, events in all_odds.items():
            today_events = [e for e in events if client.is_today(e.get("commence_time", ""))]
            if today_events:
                today_odds[sport] = today_events
                logger.info(f"  {sport}: {len(today_events)} eventos hoy")

        # 4. Extraer candidatos
        candidates = selector.extract_picks(today_odds)

        # 5. Construir parlay
        parlay = selector.build_parlay(candidates)

        # 6. Enviar
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
