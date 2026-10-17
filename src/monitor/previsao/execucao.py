"""Casos do backtest (soja completa, soja desde 2021, milho) e previsão ilustrativa."""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from monitor import config
from monitor.analise.base import montar_base
from monitor.analise.mensal import recortar
from monitor.previsao.backtest import HORIZONTES, JANELA, backtest, prever
from monitor.previsao.metricas import avaliar, com_veredito
from monitor.previsao.modelos import MODELOS

VARIANTE_COMPLETA = "série completa"
VARIANTE_ROBUSTEZ = "desde jan/2021"
# Robustez da soja: só dados a partir da quebra de jan/2021 (69 meses até set/2026). Com a
# janela de 60 meses sobrariam 9 origens; a janela cai para 36 para haver ~30 origens.
INICIO_ROBUSTEZ_SOJA = pd.Timestamp("2021-01-01")
JANELA_ROBUSTEZ = 36


@dataclass(frozen=True)
class Caso:
    serie: str
    variante: str
    janela: int
    dados: pd.DataFrame  # US$/t, período em comum com o dólar
    cambio: pd.DataFrame  # PTAX média mensal (R$/US$), período em comum: exógena do ARIMAX


def casos(dir_processed: Path = config.DIR_PROCESSED) -> list[Caso]:
    base = montar_base(dir_processed)
    soja, milho = base.precos["wb_soja"]["US$/t"], base.precos["wb_milho"]["US$/t"]
    return [
        Caso("wb_soja", VARIANTE_COMPLETA, JANELA, soja, base.ptax),
        Caso("wb_soja", VARIANTE_ROBUSTEZ, JANELA_ROBUSTEZ, recortar(soja, INICIO_ROBUSTEZ_SOJA, base.fim), base.ptax),
        Caso("wb_milho", VARIANTE_COMPLETA, JANELA, milho, base.ptax),
    ]


def avaliar_caso(caso: Caso) -> pd.DataFrame:
    erros = backtest(caso.dados, MODELOS, janela=caso.janela, horizontes=HORIZONTES, cambio=caso.cambio)
    return avaliar(erros).assign(serie=caso.serie, variante=caso.variante, janela=caso.janela)


def avaliar_casos(lista: list[Caso], paralelo: bool = True) -> pd.DataFrame:
    """Avaliação de todos os casos, com p-valor BH sobre todos os testes DM juntos."""
    if paralelo:
        with ProcessPoolExecutor(max_workers=len(lista)) as pool:
            resultados = list(pool.map(avaliar_caso, lista))
    else:
        resultados = [avaliar_caso(c) for c in lista]
    return com_veredito(pd.concat(resultados, ignore_index=True))


def previsoes_ilustrativas(lista: list[Caso]) -> pd.DataFrame:
    """Previsão de todos os modelos a partir do último mês, só nos casos de série completa."""
    return pd.concat(
        [prever(c.dados, f, nome, janela=c.janela, cambio=c.cambio) for c in lista if c.variante == VARIANTE_COMPLETA
         for nome, f in MODELOS.items()],
        ignore_index=True,
    )
