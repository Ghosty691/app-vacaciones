"""
notificaciones.py
────────────────────────────────────────────────────────────────────────────
Sistema de notificaciones multicanal:
  · Portal interno    → siempre (Notificacion en BD)
  · Email (SMTP)      → OBLIGATORIO para todos los usuarios
  · SMS (Twilio)      → opcional si el usuario lo activa
  · Telegram (Bot)    → opcional si el usuario lo activa

Configuración (.env o variables de entorno):
  SMTP_HOST       = smtp.gmail.com
  SMTP_PORT       = 587
  SMTP_USER       = noreply@empresa.com
  SMTP_PASS       = xxxxxxxx

  TWILIO_SID      = ACxxxxxxxx
  TWILIO_TOKEN    = xxxxxxxx
  TWILIO_FROM     = +34xxxxxxxxx

  TELEGRAM_TOKEN  = xxxxxxxxx:xxxxxxxxxxxxxxxx

Si las credenciales no están configuradas, el canal correspondiente
se desactiva con un aviso en consola (la app no falla).
"""

from __future__ import annotations
import os
import smtplib
import logging
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import Session, Usuario, Notificacion

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN  (lee del entorno; si falta, el canal queda desactivado)
# ─────────────────────────────────────────────────────────────────────────────

SMTP_HOST  = os.getenv("SMTP_HOST",  "smtp.gmail.com")
SMTP_PORT  = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER  = os.getenv("SMTP_USER",  "")
SMTP_PASS  = os.getenv("SMTP_PASS",  "")

TWILIO_SID   = os.getenv("TWILIO_SID",   "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_FROM",  "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

EMAIL_CONFIGURADO    = bool(SMTP_USER and SMTP_PASS)
SMS_CONFIGURADO      = bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM)
TELEGRAM_CONFIGURADO = bool(TELEGRAM_TOKEN)


# ─────────────────────────────────────────────────────────────────────────────
# CANALES INDIVIDUALES
# ─────────────────────────────────────────────────────────────────────────────

def _enviar_email(destinatario: str, asunto: str, cuerpo_html: str) -> bool:
    """Envía un email HTML mediante SMTP con TLS."""
    if not EMAIL_CONFIGURADO:
        logger.warning("[EMAIL] SMTP no configurado — email no enviado a %s", destinatario)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = f"Portal Vacaciones <{SMTP_USER}>"
        msg["To"]      = destinatario
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, destinatario, msg.as_string())
        logger.info("[EMAIL] Enviado a %s", destinatario)
        return True
    except Exception as exc:
        logger.error("[EMAIL] Error enviando a %s: %s", destinatario, exc)
        return False


def _enviar_sms(telefono: str, mensaje: str) -> bool:
    """Envía SMS mediante Twilio."""
    if not SMS_CONFIGURADO:
        logger.warning("[SMS] Twilio no configurado — SMS no enviado a %s", telefono)
        return False
    try:
        from twilio.rest import Client  # type: ignore
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(body=mensaje, from_=TWILIO_FROM, to=telefono)
        logger.info("[SMS] Enviado a %s", telefono)
        return True
    except ImportError:
        logger.warning("[SMS] Instala 'twilio': pip install twilio")
        return False
    except Exception as exc:
        logger.error("[SMS] Error: %s", exc)
        return False


def _enviar_telegram(chat_id: str, mensaje: str) -> bool:
    """Envía mensaje vía Telegram Bot API."""
    if not TELEGRAM_CONFIGURADO:
        logger.warning("[TELEGRAM] Token no configurado — mensaje no enviado a %s", chat_id)
        return False
    try:
        import urllib.request, json, urllib.parse  # noqa
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML",
        }).encode()
        with urllib.request.urlopen(url, data=data, timeout=8) as resp:
            resultado = json.loads(resp.read())
        if resultado.get("ok"):
            logger.info("[TELEGRAM] Enviado a chat_id %s", chat_id)
            return True
        logger.warning("[TELEGRAM] Respuesta no-OK: %s", resultado)
        return False
    except Exception as exc:
        logger.error("[TELEGRAM] Error: %s", exc)
        return False


