"""O dashboard não pode puxar scipy nem statsmodels (deploy leve, ver requirements.txt)."""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

CODIGO = """
import sys
for pesado in ("scipy", "statsmodels"):
    sys.modules[pesado] = None  # qualquer import vira ImportError
sys.path[:0] = [{app!r}, {src!r}]
import carga, graficos, ui
from monitor import config
from monitor.analise.base import montar_base
carga.base_mensal.__wrapped__()  # lê os Parquet e converte, sem cache do Streamlit
print("ok")
"""


def test_app_importa_e_monta_a_base_sem_scipy_nem_statsmodels():
    codigo = CODIGO.format(app=str(RAIZ / "app"), src=str(RAIZ / "src"))
    r = subprocess.run([sys.executable, "-I", "-c", codigo], capture_output=True, text=True, cwd=RAIZ)
    assert r.returncode == 0, r.stderr[-800:]
    assert "ok" in r.stdout


def test_requirements_sem_pacotes_pesados():
    pacotes = {l.split("==")[0].lower() for l in (RAIZ / "requirements.txt").read_text().splitlines()
               if l.strip() and not l.startswith("#")}
    assert pacotes == {"streamlit", "plotly", "pandas", "pyarrow", "numpy"}
    assert all("==" in l for l in (RAIZ / "requirements.txt").read_text().splitlines()
               if l.strip() and not l.startswith("#"))
