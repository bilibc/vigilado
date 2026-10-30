"""Tests de la API: sesión, recepción de eventos del equipo, tiempo real, permisos, registro y retención."""
import json
from datetime import timedelta

from fastapi.testclient import TestClient

from app.db import Sesion
from app.modelos import Alerta, ahora
from app.principal import app, purgar_clips
from app.sembrar import sembrar

S = sembrar("duena@tienda.es", "clave-muy-segura-1", "Perfumería Centro", "Tienda Centro")
OTRA = sembrar("otro@ajena.es", "clave-muy-segura-2", "Otra empresa", "Tienda ajena")


def cliente():
    return TestClient(app)


def entrar(c, email="duena@tienda.es", clave="clave-muy-segura-1"):
    r = c.post("/api/v1/sesion", json={"email": email, "clave": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()["token"]


def evento(eid="ev1", prioridad="media", **extra):
    return {"evento_id": eid, "camara_id": "cam-perfumeria", "track_id": 3, "tipo": "ocultacion_bolsillo",
            "titulo": "Gesto compatible con ocultación en bolsillo o cintura", "puntuacion": 0.65, "prioridad": prioridad,
            "inicio": "2026-10-30T10:00:00+00:00", "actualizado": "2026-10-30T10:00:05+00:00",
            "pasos": [{"t": 0, "tipo": "coge", "texto": "Coge en «Perfumes» (mano derecha)", "datos": {}},
                      {"t": 1.2, "tipo": "ocultacion", "texto": "Mano derecha a bolsillo o cintura durante 0.8 s", "datos": {}}],
            **extra}


def enviar(c, datos, token=S["token_equipo"], clip=b"\x00\x00\x00\x18ftypmp42" + b"0" * 2000):
    files = {"clip": ("x.mp4", clip, "video/mp4")} if clip else None
    return c.post("/api/v1/edge/eventos", data={"datos": json.dumps(datos)}, files=files,
                  headers={"Authorization": f"Bearer {token}"})


def test_login_incorrecto():
    with cliente() as c:
        assert c.post("/api/v1/sesion", json={"email": "duena@tienda.es", "clave": "mal"}).status_code == 401


def test_equipo_sin_token_valido_rechazado():
    with cliente() as c:
        assert enviar(c, evento("x"), token="vgl_falso").status_code == 401


def test_flujo_completo_alerta_tiempo_real_revision_y_clip():
    with cliente() as c:
        cab, token = entrar(c)
        with c.websocket_connect("/api/v1/ws") as ws:
            ws.send_text(json.dumps({"token": token}))
            import time; time.sleep(0.2)
            r = enviar(c, evento("ev-flujo"))
            assert r.status_code == 200, r.text
            msg = json.loads(ws.receive_text())
            assert msg["tipo"] == "alerta" and msg["nueva"] and msg["alerta"]["id"] == "ev-flujo"
        # la cámara se ha dado de alta sola
        assert any(x["codigo"] == "cam-perfumeria" for x in c.get("/api/v1/camaras", headers=cab).json())
        # actualización del mismo evento (sale sin pasar por caja): no duplica
        assert enviar(c, evento("ev-flujo", prioridad="alta"), clip=None).status_code == 200
        lista = c.get("/api/v1/alertas", headers=cab).json()
        assert [a["prioridad"] for a in lista if a["id"] == "ev-flujo"] == ["alta"]
        # ver clip: enlace firmado, de un solo clip, y queda registrado
        url = c.get("/api/v1/alertas/ev-flujo/enlace-clip", headers=cab).json()["url"]
        assert "token" not in url and c.get(url).status_code == 200
        assert c.get(url.replace("ev-flujo", "ev-otro")).status_code in (403, 404)
        assert c.get("/api/v1/alertas/ev-flujo/clip?firma=" + token).status_code == 403  # la sesión no vale como firma
        r = c.patch("/api/v1/alertas/ev-flujo", json={"estado": "descartada", "nota": "Era su móvil"}, headers=cab)
        assert r.json()["estado"] == "descartada"
        acciones = [x["accion"] for x in c.get("/api/v1/registro", headers=cab).json()]
        assert "ver_clip" in acciones and "cambiar_alerta" in acciones and "inicio_sesion" in acciones
        est = c.get("/api/v1/estadisticas", headers=cab).json()
        assert est["por_estado"].get("descartada", 0) >= 1 and est["tasa_descartadas"] is not None


def test_aislamiento_entre_empresas():
    with cliente() as c:
        assert enviar(c, evento("ev-privado")).status_code == 200
        cab_otro, tok_otro = entrar(c, "otro@ajena.es", "clave-muy-segura-2")
        assert c.get("/api/v1/alertas/ev-privado", headers=cab_otro).status_code == 404
        assert c.get("/api/v1/alertas/ev-privado/enlace-clip", headers=cab_otro).status_code == 404
        assert all(a["id"] != "ev-privado" for a in c.get("/api/v1/alertas", headers=cab_otro).json())


def test_roles():
    with cliente() as c:
        cab, _ = entrar(c)
        r = c.post("/api/v1/usuarios", json={"email": "lectura@tienda.es", "nombre": "Solo ver", "clave": "otra-clave-larga",
                                              "rol": "lectura"}, headers=cab)
        assert r.status_code == 201
        assert enviar(c, evento("ev-roles")).status_code == 200
        cab_l, _ = entrar(c, "lectura@tienda.es", "otra-clave-larga")
        assert c.get("/api/v1/alertas/ev-roles", headers=cab_l).status_code == 200
        assert c.patch("/api/v1/alertas/ev-roles", json={"estado": "confirmada"}, headers=cab_l).status_code == 403
        assert c.get("/api/v1/registro", headers=cab_l).status_code == 403
        assert c.patch("/api/v1/alertas/ev-roles", json={"estado": "inventado"}, headers=cab).status_code == 422


def test_retencion_borra_clips_viejos_pero_conserva_incidentes():
    with cliente() as c:
        assert enviar(c, evento("ev-viejo")).status_code == 200
        assert enviar(c, evento("ev-confirmado")).status_code == 200
        cab, _ = entrar(c)
        c.patch("/api/v1/alertas/ev-confirmado", json={"estado": "confirmada"}, headers=cab)
    with Sesion() as db:
        for i in ("ev-viejo", "ev-confirmado"):
            db.get(Alerta, i).creada = ahora() - timedelta(days=40)
        db.commit()
        purgar_clips(db)
        assert db.get(Alerta, "ev-viejo").clip_borrado is True
        assert db.get(Alerta, "ev-confirmado").clip_borrado is False


def test_latido_marca_camaras_en_linea():
    with cliente() as c:
        r = c.post("/api/v1/edge/latido", json={"camaras": [{"id": "cam-caja", "nombre": "Caja", "en_linea": True, "fps": 9.8}]},
                   headers={"Authorization": f"Bearer {S['token_equipo']}"})
        assert r.status_code == 200
        cab, _ = entrar(c)
        cam = next(x for x in c.get("/api/v1/camaras", headers=cab).json() if x["codigo"] == "cam-caja")
        assert cam["en_linea"] and cam["fps"] == 9.8
