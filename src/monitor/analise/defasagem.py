"""Análise de defasagem: o dólar antecipa os preços de soja e milho? (etapa 5)

Tudo em retornos log mensais: dólar (R$/US$) contra soja e milho em US$/t. Em R$/t a
relação teria um componente mecânico (R$/t = US$/t × câmbio), por isso fica de fora.

Convenção: defasagem k = dólar no mês t−k contra o preço no mês t (k > 0: o dólar vem antes).
O alinhamento é sempre pela data, então meses excluídos nunca aproximam meses distantes.

Uso: python -m monitor.analise.defasagem
"""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller

from monitor import config
from monitor.analise.base import BaseMensal, montar_base
from monitor.analise.correlacao import correlacao
from monitor.analise.variacao import retorno_log

MAX_DEFASAGEM = 12
ALFA = 0.05
# Mudanças de definição da soja no Pink Sheet: o retorno desses meses compara duas definições.
QUEBRAS_SOJA = (pd.Timestamp("2021-01-01"), pd.Timestamp("2025-01-01"))
UNIDADE_R = "r de Pearson (adimensional)"
UNIDADE_F = "estatística F (adimensional)"
UNIDADE_ADF = "estatística ADF (adimensional)"
VARIANTE_COMPLETA = "série completa"
VARIANTE_SEM_QUEBRAS = "sem os retornos de jan/2021 e jan/2025"

COLUNAS_TESTE = [
    "teste", "variante", "serie_x", "unidade_x", "serie_y", "unidade_y", "defasagem",
    "estatistica", "unidade_estatistica", "p_valor", "ic95_inf", "ic95_sup", "n", "inicio", "fim",
]


def defasar(df: pd.DataFrame, meses: int) -> pd.DataFrame:
    """Leva o valor do mês t para o mês t+meses (o valor de t−k passa a estar datado em t)."""
    out = df.copy()
    out["data"] = out["data"] + pd.DateOffset(months=meses)
    return out


def excluir_meses(df: pd.DataFrame, meses: tuple[pd.Timestamp, ...]) -> pd.DataFrame:
    """Remove as observações desses meses; quem depender delas (como defasagem) também sai."""
    return df[~df["data"].isin(meses)].reset_index(drop=True)


def correlacao_cruzada(x: pd.DataFrame, y: pd.DataFrame, max_defasagem: int = MAX_DEFASAGEM) -> pd.DataFrame:
    """Pearson entre x em t−k e y em t, para k = 0..max_defasagem."""
    linhas = []
    for k in range(max_defasagem + 1):
        res = correlacao(defasar(x, k), y)
        linhas.append({
            "teste": "correlação cruzada",
            "serie_x": res.serie_x, "unidade_x": res.unidade_x,
            "serie_y": res.serie_y, "unidade_y": res.unidade_y,
            "defasagem": k, "estatistica": res.r, "unidade_estatistica": UNIDADE_R,
            "p_valor": res.p_valor, "ic95_inf": res.ic95[0], "ic95_sup": res.ic95[1],
            "n": res.n, "inicio": res.inicio, "fim": res.fim,
        })
    return pd.DataFrame(linhas)


def granger(x: pd.DataFrame, y: pd.DataFrame, max_defasagem: int = MAX_DEFASAGEM) -> pd.DataFrame:
    """Teste F de Granger "x antecipa y" com p = 1..max_defasagem defasagens de cada série.

    Modelo restrito: y_t ~ 1 + y_{t−1..t−p}; irrestrito: + x_{t−1..t−p}. Mesmo F do
    `ssr_ftest` do statsmodels, mas montado por data para aceitar meses excluídos.
    """
    linhas = []
    for p in range(1, max_defasagem + 1):
        f, p_valor, m = _f_granger(x, y, p)
        linhas.append({
            "teste": "Granger",
            "serie_x": str(x["serie"].iloc[0]), "unidade_x": str(x["unidade"].iloc[0]),
            "serie_y": str(y["serie"].iloc[0]), "unidade_y": str(y["unidade"].iloc[0]),
            "defasagem": p, "estatistica": f, "unidade_estatistica": UNIDADE_F,
            "p_valor": p_valor, "ic95_inf": np.nan, "ic95_sup": np.nan,
            "n": len(m), "inicio": m.index.min(), "fim": m.index.max(),
        })
    return pd.DataFrame(linhas)


