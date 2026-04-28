import streamlit as st # type: ignore
from database import init_db
from auth import login, logout
from onboarding import mostrar_onboarding, onboarding_requerido
from vacaciones_utils import verificar_cierre_anual_automatico
from vistas.empleado import panel_empleado
from vistas.manager  import panel_manager
from vistas.admin    import panel_admin

st.set_page_config(
    page_title="Portal Vacaciones — Empresa",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
    [data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

init_db()

try:
    verificar_cierre_anual_automatico()
except Exception:
    pass

if "usuario_id" not in st.session_state:
    login()

elif onboarding_requerido():
    mostrar_onboarding()

else:
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/beach.png", width=60)
        st.markdown(f"### {st.session_state['usuario_nombre']}")
        st.caption(f"🏢 {st.session_state.get('usuario_depto', '')}")
        st.caption(f"🔖 Rol: `{st.session_state['usuario_rol']}`")
        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            logout()
        st.divider()
        st.caption("Portal de Empleados v2.0")
        st.caption("© 2026 Empresa S.A.")

    rol = st.session_state["usuario_rol"]
    if rol == "empleado":
        panel_empleado()
    elif rol == "manager":
        panel_manager()
    elif rol == "admin":
        panel_admin()
    else:
        st.error("Rol no reconocido. Contacta con el administrador.")