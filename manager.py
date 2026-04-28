"""
vistas/manager.py
Panel del manager: aprobación de solicitudes, gestión de equipo y estadísticas.
"""

import streamlit as st  # type: ignore
from datetime import date

from database import Session, Usuario, SolicitudVacaciones, HorasExtra
from acumulacion_dias import obtener_saldo, consumir_dias, devolver_dias
from notificaciones import notif_solicitud_aprobada, notif_solicitud_rechazada
from ajustes_notificaciones import panel_ajustes_notificaciones


def panel_manager(seleccion: str = "🏠 Mi Panel"):
    usuario_id = st.session_state["usuario_id"]
    depto = st.session_state.get("usuario_depto", "")

    # ── Navegación lateral ────────────────────────────────────────────────────
    if seleccion in ("🏠 Mi Panel", "📅 Mis Vacaciones"):
        # Importar panel empleado para vistas propias
        from vistas.empleado import panel_empleado
        panel_empleado(seleccion)
        return

    if seleccion == "👥 Gestión de Equipo":
        _vista_gestion_equipo(usuario_id, depto)

    elif seleccion == "📊 Estadísticas Depto.":
        _vista_estadisticas(depto)


def _vista_gestion_equipo(manager_id: int, depto: str):
    st.header("👥 Gestión del Equipo")

    tab_sol, tab_horas, tab_empleados = st.tabs([
        "📋 Solicitudes pendientes",
        "⏱️ Horas extra del equipo",
        "👤 Mis empleados",
    ])

    # ── Solicitudes pendientes ─────────────────────────────────────────────
    with tab_sol:
        st.subheader("Solicitudes pendientes de aprobación")

        session = Session()
        # Solicitudes pendientes de empleados del mismo departamento
        solicitudes = (
            session.query(SolicitudVacaciones)
            .join(Usuario, SolicitudVacaciones.empleado_id == Usuario.id)
            .filter(
                Usuario.departamento == depto,
                Usuario.id != manager_id,
                SolicitudVacaciones.estado == "pendiente",
            )
            .order_by(SolicitudVacaciones.fecha_inicio)
            .all()
        )
        session.close()

        if not solicitudes:
            st.success("✅ No hay solicitudes pendientes.")
        else:
            st.info(f"Hay **{len(solicitudes)}** solicitudes pendientes de revisión.")
            for s in solicitudes:
                with st.container(border=True):
                    session = Session()
                    emp = session.query(Usuario).get(s.empleado_id)
                    session.close()

                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{emp.nombre if emp else 'Desconocido'}**")
                        st.caption(f"Del {s.fecha_inicio.strftime('%d/%m/%Y')} al {s.fecha_fin.strftime('%d/%m/%Y')} · {s.dias:.0f} días")
                        if s.motivo:
                            st.caption(f"📝 {s.motivo}")

                    with col2:
                        saldo = obtener_saldo(s.empleado_id)
                        st.metric("Saldo disponible", f"{saldo.get('disponibles', 0):.1f} días")

                    with col3:
                        comentario = st.text_input(
                            "Comentario (opcional)",
                            key=f"cmt_{s.id}",
                            placeholder="Añade un comentario...",
                        )
                        col_a, col_r = st.columns(2)
                        with col_a:
                            if st.button("✅ Aprobar", key=f"apr_{s.id}", type="primary", use_container_width=True):
                                session = Session()
                                sol = session.query(SolicitudVacaciones).get(s.id)
                                sol.estado = "aprobada"
                                sol.comentario_manager = comentario
                                session.commit()
                                session.close()
                                consumir_dias(s.empleado_id, s.dias)
                                try:
                                    notif_solicitud_aprobada(
                                        s.empleado_id, s.fecha_inicio, s.fecha_fin,
                                        s.dias, comentario
                                    )
                                except Exception:
                                    pass
                                st.success("Solicitud aprobada.")
                                st.rerun()
                        with col_r:
                            if st.button("❌ Rechazar", key=f"rec_{s.id}", use_container_width=True):
                                if not comentario.strip():
                                    st.error("Añade un motivo de rechazo.")
                                else:
                                    session = Session()
                                    sol = session.query(SolicitudVacaciones).get(s.id)
                                    sol.estado = "rechazada"
                                    sol.comentario_manager = comentario
                                    session.commit()
                                    session.close()
                                    try:
                                        notif_solicitud_rechazada(
                                            s.empleado_id, s.fecha_inicio, s.fecha_fin, comentario
                                        )
                                    except Exception:
                                        pass
                                    st.success("Solicitud rechazada.")
                                    st.rerun()

    # ── Horas extra del equipo ─────────────────────────────────────────────
    with tab_horas:
        st.subheader("Horas extra registradas por el equipo")
        session = Session()
        horas = (
            session.query(HorasExtra)
            .join(Usuario, HorasExtra.empleado_id == Usuario.id)
            .filter(
                Usuario.departamento == depto,
                Usuario.id != manager_id,
                HorasExtra.tipo_compensacion == "pendiente",
            )
            .order_by(HorasExtra.fecha.desc())
            .all()
        )
        session.close()

        if not horas:
            st.info("No hay horas extra pendientes de gestión.")
        else:
            for h in horas:
                with st.container(border=True):
                    session = Session()
                    emp = session.query(Usuario).get(h.empleado_id)
                    session.close()

                    col1, col2, col3 = st.columns([3, 1, 2])
                    col1.markdown(f"**{emp.nombre if emp else '?'}** — {h.fecha.strftime('%d/%m/%Y')}")
                    col1.caption(h.descripcion)
                    col2.metric("Horas", f"{h.horas:.1f}h")

                    with col3:
                        tipo = st.selectbox(
                            "Compensación",
                            ["pendiente", "dias_libres", "pago"],
                            format_func=lambda x: {"pendiente": "⏳ Pendiente", "dias_libres": "🕐 Días libres", "pago": "💰 Pago"}[x],
                            index=0,
                            key=f"he_tipo_{h.id}",
                        )
                        if tipo != "pendiente" and st.button("Guardar", key=f"he_save_{h.id}", use_container_width=True):
                            session = Session()
                            he = session.query(HorasExtra).get(h.id)
                            he.tipo_compensacion = tipo
                            session.commit()
                            session.close()
                            st.success("Actualizado.")
                            st.rerun()

    # ── Mis empleados ─────────────────────────────────────────────────────
    with tab_empleados:
        st.subheader(f"Empleados — {depto}")
        session = Session()
        empleados = (
            session.query(Usuario)
            .filter(
                Usuario.departamento == depto,
                Usuario.id != manager_id,
                Usuario.rol == "empleado",
            )
            .all()
        )
        session.close()

        if not empleados:
            st.info("No tienes empleados asignados en este departamento.")
        else:
            for emp in empleados:
                saldo = obtener_saldo(emp.id)
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    col1.markdown(f"**{emp.nombre}**")
                    col1.caption(emp.email)
                    col2.metric("Totales", f"{saldo.get('totales', 0):.0f}")
                    col3.metric("Usados", f"{saldo.get('usados', 0):.0f}")
                    col4.metric("Disponibles", f"{saldo.get('disponibles', 0):.1f}")