def _f_granger(x: pd.DataFrame, y: pd.DataFrame, p: int) -> tuple[float, float, pd.DataFrame]:
    y_t = _por_data(y)
    colunas = {"y": y_t}
    for k in range(1, p + 1):
        colunas[f"y_l{k}"] = _por_data(defasar(y, k))
        colunas[f"x_l{k}"] = _por_data(defasar(x, k))
    m = pd.DataFrame(colunas).reindex(y_t.index).dropna()
    gl = len(m) - 2 * p - 1
    if gl < 10:
        raise ValueError(f"Poucas observações para Granger com {p} defasagens (n = {len(m)})")
    const = np.ones((len(m), 1))
    y_lags = m[[f"y_l{k}" for k in range(1, p + 1)]].to_numpy()
    x_lags = m[[f"x_l{k}" for k in range(1, p + 1)]].to_numpy()
    rss_r = _rss(np.hstack([const, y_lags]), m["y"].to_numpy())
    rss_u = _rss(np.hstack([const, y_lags, x_lags]), m["y"].to_numpy())
    f = ((rss_r - rss_u) / p) / (rss_u / gl)
    return float(f), float(stats.f.sf(f, p, gl)), m


def _rss(X: np.ndarray, y: np.ndarray) -> float:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(((y - X @ beta) ** 2).sum())


def _por_data(df: pd.DataFrame) -> pd.Series:
    return df.set_index("data")["valor"]


def adf(df: pd.DataFrame) -> dict:
    """Dickey-Fuller aumentado com constante, defasagens por AIC. H0: raiz unitária."""
    if df["unidade"].nunique() != 1:
        raise ValueError("Esperada uma única unidade")
    stat, p_valor, lags, n, criticos, _ = adfuller(
        df["valor"].to_numpy(), regression="c", autolag="AIC", result_object=False
    )
    return {
        "serie": str(df["serie"].iloc[0]), "unidade": str(df["unidade"].iloc[0]),
        "estatistica": float(stat), "unidade_estatistica": UNIDADE_ADF,
        "p_valor": float(p_valor), "valor_critico_5pct": float(criticos["5%"]),
        "defasagens_usadas": int(lags), "n": int(n), "estacionaria_5pct": bool(p_valor < ALFA),
    }


def ajustar_bh(testes: pd.DataFrame, alfa: float = ALFA) -> pd.DataFrame:
    """Benjamini-Hochberg sobre todos os testes juntos (controla a taxa de falsas descobertas)."""
    rejeita, p_bh, *_ = multipletests(testes["p_valor"], alpha=alfa, method="fdr_bh")
    return testes.assign(p_bh=p_bh, significativo_bh=rejeita)


def analisar(base: BaseMensal, max_defasagem: int = MAX_DEFASAGEM) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (ADF dos retornos, correlação cruzada + Granger com p-valor BH)."""
    ret_dolar = retorno_log(base.ptax)
    ret_soja = retorno_log(base.precos["wb_soja"]["US$/t"])
    ret_milho = retorno_log(base.precos["wb_milho"]["US$/t"])

    estacionariedade = pd.DataFrame([adf(r) for r in (ret_dolar, ret_soja, ret_milho)])

    casos = [
        (VARIANTE_COMPLETA, ret_soja),
        (VARIANTE_SEM_QUEBRAS, excluir_meses(ret_soja, QUEBRAS_SOJA)),
        (VARIANTE_COMPLETA, ret_milho),
    ]
    blocos = [
        f(ret_dolar, ret, max_defasagem).assign(variante=variante)
        for variante, ret in casos
        for f in (correlacao_cruzada, granger)
    ]
    testes = ajustar_bh(pd.concat(blocos, ignore_index=True)[COLUNAS_TESTE])
    return estacionariedade, testes


def main() -> None:
    base = montar_base()
    estacionariedade, testes = analisar(base)
    print("ADF nos retornos log mensais (H0: raiz unitária):")
    for r in estacionariedade.itertuples():
        print(f"  {r.serie} [{r.unidade}]: {r.estatistica:.2f} [{r.unidade_estatistica}] "
              f"(crítico 5%: {r.valor_critico_5pct:.2f}; p = {r.p_valor:.2g}; n = {r.n})")

    print(f"\n{len(testes)} testes; p_bh = p-valor ajustado por Benjamini-Hochberg sobre todos eles.")
    for (teste, serie_y, variante), g in testes.groupby(["teste", "serie_y", "variante"], sort=False):
        print(f"\n{teste}: {g['serie_x'].iloc[0]} [{g['unidade_x'].iloc[0]}] → {serie_y} "
              f"[{g['unidade_y'].iloc[0]}], {variante} — {g['unidade_estatistica'].iloc[0]}")
        print(g[["defasagem", "estatistica", "p_valor", "p_bh", "n"]].round(3).to_string(index=False))
    print(f"\nO dólar ({config.BCB_SERIE_1_NOME}) é a série x. {config.AVISO_INVESTIMENTO}")


if __name__ == "__main__":
    main()
