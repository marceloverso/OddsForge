import json
import math
import logging
import time
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  🔧 ODDSFORGE - FUNCIONES PRINCIPALES
# ═══════════════════════════════════════════════════════════════

# ─── SESIÓN HTTP CON REINTENTOS ────────────────────────────
def crear_sesion():
    """Crea sesión HTTP con reintentos automáticos"""
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

SESION = crear_sesion()

# ─── UTILIDADES DE HORA ────────────────────────────────────
def hora_colombia():
    """Retorna hora actual en Colombia (UTC-5)"""
    return datetime.now(timezone.utc) - timedelta(hours=5)

def get_bloque_actual():
    """Retorna el bloque de ejecución actual"""
    hora = hora_colombia().hour
    hora_norm = hora if hora >= 7 else hora + 24
    for nombre, (inicio, fin) in config.BLOQUES_EJECUCION.items():
        if inicio <= hora_norm < fin:
            return nombre
    return None

def es_hora_cierre():
    """True si es hora de cierre (23:00 Col) - Para Claude AI"""
    hora = hora_colombia().hour
    return 23 <= hora < 24

# ─── CÁLCULOS MATEMÁTICOS ──────────────────────────────────
def calcular_poisson(avg_home, avg_away, threshold=3.5):
    """Calcula probabilidad Poisson de <threshold goles"""
    if not avg_home or not avg_away or avg_home <= 0 or avg_away <= 0:
        return 0.0
    
    def poisson_prob(lmb, k):
        return (math.exp(-lmb) * (lmb**k)) / math.factorial(k)
    
    prob = 0
    for h in range(6):
        for a in range(6):
            if (h + a) < threshold:
                prob += poisson_prob(avg_home, h) * poisson_prob(avg_away, a)
    
    return round(prob * 100, 1)

def calcular_value(prob_real, cuota):
    """Calcula value betting %"""
    if not cuota or cuota <= 0:
        return 0.0
    return round(((prob_real / 100) * cuota - 1) * 100, 2)

# ─── APIS EXTERNAS ────────────────────────────────────────
def get_todos_los_partidos():
    """Obtiene todos los partidos de hoy con cuotas"""
    try:
        r = SESION.get(
            f"{config.ODDS_BASE}/sports/soccer/odds",
            params={
                "apiKey": config.API_KEY,
                "regions": "eu",
                "markets": "totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso"
            },
            timeout=30
        )
        
        usados = r.headers.get("x-requests-used", "?")
        restantes = r.headers.get("x-requests-remaining", "?")
        logger.info(f"📡 Odds API: {usados} usados / {restantes} restantes")
        
        if r.status_code in [401, 429] or not r.ok:
            logger.warning(f"⚠️ API error {r.status_code}")
            return []
        
        data = r.json()
        logger.info(f"✅ {len(data)} partidos obtenidos")
        return data
    
    except Exception as e:
        logger.error(f"💥 {type(e).__name__}: {e}")
        return []

def extraer_cuotas(partido, thresholds=[2.5, 3.5]):
    """Extrae cuotas para múltiples thresholds"""
    try:
        resultado = {}
        
        for threshold in thresholds:
            cuotas_under, cuotas_over = [], []
            
            for bm in partido.get("bookmakers", []):
                for market in bm.get("markets", []):
                    if market["key"] != "totals":
                        continue
                    
                    for outcome in market["outcomes"]:
                        point = float(outcome.get("point", 0))
                        if abs(point - threshold) < 0.01:
                            if outcome["name"] == "Under":
                                cuotas_under.append(float(outcome["price"]))
                            elif outcome["name"] == "Over":
                                cuotas_over.append(float(outcome["price"]))
            
            if cuotas_under:
                avg_u = round(sum(cuotas_under) / len(cuotas_under), 2)
                avg_o = round(sum(cuotas_over) / len(cuotas_over), 2) if cuotas_over else None
                
                resultado[f"t{threshold}"] = {
                    "under": avg_u,
                    "over": avg_o,
                    "nbm": len(cuotas_under)
                }
        
        return resultado if resultado else None
    
    except:
        return None

