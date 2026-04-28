"""
vistas/admin.py
Panel de administración global: usuarios, festivos, cierre anual y estadísticas.
"""

import streamlit as st  # type: ignore
from datetime import date

from database import Session, Usuario, SolicitudVacaciones, HorasExtra, FestivoPersonalizado
from acumulacion_dias import ejecutar_cierre_anual, obtener_saldo
from ajustes_notificaciones import panel_ajustes_notificaciones


def panel_admin(seleccion: str = "🏠 Mi Panel"):
    usuario_id = st.session_state["usuario_id"]

    if seleccion in ("🏠 Mi Panel", "📅 Mis Vacaciones"):
        from vistas.empleado import panel_empleado
        panel_empleado(seleccion)
        return

    if seleccion == "👥 Gestión de Equipo":
        _vista_gestion_usuarios(usuario_id)

    elif seleccion == "⚙️ Administración Global":
        _vista_admin_global()


def _vista_gestion_usuarios(admin_id: int):
    st.header("👥 Gestión de Usuarios")

    tab_emp, tab_sol, tab_roles = st.tabs([
        "👤 Todos los empleados",
        "📋 Todas las solicitudes",
        "🔧 Roles y departamentos",
    ])

    # ── Todos los empleados ────────────────────────────────────────────────
    with tab_emp:
        st.subheader("Listado completo de empleados")
        session = Session()
        usuarios = session.query(Usuario).order_by(Usuario.departamento, Usuario.nombre).all()
        session.close()

        filtro_depto = st.selectbox(
            "Filtrar por departamento",
            ["Todos"] + sorted({u.departamento for u in usuarios}),
        )

        for u in usuarios:
            if filtro_depto != "Todos" and u.departamento != filtro_depto:
                continue
            saldo = obtener_saldo(u.id)
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                col1.markdown(f"**{u.nombre}**")
                col1.caption(f"{u.email} · {u.departamento} · {u.rol.capitalize()}")
                col2.metric("Totales", f"{saldo.get('totales', 0):.0f}")
                col3.metric("Usados", f"{saldo.get('usados', 0):.0f}")
                col4.metric("Acum.", f"{saldo.get('acumulados', 0):.1f}")
                col5.metric("Disp.", f"{saldo.get('disponibles', 0):.1f}")

                with st.expander(f"✏️ Editar {u.nombre}"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        nuevo_rol = st.selectbox(
                            "Rol",
                            ["empleado", "manager", "admin"],
                            index=["empleado", "manager", "admin"].index(u.rol),
                            key=f"rol_{u.id}",
                        )
                    with col_b:
                        nuevo_depto = st.text_input("Departamento", value=u.departamento, key=f"depto_{u.id}")
                    with col_c:
                        nuevos_dias = st.number_input(
                            "Días vacaciones/año",
                            value=float(u.dias_vacaciones_totales),
                            min_value=0.0,
                            step=1.0,
                            key=f"dias_{u.id}",
                        )

                    if st.button("💾 Guardar cambios", key=f"save_{u.id}"):
                        session = Session()
                        usr = session.query(Usuario).get(u.id)
                        usr.rol = nuevo_rol
                        usr.departamento = nuevo_depto.strip()
                        usr.dias_vacaciones_totales = nuevos_dias
                        session.commit()
                        session.close()
                        st.success("✅ Cambios guardados.")
                        st.rerun()

                    if u.id != admin_id:
                        if st.button("🗑️ Eliminar usuario", key=f"del_{u.id}", type="secondary"):
                            session = Session()
                            usr = session.query(Usuario).get(u.id)
                            session.delete(usr)
                            session.commit()
                            session.close()
                            st.warning(f"Usuario {u.nombre} eliminado.")
                            st.rerun()

    # ── Todas las solicitudes ──────────────────────────────────────────────
    with tab_sol:
        st.subheader("Todas las solicitudes de vacaciones")
        session = Session()
        solicitudes = (
            session.query(SolicitudVacaciones)
            .order_by(SolicitudVacaciones.fecha_inicio.desc())
            .all()
        )
        session.close()

        filtro_estado = st.selectbox("Filtrar por estado", ["Todos", "pendiente", "aprobada", "rechazada"])

        estado_color = {"pendiente": "🟡", "aprobada": "🟢", "rechazada": "🔴"}

        for s in solicitudes:
            if filtro_estado != "Todos" and s.estado != filtro_estado:
                continue
            session = Session()
            emp = session.query(Usuario).get(s.empleado_id)
            session.close()

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                col1.markdown(f"**{emp.nombre if emp else '?'}** · {emp.departamento if emp else ''}")
                col2.write(f"{s.fecha_inicio.strftime('%d/%m/%Y')} → {s.fecha_fin.strftime('%d/%m/%Y')}")
                col3.write(f"{s.dias:.0f} días")
                col4.write(f"{estado_color.get(s.estado, '⚪')} {s.estado.capitalize()}")
                if s.comentario_manager:
                    st.caption(f"💬 {s.comentario_manager}")

    # ── Roles y departamentos ──────────────────────────────────────────────
    with tab_roles:
        st.subheader("Resumen por departamentos")
        session = Session()
        usuarios = session.query(Usuario).all()
        session.close()

        deptos = sorted({u.departamento for u in usuarios})
        for d in deptos:
            emps = [u for u in usuarios if u.departamento == d]
            with st.container(border=True):
                st.markdown(f"**{d}** · {len(emps)} personas")
                cols = st.columns(len(emps)) if emps else []
                for col, emp in zip(cols, emps):
                    col.caption(f"{emp.nombre}\n({emp.rol})")


def _vista_admin_global():
    st.header("⚙️ Administración Global")

    tab_cierre, tab_festivos, tab_ajustes = st.tabs([
        "🔄 Cierre anual",
        "📆 Festivos personalizados",
        "🔔 Mis ajustes",
    ])

    # ── Cierre anual ──────────────────────────────────────────────────────
    with tab_cierre:
        st.subheader("Cierre anual de vacaciones")
        st.info(
            "El cierre anual transfiere los días no utilizados al saldo acumulado "
            "de cada empleado y reinicia el contador para el nuevo año. "
            "Este proceso es **automático el 1 de enero**, pero puedes ejecutarlo manualmente."
        )

        anio_actual = date.today().year
        st.warning(f"⚠️ Ejecutar el cierre para el año **{anio_actual}** afectará a TODOS los empleados.")

        if st.button("🔄 Ejecutar cierre anual ahora", type="primary"):
            with st.spinner("Procesando..."):
                resultados = ejecutar_cierre_anual(anio_actual)
            st.success(f"✅ Procesados {len(resultados)} empleados.")
            for r in resultados:
                st.write(
                    f"· **{r['nombre']}**: {r['dias_nuevos']:.0f} días nuevos + "
                    f"{r['dias_acumulados']:.1f} acumulados = **{r['dias_total']:.1f} total**"
                )

    # ── Festivos personalizados ────────────────────────────────────────────
    with tab_festivos:
        st.subheader("Festivos locales / personalizados")
        st.caption("Añade festivos de tu comunidad autónoma o empresa. Estos días no se descontarán en solicitudes de días hábiles.")

        session = Session()
        festivos = session.query(FestivoPersonalizado).order_by(FestivoPersonalizado.fecha).all()
        session.close()

        if festivos:
            for f in festivos:
                col1, col2, col3 = st.columns([2, 3, 1])
                col1.write(f.fecha.strftime("%d/%m/%Y"))
                col2.write(f.descripcion)
                with col3:
                    estado = "✅ Activo" if f.activo else "⭕ Inactivo"
                    if st.button(estado, key=f"toggle_fest_{f.id}", use_container_width=True):
                        session = Session()
                        fest = session.query(FestivoPersonalizado).get(f.id)
                        fest.activo = not fest.activo
                        session.commit()
                        session.close()
                        st.rerun()
        else:
            st.info("No hay festivos personalizados. Añade el primero.")

        st.divider()
        st.subheader("Añadir festivo")
        with st.container(border=True):
            col_f, col_d = st.columns([2, 3])
            nueva_fecha = col_f.date_input("📅 Fecha del festivo", key="new_fest_fecha")
            nueva_desc = col_d.text_input("📝 Descripción", placeholder="Ej: Día de la Comunidad", key="new_fest_desc")

            if st.button("➕ Añadir festivo", type="primary"):
                if not nueva_desc.strip():
                    st.error("Añade una descripción.")
                else:
                    session = Session()
                    existe = session.query(FestivoPersonalizado).filter_by(fecha=nueva_fecha).first()
                    if existe:
                        st.error("Ya existe un festivo en esa fecha.")
                    else:
                        session.add(FestivoPersonalizado(fecha=nueva_fecha, descripcion=nueva_desc.strip()))
                        session.commit()
                        st.success(f"✅ Festivo '{nueva_desc}' añadido.")
                    session.close()
                    st.rerun()

    # ── Ajustes propios del admin ─────────────────────────────────────────
    with tab_ajustes:
        panel_ajustes_notificaciones()