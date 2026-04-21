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
            
            # Extraer cuotas (SOLO OVER 1.5 + BTTS)
            cuotas_dict = extraer_cuotas(partido)
            if not cuotas_dict:
                continue
            
            # Obtener H2H
            h2h = obtener_h2h(local, visitante) if config.RAPIDAPI_KEY else None
            
            # ═══════════════════════════════════════════════
            #  ⚪ COMBINADA: OVER 1.5 + AMBOS ANOTAN
            # ═══════════════════════════════════════════════
            
            if "over15" in cuotas_dict and "btts" in cuotas_dict:
                cuota_over15 = cuotas_dict["over15"]["cuota"]
                cuota_btts = cuotas_dict["btts"]["cuota"]
                cuota_combinada = round(cuota_over15 * cuota_btts, 2)
                
                nbm = min(cuotas_dict["over15"]["nbm"], cuotas_dict["btts"]["nbm"])
                
                # Score simple pero efectivo
                score = 0
                razones = []
                
                # Bonus por cuota alta
                if cuota_combinada > 3.5:
                    score += 30
                    razones.append(f"Cuota combinada {cuota_combinada}: +30")
                elif cuota_combinada > 3.0:
                    score += 25
                    razones.append(f"Cuota combinada {cuota_combinada}: +25")
                elif cuota_combinada > 2.5:
                    score += 20
                    razones.append(f"Cuota combinada {cuota_combinada}: +20")
                else:
                    score += 15
                    razones.append(f"Cuota combinada {cuota_combinada}: +15")
                
                # Bonus por bookmakers
                if nbm >= 10:
                    score += 20
                    razones.append(f"{nbm} BM: +20")
                elif nbm >= 6:
                    score += 15
                    razones.append(f"{nbm} BM: +15")
                else:
                    score += 8
                    razones.append(f"{nbm} BM: +8")
                
                # Bonus por H2H
                if h2h and (h2h.get("goles_local", 0) > 0 and h2h.get("goles_visitante", 0) > 0):
                    score += 25
                    razones.append(f"H2H ambos anotan: +25")
                
                score = min(score, 100)
                
                # Validar
                combinada_ok = (score >= config.SCORE_MINIMO)
                
                if combinada_ok:
                    combinada_id = build_alert_id("combinada", local, visitante, sport_key, 
                                                  partido.get("commence_time", ""))
                    
                    if combinada_id not in existing_ids:
                        msg = formatear_alerta_combinada(
                            local=local,
                            visitante=visitante,
                            hora_col=hora_col,
                            score=score,
                            cuota_over15=cuota_over15,
                            cuota_btts=cuota_btts,
                            cuota_combinada=cuota_combinada,
                            razones=razones,
                            h2h=h2h,
                            liga=liga
                        )
                        
                        if msg and enviar_telegram(msg):
                            alertas_enviadas += 1
                            
                            if registrar_alerta_combinada(
                                historial=historial,
                                local=local,
                                visitante=visitante,
                                liga=liga,
                                score=score,
                                cuota_combinada=cuota_combinada,
                                hora_col=hora_col,
                                sport_key=sport_key,
                                commence_time=partido.get("commence_time", ""),
                                h2h=h2h,
                                cuota_over15=cuota_over15,
                                cuota_btts=cuota_btts
                            ):
                                existing_ids.add(combinada_id)
                            
                            # Guardar y sincronizar
                            guardar_historial(historial)
                            sincronizar_google_sheets(historial)
                            
                            import time
                            time.sleep(1)
        
        # ─── GUARDAR HISTORIAL FINAL ──────────────────
        guardar_historial(historial)
        
        # ─── RESUMEN Y ESTADÍSTICAS ──────────────────
        stats = calcular_stats()

        # ─── CONTAR LIGAS ÚNICAS ─────────────────────── ← AQUÍ VA
        ligas_unicas = set()
        for alerta in historial.get("alertas", []):
            if alerta.get("fecha") == hora_colombia().strftime("%Y-%m-%d"):
                ligas_unicas.add(alerta.get("liga", ""))
        
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
