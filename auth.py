import streamlit as st # type: ignore
from datetime import date
from database import Session, Usuario

def login():
    st.markdown("""
    <style>
        .login-header { text-align: center; padding: 2rem 0 1rem 0; }
        .login-header h1 { font-size: 2.5rem; color: #1a73e8; }
        .login-header p  { color: #666; font-size: 1rem; }
    </style>
    <div class="login-header">
        <h1>🏖️ Portal de Empleados</h1>
        <p>Sistema de control de vacaciones y compensación de horas</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        tab1, tab2 = st.tabs(["🔐 Iniciar sesión", "🆕 Registrarse"])

        # ── Inicio de sesión ─────────────────────────────────────────────
        with tab1:
            with st.container(border=True):
                st.subheader("Introduce tus credenciales")
                email = st.text_input("📧 Email corporativo", placeholder="nombre@empresa.com")
                password = st.text_input("🔑 Contraseña", type="password", placeholder="Tu contraseña")

                if st.button("Entrar →", use_container_width=True, type="primary"):
                    if not email or not password:
                        st.warning("Rellena todos los campos.")
                    else:
                        session = Session()
                        usuario = session.query(Usuario).filter_by(
                            email=email.strip(), password=password
                        ).first()
                        session.close()
                        if usuario:
                            st.session_state["usuario_id"]     = usuario.id
                            st.session_state["usuario_nombre"] = usuario.nombre
                            st.session_state["usuario_rol"]    = usuario.rol
                            st.session_state["usuario_depto"]  = usuario.departamento
                            st.rerun()
                        else:
                            st.error("❌ Email o contraseña incorrectos.")

        # ── Registro ─────────────────────────────────────────────────────
        with tab2:
            with st.container(border=True):
                st.subheader("Crea tu cuenta")
                nombre = st.text_input("👤 Nombre completo")
                email_reg = st.text_input("📧 Email corporativo", key="reg_email")
                password_reg = st.text_input(
                    "🔑 Contraseña", type="password", placeholder="Mínimo 8 caracteres",
                    key="reg_password"
                )
                confirm = st.text_input(
                    "🔁 Confirmar contraseña", type="password",
                    key="reg_confirm"
                )

                if st.button("Registrarse →", use_container_width=True, type="primary"):
                    errores = []
                    if not nombre or not email_reg or not password_reg:
                        errores.append("Todos los campos son obligatorios.")
                    if password_reg != confirm:
                        errores.append("Las contraseñas no coinciden.")
                    if len(password_reg) < 8:
                        errores.append("La contraseña debe tener al menos 8 caracteres.")
                    session = Session()
                    existe = session.query(Usuario).filter_by(email=email_reg.strip()).first()
                    session.close()
                    if existe:
                        errores.append("Ya existe una cuenta con ese email.")

                    if errores:
                        for e in errores:
                            st.error(e)
                    else:
                        session = Session()
                        es_primer_usuario = session.query(Usuario).count() == 0
                        nuevo = Usuario(
                            nombre=nombre.strip(),
                            email=email_reg.strip(),
                            password=password_reg,
                            rol="admin" if es_primer_usuario else "empleado",
                            departamento="General",
                            dias_vacaciones_totales=22.0,
                            dias_vacaciones_usados=0.0,
                            dias_acumulados=0.0,
                            tipo_dias="habiles",
                            ultimo_reset_anual=date.today().year,
                            onboarding_completado=0,
                            preferencias_json="{}",
                            notif_email=True,
                            notif_sms=False,
                            notif_telegram=False,
                        )
                        session.add(nuevo)
                        session.commit()
                        session.refresh(nuevo)
                        session.close()

                        st.session_state["usuario_id"]     = nuevo.id
                        st.session_state["usuario_nombre"] = nuevo.nombre
                        st.session_state["usuario_rol"]    = nuevo.rol
                        st.session_state["usuario_depto"]  = nuevo.departamento
                        st.rerun()


def logout():
    for key in ["usuario_id", "usuario_nombre", "usuario_rol", "usuario_depto"]:
        st.session_state.pop(key, None)
    st.rerun()


def usuario_actual():
    session = Session()
    u = session.query(Usuario).get(st.session_state["usuario_id"])
    session.close()
    return u