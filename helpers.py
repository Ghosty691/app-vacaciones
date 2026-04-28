"""
utils/helpers.py
────────────────
Funciones auxiliares reutilizables para todo el sistema de vacaciones
y compensación de horas.
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# FESTIVOS Y DÍAS HÁBILES
# ─────────────────────────────────────────────────────────────────────────────

FESTIVOS_2024 = {
    date(2024, 1, 1), date(2024, 1, 6),  date(2024, 3, 29),
    date(2024, 5, 1), date(2024, 8, 15), date(2024, 10, 12),
    date(2024, 11, 1), date(2024, 12, 6), date(2024, 12, 8),
    date(2024, 12, 25),
}

FESTIVOS_2025 = {
    date(2025, 1, 1),  date(2025, 1, 6),  date(2025, 4, 17),
    date(2025, 4, 18), date(2025, 5, 1),  date(2025, 8, 15),
    date(2025, 10, 12), date(2025, 11, 1), date(2025, 12, 6),
    date(2025, 12, 8),  date(2025, 12, 25),
}

TODOS_LOS_FESTIVOS = FESTIVOS_2024 | FESTIVOS_2025


def es_dia_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in TODOS_LOS_FESTIVOS


def calcular_dias_habiles(inicio: date, fin: date) -> int:
    if inicio > fin:
        return 0
    dias = 0
    actual = inicio
    while actual <= fin:
        if es_dia_habil(actual):
            dias += 1
        actual += timedelta(days=1)
    return dias


def fecha_fin_desde_dias(inicio: date, dias_habiles: int) -> date:
    contados = 0
    actual = inicio
    while contados < dias_habiles:
        if es_dia_habil(actual):
            contados += 1
        if contados < dias_habiles:
            actual += timedelta(days=1)
    return actual


# ─────────────────────────────────────────────────────────────────────────────
# HORAS EXTRA
# ─────────────────────────────────────────────────────────────────────────────

def resumen_horas(horas_list) -> dict:
    total       = sum(h.horas for h in horas_list)
    compensadas = sum(h.horas for h in horas_list if h.tipo_compensacion == "compensado")
    pagadas     = sum(h.horas for h in horas_list if h.tipo_compensacion == "pagado")
    pendientes  = total - compensadas - pagadas
    return {"total": total, "compensadas": compensadas,
            "pagadas": pagadas, "pendientes": pendientes}


def horas_a_df(horas_list) -> pd.DataFrame:
    if not horas_list:
        return pd.DataFrame()
    return pd.DataFrame([{
        "Fecha":       h.fecha.strftime("%d/%m/%Y"),
        "Horas":       h.horas,
        "Estado":      h.tipo_compensacion.capitalize(),
        "Descripción": h.descripcion or "—",
    } for h in horas_list])


# ─────────────────────────────────────────────────────────────────────────────
# VACACIONES
# ─────────────────────────────────────────────────────────────────────────────

def dias_disponibles(usuario) -> float:
    return usuario.dias_vacaciones_totales - usuario.dias_vacaciones_usados


def solicitudes_a_df(solicitudes_list) -> pd.DataFrame:
    if not solicitudes_list:
        return pd.DataFrame()
    ICONOS = {"aprobada": "✅", "rechazada": "❌", "pendiente": "⏳"}
    return pd.DataFrame([{
        "Desde":              s.fecha_inicio.strftime("%d/%m/%Y"),
        "Hasta":              s.fecha_fin.strftime("%d/%m/%Y"),
        "Días":               s.dias,
        "Estado":             f"{ICONOS.get(s.estado,'')} {s.estado.capitalize()}",
        "Motivo":             s.motivo or "—",
        "Comentario manager": s.comentario_manager or "—",
    } for s in solicitudes_list])


# ─────────────────────────────────────────────────────────────────────────────
# VALIDACIONES
# ─────────────────────────────────────────────────────────────────────────────

def validar_solicitud(fecha_inicio: date, fecha_fin: date, dias_disponibles_: float):
    if fecha_fin < fecha_inicio:
        return False, "La fecha de fin no puede ser anterior a la de inicio."
    dias = calcular_dias_habiles(fecha_inicio, fecha_fin)
    if dias <= 0:
        return False, "El rango de fechas no contiene días hábiles."
    if fecha_inicio < date.today():
        return False, "No puedes solicitar vacaciones en fechas pasadas."
    if dias > dias_disponibles_:
        return False, f"No tienes suficientes días. Solicitas {dias} pero dispones de {dias_disponibles_}."
    return True, f"Solicitud válida: {dias} día(s) hábil(es)."


def validar_horas_extra(fecha: date, horas: float):
    if fecha > date.today():
        return False, "No puedes registrar horas extra en fechas futuras."
    if horas <= 0:
        return False, "Las horas deben ser un valor positivo."
    if horas > 12:
        return False, "No se pueden registrar más de 12 horas extra en un día."
    return True, "Registro válido."


# ─────────────────────────────────────────────────────────────────────────────
# FORMATO
# ─────────────────────────────────────────────────────────────────────────────

def formato_horas(horas: float) -> str:
    h    = int(horas)
    min_ = int((horas - h) * 60)
    return f"{h}h" if min_ == 0 else f"{h}h {min_}min"


def badge_estado(estado: str) -> str:
    return {"aprobada": "✅", "rechazada": "❌", "pendiente": "⏳",
            "compensado": "🔄", "pagado": "💶"}.get(estado, "❓")


def color_estado(estado: str) -> str:
    return {"aprobada": "#28a745", "rechazada": "#dc3545", "pendiente": "#ffc107",
            "compensado": "#17a2b8", "pagado": "#6f42c1"}.get(estado, "#6c757d")


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICAS STREAMLIT REUTILIZABLES
# ─────────────────────────────────────────────────────────────────────────────

def mostrar_metricas_vacaciones(usuario):
    disponibles = dias_disponibles(usuario)
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Días totales",      f"{usuario.dias_vacaciones_totales:.0f}")
    col2.metric("✈️  Días disfrutados",  f"{usuario.dias_vacaciones_usados:.0f}")
    col3.metric("🟢 Días disponibles",  f"{disponibles:.0f}",
                delta=f"{disponibles:.0f} restantes",
                delta_color="normal" if disponibles > 5 else "inverse")


def mostrar_metricas_horas(horas_list):
    r = resumen_horas(horas_list)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⏱️  Total horas extra", formato_horas(r["total"]))
    c2.metric("🔄 Compensadas",        formato_horas(r["compensadas"]))
    c3.metric("💶 Pagadas",            formato_horas(r["pagadas"]))
    c4.metric("⚠️  Pendientes",        formato_horas(r["pendientes"]),
              delta=f"-{formato_horas(r['pendientes'])}" if r["pendientes"] > 0 else "Al día",
              delta_color="inverse" if r["pendientes"] > 0 else "normal")