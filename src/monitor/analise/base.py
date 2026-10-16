"""Monta a base mensal (dólar + soja + milho) no período em comum, em US$ e R$."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from monitor import config
from monitor.analise.conversao import converter_para_reais, tonelada_para_saca
from monitor.analise.correlacao import ResultadoCorrelacao, correlacao
from monitor.analise.mensal import media_mensal, periodo_comum, recortar
from monitor.analise.variacao import retorno_log
from monitor.armazenamento import caminho_parquet, ler_serie

COMMODITIES = tuple(config.WB_SERIES)  # ("wb_soja", "wb_milho")


@dataclass(frozen=True)
class BaseMensal:
    inicio: pd.Timestamp
    fim: pd.Timestamp
    ptax: pd.DataFrame  # média mensal, R$/US$
    precos: dict[str, dict[str, pd.DataFrame]]  # commodity -> unidade -> série

    def unidades(self, commodity: str) -> list[str]:
        return list(self.precos[commodity])


def montar_base(dir_processed: Path = config.DIR_PROCESSED) -> BaseMensal:
    ptax_mensal = media_mensal(ler_serie(caminho_parquet(dir_processed, "ptax_venda")))
    usd = {c: ler_serie(caminho_parquet(dir_processed, c)) for c in COMMODITIES}
    inicio, fim = periodo_comum(ptax_mensal, *usd.values())

    ptax = recortar(ptax_mensal, inicio, fim)
    precos: dict[str, dict[str, pd.DataFrame]] = {}
    for c, df in usd.items():
        usd_t = recortar(df, inicio, fim)
        brl_t = converter_para_reais(usd_t, ptax)
        precos[c] = {
            "US$/t": usd_t,
            "R$/t": brl_t,
            "US$/sc 60 kg": tonelada_para_saca(usd_t),
            "R$/sc 60 kg": tonelada_para_saca(brl_t),
        }
    return BaseMensal(inicio, fim, ptax, precos)


def correlacoes_de_retornos(base: BaseMensal) -> list[ResultadoCorrelacao]:
    """Retorno log mensal do dólar x retorno log mensal de cada commodity, em US$/t e em R$/t.

    A versão em R$/t contém um componente mecânico (preço em R$ = preço em US$ × câmbio);
    a versão em US$/t mede a relação entre o dólar e o preço internacional.
    """
    ret_ptax = retorno_log(base.ptax)
    return [
        correlacao(ret_ptax, retorno_log(base.precos[c][unidade]))
        for c in COMMODITIES
        for unidade in ("US$/t", "R$/t")
    ]
