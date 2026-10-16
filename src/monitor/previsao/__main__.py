"""Backtest de ARIMA/ETS contra o ingênuo e previsão ilustrativa (etapa 6).

Uso: python -m monitor.previsao   (alguns minutos: um ajuste por origem, modelo e ordem)
"""

from monitor import config
from monitor.previsao.backtest import HORIZONTES
from monitor.previsao.execucao import avaliar_casos, casos, previsoes_ilustrativas


def main() -> None:
    lista = casos()
    aval = avaliar_casos(lista)

    print(f"Backtest: janela deslizante, horizontes {HORIZONTES} meses; erros em US$/t.")
    print("rMAE = MAE do modelo ÷ MAE do ingênuo (< 1 ganha). DM-HLN com perda absoluta; "
          f"p_bh = Benjamini-Hochberg sobre os {len(aval)} testes.")
    for (serie, variante), g in aval.groupby(["serie", "variante"], sort=False):
        print(f"\n{serie} [US$/t], {variante} (janela {g['janela'].iloc[0]} meses; "
              f"origens {g['inicio'].min():%Y-%m} a {g['fim'].max():%Y-%m})")
        print(g[["modelo", "h", "T", "rmae", "rmae_ic95_inf", "rmae_ic95_sup", "dm_hln", "p_valor", "p_bh",
                 "cobertura95_modelo", "veredito"]].round(3).to_string(index=False))
        print("  especificações mais escolhidas: " + " | ".join(
            f"{m}: {e}" for m, e in g.drop_duplicates("modelo")[["modelo", "especificacoes"]].itertuples(index=False)))

    prev = previsoes_ilustrativas(lista)
    prev = prev[prev["h"].isin(HORIZONTES)]
    print("\nPrevisão ilustrativa (intervalo de 95%), US$/t:")
    for c in (c for c in lista if c.serie in set(prev["serie"]) and c.variante == "série completa"):
        print(f"\n{c.serie} (último mês: {c.dados['data'].max():%Y-%m}, {c.dados['valor'].iloc[-1]:.1f} US$/t)")
        p = prev[prev["serie"] == c.serie]
        print(p.assign(mes=p["data"].dt.strftime("%Y-%m"))[
            ["modelo", "especificacao", "mes", "previsto", "inf", "sup"]].round(1).to_string(index=False))
    print(f"\nFonte: {config.FONTE_WB}. {config.AVISO_INVESTIMENTO}")


if __name__ == "__main__":
    main()
