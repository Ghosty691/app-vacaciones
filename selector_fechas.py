from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, Tuple, List
import streamlit as st # type: ignore

from vacaciones_utils import obtener_festivos_anio, es_dia_valido, calcular_dias


def _construir_lista_dias_disponibles(
    tipo_dias: str,
    desde: date = date.today() + timedelta(days=1),
    hasta: date | None = None,
) -> List[date]:
    if hasta is None:
        hasta = date(desde.year + 1, 12, 31)
    festivos = obtener_festivos_anio(desde.year, hasta.year)
    disponibles = []
    d = desde
    while d <= hasta:
        if es_dia_valido(d, tipo_dias, festivos):
            disponibles.append(d)
        d += timedelta(days=1)
    return disponibles


def selector_fechas_vacaciones(
    saldo_disponible: float,
    tipo_dias: str = "habiles",
) -> Tuple[Optional[date], Optional[date], float, bool]:
    hoy = date.today()
    anio_actual = hoy.year

    disponibles = _construir_lista_dias_disponibles(tipo_dias=tipo_dias)
    if not disponibles:
        st.warning("No hay días disponibles en el futuro inmediato.")
        return None, None, 0.0, False

    opciones_str = [d.strftime("%a %d/%m/%Y") for d in disponibles]
    dict_fecha = {s: d for s, d in zip(opciones_str, disponibles)}

    col1, col2 = st.columns(2)
    with col1:
        sel_inicio = st.selectbox("📅 Fecha de inicio", options=opciones_str, key="sf_inicio")
    inicio = dict_fecha[sel_inicio]
    opciones_fin = [s for s, d in dict_fecha.items() if d >= inicio]
    with col2:
        sel_fin = st.selectbox("📅 Fecha de fin", options=opciones_fin, key="sf_fin")
    fin = dict_fecha[sel_fin]

    dias = calcular_dias(inicio, fin, tipo_dias)
    label_tipo = "naturales" if tipo_dias == "naturales" else "hábiles"

    es_valido = True
    errores = []
    if fin < inicio:
        errores.append("La fecha de fin no puede ser anterior a la de inicio.")
        es_valido = False
    if dias == 0:
        errores.append("El rango no contiene días disponibles.")
        es_valido = False
    elif dias > saldo_disponible:
        errores.append(f"No tienes saldo suficiente. Solicitas {dias:.0f} días, pero solo tienes {saldo_disponible:.1f}.")
        es_valido = False

    if errores:
        for e in errores:
            st.error(f"⛔ {e}")
    else:
        st.success(f"✅ **{dias:.0f} días {label_tipo}** del {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}.")

    # Festivos del año (informativo)
    with st.expander(f"📆 Ver festivos {anio_actual}", expanded=False):
        festivos_anio = sorted(obtener_festivos_anio(anio_actual))
        for f in festivos_anio:
            st.markdown(f"🔴 {f.strftime('%d/%m/%Y')}")

    # Festivos intermedios en modo hábiles
    if es_valido and tipo_dias == "habiles":
        festivos_rango = [f for f in obtener_festivos_anio(inicio.year, fin.year) if inicio <= f <= fin]
        if festivos_rango:
            st.info(f"ℹ️ Hay {len(festivos_rango)} festivo(s) en el rango que no se descuentan.")

    return inicio, fin, dias, es_valido