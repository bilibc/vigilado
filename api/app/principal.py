"""API de Vigilado."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .config import ajustes
from .db import Base, Sesion, motor, obtener_db
from .modelos import ESTADOS, ROLES, Alerta, Camara, Equipo, Registro, Tienda, Usuario, ahora
from .seguridad import (comprobar_clave, crear_sesion, equipo_actual, hash_clave, leer_sesion, nuevo_token_equipo,
                        registrar, requiere, usuario_actual)
from .tiempo_real import difusor

log = logging.getLogger("vigilado.api")
PUEDE_REVISAR = ("propietario", "encargado")


def purgar_clips(db: Session) -> int:
    """Borra los clips más antiguos que la retención. Se conservan los de incidentes confirmados (acreditan hechos)."""
    limite = ahora() - timedelta(days=ajustes.retencion_dias)
    n = 0
    for a in db.query(Alerta).filter(Alerta.creada < limite, Alerta.clip_borrado.is_(False), Alerta.estado != "confirmada"):
        if a.clip:
            Path(a.clip).unlink(missing_ok=True)
        a.clip, a.clip_borrado = None, True
        registrar(db, None, a.organizacion_id, None, "clip_caducado", a.id, f"Retención de {ajustes.retencion_dias} días")
        n += 1
    db.commit()
    return n


async def _purga_periodica():
    while True:
        with Sesion() as db:
            n = purgar_clips(db)
            if n:
                log.info("Clips caducados borrados: %d", n)
        await asyncio.sleep(3600)


@asynccontextmanager
async def ciclo(app):
    Base.metadata.create_all(motor)
    tarea = asyncio.create_task(_purga_periodica())
    yield
    tarea.cancel()


app = FastAPI(title="Vigilado API", version="0.1.0", lifespan=ciclo)
app.add_middleware(CORSMiddleware, allow_origins=ajustes.origenes_cors, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- esquemas
class EntradaLogin(BaseModel):
    email: str
    clave: str


class CambioAlerta(BaseModel):
    estado: str | None = None
    nota: str | None = Field(default=None, max_length=2000)


class NuevaTienda(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    direccion: str = ""


class NuevaCamara(BaseModel):
    codigo: str = Field(min_length=1, max_length=100)
    nombre: str = Field(min_length=1, max_length=200)
    ubicacion: str = ""


class CambioCamara(BaseModel):
    nombre: str | None = None
    ubicacion: str | None = None
    activa: bool | None = None


class NuevoUsuario(BaseModel):
    email: EmailStr
    nombre: str
    clave: str = Field(min_length=10)
    rol: str = "encargado"


def alerta_dict(a: Alerta) -> dict:
    c = a.camara
    return {"id": a.id, "tipo": a.tipo, "titulo": a.titulo, "puntuacion": a.puntuacion, "prioridad": a.prioridad,
            "inicio": a.inicio.isoformat() + "Z", "actualizada": a.actualizada.isoformat() + "Z", "pasos": a.pasos,
            "estado": a.estado, "nota": a.nota, "simulacion": a.simulacion,
            "tiene_clip": bool(a.clip) and not a.clip_borrado, "clip_borrado": a.clip_borrado,
            "revisada_en": a.revisada_en.isoformat() + "Z" if a.revisada_en else None,
            "camara": {"id": c.id, "nombre": c.nombre, "ubicacion": c.ubicacion, "tienda": c.tienda.nombre,
                       "tienda_id": c.tienda_id}}


def camara_dict(c: Camara) -> dict:
    vivo = c.ultimo_latido and (ahora() - c.ultimo_latido) < timedelta(seconds=60)
    return {"id": c.id, "codigo": c.codigo, "nombre": c.nombre, "ubicacion": c.ubicacion, "activa": c.activa,
            "en_linea": bool(vivo and c.en_linea), "fps": c.fps, "tienda_id": c.tienda_id, "tienda": c.tienda.nombre,
            "ultimo_latido": c.ultimo_latido.isoformat() + "Z" if c.ultimo_latido else None}


def _alerta_de(db: Session, u: Usuario, alerta_id: str) -> Alerta:
    a = db.get(Alerta, alerta_id)
    if not a or a.organizacion_id != u.organizacion_id:
        raise HTTPException(404, "Alerta no encontrada")
    return a


# ---------------------------------------------------------------- sesión
@app.post("/api/v1/sesion")
def iniciar_sesion(e: EntradaLogin, request: Request, db: Session = Depends(obtener_db)):
    u = db.query(Usuario).filter_by(email=e.email.lower().strip()).first()
    if not u or not u.activo or not comprobar_clave(e.clave, u.hash_clave):
        raise HTTPException(401, "Email o contraseña incorrectos")
    registrar(db, request, u.organizacion_id, u, "inicio_sesion")
    db.commit()
    return {"token": crear_sesion(u), "usuario": {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol}}


@app.get("/api/v1/yo")
def yo(u: Usuario = Depends(usuario_actual)):
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol, "organizacion_id": u.organizacion_id}


# ---------------------------------------------------------------- alertas
@app.get("/api/v1/alertas")
def listar_alertas(estado: str | None = None, prioridad: str | None = None, tienda_id: str | None = None,
                   limite: int = Query(100, le=500), u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    q = db.query(Alerta).filter(Alerta.organizacion_id == u.organizacion_id)
    if estado:
        q = q.filter(Alerta.estado == estado)
    if prioridad:
        q = q.filter(Alerta.prioridad == prioridad)
    if tienda_id:
        q = q.join(Camara).filter(Camara.tienda_id == tienda_id)
    return [alerta_dict(a) for a in q.order_by(Alerta.inicio.desc()).limit(limite)]


@app.get("/api/v1/alertas/{alerta_id}")
def ver_alerta(alerta_id: str, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    return alerta_dict(_alerta_de(db, u, alerta_id))


@app.patch("/api/v1/alertas/{alerta_id}")
async def cambiar_alerta(alerta_id: str, c: CambioAlerta, request: Request,
                         u: Usuario = Depends(requiere(*PUEDE_REVISAR)), db: Session = Depends(obtener_db)):
    a = _alerta_de(db, u, alerta_id)
    if c.estado:
        if c.estado not in ESTADOS:
            raise HTTPException(422, f"Estado no válido. Usa: {', '.join(ESTADOS)}")
        a.estado, a.revisada_por, a.revisada_en = c.estado, u.id, ahora()
    if c.nota is not None:
        a.nota = c.nota
    registrar(db, request, u.organizacion_id, u, "cambiar_alerta", a.id, f"estado={a.estado}")
    db.commit()
    datos = alerta_dict(a)
    await difusor.enviar(u.organizacion_id, {"tipo": "alerta", "alerta": datos})
    return datos


@app.get("/api/v1/alertas/{alerta_id}/enlace-clip")
def enlace_clip(alerta_id: str, request: Request, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    """Enlace firmado para el <video>: solo sirve para ESE clip y caduca en 5 minutos (la sesión nunca va en la URL).
    Pedir el enlace es «ver el clip» y queda en el registro de accesos."""
    a = _alerta_de(db, u, alerta_id)
    if not a.clip or a.clip_borrado:
        raise HTTPException(404, "El clip ya no está disponible")
    firma = jwt.encode({"sub": u.id, "alerta": a.id, "tipo": "clip", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                       ajustes.secreto, algorithm="HS256")
    registrar(db, request, u.organizacion_id, u, "ver_clip", a.id)
    db.commit()
    return {"url": f"/api/v1/alertas/{a.id}/clip?firma={firma}"}


@app.get("/api/v1/alertas/{alerta_id}/clip")
def ver_clip(alerta_id: str, firma: str, db: Session = Depends(obtener_db)):
    try:
        d = jwt.decode(firma, ajustes.secreto, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Enlace caducado o no válido")
    if d.get("tipo") != "clip" or d.get("alerta") != alerta_id:
        raise HTTPException(403, "Este enlace no es para este clip")
    u = db.get(Usuario, d["sub"])
    if not u or not u.activo:
        raise HTTPException(401, "Usuario no válido")
    a = _alerta_de(db, u, alerta_id)
    if not a.clip or a.clip_borrado or not Path(a.clip).exists():
        raise HTTPException(404, "El clip ya no está disponible")
    return FileResponse(a.clip, media_type="video/mp4")


# ---------------------------------------------------------------- tiendas y cámaras
@app.get("/api/v1/tiendas")
def listar_tiendas(u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    ts = db.query(Tienda).filter_by(organizacion_id=u.organizacion_id).order_by(Tienda.nombre).all()
    return [{"id": t.id, "nombre": t.nombre, "direccion": t.direccion, "camaras": len(t.camaras)} for t in ts]


@app.post("/api/v1/tiendas", status_code=201)
def crear_tienda(t: NuevaTienda, request: Request, u: Usuario = Depends(requiere("propietario")), db: Session = Depends(obtener_db)):
    tienda = Tienda(organizacion_id=u.organizacion_id, nombre=t.nombre, direccion=t.direccion)
    db.add(tienda)
    registrar(db, request, u.organizacion_id, u, "crear_tienda", detalle=t.nombre)
    db.commit()
    return {"id": tienda.id, "nombre": tienda.nombre, "direccion": tienda.direccion, "camaras": 0}


def _tienda_de(db: Session, u: Usuario, tienda_id: str) -> Tienda:
    t = db.get(Tienda, tienda_id)
    if not t or t.organizacion_id != u.organizacion_id:
        raise HTTPException(404, "Tienda no encontrada")
    return t


@app.post("/api/v1/tiendas/{tienda_id}/equipos", status_code=201)
def crear_equipo(tienda_id: str, request: Request, nombre: str = "Equipo de la tienda",
                 u: Usuario = Depends(requiere("propietario")), db: Session = Depends(obtener_db)):
    """Da de alta el mini PC de una tienda. El token se muestra UNA vez."""
    _tienda_de(db, u, tienda_id)
    token, h = nuevo_token_equipo()
    db.add(Equipo(tienda_id=tienda_id, nombre=nombre, token_hash=h))
    registrar(db, request, u.organizacion_id, u, "crear_equipo", tienda_id, nombre)
    db.commit()
    return {"token": token, "aviso": "Guárdalo ahora: no se vuelve a mostrar."}


@app.get("/api/v1/camaras")
def listar_camaras(u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    cs = db.query(Camara).join(Tienda).filter(Tienda.organizacion_id == u.organizacion_id).order_by(Tienda.nombre, Camara.nombre)
    return [camara_dict(c) for c in cs]


@app.post("/api/v1/tiendas/{tienda_id}/camaras", status_code=201)
def crear_camara(tienda_id: str, c: NuevaCamara, request: Request, u: Usuario = Depends(requiere("propietario")),
                 db: Session = Depends(obtener_db)):
    _tienda_de(db, u, tienda_id)
    cam = Camara(tienda_id=tienda_id, codigo=c.codigo, nombre=c.nombre, ubicacion=c.ubicacion)
    db.add(cam)
    registrar(db, request, u.organizacion_id, u, "crear_camara", detalle=c.nombre)
    db.commit()
    return camara_dict(cam)


@app.patch("/api/v1/camaras/{camara_id}")
def cambiar_camara(camara_id: str, c: CambioCamara, request: Request, u: Usuario = Depends(requiere("propietario")),
                   db: Session = Depends(obtener_db)):
    cam = db.get(Camara, camara_id)
    if not cam or cam.tienda.organizacion_id != u.organizacion_id:
        raise HTTPException(404, "Cámara no encontrada")
    for k, v in c.model_dump(exclude_none=True).items():
        setattr(cam, k, v)
    registrar(db, request, u.organizacion_id, u, "cambiar_camara", cam.id)
    db.commit()
    return camara_dict(cam)


# ---------------------------------------------------------------- usuarios y registro
@app.get("/api/v1/usuarios")
def listar_usuarios(u: Usuario = Depends(requiere("propietario")), db: Session = Depends(obtener_db)):
    return [{"id": x.id, "email": x.email, "nombre": x.nombre, "rol": x.rol, "activo": x.activo}
            for x in db.query(Usuario).filter_by(organizacion_id=u.organizacion_id).order_by(Usuario.nombre)]


@app.post("/api/v1/usuarios", status_code=201)
def crear_usuario(n: NuevoUsuario, request: Request, u: Usuario = Depends(requiere("propietario")), db: Session = Depends(obtener_db)):
    if n.rol not in ROLES:
        raise HTTPException(422, f"Rol no válido. Usa: {', '.join(ROLES)}")
    if db.query(Usuario).filter_by(email=n.email.lower()).first():
        raise HTTPException(409, "Ya existe un usuario con ese email")
    nuevo = Usuario(organizacion_id=u.organizacion_id, email=n.email.lower(), nombre=n.nombre, rol=n.rol,
                    hash_clave=hash_clave(n.clave))
    db.add(nuevo)
    registrar(db, request, u.organizacion_id, u, "crear_usuario", detalle=f"{n.email} ({n.rol})")
    db.commit()
    return {"id": nuevo.id, "email": nuevo.email, "nombre": nuevo.nombre, "rol": nuevo.rol, "activo": True}


@app.get("/api/v1/registro")
def ver_registro(limite: int = Query(200, le=1000), u: Usuario = Depends(requiere("propietario")), db: Session = Depends(obtener_db)):
    filas = db.query(Registro).filter_by(organizacion_id=u.organizacion_id).order_by(Registro.momento.desc()).limit(limite)
    return [{"momento": r.momento.isoformat() + "Z", "usuario": r.usuario_email or "sistema", "accion": r.accion,
             "objeto": r.objeto, "detalle": r.detalle, "ip": r.ip} for r in filas]


# ---------------------------------------------------------------- estadísticas
@app.get("/api/v1/estadisticas")
def estadisticas(dias: int = Query(14, le=90), u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    desde = ahora() - timedelta(days=dias)
    alertas = db.query(Alerta).filter(Alerta.organizacion_id == u.organizacion_id, Alerta.inicio >= desde).all()
    revisadas = [a for a in alertas if a.estado in ("descartada", "confirmada")]
    por_dia = Counter(a.inicio.date().isoformat() for a in alertas)
    hoy = ahora().date()
    serie = [{"dia": (hoy - timedelta(days=i)).isoformat(), "alertas": por_dia.get((hoy - timedelta(days=i)).isoformat(), 0)}
             for i in range(dias - 1, -1, -1)]
    return {
        "total": len(alertas),
        "por_estado": dict(Counter(a.estado for a in alertas)),
        "por_prioridad": dict(Counter(a.prioridad for a in alertas)),
        "por_camara": [{"camara": k, "alertas": v} for k, v in Counter(a.camara.nombre for a in alertas).most_common()],
        "por_dia": serie,
        # La métrica que más importa al cliente: de las alertas revisadas, cuántas eran falsas
        "tasa_descartadas": round(sum(a.estado == "descartada" for a in revisadas) / len(revisadas), 3) if revisadas else None,
        "pendientes": sum(a.estado == "nueva" for a in alertas),
    }


# ---------------------------------------------------------------- equipos de tienda
@app.post("/api/v1/edge/eventos")
async def recibir_evento(datos: str = Form(...), clip: UploadFile | None = File(None), eq: Equipo = Depends(equipo_actual),
                         db: Session = Depends(obtener_db)):
    d = json.loads(datos)
    tienda = db.get(Tienda, eq.tienda_id)
    cam = db.query(Camara).filter_by(tienda_id=tienda.id, codigo=d["camara_id"]).first()
    if not cam:  # primera alerta de una cámara nueva: se da de alta sola
        cam = Camara(tienda_id=tienda.id, codigo=d["camara_id"], nombre=d["camara_id"])
        db.add(cam)
        db.flush()
    a = db.get(Alerta, d["evento_id"])
    nueva = a is None
    if nueva:
        a = Alerta(id=d["evento_id"], organizacion_id=tienda.organizacion_id, camara_id=cam.id,
                   inicio=datetime.fromisoformat(d["inicio"].replace("Z", "+00:00")).replace(tzinfo=None))
        db.add(a)
    a.tipo, a.titulo, a.puntuacion, a.prioridad = d["tipo"], d.get("titulo", d["tipo"]), d["puntuacion"], d["prioridad"]
    a.pasos, a.simulacion, a.actualizada = d.get("pasos", []), bool(d.get("simulacion")), ahora()
    if clip is not None:
        carpeta = ajustes.carpeta_clips / tienda.organizacion_id
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{a.id}.mp4"
        ruta.write_bytes(await clip.read())
        a.clip, a.clip_borrado = str(ruta), False
    db.commit()
    db.refresh(a)
    await difusor.enviar(tienda.organizacion_id, {"tipo": "alerta", "nueva": nueva, "alerta": alerta_dict(a)})
    return {"ok": True, "id": a.id}


class Latido(BaseModel):
    camaras: list[dict] = []


@app.post("/api/v1/edge/latido")
async def latido(l: Latido, eq: Equipo = Depends(equipo_actual), db: Session = Depends(obtener_db)):
    tienda = db.get(Tienda, eq.tienda_id)
    for c in l.camaras:
        cam = db.query(Camara).filter_by(tienda_id=tienda.id, codigo=c.get("id")).first()
        if not cam:
            cam = Camara(tienda_id=tienda.id, codigo=c.get("id"), nombre=c.get("nombre") or c.get("id"))
            db.add(cam)
        elif cam.nombre == cam.codigo and c.get("nombre"):  # dada de alta sola: toma el nombre que da el equipo
            cam.nombre = c["nombre"]
        cam.en_linea, cam.fps, cam.ultimo_latido = bool(c.get("en_linea")), float(c.get("fps") or 0), ahora()
    db.commit()
    await difusor.enviar(tienda.organizacion_id, {"tipo": "camaras"})
    return {"ok": True}


# ---------------------------------------------------------------- tiempo real
@app.websocket("/api/v1/ws")
async def ws(websocket: WebSocket):
    """El panel manda {"token": ...} como primer mensaje (la sesión no va en la URL, que acaba en los logs)."""
    await websocket.accept()
    try:
        primero = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=10))
        sesion = leer_sesion(primero.get("token", ""))
    except (asyncio.TimeoutError, ValueError, HTTPException, WebSocketDisconnect):
        await websocket.close(code=4401)
        return
    org = sesion["org"]
    difusor.registrar(org, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        difusor.desconectar(org, websocket)


@app.get("/api/v1/salud")
def salud():
    return {"ok": True, "version": app.version, "retencion_dias": ajustes.retencion_dias}


if ajustes.carpeta_panel and Path(ajustes.carpeta_panel).exists():
    _panel = Path(ajustes.carpeta_panel).resolve()
    app.mount("/assets", StaticFiles(directory=_panel / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def panel(ruta: str):
        """Sirve el panel. Cualquier ruta que no sea un archivo (p. ej. /alertas/123) devuelve index.html."""
        f = (_panel / ruta).resolve()
        if ruta and f.is_file() and _panel in f.parents:
            return FileResponse(f)
        return FileResponse(_panel / "index.html")
