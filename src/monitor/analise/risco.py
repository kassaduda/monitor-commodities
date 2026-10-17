"""Risco no tempo: correlação deslizante, volatilidade móvel e bandas de Bollinger (só pandas).

Estatísticas descritivas sobre séries mensais já processadas; não são testes de hipótese.
Janelas em número de meses (a série é mensal e consecutiva).
"""

import pandas as pd

from monitor.analise.variacao import _exigir_meses_consecutivos
from monitor.config import JANELA_BOLLINGER, JANELA_CORRELACAO, JANELA_VOLATILIDADE, K_BOLLINGER
from monitor.limpeza import COLUNAS_PADRAO

UNIDADE_R = "r de Pearson (adimensional)"


def correlacao_deslizante(x: pd.DataFrame, y: pd.DataFrame, janela: int = JANELA_CORRELACAO) -> pd.DataFrame:
    """Pearson entre x e y nos `janela` meses que terminam em cada data (a data é o último mês da janela)."""
    juntos = x[["data", "valor"]].merge(y[["data", "valor"]], on="data", suffixes=("_x", "_y")).sort_values("data", ignore_index=True)
    if len(juntos) < janela:
        raise ValueError(f"Série curta demais para janela de {janela} meses (n = {len(juntos)})")
    _exigir_meses_consecutivos(juntos)
    r = juntos["valor_x"].rolling(janela).corr(juntos["valor_y"])
    out = pd.DataFrame({"data": juntos["data"], "valor": r}).dropna(subset=["valor"]).reset_index(drop=True)
    out["serie"] = f"corr_{janela}m_{x['serie'].iloc[0]}_{y['serie'].iloc[0]}"
    out["unidade"] = f"{UNIDADE_R}, janela de {janela} meses"
    out["fonte"] = f"{x['fonte'].iloc[0]}; {y['fonte'].iloc[0]}"
    return out[COLUNAS_PADRAO]


def volatilidade_movel(retornos: pd.DataFrame, janela: int = JANELA_VOLATILIDADE) -> pd.DataFrame:
    """Desvio-padrão amostral (ddof = 1) dos retornos nos `janela` meses que terminam em cada data."""
    if retornos["unidade"].nunique() != 1:
        raise ValueError("Esperada uma única unidade")
    d = retornos.sort_values("data", ignore_index=True)
    _exigir_meses_consecutivos(d)
    out = d.copy()
    out["valor"] = d["valor"].rolling(janela).std()
    out["serie"] = d["serie"] + f"_vol{janela}m"
    out["unidade"] = f"desvio-padrão em {janela} meses de {d['unidade'].iloc[0]}"
    return out.dropna(subset=["valor"]).reset_index(drop=True)[COLUNAS_PADRAO]


def bandas_bollinger(df: pd.DataFrame, janela: int = JANELA_BOLLINGER, k: float = K_BOLLINGER) -> pd.DataFrame:
    """Média móvel e bandas ± k desvios-padrão (população, ddof = 0, como no Bollinger clássico).

    A janela inclui o próprio mês. "Choque": o valor do mês fica fora das bandas.
    Colunas: data, valor, media, inferior, superior, choque (bool) e sentido ("acima", "abaixo" ou "").
    """
    if df["unidade"].nunique() != 1:
        raise ValueError("Esperada uma única unidade")
    d = df.sort_values("data", ignore_index=True)
    _exigir_meses_consecutivos(d)
    v = d["valor"]
    media = v.rolling(janela).mean()
    desvio = v.rolling(janela).std(ddof=0)
    out = pd.DataFrame({"data": d["data"], "valor": v, "media": media,
                        "inferior": media - k * desvio, "superior": media + k * desvio})
    out = out.dropna(subset=["media"]).reset_index(drop=True)
    out["sentido"] = ""
    out.loc[out["valor"] > out["superior"], "sentido"] = "acima"
    out.loc[out["valor"] < out["inferior"], "sentido"] = "abaixo"
    out["choque"] = out["sentido"] != ""
    return out
