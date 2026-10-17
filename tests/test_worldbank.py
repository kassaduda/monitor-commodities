from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from monitor import config
from monitor.coleta.worldbank import ErroPinkSheet, SeriePinkSheet, ler_pink_sheet
from monitor.limpeza import COLUNAS_PADRAO
from monitor.limpeza.worldbank import limpar_pink_sheet, periodo_para_data
from pink_sheet_util import criar_planilha

# Amostra real (World Bank Pink Sheet, CC BY 4.0, edição de 02/10/2026): 10 meses, colunas A até Maize.
AMOSTRA = Path(__file__).parent / "fixtures" / "pink_sheet_amostra.xlsx"
COLUNAS = list(config.WB_SERIES.values())


# --- leitura da amostra real -------------------------------------------------


def test_le_amostra_real() -> None:
    ps = ler_pink_sheet(AMOSTRA, COLUNAS)
    assert ps.atualizado_em == date(2026, 10, 2)
    soja, milho = ps.series["Soybeans"], ps.series["Maize"]
    assert soja.unidade == milho.unidade == "($/mt)"
    assert soja.registros[0] == ("1960M01", 94)
    assert ("2010M01", 436) in soja.registros
    assert soja.registros[-1] == ("2026M09", 524)
    assert milho.registros[-1] == ("2026M09", 239.6)
    assert len(soja.registros) == len(milho.registros) == 10


def test_limpa_amostra_real() -> None:
    ps = ler_pink_sheet(AMOSTRA, COLUNAS)
    df = limpar_pink_sheet(ps.series["Soybeans"], "wb_soja")
    assert list(df.columns) == COLUNAS_PADRAO
    assert df["data"].dtype == "datetime64[ns]" and df["valor"].dtype == "float64"
    assert df["data"].iloc[-1] == pd.Timestamp("2026-09-01")
    assert df["valor"].iloc[-1] == pytest.approx(524.0)
    assert (df["unidade"] == "US$/t").all()
    assert (df["fonte"] == config.FONTE_WB).all()
    # as datas das quebras de definição da soja estão presentes na amostra
    for quebra, _ in config.QUEBRAS_DEFINICAO["wb_soja"]:
        assert pd.Timestamp(quebra) in set(df["data"])


# --- leitura: layout ---------------------------------------------------------


def test_le_planilha_sintetica_e_ignora_linhas_que_nao_sao_meses(tmp_path) -> None:
    caminho = criar_planilha(tmp_path / "ps.xlsx", [
        ["2026M08", 63.1, 482, 224],
        [None, None, None, None],
        ["2026M09", 62.0, 524, 239.6],
        ["Nota: dados preliminares", None, None, None],
    ])
    ps = ler_pink_sheet(caminho, COLUNAS)
    assert ps.series["Soybeans"].registros == [("2026M08", 482), ("2026M09", 524)]


def test_sem_data_de_atualizacao_devolve_none(tmp_path) -> None:
    caminho = criar_planilha(tmp_path / "ps.xlsx", [["2026M09", 62.0, 524, 239.6]], atualizado="")
    assert ler_pink_sheet(caminho, COLUNAS).atualizado_em is None


def test_aba_ausente_levanta_erro(tmp_path) -> None:
    caminho = criar_planilha(tmp_path / "ps.xlsx", [["2026M09", 62.0, 524, 239.6]], aba="Outra")
    with pytest.raises(ErroPinkSheet, match="Monthly Prices"):
        ler_pink_sheet(caminho, COLUNAS)


def test_coluna_ausente_levanta_erro(tmp_path) -> None:
    caminho = criar_planilha(tmp_path / "ps.xlsx", [["2026M09", 62.0, 524, 239.6]],
                             cabecalho=[None, "Crude oil, WTI", "Soybeans", "Corn"])
    with pytest.raises(ErroPinkSheet, match="Cabeçalho"):
        ler_pink_sheet(caminho, COLUNAS)


def test_coluna_repetida_levanta_erro(tmp_path) -> None:
    caminho = criar_planilha(tmp_path / "ps.xlsx", [["2026M09", 524, 524, 239.6, 347]],
                             cabecalho=[None, "Soybeans", "Soybeans", "Maize", "Wheat, US HRW"])
    with pytest.raises(ErroPinkSheet, match="repetidas"):
        ler_pink_sheet(caminho, COLUNAS)


# --- limpeza -------------------------------------------------------------------


def _serie(registros: list[tuple[str, object]], unidade: str = "($/mt)") -> SeriePinkSheet:
    return SeriePinkSheet("Soybeans", unidade, registros)


def test_periodo_vira_primeiro_dia_do_mes() -> None:
    assert periodo_para_data("2025M01") == pd.Timestamp("2025-01-01")
    assert periodo_para_data("2026M12") == pd.Timestamp("2026-12-01")


@pytest.mark.parametrize("ausente", [None, "…", "...", "..", " "])
def test_marcadores_de_ausencia_sao_omitidos(ausente: object) -> None:
    df = limpar_pink_sheet(_serie([("2026M08", ausente), ("2026M09", 524)]), "wb_soja")
    assert df["data"].tolist() == [pd.Timestamp("2026-09-01")]


def test_numero_em_texto_e_aceito() -> None:
    df = limpar_pink_sheet(_serie([("2026M09", "524.5")]), "wb_soja")
    assert df["valor"].tolist() == [524.5]


@pytest.mark.parametrize("invalido", ["#VALUE!", "n/a", True, -1, 0])
def test_valores_invalidos_levantam_erro(invalido: object) -> None:
    with pytest.raises(ValueError):
        limpar_pink_sheet(_serie([("2026M09", invalido)]), "wb_soja")


def test_mudanca_de_unidade_levanta_erro() -> None:
    with pytest.raises(ValueError, match="unidade"):
        limpar_pink_sheet(_serie([("2026M09", 524)], unidade="($/bu)"), "wb_soja")


def test_periodo_repetido_levanta_erro() -> None:
    with pytest.raises(ValueError, match="repetidos"):
        limpar_pink_sheet(_serie([("2026M09", 524), ("2026M09", 525)]), "wb_soja")


def test_serie_toda_ausente_devolve_vazio_tipado() -> None:
    df = limpar_pink_sheet(_serie([("2026M09", "…")]), "wb_soja")
    assert df.empty and list(df.columns) == COLUNAS_PADRAO
    assert df["data"].dtype == "datetime64[ns]"
