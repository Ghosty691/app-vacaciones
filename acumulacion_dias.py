"""
acumulacion_dias.py
Gestión del saldo de vacaciones con acumulación interanual.
Usa la columna dias_acumulados de la tabla usuarios (ya no en JSON).
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from database import Session, Usuario, SolicitudVacaciones
from vacaciones_utils import calcular_dias, dias_disponibles, ejecutar_cierre_anual as cierre_anual
from notificaciones import notif_anio_nuevo_saldo, notif_dias_bajos

logger = logging.getLogger(__name__)

DIAS_BASE_ANUALES = 22.0
UMBRAL_DIAS_BAJOS = 5.0


def tipo_dias_usuario(usuario_id: int) -> str:
    session = Session()
    usuario = session.query(Usuario).get(usuario_id)
    session.close()
    if not usuario:
        return "habiles"
    try:
        prefs = json.loads(usuario.preferencias_json or "{}")
        return prefs.get("tipo_dias", "habiles")
    except Exception:
        return "habiles"


def calcular_dias_solicitud(usuario_id: int, inicio: date, fin: date, tipo: Optional[str] = None) -> float:
    if tipo is None:
        tipo = tipo_dias_usuario(usuario_id)
    return calcular_dias(inicio, fin, tipo)


def obtener_saldo(usuario_id: int) -> dict:
    session = Session()
    usuario = session.query(Usuario).get(usuario_id)
    if not usuario:
        session.close()
        return {}

    anio_actual = date.today().year

    pendientes = 0.0
    for s in usuario.solicitudes:
        if s.estado == "pendiente" and s.fecha_inicio.year == anio_actual:
            pendientes += s.dias

    try:
        prefs = json.loads(usuario.preferencias_json or "{}")
    except Exception:
        prefs = {}
    tipo_dias = prefs.get("tipo_dias", "habiles")

    totales    = usuario.dias_vacaciones_totales
    usados     = usuario.dias_vacaciones_usados
    acumulados = float(usuario.dias_acumulados or 0.0)
    disponibles = max(0.0, totales + acumulados - usados - pendientes)

    session.close()
    return {
        "totales":     totales,
        "usados":      usados,
        "pendientes":  pendientes,
        "acumulados":  acumulados,
        "disponibles": disponibles,
        "tipo_dias":   tipo_dias,
        "anio":        anio_actual,
    }


def consumir_dias(usuario_id: int, dias: float) -> float:
    session = Session()
    usuario = session.query(Usuario).get(usuario_id)
    if usuario:
        usuario.dias_vacaciones_usados = (usuario.dias_vacaciones_usados or 0.0) + dias
        session.commit()
    session.close()

    saldo = obtener_saldo(usuario_id)
    disponibles = saldo.get("disponibles", 0.0)
    if disponibles <= UMBRAL_DIAS_BAJOS:
        notif_dias_bajos(usuario_id, disponibles)
    return disponibles


def devolver_dias(usuario_id: int, dias: float):
    session = Session()
    usuario = session.query(Usuario).get(usuario_id)
    if usuario:
        usuario.dias_vacaciones_usados = max(0.0, (usuario.dias_vacaciones_usados or 0.0) - dias)
        session.commit()
    session.close()


def ejecutar_cierre_anual(anio_nuevo: int) -> list[dict]:
    """
    Delega en vacaciones_utils.ejecutar_cierre_anual() y devuelve resumen.
    """
    resumen_dict = cierre_anual(forzar=True)  # fuerza el cierre
    session = Session()
    usuarios = session.query(Usuario).all()
    resultado = []
    for u in usuarios:
        resultado.append({
            "nombre":          u.nombre,
            "email":           u.email,
            "dias_nuevos":     u.dias_vacaciones_totales,
            "dias_acumulados": float(u.dias_acumulados or 0.0),
            "dias_total":      u.dias_vacaciones_totales + float(u.dias_acumulados or 0.0),
        })
    session.close()
    # Enviar notificaciones
    for u in usuarios:
        try:
            notif_anio_nuevo_saldo(
                usuario_id      = u.id,
                anio            = anio_nuevo,
                dias_nuevos     = u.dias_vacaciones_totales,
                dias_acumulados = float(u.dias_acumulados or 0.0),
                dias_total      = u.dias_vacaciones_totales + float(u.dias_acumulados or 0.0),
            )
        except Exception as exc:
            logger.error("[CIERRE_ANUAL] Error notif usuario %s: %s", u.id, exc)
    logger.info("[CIERRE_ANUAL] Procesados %d empleados.", len(resultado))
    return resultado


def guardar_tipo_dias(usuario_id: int, tipo: str):
    if tipo not in ("habiles", "naturales"):
        raise ValueError("tipo debe ser 'habiles' o 'naturales'")
    session = Session()
    u = session.query(Usuario).get(usuario_id)
    if u:
        try:
            prefs = json.loads(u.preferencias_json or "{}")
        except Exception:
            prefs = {}
        prefs["tipo_dias"] = tipo
        u.preferencias_json = json.dumps(prefs, ensure_ascii=False)
        session.commit()
    session.close()


def guardar_canales_extra(usuario_id: int, sms: bool, telefono: str, telegram: bool, telegram_chat_id: str):
    session = Session()
    u = session.query(Usuario).get(usuario_id)
    if u:
        try:
            prefs = json.loads(u.preferencias_json or "{}")
        except Exception:
            prefs = {}
        prefs["notificaciones_extra"] = {"sms": sms, "telegram": telegram}
        prefs["telefono_sms"]         = telefono.strip()
        prefs["telegram_chat_id"]     = telegram_chat_id.strip()
        u.preferencias_json = json.dumps(prefs, ensure_ascii=False)
        session.commit()
    session.close()