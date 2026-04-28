"""
migrate_v2.py
─────────────────────────────────────────────────────────────────────────────
Migración v2: añade todas las columnas nuevas a la BD existente.
Ejecutar UNA SOLA VEZ antes de arrancar la app con las nuevas funcionalidades.

Uso:
    python migrate_v2.py
"""

import sqlite3
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "vacaciones.db")

if not os.path.exists(DB_PATH):
    print("ERROR: Base de datos no encontrada en:", DB_PATH)
    print("Ejecuta este script desde la carpeta raiz del proyecto.")
    exit(1)

conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def columnas_existentes(tabla):
    cursor.execute(f"PRAGMA table_info({tabla})")
    return [row[1] for row in cursor.fetchall()]


def add_column(tabla, columna, definicion):
    if columna not in columnas_existentes(tabla):
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
        print(f"  OK: {tabla}.{columna} anadida.")
    else:
        print(f"  --: {tabla}.{columna} ya existe.")


print("\n[1/4] Migrando tabla 'usuarios'...")
add_column("usuarios", "dias_acumulados",       "REAL    DEFAULT 0.0")
add_column("usuarios", "tipo_dias",             "TEXT    DEFAULT 'habiles'")
add_column("usuarios", "ultimo_reset_anual",    "INTEGER DEFAULT 0")
add_column("usuarios", "onboarding_completado", "INTEGER DEFAULT 0")
add_column("usuarios", "preferencias_json",     "TEXT    DEFAULT '{}'")
add_column("usuarios", "notif_email",           "INTEGER DEFAULT 1")
add_column("usuarios", "notif_sms",             "INTEGER DEFAULT 0")
add_column("usuarios", "notif_telegram",        "INTEGER DEFAULT 0")
add_column("usuarios", "telefono_sms",          "TEXT    DEFAULT ''")
add_column("usuarios", "telegram_chat_id",      "TEXT    DEFAULT ''")

print("\n[2/4] Migrando tabla 'solicitudes_vacaciones'...")
add_column("solicitudes_vacaciones", "tipo_dias", "TEXT DEFAULT 'habiles'")

print("\n[3/4] Creando tabla 'notificaciones'...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS notificaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER REFERENCES usuarios(id),
    fecha       DATE    NOT NULL,
    tipo        TEXT    DEFAULT 'info',
    titulo      TEXT    NOT NULL,
    mensaje     TEXT    DEFAULT '',
    leida       INTEGER DEFAULT 0
)
""")
print("  OK: tabla 'notificaciones' lista.")

print("\n[4/4] Creando tabla 'festivos_personalizados'...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS festivos_personalizados (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       DATE    NOT NULL UNIQUE,
    descripcion TEXT    DEFAULT 'Festivo local',
    activo      INTEGER DEFAULT 1
)
""")
print("  OK: tabla 'festivos_personalizados' lista.")

# Poner el año actual como reset para usuarios ya existentes
anio_actual = date.today().year
cursor.execute(
    "UPDATE usuarios SET ultimo_reset_anual = ? WHERE ultimo_reset_anual = 0",
    (anio_actual,)
)
filas = cursor.rowcount
if filas:
    print(f"\n  OK: {filas} usuarios actualizados con ultimo_reset_anual = {anio_actual}")

conn.commit()
conn.close()

print("\n============================================================")
print("MIGRACION v2 COMPLETADA. Arranca la app con:")
print("   streamlit run app.py")
print("============================================================\n")