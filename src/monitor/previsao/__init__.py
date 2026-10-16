"""Previsão mensal ilustrativa de soja e milho (US$/t) e backtest contra o modelo ingênuo.

Camadas: `modelos` (ingênuo, ARIMA, ETS sobre o log do preço) -> `backtest` (janela
deslizante, sem vazamento) -> `metricas` (rMAE vs ingênuo com bootstrap em blocos, Diebold-Mariano-HLN).
Não é recomendação de investimento.
"""
