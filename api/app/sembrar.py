"""Crea una organización de prueba con su tienda, usuario propietario y token de equipo.

    python -m app.sembrar --email tu@correo.es --clave "una-clave-larga" [--org "Mi empresa"] [--tienda "Tienda 1"]
"""
from __future__ import annotations

import argparse

from .db import Base, Sesion, motor
from .modelos import Equipo, Organizacion, Tienda, Usuario
from .seguridad import hash_clave, nuevo_token_equipo


def sembrar(email: str, clave: str, org: str = "Mi comercio", tienda: str = "Tienda principal") -> dict:
    Base.metadata.create_all(motor)
    with Sesion() as db:
        if db.query(Usuario).filter_by(email=email.lower()).first():
            raise SystemExit(f"Ya existe el usuario {email}")
        o = Organizacion(nombre=org)
        db.add(o)
        db.flush()
        t = Tienda(organizacion_id=o.id, nombre=tienda)
        db.add(t)
        db.flush()
        db.add(Usuario(organizacion_id=o.id, email=email.lower(), nombre=email.split("@")[0], rol="propietario",
                       hash_clave=hash_clave(clave)))
        token, h = nuevo_token_equipo()
        db.add(Equipo(tienda_id=t.id, nombre="Equipo de pruebas", token_hash=h))
        db.commit()
        return {"organizacion": o.id, "tienda": t.id, "token_equipo": token}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    ap.add_argument("--org", default="Mi comercio")
    ap.add_argument("--tienda", default="Tienda principal")
    a = ap.parse_args()
    r = sembrar(a.email, a.clave, a.org, a.tienda)
    print(f"Listo. Usuario {a.email} (propietario).")
    print(f"Token del equipo de la tienda (guárdalo, no se vuelve a mostrar):\n{r['token_equipo']}")
