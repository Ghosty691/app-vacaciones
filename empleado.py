"""
vistas/empleado.py
Panel principal del empleado: inicio, solicitud de vacaciones, horas extra y ajustes.
"""

import streamlit as st  # type: ignore
from datetime import date

from database import Session, Usuario, SolicitudVacaciones, HorasExtra, Notificacion
from acumulacion_dias import obtener_saldo, consumir_dias
from selector_fechas import selector_fechas_vacaciones
from notificaciones import notif_solicitud_recibida
from ajustes_notificaciones import panel_ajustes_notificaciones


def panel_empleado(seleccion: str = "🏠 Mi Panel"):
    usuario_id = st.session_state["usuario_id"]

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 Inicio",
        "📅 Mis Vacaciones",
        "⏱️ Horas Extra",
        "⚙️ Ajustes",
    ])

    # ── TAB 1: INICIO ────────────────────────────────────────────────────────
    with tab1:
        session = Session()
        usuario = session.query(Usuario).get(usuario_id)
        session.close()

        st.title(f"¡Hola, {usuario.nombre.split()[0]}! 👋")
        st.caption(f"Departamento: {usuario.departamento} · Rol: {usuario.rol.capitalize()}")

        saldo = obtener_saldo(usuario_id)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📅 Días totales", f"{saldo.get('totales', 0):.0f}")
        col2.metric("✅ Días usados", f"{saldo.get('usados', 0):.0f}")
        col3.metric("⏳ Pendientes", f"{saldo.get('pendientes', 0):.0f}")
        col4.metric("🟢 Disponibles", f"{saldo.get('disponibles', 0):.1f}")

        if saldo.get("acumulados", 0) > 0:
            st.info(f"ℹ️ Tienes **{saldo['acumulados']:.1f} días acumulados** de años anteriores incluidos en tu saldo.")

        st.divider()
        st.subheader("🔔 Notificaciones recientes")
        session = Session()
        notifs = (
            session.query(Notificacion)
            .filter_by(empleado_id=usuario_id)
            .order_by(Notificacion.fecha.desc())
            .limit(5)
            .all()
        )
        session.close()

        if not notifs:
            st.info("No tienes notificaciones recientes.")
        else:
            iconos = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
            for n in notifs:
                icono = iconos.get(n.tipo, "ℹ️")
                leida_css = "" if not n.leida else "color:#999;"
                with st.container(border=True):
                    st.markdown(
                        f"<span style='{leida_css}'>{icono} **{n.titulo}** &nbsp;&nbsp;<small>{n.fecha}</small><br>{n.mensaje}</span>",
                        unsafe_allow_html=True,
                    )
            # Marcar como leídas
            session = Session()
            session.query(Notificacion).filter_by(empleado_id=usuario_id, leida=False).update({"leida": True})
            session.commit()
            session.close()

    # ── TAB 2: MIS VACACIONES ────────────────────────────────────────────────
    with tab2:
        st.header("📅 Mis Vacaciones")

        sub1, sub2 = st.tabs(["➕ Nueva solicitud", "📋 Mis solicitudes"])

        with sub1:
            st.subheader("Solicitar vacaciones")
            saldo = obtener_saldo(usuario_id)

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Disponibles", f"{saldo.get('disponibles', 0):.1f} días")
            col_b.metric("Tipo de días", saldo.get("tipo_dias", "hábiles").capitalize())
            col_c.metric("Año", saldo.get("anio", date.today().year))

            st.divider()

            inicio, fin, dias, ok = selector_fechas_vacaciones(
                saldo_disponible=saldo.get("disponibles", 0),
                tipo_dias=saldo.get("tipo_dias", "habiles"),
            )

            motivo = st.text_area(
                "📝 Motivo (opcional)",
                placeholder="Vacaciones de verano, asunto personal...",
                max_chars=300,
            )

            if ok and st.button("📨 Enviar solicitud", type="primary", use_container_width=True):
                session = Session()
                nueva = SolicitudVacaciones(
                    empleado_id=usuario_id,
                    fecha_inicio=inicio,
                    fecha_fin=fin,
                    dias=dias,
                    tipo_dias=saldo.get("tipo_dias", "habiles"),
                    motivo=motivo,
                    estado="pendiente",
                )
                session.add(nueva)
                session.commit()
                session.close()

                try:
                    notif_solicitud_recibida(usuario_id, inicio, fin, dias)
                except Exception:
                    pass

                st.success(f"✅ Solicitud enviada: {dias:.0f} días del {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}.")
                st.rerun()

        with sub2:
            st.subheader("Historial de solicitudes")
            session = Session()
            solicitudes = (
                session.query(SolicitudVacaciones)
                .filter_by(empleado_id=usuario_id)
                .order_by(SolicitudVacaciones.fecha_inicio.desc())
                .all()
            )
            session.close()

            if not solicitudes:
                st.info("Aún no tienes solicitudes registradas.")
            else:
                estado_color = {
                    "pendiente": "🟡",
                    "aprobada":  "🟢",
                    "rechazada": "🔴",
                }
                for s in solicitudes:
                    with st.container(border=True):
                        col_i, col_f, col_d, col_e = st.columns([2, 2, 1, 1])
                        col_i.write(f"**{s.fecha_inicio.strftime('%d/%m/%Y')}**")
                        col_f.write(f"**{s.fecha_fin.strftime('%d/%m/%Y')}**")
                        col_d.write(f"{s.dias:.0f} días")
                        col_e.write(f"{estado_color.get(s.estado, '⚪')} {s.estado.capitalize()}")
                        if s.comentario_manager:
                            st.caption(f"💬 Manager: {s.comentario_manager}")

    # ── TAB 3: HORAS EXTRA ───────────────────────────────────────────────────
    with tab3:
        st.header("⏱️ Horas Extra")

        sub_reg, sub_hist = st.tabs(["➕ Registrar horas", "📋 Mis registros"])

        with sub_reg:
            st.subheader("Registrar horas extra")
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    fecha_he = st.date_input("📅 Fecha", value=date.today(), key="he_fecha")
                with col2:
                    horas_he = st.number_input("⏰ Horas realizadas", min_value=0.5, max_value=24.0, step=0.5, value=1.0, key="he_horas")

                desc_he = st.text_area("📝 Descripción", placeholder="Describe el trabajo realizado...", key="he_desc")

                tipo_comp = st.selectbox(
                    "💡 Compensación preferida",
                    options=["pendiente", "dias_libres", "pago"],
                    format_func=lambda x: {"pendiente": "⏳ Pendiente de decisión", "dias_libres": "🕐 Días libres", "pago": "💰 Pago en nómina"}[x],
                    key="he_tipo",
                )

                if st.button("💾 Registrar horas extra", type="primary", use_container_width=True):
                    if not desc_he.strip():
                        st.error("❌ Introduce una descripción.")
                    else:
                        session = Session()
                        nueva_he = HorasExtra(
                            empleado_id=usuario_id,
                            fecha=fecha_he,
                            horas=horas_he,
                            descripcion=desc_he.strip(),
                            tipo_compensacion=tipo_comp,
                        )
                        session.add(nueva_he)
                        session.commit()
                        session.close()
                        st.success(f"✅ Registradas {horas_he:.1f}h del {fecha_he.strftime('%d/%m/%Y')}.")
                        st.rerun()

        with sub_hist:
            st.subheader("Mis registros de horas extra")
            session = Session()
            horas_list = (
                session.query(HorasExtra)
                .filter_by(empleado_id=usuario_id)
                .order_by(HorasExtra.fecha.desc())
                .all()
            )
            total_horas = sum(h.horas for h in horas_list)
            session.close()

            if not horas_list:
                st.info("No tienes horas extra registradas.")
            else:
                st.metric("Total horas extra", f"{total_horas:.1f}h")
                comp_labels = {"pendiente": "⏳ Pendiente", "dias_libres": "🕐 Días libres", "pago": "💰 Pago"}
                for h in horas_list:
                    with st.container(border=True):
                        col_f, col_h, col_t, col_d = st.columns([2, 1, 2, 3])
                        col_f.write(h.fecha.strftime("%d/%m/%Y"))
                        col_h.write(f"**{h.horas:.1f}h**")
                        col_t.write(comp_labels.get(h.tipo_compensacion, h.tipo_compensacion))
                        col_d.write(h.descripcion)

    # ── TAB 4: AJUSTES ───────────────────────────────────────────────────────
    with tab4:
        panel_ajustes_notificaciones()