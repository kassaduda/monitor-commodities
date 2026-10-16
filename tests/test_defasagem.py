import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import grangercausalitytests

from monitor.analise.base import BaseMensal
from monitor.analise.defasagem import (
    QUEBRAS_SOJA,
    UNIDADE_F,
    UNIDADE_R,
    VARIANTE_SEM_QUEBRAS,
    adf,
    ajustar_bh,
    analisar,
    correlacao_cruzada,
    defasar,
    excluir_meses,
    granger,
)
from monitor.limpeza import COLUNAS_PADRAO

UNIDADE_RET = "log-retorno mensal (US$/t)"


def _mensal(valores, serie="x", unidade=UNIDADE_RET, inicio="2010-02-01") -> pd.DataFrame:
    datas = pd.date_range(inicio, periods=len(valores), freq="MS")
    return pd.DataFrame(
        {"data": datas, "serie": serie, "valor": np.asarray(valores, float), "unidade": unidade, "fonte": "teste"}
    )[COLUNAS_PADRAO]


def _x_antecipa_y(n=200, k=3, seed=0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """y_t = 0,8·x_{t−k} + ruído."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n + k)
    y = 0.8 * x[:-k] + 0.3 * rng.normal(size=n)
    return (
        _mensal(x[k:], "dolar", "log-retorno mensal (R$/US$)"),
        _mensal(y, "soja"),
    )


def test_defasar_move_datas_e_mantem_valor_e_unidade() -> None:
    df = _mensal([1.0, 2.0])
    d = defasar(df, 3)
    assert list(d["data"]) == [pd.Timestamp("2010-05-01"), pd.Timestamp("2010-06-01")]
    assert list(d["valor"]) == [1.0, 2.0]
    assert (d["unidade"] == UNIDADE_RET).all()


def test_correlacao_cruzada_encontra_a_defasagem_e_traz_unidades() -> None:
    x, y = _x_antecipa_y(k=3)
    cc = correlacao_cruzada(x, y, max_defasagem=6)
    assert list(cc["defasagem"]) == list(range(7))
    assert cc.loc[cc["estatistica"].abs().idxmax(), "defasagem"] == 3
    assert cc.loc[3, "estatistica"] > 0.9
    assert cc.drop(index=3)["estatistica"].abs().max() < 0.25
    assert (cc["unidade_estatistica"] == UNIDADE_R).all()
    assert (cc["unidade_x"] == "log-retorno mensal (R$/US$)").all()
    assert (cc["unidade_y"] == UNIDADE_RET).all()
    # cada defasagem perde um par no início
    assert list(cc["n"]) == [200 - k for k in range(7)]


def test_granger_igual_ao_statsmodels_sem_meses_excluidos() -> None:
    x, y = _x_antecipa_y(n=150, k=2, seed=1)
    g = granger(x, y, max_defasagem=4)
    dados = np.column_stack([y["valor"], x["valor"]])
    ref = grangercausalitytests(dados, maxlag=4)
    for p in range(1, 5):
        f_ref, p_ref, *_ = ref[p][0]["ssr_ftest"]
        linha = g[g["defasagem"] == p].iloc[0]
        assert linha["estatistica"] == pytest.approx(f_ref, rel=1e-8)
        assert linha["p_valor"] == pytest.approx(p_ref, rel=1e-6, abs=1e-300)
    assert (g["unidade_estatistica"] == UNIDADE_F).all()


def test_granger_detecta_x_antecipando_y_e_nao_o_contrario() -> None:
    x, y = _x_antecipa_y(k=2, seed=2)
    g = granger(x, y, max_defasagem=3)
    # com p < 2 o modelo não inclui x_{t−2}; a partir de p = 2 o efeito aparece
    assert g.loc[g["defasagem"] >= 2, "p_valor"].max() < 1e-6
    rng = np.random.default_rng(3)
    ruido = _mensal(rng.normal(size=200), "ruido")
    assert granger(ruido, y, max_defasagem=3)["p_valor"].min() > 0.01


def test_excluir_meses_tira_tambem_as_linhas_que_usam_o_mes_como_defasagem() -> None:
    x, y = _x_antecipa_y(n=60, k=1, seed=4)
    mes = pd.Timestamp("2012-01-01")
    y_sem = excluir_meses(y, (mes,))
    assert len(y_sem) == len(y) - 1
    # correlação cruzada: o mês sai só como y_t → 1 par a menos em cada defasagem
    assert list(correlacao_cruzada(x, y_sem, 3)["n"]) == list(correlacao_cruzada(x, y, 3)["n"] - 1)
    # Granger com p defasagens: o mês some como y_t e como y_{t−1..t−p} → p + 1 linhas a menos
    n_com, n_sem = granger(x, y, 3)["n"], granger(x, y_sem, 3)["n"]
    assert list(n_com - n_sem) == [2, 3, 4]


def test_adf_distingue_ruido_de_passeio_aleatorio() -> None:
    rng = np.random.default_rng(5)
    e = rng.normal(size=200)
    estacionario = adf(_mensal(e))
    passeio = adf(_mensal(np.cumsum(e), unidade="US$/t"))
    assert estacionario["estacionaria_5pct"] and estacionario["p_valor"] < 0.01
    assert not passeio["estacionaria_5pct"]
    assert passeio["unidade"] == "US$/t"
    assert estacionario["unidade_estatistica"].startswith("estatística ADF")


def test_bh_ajusta_p_valores() -> None:
    testes = pd.DataFrame({"p_valor": [0.01, 0.02, 0.03, 0.5]})
    out = ajustar_bh(testes)
    # BH: p_(i) · m / i, com monotonicidade → 0,04; 0,04; 0,04; 0,5
    assert list(out["p_bh"].round(6)) == [0.04, 0.04, 0.04, 0.5]
    assert list(out["significativo_bh"]) == [True, True, True, False]
    assert (out["p_bh"] >= out["p_valor"]).all()


def _base_sintetica(n=120, seed=6) -> BaseMensal:
    rng = np.random.default_rng(seed)
    datas = pd.date_range("2016-01-01", periods=n, freq="MS")

    def nivel(serie, unidade, inicio):
        v = inicio * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
        return pd.DataFrame(
            {"data": datas, "serie": serie, "valor": v, "unidade": unidade, "fonte": "teste"}
        )[COLUNAS_PADRAO]

    ptax = nivel("ptax_venda", "R$/US$", 4.0)
    precos = {c: {"US$/t": nivel(c, "US$/t", 400.0)} for c in ("wb_soja", "wb_milho")}
    return BaseMensal(datas[0], datas[-1], ptax, precos)


def test_analisar_roda_soja_com_e_sem_quebras_e_milho_com_unidades() -> None:
    estacionariedade, testes = analisar(_base_sintetica(), max_defasagem=4)
    assert len(estacionariedade) == 3
    assert estacionariedade["unidade"].str.startswith("log-retorno mensal").all()
    # 3 casos × (5 defasagens de correlação + 4 de Granger)
    assert len(testes) == 3 * (5 + 4)
    for col in ("unidade_x", "unidade_y", "unidade_estatistica"):
        assert testes[col].str.len().gt(0).all()
    assert (testes["unidade_y"] == "log-retorno mensal (US$/t)").all()
    soja = testes[testes["serie_y"].str.startswith("wb_soja")]
    com = soja[soja["variante"] != VARIANTE_SEM_QUEBRAS].set_index(["teste", "defasagem"])["n"]
    sem = soja[soja["variante"] == VARIANTE_SEM_QUEBRAS].set_index(["teste", "defasagem"])["n"]
    base = _base_sintetica()
    assert all(base.inicio < m <= base.fim for m in QUEBRAS_SOJA)
    assert (sem < com).all()
    assert testes["p_bh"].between(0, 1).all()
