import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  🔧 ODDSFORGE - CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# ─── API KEYS ────────────────────────────────────────────────
API_KEY = os.environ.get("API_KEY", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

# ─── BOT SETTINGS ────────────────────────────────────────────
BANKROLL = int(os.environ.get("BANKROLL", 300000))
SCORE_MINIMO = int(os.environ.get("SCORE_MINIMO", 70))
VALUE_BETTING_MIN = int(os.environ.get("VALUE_BETTING_MIN", 2))
BASE_STAKE = int(os.environ.get("BASE_STAKE", 5000))

# ─── PATHS ───────────────────────────────────────────────────
DATA_DIR = Path("./bot_data")
HISTORIAL_F = DATA_DIR / "historial.json"
RESULTADOS_F = DATA_DIR / "resultados.json"
DATA_DIR.mkdir(exist_ok=True)

# ─── API ENDPOINTS ───────────────────────────────────────────
ODDS_BASE = "https://api.the-odds-api.com/v4"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"

# ─── THRESHOLDS ──────────────────────────────────────────────
THRESHOLDS = [2.5, 3.5]  # Solo 2.5 y 3.5
SOLO_UNDER_35_OVER_25 = True  # Solo Under 3.5 + Over 2.5

# ─── RATES POR LIGA ──────────────────────────────────────────
UNDER_RATES = {
    "soccer_colombia_primera_a": 0.70,
    "soccer_argentina_primera_division": 0.70,
    "soccer_chile_campeonato": 0.69,
    "soccer_brazil_campeonato": 0.67,
    "soccer_efl_champ": 0.65,
    "soccer_france_ligue_one": 0.63,
    "soccer_germany_bundesliga": 0.58,
    "soccer_italy_serie_a": 0.63,
    "soccer_spain_la_liga": 0.63,
    "soccer_portugal_primeira_liga": 0.62,
}

# ─── HORARIOS DE EJECUCIÓN ──────────────────────────────────
BLOQUES_EJECUCION = {
    "manana": (7, 10),
    "media_manana": (10, 12),
    "mediodia": (12, 14),
    "tarde": (14, 17),
    "noche": (17, 20),
    "madrugada1": (20, 23),
    "madrugada2": (23, 26),
    "madrugada3": (26, 30),
}

# ─── VALIDACIÓN ──────────────────────────────────────────────
REQUERIDAS = ["API_KEY", "BOT_TOKEN", "CHAT_ID"]

def validar_config():
    """Valida que todas las variables requeridas estén configuradas"""
    faltantes = [v for v in REQUERIDAS if not os.environ.get(v)]
    if faltantes:
        raise ValueError(f"❌ Variables de entorno faltantes: {', '.join(faltantes)}")
    return True
