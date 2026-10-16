import numpy as np
import pandas as pd
import pytest

from monitor.analise.base import correlacoes_de_retornos, montar_base
from monitor.analise.conversao import converter_para_reais, tonelada_para_saca
from monitor.analise.correlacao import correlacao
from monitor.analise.mensal import media_mensal, periodo_comum, recortar
from monitor.analise.variacao import retorno_log, variacao_mensal
from monitor.armazenamento import caminho_parquet, salvar_serie
from monitor.limpeza import COLUNAS_PADRAO


def _df(datas, valores, serie="x", unidade="US$/t", fonte="teste") -> pd.DataFrame:
    return pd.DataFrame(
        {"data": pd.to_datetime(datas), "serie": serie, "valor": [float(v) for v in valores],
         "unidade": unidade, "fonte": fonte}
    )[COLUNAS_PADRAO]


def _mensal(inicio: str, valores, **kw) -> pd.DataFrame:
    return _df(pd.date_range(inicio, periods=len(valores), freq="MS"), valores, **kw)


# --- média mensal e período em comum ------------------------------------------------


def test_media_mensal_por_mes_datada_no_primeiro_dia() -> None:
    diario = _df(["2026-09-01", "2026-09-30", "2026-10-01"], [5.0, 5.2, 5.5],
                 serie="ptax_venda", unidade="R$/US$", fonte="BCB")
    m = media_mensal(diario)
    assert m["data"].tolist() == [pd.Timestamp("2026-09-01"), pd.Timestamp("2026-10-01")]
    assert m["valor"].tolist() == pytest.approx([5.1, 5.5])
    assert (m["unidade"] == "R$/US$").all() and (m["serie"] == "ptax_venda_media_mensal").all()


def test_media_mensal_rejeita_mistura_de_series() -> None:
    df = pd.concat([_df(["2026-09-01"], [5.0], serie="a"), _df(["2026-09-02"], [5.0], serie="b")])
    with pytest.raises(ValueError, match="única série"):
        media_mensal(df)


def test_periodo_comum_e_a_intersecao_e_respeita_2010() -> None:
    ptax = _mensal("2009-06-01", [5.0] * 209)  # 2009-06 .. 2026-10 (out/2026 é mês parcial)
    soja = _mensal("1960-01-01", [400.0] * 801)  # 1960-01 .. 2026-09
    inicio, fim = periodo_comum(ptax, soja)
    assert (inicio, fim) == (pd.Timestamp("2010-01-01"), pd.Timestamp("2026-09-01"))


def test_periodo_comum_sem_intersecao_levanta_erro() -> None:
    with pytest.raises(ValueError, match="sem período em comum"):
        periodo_comum(_mensal("2010-01-01", [1, 2]), _mensal("2015-01-01", [1, 2]))


def test_recortar_inclui_as_pontas() -> None:
    df = _mensal("2010-01-01", [1, 2, 3, 4])
    r = recortar(df, pd.Timestamp("2010-02-01"), pd.Timestamp("2010-03-01"))
    assert r["valor"].tolist() == [2.0, 3.0]


# --- conversão ---------------------------------------------------------------------


def test_converte_us_por_tonelada_para_reais() -> None:
    preco = _mensal("2026-08-01", [482, 524], serie="wb_soja")
    cambio = _mensal("2026-08-01", [5.15, 5.0], serie="ptax", unidade="R$/US$", fonte="BCB")
    brl = converter_para_reais(preco, cambio)
    assert brl["valor"].tolist() == pytest.approx([482 * 5.15, 2620.0])
    assert (brl["unidade"] == "R$/t").all() and (brl["serie"] == "wb_soja_brl").all()
    assert "BCB" in brl["fonte"].iloc[0]


def test_conversao_exige_cambio_para_todos_os_meses() -> None:
    preco = _mensal("2026-08-01", [482, 524])
    cambio = _mensal("2026-08-01", [5.15], unidade="R$/US$")
    with pytest.raises(ValueError, match="2026-09"):
        converter_para_reais(preco, cambio)


@pytest.mark.parametrize(("u_preco", "u_cambio"), [("R$/t", "R$/US$"), ("US$/t", "US$/R$")])
def test_conversao_valida_unidades(u_preco: str, u_cambio: str) -> None:
    with pytest.raises(ValueError, match="esperada"):
        converter_para_reais(_mensal("2026-09-01", [524], unidade=u_preco),
                             _mensal("2026-09-01", [5.0], unidade=u_cambio))


