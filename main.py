import logging
import sys
from pathlib import Path

import config
from functions import (
    crear_sesion, hora_colombia, get_bloque_actual, es_hora_cierre,
    get_todos_los_partidos, extraer_cuotas, calcular_poisson, calcular_score,
    es_hoy_y_futuro, hora_local_col, nombre_liga, obtener_h2h,
    enviar_telegram, formatear_alerta, registrar_alerta,
    cargar_historial, guardar_historial, sincronizar_google_sheets,
    calcular_stats, formatear_stats, analisis_claude_ai, SESION, buscar_y_actualizar_resultados, build_alert_id
)

# ═══════════════════════════════════════════════════════════════
#  🔥 ODDSFORGE - MAIN
#  Professional Betting Alerts - Under 3.5 & Over 2.5
# ═══════════════════════════════════════════════════════════════

# ─── LOGGING ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ─── VALIDACIÓN DE CONFIG ───────────────────────────────────
try:
    config.validar_config()
    logger.info("✅ Configuración validada")
except ValueError as e:
    logger.critical(f"❌ {e}")
    sys.exit(1)

def main():
    """Ejecución principal del bot"""
    try:
        bloque = get_bloque_actual()
        ahora = hora_colombia().strftime("%Y-%m-%d %H:%M")
        
        if bloque is None:
            logger.info(f"⏸ Fuera de horario de ejecución")
            return
        
        logger.info(f"🔥 ODDSFORGE — {ahora} | Bloque: {bloque}")
        
        # ─── CARGAR HISTORIAL ────────────────────────────
        historial = cargar_historial()
        existing_ids = {a.get("id") for a in historial.get("alertas", [])}
         # ─── ACTUALIZAR RESULTADOS PENDIENTES ─────────
        resultados_actualizados = buscar_y_actualizar_resultados(historial)
        if resultados_actualizados > 0:
            guardar_historial(historial)
            sincronizar_google_sheets(historial)
        
        # ─── OBTENER TODOS LOS PARTIDOS ───────────────
        todos = get_todos_los_partidos()
        
        if not todos:
            logger.warning("⚠️ Sin partidos disponibles")
            return
        
        logger.info(f"📊 Analizando {len(todos)} partidos...")
        
        alertas_enviadas = 0
        partidos_analizados = 0
        
        # ─── ANALIZAR CADA PARTIDO ───────────────────
        for partido in todos:
            # Validar que sea hoy y en el futuro
            if not es_hoy_y_futuro(partido.get("commence_time", "")):
                continue
            
            # Extraer datos
            local = partido.get("home_team", "?")
            visitante = partido.get("away_team", "?")
            hora_col = hora_local_col(partido.get("commence_time", ""))
            sport_key = partido.get("sport_key", "")
            liga = nombre_liga(partido)
            partidos_analizados += 1
            
            # Extraer cuotas
            cuotas_dict = extraer_cuotas(partido, thresholds=[2.5, 3.5])
            if not cuotas_dict:
                continue
            
            # Obtener tasa de Under para esta liga
            under_rate = config.UNDER_RATES.get(sport_key, 0.63)
            
            # Calcular probabilidades Poisson
            prob_poisson_25 = calcular_poisson(1.3, 1.2, threshold=2.5)
            prob_poisson_35 = calcular_poisson(1.3, 1.2, threshold=3.5)
            
            # Obtener H2H (si está disponible)
            h2h = obtener_h2h(local, visitante) if config.RAPIDAPI_KEY else None
            
            # ═══════════════════════════════════════════════
            #  🔵 UNDER 3.5 - MENOS DE 4 GOLES
            # ═══════════════════════════════════════════════
            if "t3.5" in cuotas_dict:
                score_u35, razones_u35, value_u35 = calcular_score(
                    threshold=3.5,
                    rate=under_rate,
                    cuota=cuotas_dict["t3.5"]["under"],
                    cuota_alt=cuotas_dict["t3.5"]["over"],
                    num_bm=cuotas_dict["t3.5"]["nbm"],
                    prob_poisson=prob_poisson_35,
                    es_under=True
                )
                
                # Validar score y value
                under_ok = (score_u35 >= config.SCORE_MINIMO and value_u35 > config.VALUE_BETTING_MIN)
                
                if under_ok:
                    under_id = build_alert_id("under35", local, visitante, sport_key, 
                          partido.get("commence_time", ""))
                    
                    if under_id not in existing_ids:
                        msg = formatear_alerta(
                            tipo="under",
                            threshold="3.5",
                            liga=liga,
                            local=local,
                            visitante=visitante,
                            hora_col=hora_col,
                            score=score_u35,
                            cuota=cuotas_dict["t3.5"]["under"],
                            prob=prob_poisson_35,
                            value_pct=value_u35,
                            razones=razones_u35,
                            h2h=h2h
                        )
                        
                        if msg and enviar_telegram(msg):
                            alertas_enviadas += 1
                            
                            if registrar_alerta(
                                historial=historial,
                                tipo="under35",
                                threshold=3.5,
                                local=local,
                                visitante=visitante,
                                liga=liga,
                                score=score_u35,
                                cuota=cuotas_dict["t3.5"]["under"],
                                hora_col=hora_col,
                                sport_key=sport_key,
                                commence_time=partido.get("commence_time", ""),
                                value_pct=value_u35,
                                h2h=h2h
                            ):
                                existing_ids.add(under_id)
                            
                            # Guardar y sincronizar
                            guardar_historial(historial)
                            sincronizar_google_sheets(historial)
                            
                            import time
                            time.sleep(1)  # Rate limit
            
            # ═══════════════════════════════════════════════
            #  ⚪ OVER 2.5 - 3 O MÁS GOLES
            # ═══════════════════════════════════════════════
            if "t2.5" in cuotas_dict:
                score_o25, razones_o25, value_o25 = calcular_score(
                    threshold=2.5,
                    rate=under_rate,
                    cuota=cuotas_dict["t2.5"]["over"],
                    cuota_alt=cuotas_dict["t2.5"]["under"],
                    num_bm=cuotas_dict["t2.5"]["nbm"],
                    prob_poisson=100 - prob_poisson_25,
                    es_under=False
                )
                
                # Validar score y value
                over_ok = (score_o25 >= config.SCORE_MINIMO and value_o25 > config.VALUE_BETTING_MIN)
                
                if over_ok:
                    over_id = build_alert_id("over25", local, visitante, sport_key,
                                                     partido.get("commence_time", ""))
                    
                    if over_id not in existing_ids:
                        msg = formatear_alerta(
                            tipo="over",
                            threshold="2.5",
                            liga=liga,
                            local=local,
                            visitante=visitante,
                            hora_col=hora_col,
                            score=score_o25,
                            cuota=cuotas_dict["t2.5"]["over"],
                            prob=100 - prob_poisson_25,
                            value_pct=value_o25,
                            razones=razones_o25,
                            h2h=h2h
                        )
                        
                        if msg and enviar_telegram(msg):
                            alertas_enviadas += 1
                            
                            if registrar_alerta(
                                historial=historial,
                                tipo="over25",
                                threshold=2.5,
                                local=local,
                                visitante=visitante,
                                liga=liga,
                                score=score_o25,
                                cuota=cuotas_dict["t2.5"]["over"],
                                hora_col=hora_col,
                                sport_key=sport_key,
                                commence_time=partido.get("commence_time", ""),
                                value_pct=value_o25,
                                h2h=h2h
                            ):
                                existing_ids.add(over_id)
                            
                            # Guardar y sincronizar
                            guardar_historial(historial)
                            sincronizar_google_sheets(historial)
                            
                            import time
                            time.sleep(1)  # Rate limit
        
        # ─── GUARDAR HISTORIAL FINAL ──────────────────
        guardar_historial(historial)
        
        # ─── RESUMEN Y ESTADÍSTICAS ──────────────────
        stats = calcular_stats()
        
        if alertas_enviadas == 0:
            msg = (
                f"🔍 <b>ODDSFORGE</b>\n\n"
                f"📅 {ahora} (Col)\n"
                f"📊 Analicé {partidos_analizados} partido(s)\n\n"
                f"❌ Ningún partido cumple criterios:\n"
                f"   • Score ≥ {config.SCORE_MINIMO}\n"
                f"   • Value ≥ {config.VALUE_BETTING_MIN}%\n\n"
            )
            if stats:
                msg += formatear_stats(stats)
        else:
            # Contar ligas únicas
            ligas_unicas = set()
            for alerta in historial.get("alertas", []):
                if alerta.get("fecha") == hora_colombia().strftime("%Y-%m-%d"):
                ligas_unicas.add(alerta.get("liga", ""))

            msg = (
                f"✅ <b>ODDSFORGE</b>\n\n"
                f"📅 {ahora} (Col)\n"
                f"🎯 {alertas_enviadas} alerta(s) enviada(s)\n"
                f"📊 {partidos_analizados} partidos analizados de {len(ligas_unicas)} liga(s)\n\n"
            )
            if stats:
                msg += formatear_stats(stats)
        
        enviar_telegram(msg)
        logger.info(f"✅ Fin — Partidos analizados: {partidos_analizados} | Alertas: {alertas_enviadas}")
        
        # ─── CLAUDE AI A LAS 23:00 COL ───────────────
        if es_hora_cierre() and stats:
            logger.info("🤖 Enviando análisis Claude AI...")
            analisis_claude_ai(stats)
    
    except Exception as e:
        logger.critical(f"❌ Error fatal: {e}")
        try:
            enviar_telegram(f"❌ ERROR ODDSFORGE\n{str(e)[:100]}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
