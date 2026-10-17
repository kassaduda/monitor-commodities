"""Backtest com janela deslizante e previsão ilustrativa a partir do último mês.

Origem = último mês da janela de treino. Para cada origem, o modelo recebe só os `janela`
meses que terminam nela (nada do futuro) e prevê os meses origem+1..origem+H. O erro é
calculado no nível (US$/t): real − previsto, com previsto = exp(previsão em log).
"""

import numpy as np
import pandas as pd

from monitor.previsao.modelos import ALFA_INTERVALO, EXIGEM_EXOGENA, Modelo

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


def exog_defasado(log_x: pd.Series, indice_treino: pd.DatetimeIndex) -> pd.Series | None:
    """Dólar (log) defasado em 1 mês, indexado pelo mês que ele explica: janela de treino + mês seguinte à origem.

    O valor do mês t é o dólar de t−1; o do mês seguinte à origem T é o dólar de T (já conhecido em T).
    Nada depois de T entra. Devolve None se faltar dólar para algum desses meses.
    """
    meses = indice_treino.append(pd.DatetimeIndex([indice_treino[-1] + pd.DateOffset(months=1)]))
    dolar = meses - pd.DateOffset(months=1)
    if not dolar.isin(log_x.index).all():
        return None
    return pd.Series(log_x.loc[dolar].to_numpy(), index=meses)


def backtest(
    df: pd.DataFrame,
    modelos: dict[str, Modelo],
    janela: int = JANELA,
    horizontes: tuple[int, ...] = HORIZONTES,
    alfa: float = ALFA_INTERVALO,
    cambio: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Erros de previsão de cada modelo, por origem e horizonte, no nível da série.

    `cambio` (dólar mensal, R$/US$) alimenta os modelos com exógena (ARIMAX). Em cada origem o modelo recebe o dólar
    defasado em 1 mês (ver `exog_defasado`); sem dólar completo na janela, o ARIMAX pula aquela origem.
    """
    if cambio is None and EXIGEM_EXOGENA & set(modelos):
        raise ValueError(f"Modelos {sorted(EXIGEM_EXOGENA & set(modelos))} exigem o dólar (cambio)")
    log_x = serie_log(cambio) if cambio is not None else None
    log_y = serie_log(df)
    unidade = str(df["unidade"].iloc[0])
    h_max = max(horizontes)
    n = len(log_y)
    if n < janela + min(horizontes):
        raise ValueError(f"Série curta demais: {n} meses para janela de {janela}")
    linhas = []
    for fim in range(janela - 1, n - min(horizontes)):  # fim = posição da origem
        treino = log_y.iloc[fim - janela + 1 : fim + 1].copy()
        exog = exog_defasado(log_x, treino.index) if log_x is not None else None
        for nome, modelo in modelos.items():
            if exog is None and nome in EXIGEM_EXOGENA:
                continue  # sem dólar defasado completo nesta janela
            prev = modelo(treino, h_max, alfa, exog)
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
    horizonte: int = max(HORIZONTES), alfa: float = ALFA_INTERVALO, cambio: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Previsão ilustrativa a partir do último mês, com os últimos `janela` meses de treino (`cambio`: para o ARIMAX)."""
    log_y = serie_log(df)
    treino = log_y.iloc[-janela:].copy()
    exog = exog_defasado(serie_log(cambio), treino.index) if cambio is not None else None
    prev = modelo(treino, horizonte, alfa, exog)
    datas = pd.date_range(log_y.index[-1] + pd.DateOffset(months=1), periods=horizonte, freq="MS")
    return pd.DataFrame({
        "data": datas, "serie": str(df["serie"].iloc[0]), "modelo": nome,
        "especificacao": prev.especificacao, "h": np.arange(1, horizonte + 1),
        "previsto": np.exp(prev.media), "inf": np.exp(prev.inf), "sup": np.exp(prev.sup),
        "nivel_intervalo": 1 - alfa, "unidade": str(df["unidade"].iloc[0]),
    })
