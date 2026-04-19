# 🔥 OddsForge

**Professional Betting Alerts - Under 3.5 & Over 2.5**

Un bot automatizado que analiza partidos de fútbol en tiempo real y envía alertas de apuestas de valor.

## ✨ Características

- 🔵 **Under 3.5**: Alertas para partidos con <4 goles
- ⚪ **Over 2.5**: Alertas para partidos con ≥3 goles
- 🌍 **Multi-liga**: Analiza TODAS las ligas disponibles
- 📊 **Google Sheets**: Sincronización automática con estilos
- 🤖 **Claude AI**: Análisis de jornada a las 23:00 Col
- 📝 **H2H**: Últimos enfrentamientos (si RapidAPI está disponible)
- 💰 **Value Betting**: Solo alertas con value > 2%
- ✅ **Cero Duplicados**: Sistema de IDs único

## 🎯 Qué Hace OddsForge

### Análisis
1. Obtiene todos los partidos de hoy con cuotas
2. Calcula probabilidades Poisson (matemática)
3. Calcula Value Betting %
4. Genera score de confianza (0-100)
5. Solo alerta si:
   - Score ≥ 70
   - Value ≥ 2%

### Alertas
Envía a Telegram:
- Equipos y liga
- Hora del partido (Colombia)
- Análisis matemático
- H2H si está disponible
- Stake recomendado
- Razones del alert

### Registro
- Guarda en `historial.json`
- Sincroniza con Google Sheets
- Aplica colores automáticos (Verde/Rojo)

### Análisis Final
A las 23:00 Col envía resumen con Claude AI:
- Win rate de la jornada
- Ganancia/Pérdida
- Recomendaciones

## 📦 Instalación

### 1. Clonar el repo
```bash
git clone https://github.com/marceloverso/OddsForge.git
cd OddsForge
