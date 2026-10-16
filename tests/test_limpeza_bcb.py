import json
from pathlib import Path

import pandas as pd
import pytest

from monitor.limpeza import COLUNAS_PADRAO
from monitor.limpeza.bcb import limpar_sgs

AMOSTRA = Path(__file__).parent / "fixtures" / "bcb_sgs_1_amostra.json"
ARGS = {"serie": "ptax_venda", "unidade": "R$/US$", "fonte": "Banco Central do Brasil - SGS"}


def test_converte_tipos_da_amostra_real() -> None:
    df = limpar_sgs(json.loads(AMOSTRA.read_text(encoding="utf-8")), **ARGS)
    assert list(df.columns) == COLUNAS_PADRAO
    assert df["data"].dtype == "datetime64[ns]"
    assert df["valor"].dtype == "float64"
    assert df.loc[0, "data"] == pd.Timestamp("2010-01-04")
    assert df.loc[0, "valor"] == pytest.approx(1.7240)
    assert df["valor"].iloc[-1] == pytest.approx(5.0441)
    assert (df["unidade"] == "R$/US$").all()


def test_data_e_dia_mes_ano_nao_mes_dia() -> None:
    df = limpar_sgs([{"data": "02/03/2020", "valor": "5.0"}], **ARGS)
    assert df.loc[0, "data"] == pd.Timestamp("2020-03-02")


def test_ordena_e_remove_datas_duplicadas() -> None:
    registros = [
        {"data": "05/01/2010", "valor": "1.7227"},
        {"data": "04/01/2010", "valor": "1.7240"},
        {"data": "05/01/2010", "valor": "1.7227"},
    ]
    df = limpar_sgs(registros, **ARGS)
    assert df["data"].tolist() == [pd.Timestamp("2010-01-04"), pd.Timestamp("2010-01-05")]


def test_lista_vazia_devolve_dataframe_tipado() -> None:
    df = limpar_sgs([], **ARGS)
    assert df.empty
    assert list(df.columns) == COLUNAS_PADRAO
    assert df["data"].dtype == "datetime64[ns]"
    assert df["valor"].dtype == "float64"


@pytest.mark.parametrize(
    "registro",
    [
        {"data": "31/02/2020", "valor": "5.0"},  # data inexistente
        {"data": "2020-01-02", "valor": "5.0"},  # formato errado
        {"data": "02/01/2020", "valor": "5,0"},  # vírgula decimal
        {"data": "02/01/2020", "valor": ""},
        {"data": "02/01/2020", "valor": "-1"},
    ],
)
def test_valores_invalidos_levantam_erro(registro: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        limpar_sgs([registro], **ARGS)


def test_falta_de_coluna_levanta_erro() -> None:
    with pytest.raises(ValueError, match="valor"):
        limpar_sgs([{"data": "02/01/2020"}], **ARGS)
