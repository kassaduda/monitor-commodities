"""Backtest com janela deslizante e previsão ilustrativa a partir do último mês.

Origem = último mês da janela de treino. Para cada origem, o modelo recebe só os `janela`
meses que terminam nela (nada do futuro) e prevê os meses origem+1..origem+H. O erro é
calculado no nível (US$/t): real − previsto, com previsto = exp(previsão em log).
"""

import numpy as np
import pandas as pd

from monitor.previsao.modelos import ALFA_INTERVALO, Modelo

JANELA = 60
HORIZONTES = (1, 3, 6)
COLUNAS_ERROS = [
    "modelo", "especificacao", "origem", "alvo", "h", "previsto", "inf", "sup", "real", "erro", "unidade",
]


def serie_log(df: pd.DataFrame) -> pd.Series:
    """Log do preço indexado por mês; exige uma série, uma unidade, meses consecutivos e valor > 0."""
    if df["serie"].nunique() != 1 or df["unidade"].nunique() != 1:
        raise ValueError("Esperada uma única série com uma única unidade")
    s = df.sort_values("data").set_index("data")["valor"]
    esperado = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    if len(s) != len(esperado) or not (s.index == esperado).all():
        raise ValueError("A série precisa ter meses consecutivos, datados no 1º dia do mês")
    if (s <= 0).any():
        raise ValueError("Preços precisam ser positivos para usar o log")
    return np.log(s)


def backtest(
    df: pd.DataFrame,
    modelos: dict[str, Modelo],
    janela: int = JANELA,
    horizontes: tuple[int, ...] = HORIZONTES,
    alfa: float = ALFA_INTERVALO,
) -> pd.DataFrame:
    """Erros de previsão de cada modelo, por origem e horizonte, no nível da série."""
    log_y = serie_log(df)
    unidade = str(df["unidade"].iloc[0])
    h_max = max(horizontes)
    n = len(log_y)
    if n < janela + min(horizontes):
        raise ValueError(f"Série curta demais: {n} meses para janela de {janela}")
    linhas = []
    for fim in range(janela - 1, n - min(horizontes)):  # fim = posição da origem
        treino = log_y.iloc[fim - janela + 1 : fim + 1].copy()
        for nome, modelo in modelos.items():
            prev = modelo(treino, h_max, alfa)
            for h in horizontes:
                alvo = fim + h
                if alvo >= n:
                    continue
                previsto = float(np.exp(prev.media[h - 1]))
                real = float(np.exp(log_y.iloc[alvo]))
                linhas.append({
                    "modelo": nome, "especificacao": prev.especificacao,
                    "origem": log_y.index[fim], "alvo": log_y.index[alvo], "h": h,
                    "previsto": previsto,
                    "inf": float(np.exp(prev.inf[h - 1])), "sup": float(np.exp(prev.sup[h - 1])),
                    "real": real, "erro": real - previsto, "unidade": unidade,
                })
    return pd.DataFrame(linhas, columns=COLUNAS_ERROS)


def prever(
    df: pd.DataFrame, modelo: Modelo, nome: str, janela: int = JANELA,
    horizonte: int = max(HORIZONTES), alfa: float = ALFA_INTERVALO,
) -> pd.DataFrame:
    """Previsão ilustrativa a partir do último mês, com os últimos `janela` meses de treino."""
    log_y = serie_log(df)
    prev = modelo(log_y.iloc[-janela:].copy(), horizonte, alfa)
    datas = pd.date_range(log_y.index[-1] + pd.DateOffset(months=1), periods=horizonte, freq="MS")
    return pd.DataFrame({
        "data": datas, "serie": str(df["serie"].iloc[0]), "modelo": nome,
        "especificacao": prev.especificacao, "h": np.arange(1, horizonte + 1),
        "previsto": np.exp(prev.media), "inf": np.exp(prev.inf), "sup": np.exp(prev.sup),
        "nivel_intervalo": 1 - alfa, "unidade": str(df["unidade"].iloc[0]),
    })