def _guardar_notificacion_interna(
    empleado_id: int,
    titulo: str,
    mensaje: str,
    tipo: str = "info",
):
    """Persiste la notificación en la BD (bandeja interna del portal)."""
    session = Session()
    try:
        n = Notificacion(
            empleado_id=empleado_id,
            fecha=date.today(),
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            leida=False,
        )
        session.add(n)
        session.commit()
    except Exception as exc:
        logger.error("[NOTIF INTERNA] Error: %s", exc)
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# PLANTILLA HTML DE EMAIL
# ─────────────────────────────────────────────────────────────────────────────

def _plantilla_email(titulo: str, cuerpo: str, tipo: str = "info") -> str:
    colores = {
        "info":    ("#1a73e8", "#eef4fd"),
        "success": ("#34a853", "#e6f4ea"),
        "warning": ("#f9ab00", "#fef7e0"),
        "error":   ("#d93025", "#fce8e6"),
    }
    color_principal, color_fondo = colores.get(tipo, colores["info"])
    return f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 16px;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;overflow:hidden;
                    box-shadow:0 2px 12px rgba(0,0,0,0.08);">
        <!-- HEADER -->
        <tr>
          <td style="background:{color_principal};padding:24px 32px;">
            <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">
              🏖️ Portal de Vacaciones
            </h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">
              Empresa S.A. — Gestión de RRHH
            </p>
          </td>
        </tr>
        <!-- CONTENIDO -->
        <tr>
          <td style="padding:32px;">
            <div style="background:{color_fondo};border-left:4px solid {color_principal};
                        border-radius:6px;padding:16px 20px;margin-bottom:24px;">
              <h2 style="margin:0 0 8px;color:{color_principal};font-size:17px;">{titulo}</h2>
            </div>
            <div style="color:#333;font-size:15px;line-height:1.65;">
              {cuerpo}
            </div>
          </td>
        </tr>
        <!-- FOOTER -->
        <tr>
          <td style="background:#f8f9fa;padding:16px 32px;border-top:1px solid #eee;">
            <p style="margin:0;color:#999;font-size:12px;">
              Este es un mensaje automático del Portal de Vacaciones.<br>
              © 2026 Empresa S.A. · Todos los derechos reservados.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL  (usar en toda la app)
# ─────────────────────────────────────────────────────────────────────────────

def enviar_notificacion(
    empleado_id: int,
    titulo: str,
    mensaje_texto: str,
    tipo: str = "info",
    mensaje_email_html: str | None = None,
):
    """
    Envía una notificación por TODOS los canales activos del empleado.

    Parámetros:
        empleado_id        → ID del usuario destinatario
        titulo             → Título corto (usado en portal, email y SMS)
        mensaje_texto      → Texto plano (para SMS y Telegram)
        tipo               → "info" | "success" | "warning" | "error"
        mensaje_email_html → HTML adicional para el email (si None usa mensaje_texto)
    """
    session = Session()
    usuario = session.query(Usuario).get(empleado_id)
    session.close()

    if not usuario:
        return

    # 1. PORTAL INTERNO (siempre)
    _guardar_notificacion_interna(empleado_id, titulo, mensaje_texto, tipo)

    # 2. EMAIL (siempre obligatorio)
    cuerpo_html = mensaje_email_html or f"<p>{mensaje_texto}</p>"
    html_completo = _plantilla_email(titulo, cuerpo_html, tipo)
    _enviar_email(usuario.email, f"[Portal Vacaciones] {titulo}", html_completo)

    # 3. SMS (opcional, si el usuario lo tiene activado)
    if usuario.notif_sms and usuario.telefono_sms:
        sms_texto = f"[Portal Vacaciones] {titulo}\n{mensaje_texto}"
        _enviar_sms(usuario.telefono_sms, sms_texto)

    # 4. TELEGRAM (opcional, si el usuario lo tiene activado)
    if usuario.notif_telegram and usuario.telegram_chat_id:
        tg_texto = f"<b>🏖️ Portal Vacaciones</b>\n<b>{titulo}</b>\n\n{mensaje_texto}"
        _enviar_telegram(usuario.telegram_chat_id, tg_texto)


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICACIONES PREDEFINIDAS (llamar desde los paneles)
# ─────────────────────────────────────────────────────────────────────────────

