"""Verifica resultados al final del día."""
import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from config import CONFIG
from sheets_client import SheetsClient
from sportsdb_client import SportsDBClient
from telegram import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("results_checker")
COLOMBIA_TZ = timezone(timedelta(hours=-5))


async def main():
    logger.info("🌙 === RESULTS CHECKER — MODO NOCHE ===")

    sheets = SheetsClient()
    sportsdb = SportsDBClient()
    telegram = TelegramNotifier()

    try:
        today_str = datetime.now(COLOMBIA_TZ).strftime("%d/%m/%Y")
        iso_date = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d")

        pending = sheets.get_pending_picks(today_str)
        if not pending:
            msg = (
                f"📭 *Verificación nocturna — {today_str}*\n\n"
                "No se encontraron picks pendientes en el Sheet para hoy.\n"
                "¿Se generó el parlay esta mañana? Revisa el Sheet manualmente."
            )
            await telegram._send_message(msg)
            return

        by_sport = defaultdict(list)
        for p in pending:
            sport_name = CONFIG.SPORTSDB_SPORT_MAP.get(p["sport_key"], "")
            if sport_name:
                by_sport[sport_name].append(p)
            else:
                logger.warning(f"No hay mapeo TheSportsDB para {p['sport_key']}")

        all_results = []
        total_odd = 0.0

        for sport_name, picks in by_sport.items():
            logger.info(f"Consultando {sport_name}...")
            events = await sportsdb.get_events_by_date(sport_name, iso_date)
            for pick in picks:
                matched = sportsdb.find_match([pick], events)
                if matched:
                    score, status = sportsdb.determine_winner(matched, pick["pick"])
                    sheets.update_result(pick["row_index"], score, status)
                    all_results.append({
                        "sport": pick["deporte"], "home": pick["local"], "away": pick["visitante"],
                        "pick": pick["pick"], "score": score, "status": status,
                    })
                    try:
                        acc = float(str(pick.get("cuota_acumulada", "0")).replace(",", "."))
                        if acc > total_odd:
                            total_odd = acc
                    except ValueError:
                        pass
                else:
                    logger.warning(f"No match: {pick['local']} vs {pick['visitante']}")
                    all_results.append({
                        "sport": pick["deporte"], "home": pick["local"], "away": pick["visitante"],
                        "pick": pick["pick"], "score": "N/A", "status": "⏳ PENDIENTE",
                    })

        won_count = sum(1 for r in all_results if r["status"] == "✅ GANADA")
        lost_count = sum(1 for r in all_results if r["status"] == "❌ PERDIDA")
        pending_count = sum(1 for r in all_results if r["status"] == "⏳ PENDIENTE")
        all_won = (won_count > 0 and lost_count == 0 and pending_count == 0)

        await telegram.send_results_summary(today_str, all_results, all_won, total_odd)
        logger.info("✅ Verificación completada.")
    finally:
        await sportsdb.close()
        await telegram.close()


if __name__ == "__main__":
    asyncio.run(main())