def _vista_estadisticas(depto: str):
    st.header(f"📊 Estadísticas — {depto}")

    session = Session()
    empleados = session.query(Usuario).filter_by(departamento=depto, rol="empleado").all()
    solicitudes = (
        session.query(SolicitudVacaciones)
        .join(Usuario, SolicitudVacaciones.empleado_id == Usuario.id)
        .filter(Usuario.departamento == depto)
        .all()
    )
    session.close()

    total_emp = len(empleados)
    aprobadas = sum(1 for s in solicitudes if s.estado == "aprobada")
    rechazadas = sum(1 for s in solicitudes if s.estado == "rechazada")
    pendientes = sum(1 for s in solicitudes if s.estado == "pendiente")
    total_dias_usados = sum(s.dias for s in solicitudes if s.estado == "aprobada")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👤 Empleados", total_emp)
    col2.metric("✅ Aprobadas", aprobadas)
    col3.metric("❌ Rechazadas", rechazadas)
    col4.metric("⏳ Pendientes", pendientes)
    col5.metric("📅 Días usados", f"{total_dias_usados:.0f}")

    st.divider()
    st.subheader("Saldo por empleado")
    for emp in empleados:
        saldo = obtener_saldo(emp.id)
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        col1.write(emp.nombre)
        col2.write(f"Total: {saldo.get('totales', 0):.0f}")
        col3.write(f"Usados: {saldo.get('usados', 0):.0f}")
        col4.write(f"Disp.: {saldo.get('disponibles', 0):.1f}")