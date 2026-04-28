# 🏖️ Portal Vacaciones — Guía de integración v2

## Archivos nuevos entregados

| Archivo | Descripción |
|---|---|
| `festivos.py` | Festivos nacionales España + helpers días hábiles/naturales |
| `notificaciones.py` | Motor de notificaciones: email (oblig.) + SMS + Telegram |
| `acumulacion_dias.py` | Saldo, acumulación interanual y cierre anual |
| `selector_fechas.py` | Componente UI selector de fechas con festivos bloqueados |
| `ajustes_notificaciones.py` | Panel de ajustes (tipo de días, SMS, Telegram) |
| `onboarding_v2_patch.py` | Dos nuevos pasos para el onboarding existente |
| `migrate_v2.py` | Script de migración de BD (idempotente) |
| `.env.example` | Plantilla de variables de entorno |

---

## Paso 1 — Migración de la base de datos

```bash
python migrate_v2.py
```

Añade las columnas `onboarding_completado` y `preferencias_json` si no existen.
Seguro ejecutarlo aunque ya hayas corrido `migrate_onboarding.py` antes.

---

## Paso 2 — Variables de entorno

Copia `.env.example` a `.env` y rellena tus credenciales:

```bash
cp .env.example .env
# edita .env con tu editor
```

Instala la librería para leerlo:
```bash
pip install python-dotenv
```

Añade al principio de `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

Las librerías opcionales (solo si activas SMS o Telegram):
```bash
pip install twilio          # para SMS
# Telegram usa urllib de stdlib, no necesita instalación extra
```

---

## Paso 3 — Usar el selector de fechas en la vista de solicitud

En `vistas/empleado.py`, en la sección donde el empleado crea una solicitud,
sustituye tu actual date_input por:

```python
from selector_fechas import selector_fechas_vacaciones
from acumulacion_dias import obtener_saldo, calcular_dias_solicitud

saldo = obtener_saldo(st.session_state["usuario_id"])
inicio, fin, dias, ok = selector_fechas_vacaciones(
    saldo_disponible = saldo["disponibles"],
    tipo_dias        = saldo["tipo_dias"],
)

if ok and st.button("Solicitar vacaciones", type="primary"):
    # ... crear SolicitudVacaciones en BD ...
    from notificaciones import notif_solicitud_creada
    notif_solicitud_creada(
        usuario_id = st.session_state["usuario_id"],
        inicio     = inicio.strftime("%d/%m/%Y"),
        fin        = fin.strftime("%d/%m/%Y"),
        dias       = dias,
    )
    st.success("Solicitud enviada. Recibirás un email de confirmación.")
```

---

## Paso 4 — Notificar al aprobar/rechazar (vista manager)

En `vistas/manager.py`, cuando el manager aprueba o rechaza:

```python
from notificaciones import notif_solicitud_aprobada, notif_solicitud_rechazada
from acumulacion_dias import consumir_dias, devolver_dias

# Al aprobar:
consumir_dias(solicitud.empleado_id, solicitud.dias)
notif_solicitud_aprobada(
    solicitud.empleado_id,
    solicitud.fecha_inicio.strftime("%d/%m/%Y"),
    solicitud.fecha_fin.strftime("%d/%m/%Y"),
    solicitud.dias,
)

# Al rechazar:
devolver_dias(solicitud.empleado_id, solicitud.dias)   # si estaban descontados
notif_solicitud_rechazada(
    solicitud.empleado_id,
    solicitud.fecha_inicio.strftime("%d/%m/%Y"),
    solicitud.fecha_fin.strftime("%d/%m/%Y"),
    solicitud.dias,
    motivo = solicitud.comentario_manager,
)
```

---

## Paso 5 — Panel de ajustes para el empleado

Añade una pestaña "⚙️ Ajustes" en `vistas/empleado.py`:

```python
from ajustes_notificaciones import panel_ajustes_notificaciones

tab1, tab2, tab3 = st.tabs(["🏠 Inicio", "📅 Mis vacaciones", "⚙️ Ajustes"])
with tab3:
    panel_ajustes_notificaciones()
```

---

## Paso 6 — Cierre anual (1 de enero)

Ejecuta este script una vez al año (p.ej. con cron el 1 de enero):

```bash
python -c "
from acumulacion_dias import ejecutar_cierre_anual
from datetime import date
resultados = ejecutar_cierre_anual(date.today().year)
print(f'Procesados {len(resultados)} empleados')
"
```

O añade un botón en el panel admin:

```python
from acumulacion_dias import ejecutar_cierre_anual
from datetime import date

if st.button("🔄 Ejecutar cierre anual"):
    resultados = ejecutar_cierre_anual(date.today().year)
    st.success(f"Procesados {len(resultados)} empleados.")
    for r in resultados:
        st.write(f"· {r['nombre']}: {r['dias_total']:.0f} días disponibles")
```

---

## Paso 7 — Nuevos pasos en el onboarding (opcional pero recomendado)

Lee `onboarding_v2_patch.py` para instrucciones detalladas.
En resumen, debes insertar en `onboarding.py`:

1. Dos nuevas entradas en la lista `PASOS`.
2. Dos nuevos bloques `elif` en `mostrar_onboarding()`.
3. Actualizar `_guardar_preferencias()` para las nuevas claves.

---

## Resumen de dependencias

```
streamlit
sqlalchemy
python-dotenv      # para leer .env
twilio             # SOLO si activas SMS
```

Telegram y el correo SMTP no requieren librerías externas (urllib + smtplib de stdlib).

---

## Funcionamiento del modo desarrollo (sin .env)

Si `SMTP_USER` y `SMTP_PASSWORD` no están definidos, las notificaciones
**se imprimen por consola** en lugar de enviarse. Perfecto para desarrollo local.
