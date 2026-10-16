import json

import pandas as pd
import pytest

from monitor import config
from monitor.resultados import ARQUIVO_META, ARQUIVOS, FONTES_PERMITIDAS, validar_fontes


def test_validar_fontes_aceita_bcb_e_banco_mundial():
    validar_fontes({"x": pd.DataFrame({"fonte": [FONTES_PERMITIDAS], "serie": ["wb_soja"]})})


@pytest.mark.parametrize("texto", ["cepea_soja_paranagua", "CONAB preços por UF", "ESALQ/B3"])
def test_validar_fontes_recusa_cepea_e_conab_em_valores(texto):
    with pytest.raises(ValueError, match="não redistribuível"):
        validar_fontes({"x": pd.DataFrame({"serie": [texto]})})


def test_validar_fontes_recusa_nome_de_coluna():
    with pytest.raises(ValueError, match="não redistribuível"):
        validar_fontes({"x": pd.DataFrame({"cepea": [1.0]})})


def test_resultados_versionados_so_de_fontes_permitidas():
    """Os arquivos que vão para o git citam só BCB/Banco Mundial (se já foram gerados)."""
    arquivos = [config.DIR_PROCESSED / a for a in ARQUIVOS.values()]
    if not all(a.exists() for a in arquivos):
        pytest.skip("resultados ainda não gerados (python -m monitor.resultados)")
    tabelas = {a.stem: pd.read_parquet(a) for a in arquivos}
    validar_fontes(tabelas)
    assert all((t["fonte"] == FONTES_PERMITIDAS).all() for t in tabelas.values())
    meta = json.loads((config.DIR_PROCESSED / ARQUIVO_META).read_text(encoding="utf-8"))
    assert meta["fontes"] == FONTES_PERMITIDAS
