import pandas as pd
import pytest

from monitor.armazenamento import caminho_parquet, ler_serie, mesclar, salvar_serie
from monitor.limpeza import COLUNAS_PADRAO, dataframe_vazio


def _df(datas: list[str], valores: list[float], serie: str = "ptax_venda") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data": pd.to_datetime(datas),
            "serie": serie,
            "valor": [float(v) for v in valores],
            "unidade": "R$/US$",
            "fonte": "Banco Central do Brasil - SGS",
        }
    )[COLUNAS_PADRAO]


def test_mesclar_nao_duplica_datas_e_vale_o_dado_novo() -> None:
    existente = _df(["2026-10-08", "2026-10-09"], [5.01, 4.99])
    novo = _df(["2026-10-09", "2026-10-13"], [4.98, 5.00])
    m = mesclar(existente, novo)
    assert m["data"].tolist() == list(pd.to_datetime(["2026-10-08", "2026-10-09", "2026-10-13"]))
    assert m["valor"].tolist() == [5.01, 4.98, 5.00]
    assert m["data"].is_unique


def test_mesclar_ordena_por_data() -> None:
    m = mesclar(_df(["2026-10-13"], [5.0]), _df(["2026-10-01"], [4.9]))
    assert m["data"].is_monotonic_increasing


def test_mesclar_com_lados_vazios() -> None:
    df = _df(["2026-10-13"], [5.0])
    assert mesclar(dataframe_vazio(), df).equals(df)
    assert mesclar(df, dataframe_vazio()).equals(df)
    assert mesclar(dataframe_vazio(), dataframe_vazio()).empty


def test_mesclar_rejeita_series_diferentes() -> None:
    with pytest.raises(ValueError, match="séries diferentes"):
        mesclar(_df(["2026-10-13"], [5.0]), _df(["2026-10-14"], [150.0], serie="soja"))


def test_mesclar_rejeita_colunas_fora_do_padrao() -> None:
    with pytest.raises(ValueError, match="formato padrão"):
        mesclar(_df(["2026-10-13"], [5.0]).drop(columns="fonte"), dataframe_vazio())


def test_ler_arquivo_inexistente_devolve_vazio_tipado(tmp_path) -> None:
    df = ler_serie(tmp_path / "nao_existe.parquet")
    assert df.empty and list(df.columns) == COLUNAS_PADRAO
    assert df["data"].dtype == "datetime64[ns]"


def test_salvar_e_ler_preserva_dados_e_tipos(tmp_path) -> None:
    df = _df(["2010-01-04", "2026-10-14"], [1.7240, 5.0441])
    caminho = caminho_parquet(tmp_path, "ptax_venda")
    assert salvar_serie(df, caminho) is True
    lido = ler_serie(caminho)
    assert lido.equals(df)
    assert lido["data"].dtype == "datetime64[ns]" and lido["valor"].dtype == "float64"


def test_salvar_o_mesmo_conteudo_nao_toca_no_arquivo(tmp_path) -> None:
    df = _df(["2010-01-04", "2026-10-14"], [1.7240, 5.0441])
    caminho = caminho_parquet(tmp_path, "ptax_venda")
    salvar_serie(df, caminho)
    bytes_antes, mtime_antes = caminho.read_bytes(), caminho.stat().st_mtime_ns
    assert salvar_serie(df.copy(), caminho) is False
    assert caminho.read_bytes() == bytes_antes
    assert caminho.stat().st_mtime_ns == mtime_antes


def test_salvar_conteudo_diferente_reescreve(tmp_path) -> None:
    caminho = caminho_parquet(tmp_path, "ptax_venda")
    salvar_serie(_df(["2026-10-13"], [5.0096]), caminho)
    assert salvar_serie(_df(["2026-10-13", "2026-10-14"], [5.0096, 5.0441]), caminho) is True
    assert len(ler_serie(caminho)) == 2
    assert not caminho.with_suffix(".tmp").exists()