def obtener_h2h(local, visitante):
    """Obtiene H2H (últimos enfrentamientos) con RapidAPI"""
    if not config.RAPIDAPI_KEY:
        return None
    
    try:
        r = requests.get(
            f"https://{config.RAPIDAPI_HOST}/v3/fixtures/headtohead",
            headers={
                "x-rapidapi-key": config.RAPIDAPI_KEY,
                "x-rapidapi-host": config.RAPIDAPI_HOST
            },
            params={
                "h2h": f"{local}-{visitante}",
                "status": "FT"
            },
            timeout=10
        )
        
        if not r.ok:
            return None
        
        data = r.json()
        if not data.get("response") or len(data["response"]) == 0:
            return None
        
        ultimo = data["response"][0]
        
        return {
            "goles_local": ultimo.get("goals", {}).get("home", "?"),
            "goles_visitante": ultimo.get("goals", {}).get("away", "?"),
        }
    
    except Exception as e:
        logger.warning(f"⚠️ H2H: {e}")
        return None

def obtener_resultado_final(local, visitante, fecha_str):
    """Obtiene resultado FINAL del partido una vez terminado"""
    if not config.RAPIDAPI_KEY:
        return None
    
    try:
        # Convertir fecha a formato correcto
        try:
            fecha_obj = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
        except:
            return None
        
        fecha_date = fecha_obj.strftime("%Y-%m-%d")
        
        # Buscar fixture por equipos y fecha
        r = requests.get(
            f"https://{config.RAPIDAPI_HOST}/v3/fixtures",
            headers={
                "x-rapidapi-key": config.RAPIDAPI_KEY,
                "x-rapidapi-host": config.RAPIDAPI_HOST
            },
            params={
                "date": fecha_date,
                "status": "FT"  # FT = Final Time (Tiempo Final)
            },
            timeout=10
        )
        
        if not r.ok:
            return None
        
        data = r.json()
        if not data.get("response"):
            return None
        
        # Buscar el partido exacto
        for fixture in data["response"]:
            home = fixture.get("teams", {}).get("home", {}).get("name", "").lower()
            away = fixture.get("teams", {}).get("away", {}).get("name", "").lower()
            
            if local.lower() in home and visitante.lower() in away:
                goals_home = fixture.get("goals", {}).get("home")
                goals_away = fixture.get("goals", {}).get("away")
                
                if goals_home is not None and goals_away is not None:
                    total_goles = goals_home + goals_away
                    
                    return {
                        "resultado": f"{goals_home}-{goals_away}",
                        "goles_local": goals_home,
                        "goles_visitante": goals_away,
                        "total_goles": total_goles,
                        "status": "FT"
                    }
        
        return None
    
    except Exception as e:
        logger.warning(f"⚠️ obtener_resultado_final: {e}")
        return None

def actualizar_alerta_con_resultado(historial, alert_id, resultado_dict):
    """Actualiza alerta con resultado final y calcula W/L"""
    try:
        for alerta in historial.get("alertas", []):
            if alerta.get("id") == alert_id and alerta.get("estado") == "pendiente":
                
                tipo = alerta.get("tipo", "")
                threshold = alerta.get("threshold", 3.5)
                goles_totales = resultado_dict.get("total_goles", 0)
                cuota = alerta.get("cuota", 0)
                apuesta = alerta.get("apuesta_cop", 0)
                
                # Determinar si ganó o perdió
                if "under35" in tipo:
                    # Under 3.5: gana si MENOS de 4 goles
                    gano = goles_totales < 4
                elif "over25" in tipo:
                    # Over 2.5: gana si 3 O MÁS goles
                    gano = goles_totales >= 3
                else:
                    return False
                
                # Actualizar alerta
                alerta["resultado"] = resultado_dict.get("resultado", "")
                alerta["estado"] = "ganada" if gano else "perdida"
                
                if gano:
                    alerta["ganancia_real"] = round(apuesta * (cuota - 1))
                else:
                    alerta["ganancia_real"] = -apuesta
                
                logger.info(f"✅ Alerta actualizada: {alerta['local']} vs {alerta['visitante']} | {resultado_dict.get('resultado')} | {'GANADA' if gano else 'PERDIDA'}")
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ actualizar_alerta_con_resultado: {e}")
        return False

