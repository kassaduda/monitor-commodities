"""Correlação de Pearson entre duas séries no mesmo calendário, com p-valor e IC de 95%."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ResultadoCorrelacao:
    serie_x: str
    unidade_x: str
    serie_y: str
    unidade_y: str
    r: float
    p_valor: float
    ic95: tuple[float, float]
    n: int
    inicio: pd.Timestamp
    fim: pd.Timestamp

    def descricao(self) -> str:
        return (
            f"r = {self.r:+.3f} (IC 95%: {self.ic95[0]:+.3f} a {self.ic95[1]:+.3f}; p = {self.p_valor:.3g}; "
            f"n = {self.n}; {self.inicio:%Y-%m} a {self.fim:%Y-%m}) entre "
            f"{self.serie_x} [{self.unidade_x}] e {self.serie_y} [{self.unidade_y}]"
        )


def correlacao(x: pd.DataFrame, y: pd.DataFrame) -> ResultadoCorrelacao:
    """Pearson nas datas presentes nas duas séries (r adimensional)."""
    from scipy import stats  # import tardio: o dashboard lê a base sem precisar do scipy

    juntos = x[["data", "valor"]].merge(y[["data", "valor"]], on="data", suffixes=("_x", "_y"))
    if len(juntos) < 3:
        raise ValueError(f"São necessárias ao menos 3 datas em comum (há {len(juntos)})")
    res = stats.pearsonr(juntos["valor_x"], juntos["valor_y"])
    ic = res.confidence_interval(0.95)
    return ResultadoCorrelacao(
        serie_x=str(x["serie"].iloc[0]),
        unidade_x=str(x["unidade"].iloc[0]),
        serie_y=str(y["serie"].iloc[0]),
        unidade_y=str(y["unidade"].iloc[0]),
        r=float(res.statistic),
        p_valor=float(res.pvalue),
        ic95=(float(ic.low), float(ic.high)),
        n=len(juntos),
        inicio=juntos["data"].min(),
        fim=juntos["data"].max(),
    )
