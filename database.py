from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text, ForeignKey, Boolean # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker, relationship # type: ignore
from datetime import date

Base = declarative_base()
engine = create_engine("sqlite:///vacaciones.db", echo=False)
Session = sessionmaker(bind=engine)


class Usuario(Base):
    __tablename__ = "usuarios"
    id                          = Column(Integer, primary_key=True)
    nombre                      = Column(String, nullable=False)
    email                       = Column(String, unique=True, nullable=False)
    password                    = Column(String, nullable=False)
    rol                         = Column(String, default="empleado")
    departamento                = Column(String, default="General")
    dias_vacaciones_totales     = Column(Float, default=22.0)
    dias_vacaciones_usados      = Column(Float, default=0.0)
    dias_acumulados             = Column(Float, default=0.0)
    tipo_dias                   = Column(String, default="habiles")
    ultimo_reset_anual          = Column(Integer, default=0)
    onboarding_completado       = Column(Integer, default=0)
    preferencias_json           = Column(Text, default="{}")
    notif_email                 = Column(Boolean, default=True)
    notif_sms                   = Column(Boolean, default=False)
    notif_telegram              = Column(Boolean, default=False)
    telefono_sms                = Column(String, default="")
    telegram_chat_id            = Column(String, default="")
    solicitudes    = relationship("SolicitudVacaciones", back_populates="empleado", cascade="all, delete")
    horas          = relationship("HorasExtra",          back_populates="empleado", cascade="all, delete")
    notificaciones = relationship("Notificacion",        back_populates="empleado", cascade="all, delete")


class SolicitudVacaciones(Base):
    __tablename__ = "solicitudes_vacaciones"
    id                  = Column(Integer, primary_key=True)
    empleado_id         = Column(Integer, ForeignKey("usuarios.id"))
    fecha_inicio        = Column(Date, nullable=False)
    fecha_fin           = Column(Date, nullable=False)
    dias                = Column(Float, nullable=False)
    tipo_dias           = Column(String, default="habiles")
    motivo              = Column(Text, default="")
    estado              = Column(String, default="pendiente")
    comentario_manager  = Column(Text, default="")
    empleado = relationship("Usuario", back_populates="solicitudes")


class HorasExtra(Base):
    __tablename__ = "horas_extra"
    id                  = Column(Integer, primary_key=True)
    empleado_id         = Column(Integer, ForeignKey("usuarios.id"))
    fecha               = Column(Date, nullable=False)
    horas               = Column(Float, nullable=False)
    descripcion         = Column(Text, default="")
    tipo_compensacion   = Column(String, default="pendiente")
    empleado = relationship("Usuario", back_populates="horas")


class CompensacionHoras(Base):
    __tablename__ = "compensaciones"
    id                  = Column(Integer, primary_key=True)
    empleado_id         = Column(Integer, ForeignKey("usuarios.id"))
    horas_extra_id      = Column(Integer, ForeignKey("horas_extra.id"))
    fecha_compensacion  = Column(Date, nullable=False)
    horas_compensadas   = Column(Float, nullable=False)
    tipo                = Column(String)


class Notificacion(Base):
    __tablename__ = "notificaciones"
    id          = Column(Integer, primary_key=True)
    empleado_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha       = Column(Date, nullable=False, default=date.today)
    tipo        = Column(String, default="info")
    titulo      = Column(String, nullable=False)
    mensaje     = Column(Text, default="")
    leida       = Column(Boolean, default=False)
    empleado = relationship("Usuario", back_populates="notificaciones")


class FestivoPersonalizado(Base):
    __tablename__ = "festivos_personalizados"
    id          = Column(Integer, primary_key=True)
    fecha       = Column(Date, nullable=False, unique=True)
    descripcion = Column(String, default="Festivo local")
    activo      = Column(Boolean, default=True)


def init_db():
    Base.metadata.create_all(engine)