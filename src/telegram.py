"""Notificador via Telegram Bot."""
import logging

import httpx

from config import CONFIG
from selector import Parlay

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.token = CONFIG.TELEGRAM_BOT_TOKEN
        self.chat_id = CONFIG.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def send_parlay(self, parlay: Parlay) -> bool:
        if not parlay.picks:
            msg = (
                "📭 *Parlay del Día*\n\n"
                "No se encontraron suficientes partidos hoy para armar un parlay.\n"
                "Intenta mañana. ☕"
            )
            return await self._send_message(msg)

        lines = [
            "🏆 *PARLAY DEL DÍA* 🏆",
            f"📅 Fecha: {self._today_colombia()}",
            f"💰 Apuesta sugerida: ${parlay.stake_cop:,} COP",
            f"📊 Cuota total acumulada: `{parlay.total_odd}`",
            f"💵 Retorno potencial: ${parlay.potential_return:,.0f} COP",
            "",
            f"📋 *PICKS SELECCIONADOS ({len(parlay.picks)}):*",
            "",
        ]

        for i, pick in enumerate(parlay.picks, 1):
            lines.append(
                f"{i}. *{pick.sport_title}*\n"
                f"   🏠 {pick.home_team} vs {pick.away_team}\n"
                f"   🎯 Pick: `{pick.selection}`\n"
                f"   📈 Cuota: `{pick.odd}`"
            )

        lines.extend(["", parlay.disclaimer])

        message = "\n".join(lines)
        return await self._send_message(message)

    async def send_results_summary(self, date_str: str, results: list, all_won: bool, total_odd: float) -> bool:
        """Envía resumen de resultados al final del día."""
        won_count = sum(1 for r in results if r["status"] == "✅ GANADA")
        lost_count = sum(1 for r in results if r["status"] == "❌ PERDIDA")
        pending_count = sum(1 for r in results if r["status"] == "⏳ PENDIENTE")

        if all_won and won_count > 0:
            header = (
                "🎉🎉🎉 *¡FELICIDADES, CORONAMOS EL PARLAY!* 🎉🎉🎉\n"
                f"📅 Fecha: {date_str}\n"
                f"📊 Cuota acumulada: `{total_odd}`\n"
                f"💵 Si apostaste $2.000 COP, cobraste ${2000*total_odd:,.0f} COP\n\n"
                "🏆 Todos los picks fueron ganadores. ¡Buena lectura!"
            )
        else:
            header = (
                f"📉 *RESUMEN DEL DÍA — {date_str}*\n\n"
                f"✅ Ganadas: {won_count}\n"
                f"❌ Perdidas: {lost_count}\n"
                f"⏳ Pendientes (no encontradas en DB): {pending_count}\n\n"
                "El parlay no cobró, pero seguimos en la lucha. 💪"
            )

        lines = [header, "", "*DETALLE:*"]
        for r in results:
            emoji = "✅" if r["status"] == "✅ GANADA" else ("❌" if r["status"] == "❌ PERDIDA" else "⏳")
            lines.append(
                f"{emoji} {r['sport']} | {r['home']} vs {r['away']}\n"
                f"   Pick: {r['pick']} | Resultado: {r.get('score', 'N/A')} | {r['status']}"
            )

        message = "\n".join(lines)
        return await self._send_message(message)

    async def _send_message(self, text: str) -> bool:
        if not self.token or not self.chat_id:
            logger.error("Faltan credenciales de Telegram.")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("Mensaje enviado a Telegram.")
            return True
        except Exception as e:
            logger.error(f"Error enviando a Telegram: {e}")
            return False

    @staticmethod
    def _today_colombia() -> str:
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=-5))
        return datetime.now(tz).strftime("%d/%m/%Y")