def notif_solicitud_recibida(empleado_id: int, fecha_inicio: date, fecha_fin: date, dias: float):
    enviar_notificacion(
        empleado_id=empleado_id,
        titulo="Solicitud de vacaciones recibida",
        mensaje_texto=(
            f"Tu solicitud del {fecha_inicio.strftime('%d/%m/%Y')} al "
            f"{fecha_fin.strftime('%d/%m/%Y')} ({dias:.0f} días) ha sido registrada "
            f"y está pendiente de aprobación."
        ),
        tipo="info",
        mensaje_email_html=f"""
        <p>Hemos recibido tu solicitud de vacaciones.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#f8f9fa;">
            <td style="padding:10px 14px;font-weight:600;">Fecha inicio</td>
            <td style="padding:10px 14px;">{fecha_inicio.strftime('%d de %B de %Y')}</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:600;">Fecha fin</td>
            <td style="padding:10px 14px;">{fecha_fin.strftime('%d de %B de %Y')}</td>
          </tr>
          <tr style="background:#f8f9fa;">
            <td style="padding:10px 14px;font-weight:600;">Días solicitados</td>
            <td style="padding:10px 14px;">{dias:.0f} días</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:600;">Estado</td>
            <td style="padding:10px 14px;color:#f9ab00;font-weight:700;">⏳ Pendiente de aprobación</td>
          </tr>
        </table>
        <p>Te avisaremos en cuanto tu manager la revise.</p>
        """,
    )


def notif_solicitud_aprobada(empleado_id: int, fecha_inicio: date, fecha_fin: date, dias: float, comentario: str = ""):
    extra = f"<p><b>Comentario del manager:</b> {comentario}</p>" if comentario else ""
    enviar_notificacion(
        empleado_id=empleado_id,
        titulo="✅ Vacaciones aprobadas",
        mensaje_texto=(
            f"¡Buenas noticias! Tus vacaciones del {fecha_inicio.strftime('%d/%m/%Y')} "
            f"al {fecha_fin.strftime('%d/%m/%Y')} ({dias:.0f} días) han sido APROBADAS."
            + (f" Comentario: {comentario}" if comentario else "")
        ),
        tipo="success",
        mensaje_email_html=f"""
        <p>🎉 Tu solicitud de vacaciones ha sido <strong>aprobada</strong>.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#e6f4ea;">
            <td style="padding:10px 14px;font-weight:600;">Período</td>
            <td style="padding:10px 14px;">
              {fecha_inicio.strftime('%d/%m/%Y')} → {fecha_fin.strftime('%d/%m/%Y')}
            </td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:600;">Días disfrutados</td>
            <td style="padding:10px 14px;">{dias:.0f} días</td>
          </tr>
        </table>
        {extra}
        <p>¡Que las disfrutes! 🏖️</p>
        """,
    )


def notif_solicitud_rechazada(empleado_id: int, fecha_inicio: date, fecha_fin: date, motivo: str = ""):
    extra = f"<p><b>Motivo:</b> {motivo}</p>" if motivo else ""
    enviar_notificacion(
        empleado_id=empleado_id,
        titulo="❌ Solicitud de vacaciones rechazada",
        mensaje_texto=(
            f"Tu solicitud del {fecha_inicio.strftime('%d/%m/%Y')} al "
            f"{fecha_fin.strftime('%d/%m/%Y')} ha sido rechazada."
            + (f" Motivo: {motivo}" if motivo else "")
        ),
        tipo="error",
        mensaje_email_html=f"""
        <p>Lamentamos informarte de que tu solicitud de vacaciones ha sido <strong>rechazada</strong>.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#fce8e6;">
            <td style="padding:10px 14px;font-weight:600;">Período solicitado</td>
            <td style="padding:10px 14px;">
              {fecha_inicio.strftime('%d/%m/%Y')} → {fecha_fin.strftime('%d/%m/%Y')}
            </td>
          </tr>
        </table>
        {extra}
        <p>Puedes solicitar nuevas fechas desde el portal. Si tienes dudas, contacta con tu manager o RRHH.</p>
        """,
    )


