"""Modelos univariados e parcimoniosos sobre o log do preço mensal.

Cada modelo recebe só a janela de treino (pd.Series em log, índice mensal) e devolve a
previsão de 1..H meses à frente com intervalo, também em log. A ordem/forma do modelo é
escolhida dentro da janela, por AICc, então nada de fora da janela entra na escolha.
Voltar ao nível com exp() dá a mediana prevista (adequada para erro absoluto).
"""

import warnings
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

ALFA_INTERVALO = 0.05  # intervalo de 95%
ORDEM_MAX_ARIMA = 2  # p, q ∈ {0, 1, 2}; d = 1


@dataclass(frozen=True)
class Previsao:
    media: np.ndarray  # log, h = 1..H
    inf: np.ndarray
    sup: np.ndarray
    especificacao: str  # ex.: "ARIMA(1,1,0)", "ETS(A,Ad,N)"


Modelo = Callable[[pd.Series, int, float], Previsao]


def ingenuo(log_y: pd.Series, horizonte: int, alfa: float = ALFA_INTERVALO) -> Previsao:
    """Repete o último valor. Intervalo de passeio aleatório: σ das variações da janela × √h."""
    _exigir_janela(log_y)
    h = np.arange(1, horizonte + 1)
    ultimo = float(log_y.iloc[-1])
    sigma = float(np.diff(log_y.to_numpy()).std(ddof=1))
    meia = stats.norm.ppf(1 - alfa / 2) * sigma * np.sqrt(h)
    media = np.full(horizonte, ultimo)
    return Previsao(media, media - meia, media + meia, "ingênuo")


def arima(log_y: pd.Series, horizonte: int, alfa: float = ALFA_INTERVALO) -> Previsao:
    """ARIMA(p,1,q) sem constante, p e q até 2, escolhido por AICc na janela.

    d = 1 fixo (preço em log com raiz unitária) e sem drift: uma tendência estimada em 60
    meses tende a ser extrapolada demais. ARIMA(0,1,0) é o próprio ingênuo e está na grade.
    """
    _exigir_janela(log_y)
    y = log_y.to_numpy()
    melhor, ordem = None, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de convergência/inversibilidade em ordens ruins
        for p in range(ORDEM_MAX_ARIMA + 1):
            for q in range(ORDEM_MAX_ARIMA + 1):
                try:
                    res = ARIMA(y, order=(p, 1, q), trend="n").fit()
                except (ValueError, np.linalg.LinAlgError):
                    continue
                if np.isfinite(res.aicc) and (melhor is None or res.aicc < melhor.aicc):
                    melhor, ordem = res, (p, 1, q)
        if melhor is None:
            raise RuntimeError("Nenhuma ordem ARIMA convergiu na janela")
        fc = melhor.get_forecast(horizonte)
        ic = np.asarray(fc.conf_int(alpha=alfa))
    return Previsao(np.asarray(fc.predicted_mean), ic[:, 0], ic[:, 1], f"ARIMA{ordem}".replace(" ", ""))


def ets(log_y: pd.Series, horizonte: int, alfa: float = ALFA_INTERVALO) -> Previsao:
    """ETS de erro aditivo, sem sazonalidade: (A,N,N) ou (A,Ad,N), escolhido por AICc na janela."""
    _exigir_janela(log_y)
    y = log_y.copy()
    y.index = pd.DatetimeIndex(y.index, freq="MS")
    melhor, nome = None, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for tendencia, rotulo in ((None, "ETS(A,N,N)"), ("add", "ETS(A,Ad,N)")):
            res = ETSModel(y, error="add", trend=tendencia, damped_trend=tendencia is not None).fit(disp=False)
            if np.isfinite(res.aicc) and (melhor is None or res.aicc < melhor.aicc):
                melhor, nome = res, rotulo
        if melhor is None:
            raise RuntimeError("Nenhuma forma ETS convergiu na janela")
        quadro = melhor.get_prediction(start=len(y), end=len(y) + horizonte - 1).summary_frame(alpha=alfa)
    return Previsao(
        quadro["mean"].to_numpy(), quadro["pi_lower"].to_numpy(), quadro["pi_upper"].to_numpy(), nome
    )


MODELOS: dict[str, Modelo] = {"ingênuo": ingenuo, "ARIMA": arima, "ETS": ets}
REFERENCIA = "ingênuo"


def _exigir_janela(log_y: pd.Series) -> None:
    if len(log_y) < 12 or not np.isfinite(log_y.to_numpy()).all():
        raise ValueError(f"Janela de treino inválida (n = {len(log_y)}; precisa de ≥ 12 valores finitos)")
