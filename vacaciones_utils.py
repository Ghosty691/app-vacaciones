"""
vacaciones_utils.py
Utilidades centrales: festivos (nacionales + personalizados),
cálculo de días, validaciones y cierre anual.
"""

from datetime import date, timedelta
from typing import Set
import holidays as pyholidays # type: ignore

from database import Session, Usuario, FestivoPersonalizado, SolicitudVacaciones


# ── FESTIVOS ────────────────────────────────────────────────────────────────
def obtener_festivos_anio(*anios: int) -> Set[date]:
    festivos: Set[date] = set()
    for anio in anios:
        festivos.update(pyholidays.Spain(years=anio).keys())
    session = Session()
    custom = session.query(FestivoPersonalizado).filter_by(activo=True).all()
    for f in custom:
        festivos.add(f.fecha)
    session.close()
    return festivos


def es_fin_de_semana(d: date) -> bool:
    return d.weekday() >= 5


def es_dia_valido(d: date, tipo: str = "habiles", festivos: Set[date] | None = None) -> bool:
    if festivos is None:
        festivos = obtener_festivos_anio(d.year)
    if tipo == "habiles":
        return not es_fin_de_semana(d) and d not in festivos
    else:
        return d not in festivos  # naturales: solo festivos excluidos


# ── CÁLCULO DE DÍAS ─────────────────────────────────────────────────────────
def calcular_dias(inicio: date, fin: date, tipo: str = "habiles") -> float:
    if fin < inicio:
        return 0.0
    festivos = obtener_festivos_anio(inicio.year, fin.year)
    count = 0
    d = inicio
    while d <= fin:
        if es_dia_valido(d, tipo, festivos):
            count += 1
        d += timedelta(days=1)
    return float(count)


def dias_disponibles(usuario: Usuario) -> float:
    return (usuario.dias_vacaciones_totales
            + (usuario.dias_acumulados or 0.0)
            - usuario.dias_vacaciones_usados)


# ── VALIDACIONES ────────────────────────────────────────────────────────────
def validar_solicitud(usuario: Usuario, inicio: date, fin: date) -> tuple[bool, str, float]:
    if fin < inicio:
        return False, "La fecha de fin no puede ser anterior a la de inicio.", 0.0
    if inicio < date.today():
        return False, "No puedes solicitar vacaciones en fechas pasadas.", 0.0

    festivos = obtener_festivos_anio(inicio.year, fin.year)
    tipo = usuario.tipo_dias or "habiles"

    if not es_dia_valido(inicio, tipo, festivos):
        razon = "es festivo o fin de semana" if tipo == "habiles" else "es festivo"
        return False, f"Inicio ({inicio.strftime('%d/%m/%Y')}) {razon}.", 0.0
    if not es_dia_valido(fin, tipo, festivos):
        razon = "es festivo o fin de semana" if tipo == "habiles" else "es festivo"
        return False, f"Fin ({fin.strftime('%d/%m/%Y')}) {razon}.", 0.0

    dias_sol = calcular_dias(inicio, fin, tipo)
    if dias_sol <= 0:
        return False, "El rango no contiene días válidos.", 0.0

    disponible = dias_disponibles(usuario)
    if dias_sol > disponible:
        return False, f"No tienes suficientes días. Solicitas {dias_sol:.0f}, disponible {disponible:.1f}.", dias_sol

    session = Session()
    solapadas = session.query(SolicitudVacaciones).filter(
        SolicitudVacaciones.empleado_id == usuario.id,
        SolicitudVacaciones.estado.in_(["aprobada", "pendiente"]),
        SolicitudVacaciones.fecha_inicio <= fin,
        SolicitudVacaciones.fecha_fin   >= inicio,
    ).all()
    session.close()

    if solapadas:
        return False, "Ya tienes una solicitud en esas fechas.", dias_sol

    return True, "OK", dias_sol


# ── CIERRE ANUAL ────────────────────────────────────────────────────────────
def ejecutar_cierre_anual(forzar: bool = False) -> dict:
    anio_actual = date.today().year
    session = Session()
    usuarios = session.query(Usuario).all()
    resumen = {}
    for u in usuarios:
        if forzar or (u.ultimo_reset_anual or 0) < anio_actual:
            sobrantes = max(0.0, u.dias_vacaciones_totales - u.dias_vacaciones_usados)
            u.dias_acumulados        = (u.dias_acumulados or 0.0) + sobrantes
            u.dias_vacaciones_usados = 0.0
            u.ultimo_reset_anual     = anio_actual
            resumen[u.nombre]        = round(u.dias_acumulados, 1)
    session.commit()
    session.close()
    return resumen


def verificar_cierre_anual_automatico():
    anio_actual = date.today().year
    session = Session()
    try:
        pendientes = session.query(Usuario).filter(
            Usuario.ultimo_reset_anual < anio_actual
        ).count()
    except Exception:
        pendientes = 0
    session.close()
    if pendientes > 0:
        ejecutar_cierre_anual()