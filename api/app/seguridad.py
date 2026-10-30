"""Contraseñas (bcrypt), sesiones (JWT), tokens de equipo y permisos por rol."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import ajustes
from .db import obtener_db
from .modelos import Equipo, Registro, Usuario, ahora


def hash_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def comprobar_clave(clave: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode(), h.encode())
    except ValueError:
        return False


def crear_sesion(usuario: Usuario) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ajustes.minutos_sesion)
    return jwt.encode({"sub": usuario.id, "org": usuario.organizacion_id, "rol": usuario.rol, "exp": exp},
                      ajustes.secreto, algorithm="HS256")


def leer_sesion(token: str) -> dict:
    try:
        return jwt.decode(token, ajustes.secreto, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida o caducada")


def _bearer(request: Request) -> str:
    cab = request.headers.get("Authorization", "")
    if not cab.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta la autenticación")
    return cab[7:]


def usuario_actual(request: Request, db: Session = Depends(obtener_db)) -> Usuario:
    datos = leer_sesion(_bearer(request))
    u = db.get(Usuario, datos["sub"])
    if not u or not u.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido")
    return u


def requiere(*roles: str):
    def dep(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return u
    return dep


def nuevo_token_equipo() -> tuple[str, str]:
    token = "vgl_" + secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def equipo_actual(request: Request, db: Session = Depends(obtener_db)) -> Equipo:
    h = hashlib.sha256(_bearer(request).encode()).hexdigest()
    eq = db.query(Equipo).filter_by(token_hash=h).first()
    if not eq:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Equipo no reconocido")
    eq.ultimo_latido = ahora()
    return eq


def registrar(db: Session, request: Request | None, org: str, usuario: Usuario | None, accion: str,
              objeto: str = "", detalle: str = ""):
    db.add(Registro(organizacion_id=org, usuario_id=usuario.id if usuario else None,
                    usuario_email=usuario.email if usuario else "", accion=accion, objeto=objeto, detalle=detalle[:500],
                    ip=(request.client.host if request and request.client else "")))
