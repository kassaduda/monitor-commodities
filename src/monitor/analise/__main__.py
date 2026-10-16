"""Resumo da análise no terminal: python -m monitor.analise"""

import pandas as pd

from monitor import config
from monitor.analise.base import COMMODITIES, correlacoes_de_retornos, montar_base
from monitor.analise.variacao import variacao_mensal


def _ultimo(df: pd.DataFrame) -> str:
    return f"{df['valor'].iloc[-1]:,.2f} {df['unidade'].iloc[0]}"


def main() -> None:
    base = montar_base()
    print(f"Período em comum: {base.inicio:%Y-%m} a {base.fim:%Y-%m} ({len(base.ptax)} meses)\n")
    print(f"Dólar ({config.BCB_SERIE_1_NOME}), média mensal de {base.fim:%m/%Y}: {_ultimo(base.ptax)}")
    var = variacao_mensal(base.ptax)
    print(f"  variação no mês: {var['valor'].iloc[-1]:+.2f} [{var['unidade'].iloc[0]}]\n")

    for c in COMMODITIES:
        print(f"{c} em {base.fim:%m/%Y}:")
        for unidade, df in base.precos[c].items():
            v = variacao_mensal(df)
            print(f"  {_ultimo(df):>22}   variação no mês {v['valor'].iloc[-1]:+6.2f} [{v['unidade'].iloc[0]}]")
        print()

    print("Correlação de retornos log mensais com o dólar:")
    for r in correlacoes_de_retornos(base):
        print(f"  {r.descricao()}")
    print("\nNota: em R$/t a correlação inclui um efeito mecânico (R$/t = US$/t × câmbio).")
    print(config.AVISO_INVESTIMENTO)


if __name__ == "__main__":
    main()