def notif_horas_extra_registradas(empleado_id: int, fecha: date, horas: float, descripcion: str):
    enviar_notificacion(
        empleado_id=empleado_id,
        titulo="Horas extra registradas",
        mensaje_texto=f"Se han registrado {horas}h extra el {fecha.strftime('%d/%m/%Y')}: {descripcion}",
        tipo="info",
    )


def notif_dias_bajos(usuario_id: int, disponibles: float):
    """
    Avisa al empleado cuando su saldo de vacaciones cae por debajo del umbral.
    """
    enviar_notificacion(
        empleado_id=usuario_id,
        titulo="⚠️ Saldo de vacaciones bajo",
        mensaje_texto=f"Te quedan solamente {disponibles:.1f} días de vacaciones.",
        tipo="warning",
        mensaje_email_html=f"""
        <p>Tu saldo de vacaciones está por debajo del umbral recomendado.</p>
        <div style="font-size:2rem;font-weight:700;color:#f9ab00;text-align:center;
                    padding:16px;background:#fef7e0;border-radius:8px;margin:16px 0;">
          {disponibles:.1f} días disponibles
        </div>
        <p>Planifica tus próximos días libres con antelación.</p>
        """,
    )


def notif_anio_nuevo_saldo(
    usuario_id: int,
    anio: int,
    dias_nuevos: float,
    dias_acumulados: float,
    dias_total: float,
):
    """
    Notifica al empleado del nuevo saldo tras el cierre anual.
    """
    enviar_notificacion(
        empleado_id=usuario_id,
        titulo=f"🎉 Nuevo año {anio} — Saldo de vacaciones actualizado",
        mensaje_texto=(
            f"Se ha completado el cierre anual. "
            f"Días nuevos: {dias_nuevos:.1f}, acumulados: {dias_acumulados:.1f}, "
            f"total: {dias_total:.1f}."
        ),
        tipo="success",
        mensaje_email_html=f"""
        <p>¡Bienvenido al nuevo año {anio}! Se ha actualizado tu saldo de vacaciones.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#e6f4ea;">
            <td style="padding:10px 14px;font-weight:600;">Días del año {anio}</td>
            <td style="padding:10px 14px;">{dias_nuevos:.1f}</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:600;">Días acumulados</td>
            <td style="padding:10px 14px;">{dias_acumulados:.1f}</td>
          </tr>
          <tr style="background:#e6f4ea;">
            <td style="padding:10px 14px;font-weight:600;">TOTAL disponible</td>
            <td style="padding:10px 14px;font-weight:700;">{dias_total:.1f}</td>
          </tr>
        </table>
        <p>Puedes solicitar tus vacaciones desde el portal.</p>
        """,
    )


def notif_dias_acumulados(empleado_id: int, dias_acumulados: float):
    enviar_notificacion(
        empleado_id=empleado_id,
        titulo="Nuevo año — días acumulados actualizados",
        mensaje_texto=(
            f"Se ha realizado el cierre anual de vacaciones. "
            f"Llevas {dias_acumulados:.1f} días acumulados de años anteriores."
        ),
        tipo="info",
        mensaje_email_html=f"""
        <p>Se ha completado el <strong>cierre anual de vacaciones</strong>.</p>
        <p>Los días que no utilizaste el año pasado han sido sumados a tu saldo:</p>
        <div style="font-size:2rem;font-weight:700;color:#1a73e8;text-align:center;
                    padding:16px;background:#eef4fd;border-radius:8px;margin:16px 0;">
          {dias_acumulados:.1f} días acumulados
        </div>
        <p>Estos días están disponibles para este año junto con tu asignación anual habitual.</p>
        """,
    )


def notif_recordatorio_dias_pendientes(empleado_id: int, dias_restantes: float):
    """Útil para avisar en noviembre/diciembre de días sin usar."""
    enviar_notificacion(
        empleado_id=empleado_id,
        titulo="⚠️ Recuerda usar tus días de vacaciones",
        mensaje_texto=(
            f"Te quedan {dias_restantes:.1f} días de vacaciones sin usar este año. "
            f"Planifícalos antes de que acabe el año para que se acumulen correctamente."
        ),
        tipo="warning",
    )