@pytest.mark.parametrize(("unidade", "esperada"), [("R$/t", "R$/sc 60 kg"), ("US$/t", "US$/sc 60 kg")])
def test_tonelada_para_saca_de_60kg(unidade: str, esperada: str) -> None:
    sc = tonelada_para_saca(_mensal("2026-09-01", [2500.0], unidade=unidade))
    assert sc["valor"].tolist() == pytest.approx([150.0])  # 2500 × 60 / 1000
    assert sc["unidade"].tolist() == [esperada]


def test_saca_rejeita_unidade_que_nao_e_por_tonelada() -> None:
    with pytest.raises(ValueError, match="tonelada"):
        tonelada_para_saca(_mensal("2026-09-01", [5.0], unidade="R$/US$"))


# --- variação e retorno ------------------------------------------------------------


def test_variacao_mensal_em_percentual_com_unidade() -> None:
    v = variacao_mensal(_mensal("2026-07-01", [100, 110, 99], unidade="R$/t"))
    assert v["valor"].tolist() == pytest.approx([10.0, -10.0])
    assert v["data"].tolist() == [pd.Timestamp("2026-08-01"), pd.Timestamp("2026-09-01")]
    assert (v["unidade"] == "% m/m (R$/t)").all()


def test_retorno_log() -> None:
    r = retorno_log(_mensal("2026-08-01", [100, 110]))
    assert r["valor"].tolist() == pytest.approx([np.log(1.1)])
    assert (r["unidade"] == "log-retorno mensal (US$/t)").all()


def test_variacao_rejeita_meses_faltando() -> None:
    with pytest.raises(ValueError, match="faltando"):
        variacao_mensal(_df(["2026-07-01", "2026-09-01"], [100, 110]))


# --- correlação --------------------------------------------------------------------


def test_correlacao_perfeita_e_unidades_no_resultado() -> None:
    x = _mensal("2010-01-01", [1, 2, 3, 4, 5], serie="a", unidade="R$/US$")
    y = _mensal("2010-01-01", [2, 4, 6, 8, 10], serie="b", unidade="US$/t")
    r = correlacao(x, y)
    assert r.r == pytest.approx(1.0) and r.n == 5
    assert "[R$/US$]" in r.descricao() and "[US$/t]" in r.descricao()


def test_correlacao_usa_so_datas_em_comum() -> None:
    x = _mensal("2010-01-01", [1, 2, 3, 4, 5])
    y = _mensal("2010-03-01", [3, 1, 4, 1, 5])
    r = correlacao(x, y)
    assert r.n == 3 and r.inicio == pd.Timestamp("2010-03-01") and r.fim == pd.Timestamp("2010-05-01")


def test_correlacao_com_poucos_pontos_levanta_erro() -> None:
    with pytest.raises(ValueError, match="ao menos 3"):
        correlacao(_mensal("2010-01-01", [1, 2]), _mensal("2010-01-01", [1, 2]))


def test_efeito_mecanico_da_conversao_para_reais(tmp_path) -> None:
    """Com dólar e preço em US$ independentes, o preço em R$ ainda correlaciona com o dólar."""
    rng = np.random.default_rng(42)
    n = 201
    datas = pd.date_range("2010-01-01", periods=n, freq="MS")
    ptax = 2.0 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    soja = 400 * np.exp(np.cumsum(rng.normal(0, 0.05, n)))
    milho = 180 * np.exp(np.cumsum(rng.normal(0, 0.05, n)))
    # PTAX diária: um valor por mês basta para a média mensal
    salvar_serie(_df(datas, ptax, serie="ptax_venda", unidade="R$/US$", fonte="BCB"),
                 caminho_parquet(tmp_path, "ptax_venda"))
    salvar_serie(_df(datas, soja, serie="wb_soja"), caminho_parquet(tmp_path, "wb_soja"))
    salvar_serie(_df(datas, milho, serie="wb_milho"), caminho_parquet(tmp_path, "wb_milho"))

    base = montar_base(tmp_path)
    assert (base.inicio, base.fim) == (pd.Timestamp("2010-01-01"), pd.Timestamp("2026-09-01"))
    assert base.unidades("wb_soja") == ["US$/t", "R$/t", "US$/sc 60 kg", "R$/sc 60 kg"]

    soja_usd, soja_brl, *_ = correlacoes_de_retornos(base)
    assert soja_usd.unidade_y == "log-retorno mensal (US$/t)" and abs(soja_usd.r) < 0.2
    assert soja_brl.unidade_y == "log-retorno mensal (R$/t)" and soja_brl.r > 0.35
