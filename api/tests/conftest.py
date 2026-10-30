import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["VIGILADO_CLIPS"] = f"{_tmp}/clips"
os.environ["VIGILADO_SECRETO"] = "secreto-de-pruebas-con-longitud-suficiente-0123456789"
