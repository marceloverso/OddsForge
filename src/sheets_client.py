"""Cliente para Google Sheets usando gspread."""
import json
import logging
import os
from typing import List, Dict, Any, Optional

import gspread
from google.oauth2.service_account import Credentials

from config import CONFIG

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsClient:
    """Escribe y lee picks desde Google Sheets."""

    def __init__(self):
        self.sheet_id = CONFIG.GOOGLE_SHEETS_ID
        self.client = None
        self.sheet = None
        self._connect()

    def _connect(self):
        """Autentica con la Service Account."""
        try:
            creds_json = CONFIG.GOOGLE_CREDENTIALS_JSON
            if not creds_json:
                logger.error("Falta GOOGLE_CREDENTIALS_JSON.")
                return

            if creds_json.strip().startswith("{"):
                info = json.loads(creds_json)
                creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            else:
                creds = Credentials.from_service_account_file(creds_json, scopes=SCOPES)

            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.sheet_id).worksheet("Parlays")
            logger.info("Conectado a Google Sheets.")
        except Exception as e:
            logger.error(f"Error conectando a Sheets: {e}")

    def write_picks(self, date_str: str, picks: List[Dict[str, Any]], total_odd: float):
        """Escribe los picks del día como nuevas filas."""
        if not self.sheet:
            logger.error("No hay conexión a Sheets.")
            return

        rows = []
        for pick in picks:
            rows.append([
                date_str,
                pick.get("commence_time", ""),
                pick["sport_key"],
                pick["sport_title"],
                pick["home_team"],
                pick["away_team"],
                pick["selection"],
                pick["odd"],
                "",           # Resultado real (score)
                "⏳ PENDIENTE", # Estado
                str(total_odd), # Cuota acumulada del parlay
            ])

        try:
            self.sheet.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info(f"Escritos {len(rows)} picks en Sheets.")
        except Exception as e:
            logger.error(f"Error escribiendo en Sheets: {e}")

    def get_pending_picks(self, date_str: str) -> List[Dict[str, Any]]:
        """Lee picks del día con estado PENDIENTE."""
        if not self.sheet:
            logger.error("No hay conexión a Sheets.")
            return []

        try:
            records = self.sheet.get_all_records()
            pending = []

            for i, row in enumerate(records, start=2):
                row_fecha = str(row.get("Fecha", "")).strip()
                row_estado = str(row.get("Estado", "")).strip().upper()

                # Comparación robusta: soporta "04/05/2026", "04/05/2026 00:00:00", etc.
                fecha_match = row_fecha.startswith(date_str) or date_str in row_fecha
                estado_match = "PENDIENTE" in row_estado

                if fecha_match and estado_match:
                    pending.append({
                        "row_index": i,
                        "fecha": row.get("Fecha"),
                        "hora": row.get("Hora"),
                        "sport_key": row.get("Sport Key"),
                        "deporte": row.get("Deporte"),
                        "local": row.get("Local"),
                        "visitante": row.get("Visitante"),
                        "pick": row.get("Pick"),
                        "cuota": row.get("Cuota"),
                        "estado": row.get("Estado"),
                        "cuota_acumulada": row.get("Cuota Acumulada"),
                    })

            logger.info(f"Picks pendientes encontrados para {date_str}: {len(pending)}")
            return pending
        except Exception as e:
            logger.error(f"Error leyendo Sheets: {e}")
            return []

    def update_result(self, row_index: int, score: str, status: str):
        """Actualiza una fila con el resultado final."""
        if not self.sheet:
            return
        try:
            self.sheet.update_cell(row_index, 9, score)
            self.sheet.update_cell(row_index, 10, status)
            logger.info(f"Fila {row_index} actualizada: {status}")
        except Exception as e:
            logger.error(f"Error actualizando fila {row_index}: {e}")