def buscar_y_actualizar_resultados(historial):
    """Busca resultados de alertas pendientes y las actualiza"""
    try:
        actualizadas = 0
        
        for alerta in historial.get("alertas", []):
            # Solo procesa alertas pendientes
            if alerta.get("estado") != "pendiente":
                continue
            
            local = alerta.get("local", "")
            visitante = alerta.get("visitante", "")
            fecha = alerta.get("commence_time", "")
            
            # Obtener resultado
            resultado = obtener_resultado_final(local, visitante, fecha)
            
            if resultado:
                # Actualizar alerta
                if actualizar_alerta_con_resultado(historial, alerta.get("id"), resultado):
                    actualizadas += 1
                    time.sleep(0.5)  # Rate limit
        
        if actualizadas > 0:
            logger.info(f"📊 {actualizadas} alerta(s) actualizada(s) con resultado(s)")
        
        return actualizadas
    
    except Exception as e:
        logger.error(f"❌ buscar_y_actualizar_resultados: {e}")
        return 0
        
# ─── PARSEO DE PARTIDOS ──────────────���─────────────────────
def es_hoy_y_futuro(commence_time_str):
    """Valida que el partido sea hoy y en el futuro"""
    try:
        utc_time = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
        col_time = utc_time - timedelta(hours=5)
        return col_time.date() == hora_colombia().date() and utc_time > datetime.now(timezone.utc)
    except:
        return False

def hora_local_col(commence_time_str):
    """Convierte hora UTC a hora Colombia"""
    try:
        utc_time = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
        return (utc_time - timedelta(hours=5)).strftime("%H:%M")
    except:
        return "??"

def nombre_liga(partido):
    """Extrae nombre de liga"""
    return partido.get("sport_title", "?")

# ─── SEGURIDAD HTML ────────────────────────────────────────
def safe_html(value):
    """Escapa caracteres peligrosos para HTML"""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#39;")
    return text

# ─── SCORING ────────────────────────────────────────────────
def calcular_score(threshold, rate, cuota, cuota_alt, num_bm, prob_poisson, es_under=True):
    """Calcula score de alerta (0-100)"""
    try:
        if not cuota or cuota <= 0:
            return 0, [], 0
        
        score = 0
        razones = []
        
        # Liga
        if es_under:
            lp = max(0, min(round((rate - 0.50) * 200), 20))
        else:
            lp = max(0, min(round(((1-rate) - 0.30) * 200), 20))
        
        score += lp
        razones.append(f"Liga {round(rate*100 if es_under else (1-rate)*100)}%: +{lp}")
        
        # Value
        prob_calc = prob_poisson if es_under else (100 - prob_poisson)
        value_pct = calcular_value(prob_calc, cuota)
        
        if value_pct > 10:
            vp = 35
        elif value_pct > 5:
            vp = 25
        elif value_pct > 2:
            vp = 15
        elif value_pct > 0:
            vp = 5
        else:
            vp = 0
        
        score += vp
        razones.append(f"Value: {value_pct}% | Prob: {prob_calc}%: +{vp}")
        
        # Cuota
        if es_under:
            if 1.40 <= cuota <= 1.60:
                rp = 15
            elif 1.60 < cuota <= 1.75:
                rp = 12
            else:
                rp = 8
        else:
            if 1.80 <= cuota <= 2.10:
                rp = 15
            elif 2.10 < cuota <= 2.40:
                rp = 12
            else:
                rp = 8
        
        score += rp
        razones.append(f"Cuota {cuota}: +{rp}")
        
        # Bookmakers
        bp = 10 if num_bm >= 10 else (7 if num_bm >= 6 else 3)
        score += bp
        razones.append(f"{num_bm} BM: +{bp}")
        
        return min(score, 100), razones, value_pct
    
    except Exception as e:
        logger.error(f"❌ score: {e}")
        return 0, [], 0

