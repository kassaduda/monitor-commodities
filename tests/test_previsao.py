import numpy as np
import pandas as pd
import pytest
from scipy import stats

from monitor.limpeza import COLUNAS_PADRAO
from monitor.previsao.backtest import backtest, prever, serie_log
from monitor.previsao.metricas import (
    avaliar,
    com_veredito,
    comprimento_bloco,
    diebold_mariano_hln,
    ic_rmae_bootstrap,
    razao_mae,
)
from monitor.previsao.modelos import Previsao, arima, ets, ingenuo


def _precos(valores, serie="wb_soja", inicio="2010-01-01") -> pd.DataFrame:
    datas = pd.date_range(inicio, periods=len(valores), freq="MS")
    return pd.DataFrame(
        {"data": datas, "serie": serie, "valor": np.asarray(valores, float), "unidade": "US$/t", "fonte": "teste"}
    )[COLUNAS_PADRAO]


def _passeio(n=90, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return _precos(400 * np.exp(np.cumsum(rng.normal(0, 0.04, n))))


def _log(n=60, seed=0) -> pd.Series:
    return serie_log(_passeio(n, seed))


# ---------- modelos ----------

def test_ingenuo_repete_ultimo_valor_e_intervalo_cresce_com_h():
    y = _log()
    p = ingenuo(y, 6)
    assert np.allclose(p.media, y.iloc[-1])
    largura = p.sup - p.inf
    assert np.allclose(largura / largura[0], np.sqrt(np.arange(1, 7)))


@pytest.mark.parametrize("modelo", [arima, ets])
def test_modelos_devolvem_horizonte_completo_com_intervalo(modelo):
    p = modelo(_log(), 6)
    assert len(p.media) == len(p.inf) == len(p.sup) == 6
    assert np.all(p.inf < p.media) and np.all(p.media < p.sup)
    assert np.isfinite(p.media).all()


def test_arima_escolhe_ordem_limitada():
    p = arima(_log(), 3)
    assert p.especificacao.startswith("ARIMA(")
    pp, d, q = map(int, p.especificacao[6:-1].split(","))
    assert d == 1 and pp <= 2 and q <= 2


def test_ets_sem_sazonalidade():
    assert ets(_log(), 3).especificacao in {"ETS(A,N,N)", "ETS(A,Ad,N)"}


def test_modelo_recusa_janela_curta():
    with pytest.raises(ValueError, match="Janela"):
        ingenuo(_log(60).iloc[:5], 3)


# ---------- backtest ----------

def test_serie_log_exige_meses_consecutivos():
    df = _passeio(30).drop(index=10)
    with pytest.raises(ValueError, match="consecutivos"):
        serie_log(df)


def _espiao():
    """Modelo que registra a janela recebida e prevê o último valor."""
    janelas: list[pd.Series] = []

    def modelo(log_y, horizonte, alfa):
        janelas.append(log_y.copy())
        m = np.full(horizonte, float(log_y.iloc[-1]))
        return Previsao(m, m - 1, m + 1, "espião")

    return modelo, janelas


def test_backtest_usa_janela_fixa_que_termina_na_origem():
    df = _passeio(80)
    modelo, janelas = _espiao()
    erros = backtest(df, {"espião": modelo}, janela=24, horizontes=(1, 3))
    origens = sorted(erros["origem"].unique())
    assert len(janelas) == len(origens) == 80 - 24  # última origem ainda tem h = 1
    for j, origem in zip(janelas, origens):
        assert len(j) == 24 and j.index.max() == origem


def test_backtest_sem_vazamento_futuro_nao_muda_previsoes_passadas():
    df = _passeio(80)
    alterado = df.copy()
    alterado.loc[alterado.index >= 50, "valor"] *= 3  # muda tudo a partir do mês 50
    a = backtest(df, {"ingênuo": ingenuo, "ETS": ets}, janela=24, horizontes=(1, 3))
    b = backtest(alterado, {"ingênuo": ingenuo, "ETS": ets}, janela=24, horizontes=(1, 3))
    corte = df["data"].iloc[49]
    pa, pb = a[a["origem"] <= corte], b[b["origem"] <= corte]
    assert len(pa) > 0
    assert np.allclose(pa["previsto"], pb["previsto"]) and np.allclose(pa["sup"], pb["sup"])


def test_backtest_conta_origens_por_horizonte_e_calcula_erro_no_nivel():
    df = _passeio(70)
    erros = backtest(df, {"ingênuo": ingenuo}, janela=60, horizontes=(1, 3, 6))
    assert erros.groupby("h").size().to_dict() == {1: 10, 3: 8, 6: 5}
    linha = erros[erros["h"] == 3].iloc[0]
    valores = df.set_index("data")["valor"]
    assert linha["alvo"] == linha["origem"] + pd.DateOffset(months=3)
    assert linha["previsto"] == pytest.approx(valores[linha["origem"]])
    assert linha["erro"] == pytest.approx(valores[linha["alvo"]] - valores[linha["origem"]])
    assert (erros["unidade"] == "US$/t").all()


def test_prever_comeca_no_mes_seguinte_ao_ultimo():
    df = _passeio(70)
    prev = prever(df, ingenuo, "ingênuo", janela=60, horizonte=6)
    assert prev["data"].iloc[0] == df["data"].max() + pd.DateOffset(months=1)
    assert len(prev) == 6 and (prev["inf"] < prev["previsto"]).all()
    assert prev["previsto"].iloc[0] == pytest.approx(df["valor"].iloc[-1])


# ---------- métricas ----------

def test_rmae_igual_um_para_o_proprio_ingenuo_e_zero_para_previsao_perfeita():
    e = np.array([1.0, 2.0, 3.0])
    assert razao_mae(e, e) == 1.0
    assert razao_mae(np.zeros(3), e) == 0.0


def test_bloco_do_bootstrap_cobre_sobreposicao():
    assert comprimento_bloco(130, 6) == 6
    assert comprimento_bloco(130, 1) == 6  # ceil(130^(1/3))
    assert comprimento_bloco(30, 6) == 6


def test_ic_bootstrap_contem_estimativa_e_e_reprodutivel():
    rng = np.random.default_rng(1)
    a, b = np.abs(rng.normal(size=120)), np.abs(rng.normal(size=120))
    ic = ic_rmae_bootstrap(a, b, h=3)
    assert ic[0] < razao_mae(a, b) < ic[1]
    assert ic == ic_rmae_bootstrap(a, b, h=3)


def test_dm_hln_com_h_1_e_o_teste_t_de_uma_amostra():
    d = np.random.default_rng(2).normal(0.2, 1, 80)
    estat, p = diebold_mariano_hln(d, 1)
    t = stats.ttest_1samp(d, 0)
    assert estat == pytest.approx(t.statistic) and p == pytest.approx(t.pvalue)


def test_dm_hln_com_h_maior_que_1_confere_com_conta_manual():
    d = np.array([0.5, 0.6, 0.8, 0.4, -0.1, -0.3, 0.2, 0.4, 0.9, 0.7, 0.1, 0.3])
    t, h = len(d), 2
    dc = d - d.mean()
    v = (dc @ dc + 2 * (dc[1:] @ dc[:-1])) / t
    assert v > 0
    esperado = d.mean() / np.sqrt(v / t) * np.sqrt((t + 1 - 2 * h + h * (h - 1) / t) / t)
    estat, p = diebold_mariano_hln(d, h)
    assert estat == pytest.approx(esperado)
    assert p == pytest.approx(2 * stats.t.sf(abs(esperado), t - 1))


def test_dm_hln_usa_bartlett_quando_variancia_uniforme_sai_negativa():
    d = np.array([0.5, -0.2, 0.8, 0.1, -0.4, 0.9, 0.3, -0.1, 0.6, 0.2, 0.0, 0.7])
    t, h = len(d), 2
    dc = d - d.mean()
    g0, g1 = dc @ dc / t, dc[1:] @ dc[:-1] / t
    assert g0 + 2 * g1 <= 0
    esperado = d.mean() / np.sqrt((g0 + 2 * 0.5 * g1) / t) * np.sqrt((t + 1 - 2 * h + h * (h - 1) / t) / t)
    assert diebold_mariano_hln(d, h)[0] == pytest.approx(esperado)


def test_dm_hln_mantem_tamanho_com_horizontes_sobrepostos():
    """MA(h−1) com média zero (erros sobrepostos): rejeição a 5% perto do nominal."""
    rng = np.random.default_rng(3)
    h, t, reps = 6, 130, 600
    rejeicoes = 0
    for _ in range(reps):
        e = rng.normal(size=t + h - 1)
        d = np.convolve(e, np.ones(h), mode="valid")
        rejeicoes += diebold_mariano_hln(d, h)[1] < 0.05
    assert rejeicoes / reps < 0.10


def test_dm_hln_perdas_iguais_nao_rejeita():
    assert diebold_mariano_hln(np.zeros(20), 3) == (0.0, 1.0)


def test_avaliar_e_veredito():
    df = _passeio(100)
    erros = backtest(df, {"ingênuo": ingenuo, "ETS": ets}, janela=36, horizontes=(1, 3))
    aval = com_veredito(avaliar(erros))
    assert set(aval["modelo"]) == {"ETS"} and sorted(aval["h"]) == [1, 3]
    assert (aval["rmae_ic95_inf"] <= aval["rmae"]).all() and (aval["rmae"] <= aval["rmae_ic95_sup"]).all()
    assert aval["veredito"].isin({"ganha do ingênuo", "perde do ingênuo", "sem diferença significativa"}).all()
    assert aval["cobertura95_modelo"].between(0, 1).all()


# ---------- casos ----------

def test_casos_incluem_robustez_da_soja_so_com_dados_desde_2021(tmp_path):
    from monitor.armazenamento import caminho_parquet, salvar_serie
    from monitor.previsao.execucao import JANELA_ROBUSTEZ, VARIANTE_ROBUSTEZ, casos

    rng = np.random.default_rng(4)
    for serie, unidade in (("ptax_venda", "R$/US$"), ("wb_soja", "US$/t"), ("wb_milho", "US$/t"), ("wb_trigo", "US$/t")):
        df = _precos(100 * np.exp(np.cumsum(rng.normal(0, 0.03, 201))), serie=serie)
        salvar_serie(df.assign(unidade=unidade), caminho_parquet(tmp_path, serie))

    lista = casos(tmp_path)
    assert [(c.serie, c.variante) for c in lista] == [
        ("wb_soja", "série completa"), ("wb_soja", VARIANTE_ROBUSTEZ), ("wb_milho", "série completa")]
    robustez = lista[1]
    assert robustez.dados["data"].min() == pd.Timestamp("2021-01-01")
    assert robustez.dados["data"].max() == lista[0].dados["data"].max()
    assert robustez.janela == JANELA_ROBUSTEZ
