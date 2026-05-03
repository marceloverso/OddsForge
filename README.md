# 🤖 Parlay Bot — Fase 2 (The Odds API + TheSportsDB + Google Sheets)

Bot automatizado que:
1. **Mañana (8 AM COL)**: Arma un parlay de 10-14 picks y lo envía a Telegram + lo guarda en Google Sheets.
2. **Noche (11 PM COL)**: Verifica resultados vía TheSportsDB, actualiza el Sheet y te dice si coronaste el parlay.

## ⚠️ Disclaimer

Este proyecto es **educativo e informativo**. **No garantiza ganancias**.

- Monto sugerido: **$2.000 COP**.
- Si el juego afecta tu vida: **Coljuegos 01 8000 510 203**.

## 🏗️ Estructura

```
.
├── .github/workflows/
│   ├── daily_parlay.yml      # 8:00 AM COL (Lunes y Viernes)
│   └── nightly_results.yml   # 11:00 PM COL (mismo Lunes y Viernes)
├── src/
│   ├── __init__.py
│   ├── config.py             # Configuración central
│   ├── main.py               # Entry point mañana
│   ├── results_checker.py    # Entry point noche
│   ├── odds_client.py        # Cliente The Odds API
│   ├── selector.py           # Motor de selección
│   ├── telegram.py           # Notificador Telegram
│   ├── sheets_client.py      # Cliente Google Sheets
│   └── sportsdb_client.py    # Cliente TheSportsDB
└── requirements.txt
```

## 🔑 Secrets necesarios en GitHub

Ve a **Settings → Secrets and variables → Actions** y agrega:

| Secret | Descripción | Obligatorio |
|--------|-------------|-------------|
| `ODDS_API_KEY` | API key de The Odds API | Sí (mañana) |
| `TELEGRAM_BOT_TOKEN` | Token de @BotFather | Sí |
| `TELEGRAM_CHAT_ID` | Tu chat ID (@userinfobot) | Sí |
| `GOOGLE_SHEETS_ID` | ID del Google Sheet (de la URL) | Sí (Fase 2) |
| `GOOGLE_CREDENTIALS_JSON` | JSON completo de la Service Account | Sí (Fase 2) |
| `SPORTSDB_API_KEY` | Tu key de TheSportsDB (o deja `"3"`) | Sí (noche) |

## 📊 Configurar Google Sheets

### 1. Crear la Service Account
1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto nuevo.
3. Ve a **APIs & Services → Credentials → Create Credentials → Service Account**.
4. Dale un nombre, crea la cuenta.
5. Ve a la pestaña **Keys → Add Key → JSON**. Se descarga un archivo `.json`.
6. Ve a **APIs & Services → Library**, busca **Google Sheets API** y **Google Drive API**, y actívalas.

### 2. Preparar el Secret
Abre el archivo `.json` descargado, copia TODO el contenido y pégalo como el secret `GOOGLE_CREDENTIALS_JSON` en GitHub.

### 3. Crear el Google Sheet
1. Crea un nuevo Google Sheet.
2. Cambia el nombre de la primera hoja a exactamente: **`Parlays`**
3. En la fila 1, pega estos headers exactos:

```
Fecha | Hora | Sport Key | Deporte | Local | Visitante | Pick | Cuota | Resultado | Estado | Cuota Acumulada
```

4. Comparte el Sheet con el email de la Service Account (se ve como `algo@proyecto.iam.gserviceaccount.com`) dándole permiso de **Editor**.
5. Copia el ID del Sheet de la URL (la parte larga entre `/d/` y `/edit`) y guárdalo en `GOOGLE_SHEETS_ID`.

## 🚀 Cómo funciona

### Mañana (`main.py`)
1. Consulta deportes activos en The Odds API.
2. Obtiene cuotas decimales `h2h`.
3. Filtra partidos de hoy (hora Colombia).
4. Selecciona 10-14 favoritos moderados (cuota 1.35-2.30), máx 4 por deporte.
5. Envía el parlay a Telegram.
6. **Escribe cada pick como una fila en Google Sheets** con estado `⏳ PENDIENTE`.

### Noche (`results_checker.py`)
1. Lee del Sheet los picks del día con estado `PENDIENTE`.
2. Consulta TheSportsDB (`eventsday.php`) por deporte y fecha.
3. Hace **fuzzy matching** por nombre de equipo para encontrar el partido.
4. Compara scores y determina si el pick ganó (`✅ GANADA`) o perdió (`❌ PERDIDA`).
5. Actualiza el Sheet.
6. Si **TODOS** los picks ganaron, dispara a Telegram:
   > 🎉 *¡FELICIDADES, CORONAMOS EL PARLAY!*
7. Si no, envía el resumen con cuántos acertaste.

## ⚠️ Limitaciones de TheSportsDB

- **No comparte IDs** con The Odds API. El match se hace por nombre de equipo (fuzzy).
- En deportes muy exóticos o ligas menores puede no encontrar el partido. Quedará como `⏳ PENDIENTE` y tú lo actualizas manual.
- Es una base **crowdsourced**. La data de hoy suele aparecer unas horas después de terminado el partido.

## 💰 Costo

| Servicio | Costo |
|----------|-------|
| The Odds API | Gratis (500 req/mes) |
| TheSportsDB | Gratis (key pública "3" o registro gratuito) |
| Google Sheets | Gratis |
| GitHub Actions | Gratis (público) o 2,000 min/mes (privado) |
| Telegram Bot | Gratis |

## 📝 Notas

- Si quieres cambiar los días de ejecución, edita los `cron` en ambos workflows.
- Si un pick queda `PENDIENTE` porque TheSportsDB no lo encontró, puedes editar el Sheet manualmente.
- La cuota acumulada se guarda en cada fila para que el resumen nocturno la tenga a la mano.