# ─── TELEGRAM ────────────────────────────────────────────
def enviar_telegram(msg):
    """Envía mensaje a Telegram"""
    if not msg:
        return False
    
    try:
        chunks = [msg[i:i+3900] for i in range(0, len(msg), 3900)]
        
        for chunk in chunks:
            if not chunk.strip():
                continue
            
            r = SESION.post(
                f"{config.TELEGRAM_API}/sendMessage",
                json={"chat_id": config.CHAT_ID, "text": chunk, "parse_mode": "HTML"},
                timeout=10
            )
            
            if not r.ok:
                logger.error(f"⚠️ Telegram {r.status_code}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"⚠️ Telegram: {e}")
        return False

def formatear_alerta(tipo, threshold, liga, local, visitante, hora_col, score, cuota, 
                     prob, value_pct, razones, h2h=None):
    """Formatea alerta profesional para Telegram"""
    try:
        apuesta = config.BASE_STAKE
        
        if "under" in tipo.lower():
            emoji = "🔥" if score >= 80 else "🔵"
            msg_tipo = f"UNDER {threshold}"
        else:
            emoji = "🔥" if score >= 80 else "⚪"
            msg_tipo = f"OVER {threshold}"
        
        barra = "█" * round(score/10) + "░" * (10 - round(score/10))
        
        msg = (
            f"{emoji} <b>ALERTA: {msg_tipo}</b>\n\n"
            f"⚽ <b>{safe_html(local)} vs {safe_html(visitante)}</b>\n"
            f"🏆 {safe_html(liga)}\n"
            f"⏰ {hora_col} (Col)\n\n"
            f"📊 <b>ANÁLISIS MATEMÁTICO</b>\n"
            f"🧮 Probabilidad: {prob}%\n"
            f"💎 Value: +{value_pct}% ⭐\n"
            f"📈 Score: {score}/100\n"
            f"<code>{barra}</code>\n\n"
        )
        
        if h2h:
            msg += (
                f"📝 <b>H2H</b>\n"
                f"  • {safe_html(local)}: {h2h.get('goles_local', '?')}\n"
                f"  • {safe_html(visitante)}: {h2h.get('goles_visitante', '?')}\n\n"
            )
        
        msg += (
            f"💰 <b>GESTIÓN DE RIESGO</b>\n"
            f"💵 Stake: ${apuesta:,} COP\n"
            f"⚖️ Cuota: {cuota}\n\n"
            f"<b>Razones:</b>\n"
        )
        
        for r in razones[:4]:
            msg += f"  {safe_html(r)}\n"
        
        msg += f"\n⚠️ Bet responsibly"
        
        return msg
    
    except Exception as e:
        logger.error(f"❌ Formato: {e}")
        return ""

# ─── HISTORIAL ────────────────────────────────────────────
def ensure_historial(historial):
    """Asegura estructura del historial"""
    if not isinstance(historial, dict):
        historial = {}
    historial.setdefault("alertas", [])
    return historial

def cargar_historial():
    """Carga historial desde JSON"""
    if config.HISTORIAL_F.exists():
        try:
            with open(config.HISTORIAL_F, "r", encoding="utf-8") as f:
                h = ensure_historial(json.load(f))
                logger.info(f"✅ Historial cargado: {len(h.get('alertas', []))} alertas")
                return h
        except Exception as e:
            logger.warning(f"⚠️ Error cargando historial: {e}")
    
    return ensure_historial({})

def guardar_historial(historial):
    """Guarda historial a JSON"""
    try:
        historial = ensure_historial(historial)
        with open(config.HISTORIAL_F, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Historial guardado: {len(historial['alertas'])} alertas")
    except Exception as e:
        logger.error(f"❌ Error guardando: {e}")

def build_alert_id(tipo, local, visitante, sport_key, commence_time):
    """Genera ID único para alerta"""
    raw = "|".join([str(tipo or ""), str(sport_key or ""), str(commence_time or ""),
                    str(local or "").lower(), str(visitante or "").lower()])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

def registrar_alerta(historial, tipo, threshold, local, visitante, liga, score, cuota, 
                     hora_col, sport_key, commence_time, value_pct, h2h=None):
    """Registra nueva alerta en historial"""
    historial = ensure_historial(historial)
    alert_id = build_alert_id(tipo, local, visitante, sport_key, commence_time)
    existentes = {a.get("id") for a in historial["alertas"]}
    
    if alert_id in existentes:
        logger.warning(f"⚠️ Alerta duplicada: {local} vs {visitante}")
        return False
    
    apuesta = config.BASE_STAKE
    alerta = {
        "id": alert_id,
        "fecha": hora_colombia().strftime("%Y-%m-%d"),
        "tipo": tipo,
        "threshold": threshold,
        "local": local,
        "visitante": visitante,
        "liga": liga,
        "score": score,
        "cuota": cuota,
        "value_pct": value_pct,
        "hora_col": hora_col,
        "apuesta_cop": apuesta,
        "h2h": h2h,
        "estado": "pendiente",
        "resultado": None,
        "ganancia_real": 0,
    }
    
    historial["alertas"].append(alerta)
    logger.info(f"📝 {tipo.upper()} {threshold}: {local} vs {visitante}")
    return True

# ─── GOOGLE SHEETS ────────────────────────────────────────
def sincronizar_google_sheets(historial):
    """Sincroniza alertas con Google Sheets"""
    if not config.GOOGLE_SERVICE_ACCOUNT_JSON or not config.GOOGLE_SHEET_ID:
        logger.warning("⚠️ Google Sheets no configurado")
        return False
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        creds_dict = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                 "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
        
        alertas = historial.get("alertas", [])
        
        if not alertas:
            logger.warning("⚠️ Sin alertas para sincronizar")
            return False
        
        # Obtener o crear hoja
        try:
            ws = sh.worksheet("OddsForge")
            logger.info("✅ Hoja OddsForge encontrada")
        except:
            ws = sh.add_worksheet(title="OddsForge", rows=2000, cols=18)
            logger.info("✅ Hoja OddsForge creada")
        
        # Headers
        headers = ["#", "Fecha", "Hora", "Local", "Visitante", "Liga", "Tipo",
                   "Threshold", "Score", "Value%", "Cuota", "Apuesta", "H2H", 
                   "Resultado", "W-L", "Ganancia", "Balance", "Estado"]
        
        # Construir filas
        todas_filas = [headers]
        balance = config.BANKROLL
        
        for idx, a in enumerate(sorted(alertas, key=lambda x: x.get("fecha", "")), 1):
            estado = a.get("estado", "pendiente")
            resultado = (a.get("resultado") or "").replace("-", "x") if a.get("resultado") else ""
            ganancia = a.get("ganancia_real", 0) if estado != "pendiente" else ""
            wl = "W" if estado == "ganada" else ("L" if estado == "perdida" else "⏳")
            
            h2h_str = ""
            if a.get("h2h"):
                h2h_str = f"{a['h2h'].get('goles_local', '?')}-{a['h2h'].get('goles_visitante', '?')}"
            
            if isinstance(ganancia, (int, float)):
                balance += ganancia
            
            todas_filas.append([
                idx,
                a.get("fecha", ""),
                a.get("hora_col", ""),
                a.get("local", ""),
                a.get("visitante", ""),
                a.get("liga", ""),
                a.get("tipo", "").upper(),
                a.get("threshold", ""),
                a.get("score", ""),
                f"{a.get('value_pct', 0)}%",
                a.get("cuota", ""),
                a.get("apuesta_cop", ""),
                h2h_str,
                resultado,
                wl,
                ganancia if isinstance(ganancia, (int, float)) else "",
                balance if estado != "pendiente" else "",
                estado
            ])
        
        # Actualizar
        ws.clear()
        ws.update("A1", todas_filas, value_input_option="USER_ENTERED")
        logger.info(f"✅ Sheets: {len(todas_filas)-1} alertas")
        
        # Aplicar estilos
        aplicar_estilos_sheets(ws, len(todas_filas), config.BANKROLL)
        
        return True
    
    except ImportError:
        logger.warning("⚠️ gspread no instalado")
        return False
    except Exception as e:
        logger.error(f"❌ Sheets: {e}")
        return False

def aplicar_estilos_sheets(ws, num_rows, bankroll_inicial):
    """Aplica estilos a Google Sheets"""
    try:
        from gspread.formatting import CellFormat, Color, PatternFill
        
        # Header azul
        header_fill = PatternFill(backgroundColor=Color(0.2, 0.3, 0.5), fill_type="SOLID")
        header_fmt = CellFormat(patternFill=header_fill)
        ws.format("A1:R1", header_fmt)
        
        # Colores por balance
        for row_idx in range(2, min(num_rows + 1, 2000)):
            try:
                balance_val = ws.cell(row_idx, 17).value
                
                if balance_val:
                    balance = float(str(balance_val).replace(",", ""))
                    
                    if balance > bankroll_inicial:
                        color = Color(0.6, 1, 0.6)  # Verde
                    elif balance < bankroll_inicial:
                        color = Color(1, 0.7, 0.7)  # Rojo
                    else:
                        color = Color(1, 1, 0.9)    # Amarillo
                    
                    fmt = CellFormat(patternFill=PatternFill(backgroundColor=color, fill_type="SOLID"))
                    ws.format(f"A{row_idx}:R{row_idx}", fmt)
            except:
                pass
        
        logger.info("✅ Estilos aplicados")
    except Exception as e:
        logger.warning(f"⚠️ Estilos: {e}")

# ─── ESTADÍSTICAS ────────────────────────────────────────
def calcular_stats():
    """Calcula estadísticas del día"""
    try:
        historial = cargar_historial()
        alertas = historial.get("alertas", [])
        
        resueltas = [a for a in alertas if a["estado"] != "pendiente"]
        if not resueltas:
            return None
        
        ganadas = sum(1 for a in resueltas if a["estado"] == "ganada")
        perdidas = sum(1 for a in resueltas if a["estado"] == "perdida")
        wr = round(ganadas / len(resueltas) * 100, 1) if resueltas else 0
        gan_neta = sum(a.get("ganancia_real", 0) for a in resueltas)
        balance = config.BANKROLL + gan_neta
        
        return {
            "total": len(resueltas),
            "ganadas": ganadas,
            "perdidas": perdidas,
            "wr": wr,
            "gan_neta": gan_neta,
            "balance": balance,
            "pendientes": len(alertas) - len(resueltas),
        }
    except Exception as e:
        logger.error(f"❌ Stats: {e}")
        return None

def formatear_stats(stats):
    """Formatea estadísticas para Telegram"""
    if not stats:
        return ""
    
    emoji = "✅" if stats['wr'] > 50 else "⚠️"
    
    msg = (
        f"{emoji} <b>ESTADÍSTICAS ACUMULADAS</b>\n\n"
        f"🎯 Total resueltas: {stats['total']} | Ganadas: {stats['ganadas']}\n"
        f"📊 Win Rate: {stats['wr']}%\n"
        f"💰 Ganancia neta: ${stats['gan_neta']:,} COP\n"
        f"💵 Balance actual: ${stats['balance']:,} COP\n"
        f"⏳ Pendientes: {stats['pendientes']}\n"
        f"📊 Total en historial: {stats['total'] + stats['pendientes']}"
    )
    return msg

# ─── CLAUDE AI ────────────────────────────────────────────
def analisis_claude_ai(stats):
    """Claude AI analiza jornada a las 23:00 Col"""
    if not config.ANTHROPIC_API_KEY or not stats:
        return False
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        prompt = f"""Eres el asistente profesional de OddsForge. Resumen de la jornada de apuestas:

HOY:
- Total alertas: {stats['total']}
- Ganadas: {stats['ganadas']} | Perdidas: {stats['perdidas']}
- Win Rate: {stats['wr']}%
- Ganancia neta: ${stats['gan_neta']:,} COP
- Balance: ${stats['balance']:,} COP
- Pendientes: {stats['pendientes']}

Dale a Marcelo:
1. Emoji de ánimo (✅ excelente / 📊 regular / ⚠️ difícil)
2. 1 observación clave sobre la jornada
3. 1 recomendación para mañana
4. Máximo 80 palabras, sin markdown, profesional"""
        
        message = client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        analisis = message.content[0].text.strip()
        msg = f"🤖 <b>ANÁLISIS CLAUDE AI (23:00 Col)</b>\n\n{analisis}"
        
        enviar_telegram(msg)
        logger.info("✅ Claude AI enviado")
        return True
    
    except ImportError:
        logger.warning("⚠️ anthropic no instalado")
        return False
    except Exception as e:
        logger.error(f"❌ Claude AI: {e}")
        return False
