# 🤖 Parlay Bot — Fase 2 (Separado)

Dos workflows independientes:
- **Mañana** (`daily_parlay.yml`): 6:00 AM COL → genera parlay + Telegram + Sheets
- **Noche** (`nightly_results.yml`): 11:30 PM COL → verifica resultados + actualiza Sheets + Telegram

## ⚠️ Disclaimer

Educacional e informativo. No garantiza ganancias. Monto sugerido: $2.000 COP.

## 🏗️ Estructura

```
.
├── .github/workflows/
│   ├── daily_parlay.yml      # 6:00 AM COL
│   └── nightly_results.yml   # 11:30 PM COL
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py               # Mañana
│   ├── results_checker.py    # Noche
│   ├── odds_client.py
│   ├── selector.py           # Con fallback a fútbol
│   ├── telegram.py
│   ├── sheets_client.py      # Logs detallados
│   └── sportsdb_client.py
└── requirements.txt
```

## 🔑 Secrets

| Secret | Descripción |
|--------|-------------|
| `ODDS_API_KEY` | The Odds API |
| `TELEGRAM_BOT_TOKEN` | @BotFather |
| `TELEGRAM_CHAT_ID` | @userinfobot |
| `GOOGLE_SHEETS_ID` | ID del Sheet |
| `GOOGLE_CREDENTIALS_JSON` | JSON completo Service Account |
| `SPORTSDB_API_KEY` | `3` (gratis) o tu key |

## 📊 Consumo

- ~13 requests/día Odds API → ~390/mes (límite 500)
- TheSportsDB: gratis
- Sheets: gratis

## 📝 Sheet

Pestaña debe llamarse exactamente: **`Parlays`**

Headers fila 1:
```
Fecha | Hora | Sport Key | Deporte | Local | Visitante | Pick | Cuota | Resultado | Estado | Cuota Acumulada
```

Comparte el Sheet con el email de la Service Account como **Editor**.
