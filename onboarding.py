"""
onboarding.py  ──  Cursograma de bienvenida (primera sesión)
─────────────────────────────────────────────────────────────
Flujo interactivo multi-paso que se muestra UNA SOLA VEZ tras el primer login.
Recoge preferencias del empleado y las persiste en la BD.

Integración en app.py:
    from onboarding import mostrar_onboarding, onboarding_requerido
    ...
    if onboarding_requerido():
        mostrar_onboarding()
    else:
        # panel normal (empleado / manager / admin)
"""

import json
import streamlit as st  # type: ignore
from database import Session, Usuario
from acumulacion_dias import guardar_tipo_dias, guardar_canales_extra


# ─────────────────────────────────────────────────────────────────────────────
# CSS EXCLUSIVO DEL CURSOGRAMA  (se inyecta solo cuando está activo)
# ─────────────────────────────────────────────────────────────────────────────
ONBOARDING_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ── Reset de sección ── */
.onb-wrapper {
    font-family: 'DM Sans', sans-serif;
    max-width: 720px;
    margin: 0 auto;
    padding: 0 0 3rem 0;
}

/* ── Barra de progreso superior ── */
.onb-progress-bar {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 2.5rem;
}
.onb-step {
    flex: 1;
    height: 4px;
    background: #e2e8f0;
    border-radius: 2px;
    margin: 0 3px;
    transition: background 0.4s ease;
}
.onb-step.active   { background: #1a73e8; }
.onb-step.done     { background: #34a853; }

/* ── Encabezado de cada paso ── */
.onb-step-label {
    font-family: 'Sora', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #1a73e8;
    margin-bottom: 0.4rem;
}
.onb-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.85rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
    margin-bottom: 0.5rem;
}
.onb-subtitle {
    font-size: 1rem;
    color: #64748b;
    line-height: 1.55;
    margin-bottom: 2rem;
}

/* ── Tarjetas de opción ── */
.onb-cards {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.onb-card {
    flex: 1 1 180px;
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.2rem 1rem;
    cursor: pointer;
    transition: all 0.22s ease;
    background: #ffffff;
    text-align: center;
    user-select: none;
}
.onb-card:hover {
    border-color: #1a73e8;
    box-shadow: 0 4px 18px rgba(26,115,232,0.13);
    transform: translateY(-2px);
}
.onb-card.selected {
    border-color: #1a73e8;
    background: #eef4fd;
    box-shadow: 0 4px 18px rgba(26,115,232,0.18);
}
.onb-card-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.onb-card-title {
    font-family: 'Sora', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 0.25rem;
}
.onb-card-desc { font-size: 0.78rem; color: #64748b; line-height: 1.4; }

/* ── Resumen final ── */
.onb-summary-row {
    display: flex;
    align-items: center;
    padding: 0.85rem 1rem;
    border-radius: 10px;
    background: #f8fafc;
    margin-bottom: 0.6rem;
    gap: 1rem;
}
.onb-summary-icon { font-size: 1.4rem; min-width: 2rem; text-align: center; }
.onb-summary-text { font-size: 0.9rem; color: #334155; }
.onb-summary-value {
    margin-left: auto;
    font-family: 'Sora', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    color: #1a73e8;
    background: #eef4fd;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
}

/* ── Pantalla de bienvenida (paso 0) ── */
.onb-welcome-hero {
    text-align: center;
    padding: 2rem 1rem 1.5rem;
}
.onb-welcome-hero .hero-emoji { font-size: 4.5rem; line-height: 1; margin-bottom: 1rem; }
.onb-welcome-hero h1 {
    font-family: 'Sora', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.6rem;
}
.onb-welcome-hero p { font-size: 1rem; color: #64748b; line-height: 1.6; max-width: 520px; margin: 0 auto 1.5rem; }

/* ── Check list de features ── */
.onb-feature-list { list-style: none; padding: 0; margin: 1.2rem 0 1.8rem; text-align: left; display: inline-block; }
.onb-feature-list li { padding: 0.38rem 0; font-size: 0.92rem; color: #334155; }
.onb-feature-list li::before { content: "✦ "; color: #1a73e8; font-weight: 700; }

/* ── Pantalla de éxito ── */
.onb-success {
    text-align: center;
    padding: 3rem 1rem;
}
.onb-success .success-emoji { font-size: 5rem; margin-bottom: 1.2rem; animation: pop 0.5s cubic-bezier(.36,2,.6,1) both; }
@keyframes pop { from { transform: scale(0.3); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.onb-success h2 {
    font-family: 'Sora', sans-serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.5rem;
}
.onb-success p { font-size: 0.98rem; color: #64748b; margin-bottom: 2rem; }

/* ── Separador de paso ── */
.onb-divider { height: 1px; background: #f1f5f9; margin: 1.5rem 0; }

/* ── Forzar sidebar colapsado durante onboarding ── */
section[data-testid="stSidebar"] { display: none !important; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# ESTRUCTURA DEL CURSOGRAMA (ahora con 8 pasos: 0 al 7)
# ─────────────────────────────────────────────────────────────────────────────

PASOS = [
    "Bienvenida",
    "Notificaciones",
    "Tipo de días",
    "Canales extra",
    "Compensación",
    "Vacaciones",
    "Comunicación",
    "Resumen",
]

# Opciones para cada paso
OPCIONES_NOTIF = [
    {"icon": "🔔", "id": "todas",      "title": "Todas",        "desc": "Email + aviso en app para cada cambio"},
    {"icon": "📧", "id": "solo_email", "title": "Solo email",   "desc": "Solo correo corporativo"},
    {"icon": "📵", "id": "minimas",    "title": "Mínimas",      "desc": "Solo aprobaciones y rechazos"},
]

OPCIONES_COMP = [
    {"icon": "💰", "id": "pago",        "title": "Pago directo",   "desc": "Cobro en nómina del mes siguiente"},
    {"icon": "🕐", "id": "dias_libres", "title": "Días libres",    "desc": "Convertir horas en días de descanso"},
    {"icon": "⚖️",  "id": "mixto",      "title": "Mixto",          "desc": "Decidir según cada caso"},
]

OPCIONES_VAC = [
    {"icon": "☀️",  "id": "verano",     "title": "Verano intensivo",   "desc": "Concentrar en julio-agosto"},
    {"icon": "📅", "id": "distribuido","title": "Distribuido",         "desc": "Repartir a lo largo del año"},
    {"icon": "🎲", "id": "flexible",   "title": "Según necesidad",     "desc": "Decidirlo cuando surja"},
]

OPCIONES_COMUNI = [
    {"icon": "📩", "id": "email",    "title": "Email",         "desc": "Comunicación formal por correo"},
    {"icon": "💬", "id": "chat",     "title": "Chat interno",  "desc": "Mensajería instantánea del equipo"},
    {"icon": "🤝", "id": "presencial","title": "Presencial",   "desc": "Prefiero hablar directamente"},
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _barra_progreso(paso_actual: int, total: int):
    """Renderiza la barra de segmentos de progreso."""
    segmentos = []
    for i in range(total):
        if i < paso_actual:
            cls = "done"
        elif i == paso_actual:
            cls = "active"
        else:
            cls = ""
        segmentos.append(f'<div class="onb-step {cls}"></div>')
    st.markdown(
        f'<div class="onb-progress-bar">{"".join(segmentos)}</div>',
        unsafe_allow_html=True,
    )


def _tarjetas(opciones: list, clave_estado: str) -> str | None:
    """
    Renderiza tarjetas de selección y devuelve el id elegido.
    Usa botones de Streamlit agrupados en columnas para la interacción.
    """
    seleccion = st.session_state.get(clave_estado)
    cols = st.columns(len(opciones))
    for col, op in zip(cols, opciones):
        with col:
            css_class = "onb-card selected" if seleccion == op["id"] else "onb-card"
            st.markdown(f"""
            <div class="{css_class}">
                <div class="onb-card-icon">{op['icon']}</div>
                <div class="onb-card-title">{op['title']}</div>
                <div class="onb-card-desc">{op['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            label = f"{'✓ ' if seleccion == op['id'] else ''}{op['title']}"
            if st.button(label, key=f"btn_{clave_estado}_{op['id']}", use_container_width=True):
                st.session_state[clave_estado] = op["id"]
                st.rerun()
    return seleccion


def _guardar_preferencias():
    """Persiste las respuestas del cursograma en la BD."""
    prefs = {
        "notificaciones":  st.session_state.get("onb_notif"),
        "tipo_dias":       st.session_state.get("onb_tipo_dias", "habiles"),
        "sms":             st.session_state.get("onb_sms", False),
        "telefono_sms":    st.session_state.get("onb_telefono", ""),
        "telegram":        st.session_state.get("onb_telegram", False),
        "telegram_chat_id":st.session_state.get("onb_tg_id", ""),
        "compensacion":    st.session_state.get("onb_comp"),
        "vacaciones":      st.session_state.get("onb_vac"),
        "comunicacion":    st.session_state.get("onb_comuni"),
    }
    session = Session()
    usuario = session.query(Usuario).get(st.session_state["usuario_id"])
    if usuario:
        usuario.onboarding_completado = 1
        usuario.preferencias_json = json.dumps(prefs, ensure_ascii=False)
        session.commit()
        # Guardar tipo de días en BD
        guardar_tipo_dias(st.session_state["usuario_id"], prefs["tipo_dias"])
        # Guardar canales extra
        guardar_canales_extra(
            usuario_id       = st.session_state["usuario_id"],
            sms              = prefs["sms"],
            telefono         = prefs["telefono_sms"],
            telegram         = prefs["telegram"],
            telegram_chat_id = prefs["telegram_chat_id"],
        )
    session.close()
    st.session_state["onboarding_completado"] = True


def _label_opcion(opciones: list, id_val: str | None) -> str:
    if not id_val:
        return "—"
    for op in opciones:
        if op["id"] == id_val:
            return f"{op['icon']} {op['title']}"
    return id_val


# ─────────────────────────────────────────────────────────────────────────────
# COMPROBACIÓN: ¿Necesita onboarding este usuario?
# ─────────────────────────────────────────────────────────────────────────────

def onboarding_requerido() -> bool:
    if st.session_state.get("onboarding_completado"):
        return False
    session = Session()
    usuario = session.query(Usuario).get(st.session_state.get("usuario_id"))
    session.close()
    if usuario is None:
        return False
    completado = bool(usuario.onboarding_completado)
    st.session_state["onboarding_completado"] = completado
    return not completado


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL: mostrar_onboarding()
# ─────────────────────────────────────────────────────────────────────────────

def mostrar_onboarding():
    st.markdown(ONBOARDING_CSS, unsafe_allow_html=True)

    if "onb_paso" not in st.session_state:
        st.session_state["onb_paso"] = 0

    paso = st.session_state["onb_paso"]
    nombre_corto = st.session_state.get("usuario_nombre", "").split()[0]

    _, col_c, _ = st.columns([1, 3, 1])
    with col_c:
        st.markdown('<div class="onb-wrapper">', unsafe_allow_html=True)

        # Barra de progreso (oculta en bienvenida, canales extra y resumen)
        if paso not in (0, 3, len(PASOS)-1):
            _barra_progreso(paso - 1, len(PASOS) - 2)

        # ══════════════════════════════════════════════════════════════════
        # PASO 0 · BIENVENIDA
        # ══════════════════════════════════════════════════════════════════
        if paso == 0:
            st.markdown(f"""
            <div class="onb-welcome-hero">
                <div class="hero-emoji">🏖️</div>
                <h1>Hola, {nombre_corto} 👋</h1>
                <p>
                    Bienvenido/a al <strong>Portal de Vacaciones</strong>.<br>
                    Antes de entrar, necesitamos conocer tus preferencias
                    para personalizar tu experiencia — solo te llevará <strong>1 minuto</strong>.
                </p>
                <ul class="onb-feature-list">
                    <li>Gestiona y solicita tus vacaciones fácilmente</li>
                    <li>Controla y compensa tus horas extra</li>
                    <li>Recibe notificaciones a tu medida</li>
                    <li>Comunícate con RRHH sin fricciones</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b = st.columns([3, 1])
            with col_a:
                if st.button("Comenzar configuración →", type="primary", use_container_width=True):
                    st.session_state["onb_paso"] = 1
                    st.rerun()
            with col_b:
                if st.button("Saltar", use_container_width=True, help="Completarás el perfil más tarde desde Ajustes"):
                    _guardar_preferencias()
                    st.rerun()

        # ══════════════════════════════════════════════════════════════════
        # PASO 1 · NOTIFICACIONES
        # ══════════════════════════════════════════════════════════════════
        elif paso == 1:
            st.markdown('<div class="onb-step-label">Paso 1 de 6</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">¿Cómo quieres recibir avisos?</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Elige qué notificaciones recibirás cuando cambien el estado de tus solicitudes.</div>', unsafe_allow_html=True)

            seleccion = _tarjetas(OPCIONES_NOTIF, "onb_notif")

            st.markdown('<div class="onb-divider"></div>', unsafe_allow_html=True)
            col_back, col_next = st.columns([1, 3])
            with col_back:
                if st.button("← Atrás", use_container_width=True):
                    st.session_state["onb_paso"] = 0
                    st.rerun()
            with col_next:
                disabled = seleccion is None
                if st.button("Siguiente →", type="primary", use_container_width=True, disabled=disabled):
                    st.session_state["onb_paso"] = 2
                    st.rerun()
            if disabled:
                st.caption("⬆️ Selecciona una opción para continuar.")

        # ══════════════════════════════════════════════════════════════════
        # PASO 2 · TIPO DE DÍAS
        # ══════════════════════════════════════════════════════════════════
        elif paso == 2:
            st.markdown('<div class="onb-step-label">Paso 2 de 6</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">¿Cómo quieres contar tus días de vacaciones?</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Elige el sistema que mejor se adapte a tu forma de planificar. Podrás cambiarlo en cualquier momento desde Ajustes.</div>', unsafe_allow_html=True)

            opciones = [
                {"id": "habiles",   "icon": "📆", "title": "Días hábiles",  "desc": "Solo lunes–viernes (sin festivos)."},
                {"id": "naturales", "icon": "🗓️", "title": "Días naturales","desc": "Todos los días del calendario, excepto festivos."},
            ]

            seleccion = st.session_state.get("onb_tipo_dias")
            cols = st.columns(2)
            for col, op in zip(cols, opciones):
                with col:
                    css_class = "onb-card selected" if seleccion == op["id"] else "onb-card"
                    st.markdown(f'<div class="{css_class}"><div class="onb-card-icon">{op["icon"]}</div><div class="onb-card-title">{op["title"]}</div><div class="onb-card-desc">{op["desc"]}</div></div>', unsafe_allow_html=True)
                    label = f"{'✓ ' if seleccion == op['id'] else ''}{op['title']}"
                    if st.button(label, key=f"btn_tipo_dias_{op['id']}", use_container_width=True):
                        st.session_state["onb_tipo_dias"] = op["id"]
                        st.rerun()

            st.markdown('<div class="onb-divider"></div>', unsafe_allow_html=True)
            col_back, col_next = st.columns([1, 3])
            with col_back:
                if st.button("← Atrás", key="back_tipo_dias", use_container_width=True):
                    st.session_state["onb_paso"] = 1
                    st.rerun()
            with col_next:
                disabled = seleccion is None
                if st.button("Siguiente →", key="next_tipo_dias", type="primary", use_container_width=True, disabled=disabled):
                    st.session_state["onb_paso"] = 3
                    st.rerun()
            if disabled:
                st.caption("⬆️ Selecciona una opción para continuar.")

        # ══════════════════════════════════════════════════════════════════
        # PASO 3 · CANALES EXTRA (SMS, Telegram)
        # ══════════════════════════════════════════════════════════════════
        elif paso == 3:
            st.markdown('<div class="onb-step-label">Paso 3 de 6</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">Canales de notificación adicionales</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Recibirás notificaciones <strong>siempre por email</strong>. Activa SMS o Telegram si quieres recibirlas también por esos canales.</div>', unsafe_allow_html=True)

            st.info(f"📧 **Email activado** — {st.session_state.get('usuario_nombre', '')} (obligatorio, no se puede desactivar)", icon="✅")
            st.divider()

            # SMS
            st.markdown("**📱 SMS (opcional)**")
            col_s1, col_s2 = st.columns([1, 2])
            with col_s1:
                sms_on = st.toggle("Activar SMS", value=st.session_state.get("onb_sms", False), key="onb_toggle_sms")
                st.session_state["onb_sms"] = sms_on
            with col_s2:
                tel = st.text_input("Teléfono (+34…)", value=st.session_state.get("onb_telefono", ""), disabled=not sms_on, placeholder="+34600000000", key="onb_input_tel")
                st.session_state["onb_telefono"] = tel

            st.divider()

            # Telegram
            st.markdown("**✈️ Telegram (opcional)**")
            st.caption("Para obtener tu Chat ID habla con **@userinfobot** en Telegram.")
            col_t1, col_t2 = st.columns([1, 2])
            with col_t1:
                tg_on = st.toggle("Activar Telegram", value=st.session_state.get("onb_telegram", False), key="onb_toggle_tg")
                st.session_state["onb_telegram"] = tg_on
            with col_t2:
                tg_id = st.text_input("Chat ID de Telegram", value=st.session_state.get("onb_tg_id", ""), disabled=not tg_on, placeholder="123456789", key="onb_input_tg")
                st.session_state["onb_tg_id"] = tg_id

            st.markdown('<div class="onb-divider"></div>', unsafe_allow_html=True)
            col_back, col_next = st.columns([1, 3])
            with col_back:
                if st.button("← Atrás", key="back_canales", use_container_width=True):
                    st.session_state["onb_paso"] = 2
                    st.rerun()
            with col_next:
                errores = []
                if sms_on and not tel.strip().startswith("+"):
                    errores.append("teléfono con prefijo")
                if tg_on and not tg_id.strip().lstrip("-").isdigit():
                    errores.append("Chat ID numérico")
                if errores:
                    st.button("Siguiente →", type="primary", use_container_width=True, disabled=True, key="next_canales_dis")
                    st.caption(f"⬆️ Corrige: {', '.join(errores)}.")
                else:
                    if st.button("Siguiente →", type="primary", use_container_width=True, key="next_canales"):
                        st.session_state["onb_paso"] = 4
                        st.rerun()

        # ══════════════════════════════════════════════════════════════════
        # PASO 4 · COMPENSACIÓN DE HORAS EXTRA
        # ══════════════════════════════════════════════════════════════════
        elif paso == 4:
            st.markdown('<div class="onb-step-label">Paso 4 de 6</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">Horas extra: ¿cómo prefieres compensarlas?</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Tu preferencia ayuda a RRHH a gestionar tu compensación por defecto. Siempre podrás cambiarlo por solicitud.</div>', unsafe_allow_html=True)

            seleccion = _tarjetas(OPCIONES_COMP, "onb_comp")

            st.markdown('<div class="onb-divider"></div>', unsafe_allow_html=True)
            col_back, col_next = st.columns([1, 3])
            with col_back:
                if st.button("← Atrás", use_container_width=True):
                    st.session_state["onb_paso"] = 3
                    st.rerun()
            with col_next:
                disabled = seleccion is None
                if st.button("Siguiente →", type="primary", use_container_width=True, disabled=disabled):
                    st.session_state["onb_paso"] = 5
                    st.rerun()
            if disabled:
                st.caption("⬆️ Selecciona una opción para continuar.")

        # ══════════════════════════════════════════════════════════════════
        # PASO 5 · PLANIFICACIÓN DE VACACIONES
        # ══════════════════════════════════════════════════════════════════
        elif paso == 5:
            st.markdown('<div class="onb-step-label">Paso 5 de 6</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">¿Cuándo sueles tomar vacaciones?</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Indica tu patrón habitual para que el sistema te envíe recordatorios en el momento adecuado.</div>', unsafe_allow_html=True)

            seleccion = _tarjetas(OPCIONES_VAC, "onb_vac")

            st.markdown('<div class="onb-divider"></div>', unsafe_allow_html=True)
            col_back, col_next = st.columns([1, 3])
            with col_back:
                if st.button("← Atrás", use_container_width=True):
                    st.session_state["onb_paso"] = 4
                    st.rerun()
            with col_next:
                disabled = seleccion is None
                if st.button("Siguiente →", type="primary", use_container_width=True, disabled=disabled):
                    st.session_state["onb_paso"] = 6
                    st.rerun()
            if disabled:
                st.caption("⬆️ Selecciona una opción para continuar.")

        # ══════════════════════════════════════════════════════════════════
        # PASO 6 · CANAL DE COMUNICACIÓN
        # ══════════════════════════════════════════════════════════════════
        elif paso == 6:
            st.markdown('<div class="onb-step-label">Paso 6 de 6</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">¿Cómo prefieres comunicarte con RRHH?</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Cuando necesitemos contactarte sobre una solicitud, ¿cuál es tu canal favorito?</div>', unsafe_allow_html=True)

            seleccion = _tarjetas(OPCIONES_COMUNI, "onb_comuni")

            st.markdown('<div class="onb-divider"></div>', unsafe_allow_html=True)
            col_back, col_next = st.columns([1, 3])
            with col_back:
                if st.button("← Atrás", use_container_width=True):
                    st.session_state["onb_paso"] = 5
                    st.rerun()
            with col_next:
                disabled = seleccion is None
                if st.button("Ver resumen →", type="primary", use_container_width=True, disabled=disabled):
                    st.session_state["onb_paso"] = 7
                    st.rerun()
            if disabled:
                st.caption("⬆️ Selecciona una opción para continuar.")

        # ══════════════════════════════════════════════════════════════════
        # PASO 7 · RESUMEN Y CONFIRMACIÓN
        # ══════════════════════════════════════════════════════════════════
        elif paso == 7:
            st.markdown('<div class="onb-step-label">Confirmación</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-title">Revisa tus preferencias</div>', unsafe_allow_html=True)
            st.markdown('<div class="onb-subtitle">Así hemos configurado tu perfil. Puedes modificarlo en cualquier momento desde Ajustes.</div>', unsafe_allow_html=True)

            tipo_dias_etiqueta = "📆 Días hábiles" if st.session_state.get("onb_tipo_dias") == "habiles" else "🗓️ Días naturales"

            resumen = [
                ("🔔", "Notificaciones",          OPCIONES_NOTIF,  st.session_state.get("onb_notif")),
                ("📆", "Tipo de días",            None,            tipo_dias_etiqueta),
                ("📱", "SMS",                     None,            "Activado" if st.session_state.get("onb_sms") else "Desactivado"),
                ("✈️", "Telegram",               None,            "Activado" if st.session_state.get("onb_telegram") else "Desactivado"),
                ("💰", "Compensación horas extra", OPCIONES_COMP,  st.session_state.get("onb_comp")),
                ("📅", "Patrón de vacaciones",     OPCIONES_VAC,   st.session_state.get("onb_vac")),
                ("💬", "Canal de comunicación",    OPCIONES_COMUNI, st.session_state.get("onb_comuni")),
            ]

            for icono, etiqueta, opciones_lista, valor in resumen:
                if opciones_lista:
                    valor_mostrar = _label_opcion(opciones_lista, valor)
                else:
                    valor_mostrar = valor
                st.markdown(f"""
                <div class="onb-summary-row">
                    <span class="onb-summary-icon">{icono}</span>
                    <span class="onb-summary-text">{etiqueta}</span>
                    <span class="onb-summary-value">{valor_mostrar}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col_back, col_confirm = st.columns([1, 3])
            with col_back:
                if st.button("← Editar", use_container_width=True):
                    st.session_state["onb_paso"] = 6
                    st.rerun()
            with col_confirm:
                if st.button("✅ Confirmar y entrar al portal", type="primary", use_container_width=True):
                    _guardar_preferencias()
                    st.session_state["onb_paso"] = 8
                    st.rerun()

        # ══════════════════════════════════════════════════════════════════
        # PASO 8 · ÉXITO
        # ══════════════════════════════════════════════════════════════════
        elif paso == 8:
            st.markdown(f"""
            <div class="onb-success">
                <div class="success-emoji">🎉</div>
                <h2>¡Todo listo, {nombre_corto}!</h2>
                <p>Tu perfil está configurado. Ahora ya puedes gestionar tus vacaciones y horas extra con total comodidad.</p>
            </div>
            """, unsafe_allow_html=True)

            _, col_btn, _ = st.columns([1, 2, 1])
            with col_btn:
                if st.button("🏖️ Entrar al portal →", type="primary", use_container_width=True):
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)  # cierre onb-wrapper