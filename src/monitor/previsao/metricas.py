"""Métricas do backtest: razão de MAE (rMAE) vs ingênuo, com IC por bootstrap em blocos, e DM-HLN.

rMAE = MAE do modelo ÷ MAE do ingênuo, nas mesmas origens e no mesmo horizonte (fora da
amostra). Não é o MASE de Hyndman, que escala pelo erro do ingênuo dentro da amostra.
< 1: o modelo erra menos que repetir o último valor. Perda do DM: erro absoluto, a mesma da rMAE.
"""

import math

import numpy as np
import pandas as pd
from scipy import stats

from monitor.analise.defasagem import ALFA, ajustar_bh
from monitor.previsao.modelos import REFERENCIA

N_BOOTSTRAP = 2000
SEMENTE = 20261015


def razao_mae(abs_modelo: np.ndarray, abs_ingenuo: np.ndarray) -> float:
    return float(np.sum(abs_modelo) / np.sum(abs_ingenuo))


def comprimento_bloco(t: int, h: int) -> int:
    """Pelo menos h (erros de h passos se sobrepõem até h−1 meses) e ~T^(1/3)."""
    return max(h, math.ceil(t ** (1 / 3)))


def ic_rmae_bootstrap(
    abs_modelo: np.ndarray, abs_ingenuo: np.ndarray, h: int,
    n_boot: int = N_BOOTSTRAP, nivel: float = 0.95, semente: int = SEMENTE,
) -> tuple[float, float]:
    """IC percentil da rMAE por bootstrap circular em blocos, reamostrando origens em pares."""
    t = len(abs_modelo)
    bloco = comprimento_bloco(t, h)
    n_blocos = math.ceil(t / bloco)
    rng = np.random.default_rng(semente)
    inicios = rng.integers(0, t, size=(n_boot, n_blocos))
    idx = ((inicios[:, :, None] + np.arange(bloco)) % t).reshape(n_boot, -1)[:, :t]
    razoes = abs_modelo[idx].sum(axis=1) / abs_ingenuo[idx].sum(axis=1)
    cauda = (1 - nivel) / 2
    return float(np.quantile(razoes, cauda)), float(np.quantile(razoes, 1 - cauda))


def diebold_mariano_hln(d: np.ndarray, h: int) -> tuple[float, float]:
    """DM com a correção de Harvey, Leybourne e Newbold (1997). Retorna (estatística, p bicaudal).

    d = perda do modelo − perda do ingênuo, em ordem de origem. Variância de longo prazo com
    autocovariâncias até h−1 (pesos uniformes, como em DM/HLN; se der ≤ 0, pesos de Bartlett).
    Estatística × √[(T + 1 − 2h + h(h−1)/T) / T], comparada com t de Student com T−1 gl.
    """
    d = np.asarray(d, float)
    t = len(d)
    if t < 2 * h + 2:
        raise ValueError(f"Poucas origens para DM com h = {h} (T = {t})")
    dc = d - d.mean()
    gamas = np.array([dc[k:] @ dc[: t - k] / t for k in range(h)])
    var_lp = gamas[0] + 2 * gamas[1:].sum()
    if var_lp <= 0:
        pesos = 1 - np.arange(1, h) / h
        var_lp = gamas[0] + 2 * (pesos * gamas[1:]).sum()
    if var_lp <= 0:
        return (0.0, 1.0) if np.allclose(d, 0) else (math.nan, math.nan)
    dm = d.mean() / math.sqrt(var_lp / t)
    estat = dm * math.sqrt((t + 1 - 2 * h + h * (h - 1) / t) / t)
    return float(estat), float(2 * stats.t.sf(abs(estat), t - 1))


def avaliar(erros: pd.DataFrame, referencia: str = REFERENCIA) -> pd.DataFrame:
    """Uma linha por (modelo, h): rMAE com IC 95%, DM-HLN e cobertura do intervalo de 95%."""
    ref = erros[erros["modelo"] == referencia]
    linhas = []
    for (modelo, h), g in erros[erros["modelo"] != referencia].groupby(["modelo", "h"], sort=False):
        par = g.merge(ref[ref["h"] == h], on=["origem", "h"], suffixes=("", "_ref")).sort_values("origem")
        abs_m = par["erro"].abs().to_numpy()
        abs_r = par["erro_ref"].abs().to_numpy()
        ic = ic_rmae_bootstrap(abs_m, abs_r, int(h))
        estat, p = diebold_mariano_hln(abs_m - abs_r, int(h))
        linhas.append({
            "modelo": modelo, "h": int(h), "T": len(par),
            "inicio": par["origem"].min(), "fim": par["origem"].max(),
            "mae_modelo": abs_m.mean(), "mae_ingenuo": abs_r.mean(), "unidade_mae": par["unidade"].iloc[0],
            "rmae": razao_mae(abs_m, abs_r), "rmae_ic95_inf": ic[0], "rmae_ic95_sup": ic[1],
            "dm_hln": estat, "p_valor": p,
            "cobertura95_modelo": _cobertura(par, ""), "cobertura95_ingenuo": _cobertura(par, "_ref"),
            "especificacoes": _resumo_especificacoes(par["especificacao"]),
        })
    return pd.DataFrame(linhas)


def com_veredito(avaliacao: pd.DataFrame, alfa: float = ALFA) -> pd.DataFrame:
    """p-valor BH sobre todos os DM juntos e veredito contra o ingênuo."""
    out = ajustar_bh(avaliacao, alfa)
    out["veredito"] = np.select(
        [out["significativo_bh"] & (out["rmae"] < 1), out["significativo_bh"] & (out["rmae"] > 1)],
        ["ganha do ingênuo", "perde do ingênuo"],
        "sem diferença significativa",
    )
    return out


def _cobertura(par: pd.DataFrame, sufixo: str) -> float:
    dentro = (par["real"] >= par[f"inf{sufixo}"]) & (par["real"] <= par[f"sup{sufixo}"])
    return float(dentro.mean())


def _resumo_especificacoes(especs: pd.Series) -> str:
    freq = especs.value_counts(normalize=True).head(3)
    return "; ".join(f"{e} {f:.0%}" for e, f in freq.items())
