import numpy as np
import pandas as pd
import pytest

from monitor.analise.risco import bandas_bollinger, correlacao_deslizante, volatilidade_movel
from monitor.limpeza import COLUNAS_PADRAO


def serie(valores, nome="s", unidade="u", inicio="2020-01-01") -> pd.DataFrame:
    datas = pd.date_range(inicio, periods=len(valores), freq="MS")
    return pd.DataFrame({"data": datas, "serie": nome, "valor": np.asarray(valores, float), "unidade": unidade, "fonte": "teste"})[COLUNAS_PADRAO]


def test_correlacao_deslizante_perfeita_e_inversa():
    x = np.random.default_rng(0).normal(size=60)
    r = correlacao_deslizante(serie(x, "x"), serie(2 * x + 1, "y"), janela=12)
    assert len(r) == 60 - 12 + 1 and r["data"].iloc[0] == pd.Timestamp("2020-12-01")
    assert np.allclose(r["valor"], 1.0)
    assert np.allclose(correlacao_deslizante(serie(x, "x"), serie(-x, "y"), janela=12)["valor"], -1.0)


def test_correlacao_deslizante_so_enxerga_a_janela():
    """Mudar um valor antigo não altera a correlação das janelas que já o deixaram para trás."""
    rng = np.random.default_rng(1)
    x, y = rng.normal(size=48), rng.normal(size=48)
    base = correlacao_deslizante(serie(x), serie(y), janela=12)
    y2 = y.copy(); y2[0] += 100
    alt = correlacao_deslizante(serie(x), serie(y2), janela=12)
    assert np.allclose(base["valor"].iloc[1:], alt["valor"].iloc[1:])
    assert not np.isclose(base["valor"].iloc[0], alt["valor"].iloc[0])


def test_correlacao_deslizante_recusa_serie_curta_e_mes_faltando():
    with pytest.raises(ValueError, match="curta"):
        correlacao_deslizante(serie(range(5)), serie(range(5)), janela=12)
    x = serie(np.random.default_rng(2).normal(size=30))
    with pytest.raises(ValueError, match="faltando"):
        correlacao_deslizante(x.drop(index=10), x.drop(index=10), janela=12)


def test_volatilidade_movel_constante_e_degrau():
    assert np.allclose(volatilidade_movel(serie([0.01] * 30), janela=12)["valor"], 0.0)
    v = np.array([0.0] * 12 + [1.0] * 12)
    vol = volatilidade_movel(serie(v), janela=12)
    assert len(vol) == 24 - 12 + 1
    assert vol["valor"].iloc[0] == 0.0 and vol["valor"].iloc[-1] == 0.0
    assert vol["valor"].max() == pytest.approx(pd.Series([0.0] * 6 + [1.0] * 6).std())
    assert "desvio-padrão em 12 meses" in vol["unidade"].iloc[0]


def test_bollinger_marca_o_choque_e_o_sentido():
    v = np.tile([99.0, 101.0], 20)  # oscila ±1: dentro da banda de ±2 desvios
    v[15], v[35] = 160.0, 40.0
    b = bandas_bollinger(serie(v), janela=12, k=2.0)
    choques = b[b["choque"]]
    assert list(choques["valor"]) == [160.0, 40.0]
    assert list(choques["sentido"]) == ["acima", "abaixo"]
    assert (b["inferior"] <= b["media"]).all() and (b["media"] <= b["superior"]).all()
    assert len(b) == len(v) - 12 + 1


def test_bollinger_usa_desvio_populacional_e_inclui_o_proprio_mes():
    v = np.arange(1.0, 13.0)
    b = bandas_bollinger(serie(v), janela=12, k=2.0)
    assert b["media"].iloc[0] == pytest.approx(6.5)
    assert b["superior"].iloc[0] - b["media"].iloc[0] == pytest.approx(2 * np.std(v))  # ddof = 0


def test_bollinger_serie_sem_variacao_nao_gera_choque():
    b = bandas_bollinger(serie([50.0] * 20))
    assert not b["choque"].any()
