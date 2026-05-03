# 🤖 Parlay Bot — The Odds API + Telegram

Bot automatizado que arma un parlay diario (10-14 picks) usando [The Odds API](https://the-odds-api.com) y lo envía a Telegram.

## ⚠️ Disclaimer

Este proyecto es **educativo e informativo**. **No garantiza ganancias**. Las apuestas deportivas conllevan riesgo de pérdida total.

- Apuesta solo dinero que puedas permitirte perder.
- Monto sugerido: **$2.000 COP**.
- Si sientes que el juego está afectando tu vida, busca ayuda: **Coljuegos 01 8000 510 203**.

## 🧠 Lógica de Selección

1. Consulta deportes en temporada vía The Odds API (gratis, no consume quota).
2. Obtiene cuotas **decimales** `h2h` (moneyline) de cada deporte.
3. Filtra solo partidos de **hoy** (hora Colombia, UTC-5).
4. Selecciona **favoritos moderados** con cuota entre **1.35 y 2.30** (sweet spot ~1.65).
5. Respeta la regla: **máximo 4 picks por disciplina deportiva**.
6. Arma un parlay de **10 a 14 juegos**.
7. Calcula cuota acumulada y retorno potencial sobre $2.000 COP.

## 🏗️ Estructura

```
.
├── .github/workflows/daily_parlay.yml   # GitHub Actions (8 AM COL)
├── src/
│   ├── main.py                          # Entry point
│   ├── odds_client.py                   # Cliente The Odds API
│   ├── selector.py                      # Motor de selección
│   └── telegram.py                      # Notificador Telegram
├── config.py                            # Configuración central
└── requirements.txt
```

## 🔑 Variables de Entorno (Secrets en GitHub)

| Secret | Descripción | Obtener en |
|--------|-------------|------------|
| `ODDS_API_KEY` | API key de The Odds API | https://the-odds-api.com |
| `TELEGRAM_BOT_TOKEN` | Token de tu bot de Telegram | @BotFather |
| `TELEGRAM_CHAT_ID` | Tu chat ID de Telegram | @userinfobot |

### Configurar en GitHub

1. Ve a **Settings → Secrets and variables → Actions** en tu repo.
2. Agrega los 3 secrets arriba.

## 🚀 Uso Local (para probar)

```bash
# 1. Clona el repo
git clone <tu-repo>.git
cd parlay-bot

# 2. Crea entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Exporta variables de entorno
export ODDS_API_KEY="tu_key"
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"

# 5. Ejecuta
python src/main.py
```

## 📅 Frecuencia de Ejecución

Por defecto corre **todos los días a las 8:00 AM (hora Colombia)**.

Si solo quieres 2 veces por semana, edita el `cron` en `.github/workflows/daily_parlay.yml`:

```yaml
# Lunes y Viernes a las 8 AM COL
- cron: '0 13 * * 1,5'
```

## 💰 Costo

- **The Odds API Free Tier**: 500 requests/mes [^18^].
- Ejecutando 2 veces por semana (~8 veces/mes) y consultando ~15 deportes: **~120 requests/mes**.
- **Total mensual: $0**.

## 📝 Notas

- Las cuotas son **decimales** (ej: `1.65`), no americanas.
- El bot elige el **favorito** de cada partido si su cuota está en rango óptimo.
- Si no hay suficientes partidos hoy, envía un aviso en vez de un parlay vacío.
- Puedes modificar los deportes priorizados en `config.py` → `SPORTS_PRIORITY`.
