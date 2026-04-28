import streamlit as st # type: ignore
import os
import sys

# --- CONFIGURACIÓN DE RUTAS (Evita errores de importación en Streamlit Cloud) ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- IMPORTS DE LA APLICACIÓN ---
from database import init_db
from auth import login, logout
from onboarding import mostrar_onboarding, onboarding_requerido
from vacaciones_utils import verificar_cierre_anual_automatico
from vistas.empleado import panel_empleado
from vistas.manager  import panel_manager
from vistas.admin    import panel_admin

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Portal Vacaciones — Empresa",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
    /* Ocultar la navegación por defecto de archivos para usar nuestra lógica de roles */
    [data-testid="stSidebarNav"] { display: none; }
    
    .sidebar-user-info {
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
# Crea las tablas si no existen
init_db()

# Verifica si toca resetear vacaciones por cambio de año
try:
    verificar_cierre_anual_automatico()
except Exception as e:
    # Fallo silencioso en producción para no bloquear la app
    pass

# --- LÓGICA DE CONTROL DE FLUJO ---

# 1. Si el usuario no está logueado, mostrar pantalla de login
if "usuario_id" not in st.session_state:
    login()

# 2. Si está logueado pero no ha completado el proceso inicial (onboarding)
elif onboarding_requerido():
    mostrar_onboarding()

# 3. Aplicación principal (Navegación por Roles)
else:
    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/beach.png", width=60)
        st.markdown(f"### {st.session_state['usuario_nombre']}")
        st.caption(f"🏢 {st.session_state.get('usuario_depto', 'General')}")
        st.markdown(f"🔖 Rol: `{st.session_state['usuario_rol'].upper()}`")
        
        st.divider()
        
        # Opciones comunes a todos los usuarios
        menu_principal = ["🏠 Mi Panel", "📅 Mis Vacaciones"]
        
        # Opciones específicas por rol
        if st.session_state["usuario_rol"] == "manager":
            menu_principal += ["👥 Gestión de Equipo", "📊 Estadísticas Depto."]
        elif st.session_state["usuario_rol"] == "admin":
            menu_principal += ["👥 Gestión de Equipo", "⚙️ Administración Global"]
            
        seleccion = st.radio("Navegación", menu_principal)
        
        st.spacer()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()

    # --- RENDERIZADO DE VISTAS SEGÚN EL ROL ---
    # Nota: Todas las vistas se encuentran en la carpeta 'vistas/'
    
    if st.session_state["usuario_rol"] == "admin":
        panel_admin(seleccion)
    elif st.session_state["usuario_rol"] == "manager":
        panel_manager(seleccion)
    else:
        panel_empleado(seleccion)

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Portal de Vacaciones v2.1")