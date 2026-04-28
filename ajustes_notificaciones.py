"""
ajustes_notificaciones.py
────────────────────────────────────────────────────────────────────────────
Panel de configuración de notificaciones para el empleado.
Permite activar/desactivar SMS y Telegram, introducir teléfono y chat_id.
El email es SIEMPRE obligatorio y no se puede desactivar.

Uso: llamar panel_ajustes_notificaciones() dentro de la pestaña
     "Ajustes" de cualquier panel (empleado, manager, admin).
"""

import streamlit as st  # type: ignore
from database import Session, Usuario

# ── CSS adicional para el panel ───────────────────────────────────────────────
AJUSTES_CSS = """
<style>
.notif-card {
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    background: #ffffff;
}
.notif-card.obligatorio {
    border-color: #34a853;
    background: #f0faf3;
}
.notif-card.opcional {
    border-color: #e2e8f0;
}
.notif-canal-titulo {
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.2rem;
    color: #0f172a;
}
.notif-canal-desc {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.8rem;
}
.badge-obligatorio {
    display: inline-block;
    background: #34a853;
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.15rem 0.55rem;
    border-radius: 20px;
    margin-left: 0.5rem;
    vertical-align: middle;
}
.badge-opcional {
    display: inline-block;
    background: #94a3b8;
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.15rem 0.55rem;
    border-radius: 20px;
    margin-left: 0.5rem;
    vertical-align: middle;
}
</style>
"""


def panel_ajustes_notificaciones():
    """
    Renderiza el panel completo de configuración de notificaciones.
    Llámalo dentro de una pestaña de ajustes en el panel del empleado/manager/admin.
    """
    st.markdown(AJUSTES_CSS, unsafe_allow_html=True)
    st.subheader("🔔 Canales de notificación")
    st.caption(
        "Mantente informado de cualquier cambio en tus solicitudes y horas extra. "
        "El correo electrónico es **obligatorio** y siempre activo."
    )

    session = Session()
    usuario = session.query(Usuario).get(st.session_state["usuario_id"])
    session.close()

    if not usuario:
        st.error("No se pudo cargar tu perfil.")
        return

    # ── EMAIL (obligatorio, solo lectura) ─────────────────────────────────────
    st.markdown(f"""
    <div class="notif-card obligatorio">
        <div class="notif-canal-titulo">
            📧 Email corporativo
            <span class="badge-obligatorio">OBLIGATORIO</span>
        </div>
        <div class="notif-canal-desc">
            Recibirás un email en <strong>{usuario.email}</strong> por cada cambio relevante:
            aprobaciones, rechazos, horas extra registradas y resumen anual.
            Este canal no puede desactivarse.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── SMS (opcional) ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="notif-canal-titulo">
        📱 SMS <span class="badge-opcional">OPCIONAL</span>
    </div>
    <div class="notif-canal-desc">
        Recibe un SMS en tu móvil además del email. Requiere número de teléfono con prefijo
        internacional (ej. <code>+34612345678</code>).
    </div>
    """, unsafe_allow_html=True)

    notif_sms = st.toggle(
        "Activar notificaciones por SMS",
        value=bool(usuario.notif_sms),
        key="toggle_sms",
    )

    if notif_sms:
        telefono = st.text_input(
            "📞 Número de teléfono (con prefijo internacional)",
            value=usuario.telefono_sms or "",
            placeholder="+34612345678",
            key="input_telefono",
        )
        if not telefono.startswith("+"):
            st.warning("⚠️ Incluye el prefijo internacional, por ejemplo: **+34**612345678")
    else:
        telefono = usuario.telefono_sms or ""

    st.markdown("<br>", unsafe_allow_html=True)

    # ── TELEGRAM (opcional) ───────────────────────────────────────────────────
    st.markdown("""
    <div class="notif-canal-titulo">
        ✈️ Telegram <span class="badge-opcional">OPCIONAL</span>
    </div>
    <div class="notif-canal-desc">
        Recibe mensajes instantáneos en Telegram. Necesitas tu <strong>Chat ID</strong> de Telegram.
        Para obtenerlo, escribe a <code>@userinfobot</code> en Telegram y te lo dará al instante.
    </div>
    """, unsafe_allow_html=True)

    notif_telegram = st.toggle(
        "Activar notificaciones por Telegram",
        value=bool(usuario.notif_telegram),
        key="toggle_telegram",
    )

    if notif_telegram:
        chat_id = st.text_input(
            "🤖 Tu Chat ID de Telegram",
            value=usuario.telegram_chat_id or "",
            placeholder="123456789",
            key="input_chat_id",
        )
        with st.expander("ℹ️ ¿Cómo obtener mi Chat ID?"):
            st.markdown("""
            1. Abre Telegram y busca **@userinfobot**
            2. Pulsa **Iniciar** o escribe `/start`
            3. El bot te responderá con tu ID numérico
            4. Copia ese número aquí
            
            También puedes usar **@getmyid_bot** como alternativa.
            """)
    else:
        chat_id = usuario.telegram_chat_id or ""

    st.markdown("<br>", unsafe_allow_html=True)

    # ── GUARDAR ───────────────────────────────────────────────────────────────
    if st.button("💾 Guardar preferencias de notificación", type="primary", use_container_width=True):
        # Validaciones antes de guardar
        errores = []
        if notif_sms and (not telefono or not telefono.startswith("+")):
            errores.append("El número de teléfono debe incluir prefijo internacional (+34...).")
        if notif_telegram and not chat_id:
            errores.append("Introduce tu Chat ID de Telegram para activar este canal.")

        if errores:
            for e in errores:
                st.error(f"❌ {e}")
        else:
            session = Session()
            u = session.query(Usuario).get(st.session_state["usuario_id"])
            if u:
                u.notif_email    = True   # siempre
                u.notif_sms      = notif_sms
                u.notif_telegram = notif_telegram
                u.telefono_sms   = telefono if notif_sms else (u.telefono_sms or "")
                u.telegram_chat_id = chat_id if notif_telegram else (u.telegram_chat_id or "")
                session.commit()
            session.close()

            canales = ["📧 Email"]
            if notif_sms:     canales.append("📱 SMS")
            if notif_telegram: canales.append("✈️ Telegram")
            st.success(f"✅ Preferencias guardadas. Canales activos: {' · '.join(canales)}")

    # ── RESUMEN ACTUAL ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 Estado actual de tus canales"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📧 Email", "✅ Activo")
        with col2:
            st.metric("📱 SMS", "✅ Activo" if usuario.notif_sms else "⭕ Desactivado")
        with col3:
            st.metric("✈️ Telegram", "✅ Activo" if usuario.notif_telegram else "⭕ Desactivado")