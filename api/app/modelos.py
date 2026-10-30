"""Modelo de datos. Multi-empresa: todo cuelga de una Organización (el cliente)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # UTC sin zona (igual en SQLite y PostgreSQL)


def nuevo_id() -> str:
    return uuid.uuid4().hex


class Organizacion(Base):
    __tablename__ = "organizaciones"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(200))
    creada: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    tiendas: Mapped[list[Tienda]] = relationship(back_populates="organizacion")


class Tienda(Base):
    __tablename__ = "tiendas"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    organizacion_id: Mapped[str] = mapped_column(ForeignKey("organizaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(300), default="")
    organizacion: Mapped[Organizacion] = relationship(back_populates="tiendas")
    camaras: Mapped[list[Camara]] = relationship(back_populates="tienda")


class Camara(Base):
    __tablename__ = "camaras"
    __table_args__ = (UniqueConstraint("tienda_id", "codigo"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    tienda_id: Mapped[str] = mapped_column(ForeignKey("tiendas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(100))  # el id que usa el equipo de la tienda (p. ej. «cam-perfumeria»)
    nombre: Mapped[str] = mapped_column(String(200))
    ubicacion: Mapped[str] = mapped_column(String(200), default="")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    en_linea: Mapped[bool] = mapped_column(Boolean, default=False)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    ultimo_latido: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tienda: Mapped[Tienda] = relationship(back_populates="camaras")


class Equipo(Base):
    """Mini PC de una tienda. Se autentica con un token (solo se guarda su hash)."""
    __tablename__ = "equipos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    tienda_id: Mapped[str] = mapped_column(ForeignKey("tiendas.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    ultimo_latido: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


ROLES = ("propietario", "encargado", "lectura")


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    organizacion_id: Mapped[str] = mapped_column(ForeignKey("organizaciones.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    hash_clave: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20), default="encargado")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


ESTADOS = ("nueva", "revisada", "descartada", "confirmada")


class Alerta(Base):
    __tablename__ = "alertas"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # = evento_id del equipo (idempotente)
    organizacion_id: Mapped[str] = mapped_column(ForeignKey("organizaciones.id"), index=True)
    camara_id: Mapped[str] = mapped_column(ForeignKey("camaras.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(50))
    titulo: Mapped[str] = mapped_column(String(200))
    puntuacion: Mapped[float] = mapped_column(Float)
    prioridad: Mapped[str] = mapped_column(String(10), index=True)
    inicio: Mapped[datetime] = mapped_column(DateTime, index=True)
    actualizada: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    pasos: Mapped[list] = mapped_column(JSON, default=list)
    clip: Mapped[str | None] = mapped_column(String(300), nullable=True)
    clip_borrado: Mapped[bool] = mapped_column(Boolean, default=False)
    simulacion: Mapped[bool] = mapped_column(Boolean, default=False)
    estado: Mapped[str] = mapped_column(String(20), default="nueva", index=True)
    nota: Mapped[str] = mapped_column(Text, default="")
    revisada_por: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    revisada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creada: Mapped[datetime] = mapped_column(DateTime, default=ahora, index=True)
    camara: Mapped[Camara] = relationship()


class Registro(Base):
    """Registro de accesos y acciones (quién vio qué clip, quién cambió qué)."""
    __tablename__ = "registro"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organizacion_id: Mapped[str] = mapped_column(String(32), index=True)
    usuario_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    usuario_email: Mapped[str] = mapped_column(String(200), default="")
    accion: Mapped[str] = mapped_column(String(50))
    objeto: Mapped[str] = mapped_column(String(100), default="")
    detalle: Mapped[str] = mapped_column(String(500), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    momento: Mapped[datetime] = mapped_column(DateTime, default=ahora, index=True)
