"""Monitor de Commodities: dólar x soja e milho. Só lê arquivos; não recalcula modelos nem baixa dados.

Uso: streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))  # permite `import carga` com `streamlit run` de qualquer pasta

import carga  # noqa: E402
import ui  # noqa: E402
import graficos  # noqa: E402
from monitor import config  # noqa: E402

ROTULO_SERIE = {"wb_soja": "Soja", "wb_milho": "Milho", "ptax_venda": "Dólar"}
COR = {"wb_soja": graficos.COR_SOJA, "wb_milho": graficos.COR_MILHO}
UNIDADES = ["US$/t", "R$/t", "R$/sc 60 kg"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def br(x: float, casas: int = 2) -> str:
    """Número no formato brasileiro (1.234,56)."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rotulo(serie: str) -> str:
    """Nome amigável a partir do identificador (aceita sufixos como _brl e _ret_log)."""
    return next(nome for chave, nome in ROTULO_SERIE.items() if serie.startswith(chave))


def mes_ano(d: pd.Timestamp) -> str:
    return f"{MESES[d.month - 1]}/{d.year}"


def aviso_fixo() -> None:
    ui.warning(f"**Previsão ilustrativa. {config.AVISO_INVESTIMENTO}**", icon="⚠️")


def aba_dolar() -> None:
    df = carga.dolar_diario()
    ui.subheader("Dólar (diário)")
    ui.caption(f"Série do BCB: **{config.BCB_SERIE_1_NOME}** (SGS 1). Unidade: **{config.BCB_SERIE_1_UNIDADE}**. "
               f"Fonte: {config.FONTE_BCB}.")
    ultimo = df.iloc[-1]
    c1, c2 = st.columns(2)
    ui.metric(c1, f"Último valor ({ultimo['data']:%d/%m/%Y})", f"R$ {br(ultimo['valor'], 4)}/US$")
    ui.metric(c2, "Observações", br(len(df), 0), help=f"Desde {df['data'].min():%d/%m/%Y}")
    desde = st.slider("Mostrar a partir de", df["data"].min().year, df["data"].max().year, df["data"].min().year)
    st.plotly_chart(graficos.linha(df[df["data"].dt.year >= desde], "Dólar americano (venda), R$/US$ — diário",
                                   config.BCB_SERIE_1_UNIDADE, graficos.COR_DOLAR, "PTAX venda"),
                    width="stretch")


def aba_precos() -> None:
    base = carga.base_mensal()
    ui.subheader("Soja e milho (mensal)")
    unidade = ui.radio("Unidade", UNIDADES, horizontal=True)
    ui.caption(
        "Preços **internacionais** do Banco Mundial (Pink Sheet), mensais, em US$/t nominais. "
        "**R$/t = US$/t × PTAX média do mês** (BCB); **R$/sc 60 kg = R$/t × 60/1000**. "
        f"Período em comum com o dólar: {mes_ano(base.inicio)} a {mes_ano(base.fim)}.")
    for c in ("wb_soja", "wb_milho"):
        df = base.precos[c][unidade]
        fig = graficos.linha(df, f"{ROTULO_SERIE[c]} — {unidade} (mensal)", unidade, COR[c], ROTULO_SERIE[c])
        if c == "wb_soja":
            graficos.marcar_quebras(fig, [(pd.Timestamp(d), desc) for d, desc in config.QUEBRAS_DEFINICAO[c]])
        st.plotly_chart(fig, width="stretch")
    ui.info("**Quebras de definição da soja.** Até dez/2020: *U.S. No. 2 yellow, CIF Rotterdam*. De jan/2021 a dez/2024: "
            "*U.S. Gulf Yellow Soybean #2, CIF Rotterdam*. Desde jan/2025: *U.S. Soybeans, FOB U.S. Gulf*. "
            "CIF inclui frete e seguro até a Europa; FOB Golfo não, então a passagem de jan/2025 pode criar um degrau "
            "que não é variação de mercado. As linhas tracejadas marcam jan/2021 e jan/2025. O milho não tem quebra registrada.")


def aba_relacao() -> None:
    ui.subheader("Dólar × soja e milho")
    ui.warning("**Análise exploratória.** Associação estatística, não causalidade. A previsão não usa o dólar.", icon="🔎")

    ui.markdown("#### Correlação de retornos mensais")
    cor = carga.resultado("correlacao").copy()
    cor["Commodity"] = cor["serie_y"].map(rotulo)
    cor["Preço em"] = cor["unidade_y"].str.extract(r"\((.*)\)")[0]
    cor["r"] = cor["r"].map(lambda v: br(v, 3))
    cor["IC 95%"] = [f"{br(a, 3)} a {br(b, 3)}" for a, b in zip(cor["ic95_inf"], cor["ic95_sup"])]
    cor["p"] = cor["p_valor"].map(lambda v: "< 0,0001" if v < 1e-4 else br(v, 4))
    cor = cor.rename(columns={"n": "n (meses)"})
    st.dataframe(cor[["Commodity", "Preço em", "r", "IC 95%", "p", "n (meses)"]], hide_index=True, width="stretch")
    ui.caption("Pearson sobre retornos log mensais do dólar (R$/US$) e de cada preço (não sobre níveis, que dão "
               "correlação espúria pela tendência). **Em R$/t o resultado é em boa parte mecânico**: o preço em R$ é o "
               "preço em US$ multiplicado pelo câmbio. Em US$/t a relação é negativa e modesta, no mesmo mês.")

    ui.markdown("#### O dólar antecipa o preço? (defasagem)")
    d = carga.resultado("defasagem")
    cc = d[d["teste"] == "correlação cruzada"]
    casos = list(cc.groupby(["variante", "serie_y"], sort=False).groups)
    rotulos = [f"{rotulo(s)} — {v}" for v, s in casos]
    escolha = ui.selectbox("Caso", rotulos)
    variante, serie = casos[rotulos.index(escolha)]
    g = cc[(cc["variante"] == variante) & (cc["serie_y"] == serie)]
    st.plotly_chart(graficos.correlacao_cruzada(g, f"Correlação cruzada: dólar em t−k × {rotulo(serie)} em t (US$/t)"),
                    width="stretch")
    n_sig = int(d[d["defasagem"] >= 1]["significativo_bh"].sum())
    ui.caption(f"Retornos log mensais, soja e milho em **US$/t** ({len(d)} testes ao todo; p ajustado por "
               "Benjamini-Hochberg sobre todos juntos). IC 95% individual, sem ajuste.")
    if n_sig == 0:
        ui.success("**Resultado:** nenhuma defasagem de 1 a 12 meses (correlação cruzada ou Granger) fica significativa "
                   "após o ajuste. **Não há evidência de que o dólar antecipe soja ou milho.** Só a relação no "
                   "mesmo mês (k = 0) aparece na soja, e ela é simultânea, não preditiva.")
    else:
        ui.error(f"{n_sig} teste(s) com defasagem ≥ 1 significativo(s) após o ajuste; leia com cautela (exploratório).")
    with ui.expander("Menor p ajustado por teste e caso (k ≥ 1)"):
        resumo = d[d["defasagem"] >= 1].groupby(["teste", "serie_y", "variante"], sort=False)["p_bh"].min().reset_index()
        resumo["serie_y"] = resumo["serie_y"].map(rotulo)
        resumo["p_bh"] = resumo["p_bh"].map(lambda v: br(v, 3))
        st.dataframe(resumo.rename(columns={"teste": "Teste", "serie_y": "Commodity", "variante": "Variante",
                                            "p_bh": "Menor p BH"}), hide_index=True, width="stretch")


def aba_previsao() -> None:
    bt = carga.resultado("backtest")
    ui.subheader("Backtest e previsão ilustrativa")
    aviso_fixo()
    ui.markdown("#### Os modelos ganham do ingênuo?")
    ui.caption("Janela deslizante (60 meses; 36 na checagem da soja desde 2021), previsão a 1, 3 e 6 meses, erros em US$/t "
               "fora da amostra. **rMAE = erro absoluto médio do modelo ÷ o do ingênuo (repete o último valor).** "
               "Abaixo de 1, o modelo erra menos. O veredito vem do teste de Diebold-Mariano (correção HLN) com ajuste "
               "Benjamini-Hochberg; os ICs da rMAE são individuais.")
    t = bt.copy()
    t["Commodity"] = t["serie"].map(ROTULO_SERIE)
    t["Período"] = t["variante"]
    t["Horizonte"] = t["h"].map(lambda h: f"{h} mês" if h == 1 else f"{h} meses")
    t["rMAE [IC 95%]"] = [f"{br(r)} [{br(a)}; {br(b)}]" for r, a, b in zip(t["rmae"], t["rmae_ic95_inf"], t["rmae_ic95_sup"])]
    t["p (BH)"] = t["p_bh"].map(lambda v: br(v))
    t["Veredito"] = t["veredito"]
    t["Origens"] = t["T"]
    st.dataframe(t.sort_values(["serie", "variante", "modelo", "h"], ascending=[False, True, True, True])[
        ["Commodity", "Período", "modelo", "Horizonte", "rMAE [IC 95%]", "p (BH)", "Veredito", "Origens"]]
        .rename(columns={"modelo": "Modelo"}), hide_index=True, width="stretch")

    contagem = bt["veredito"].value_counts()
    ganha, perde = int(contagem.get("ganha do ingênuo", 0)), int(contagem.get("perde do ingênuo", 0))
    if ganha == 0:
        extra = f" (e em {perde} erra significativamente mais)" if perde else ""
        ui.success(f"**Veredito honesto:** em nenhum dos {len(bt)} casos o ARIMA ou o ETS erra significativamente menos que "
                   f"o ingênuo{extra}. Na maioria, a rMAE fica um pouco acima de 1. Por isso a previsão exibida é a **ingênua**.")
    else:
        ui.info(f"{ganha} de {len(bt)} casos em que o modelo ganha do ingênuo; veja a tabela.")
    cob = bt[bt["variante"] == "série completa"]["cobertura95_ingenuo"]
    ui.caption(f"Cobertura dos intervalos de 95% do ingênuo na série completa: {cob.min():.0%} a {cob.max():.0%} das origens "
               "(abaixo do nominal: os intervalos tendem a subestimar a incerteza).")

    ui.markdown("#### Previsão ingênua com intervalo de 95%")
    base = carga.base_mensal()
    prev = carga.resultado("previsao")
    prev = prev[prev["modelo"] == "ingênuo"]
    for c in ("wb_soja", "wb_milho"):
        p = prev[prev["serie"] == c].sort_values("h")
        hist = base.precos[c]["US$/t"]
        st.plotly_chart(graficos.previsao_ingenua(hist, p, f"{ROTULO_SERIE[c]} — US$/t: último valor e intervalo de 95%", COR[c]),
                        width="stretch")
        sel = p[p["h"].isin([1, 3, 6])]
        ui.caption(f"{ROTULO_SERIE[c]}, último valor ({mes_ano(hist['data'].iloc[-1])}): {br(hist['valor'].iloc[-1], 1)} US$/t. " +
                   "; ".join(f"{mes_ano(r.data)}: {br(r.previsto, 1)} [{br(r.inf, 1)}; {br(r.sup, 1)}]" for r in sel.itertuples()))
    ui.caption("Previsão em **US$/t**; convertê-la para R$ exigiria também prever o dólar. O valor central é o último preço; "
               "o intervalo (passeio aleatório) mostra a faixa de incerteza. Ilustrativa.")


def aba_fontes() -> None:
    m = carga.meta()
    ui.subheader("Fontes, licenças e o que não está aqui")
    ui.markdown(f"""
**Dados publicados neste dashboard**

- **Dólar:** {config.FONTE_BCB}, série 1, *{config.BCB_SERIE_1_NOME}* (PTAX de fechamento, R$/US$). Dados públicos; fonte citada.
- **Soja e milho:** Banco Mundial, *World Bank Commodity Price Data (The Pink Sheet)*, mensal, US$/t nominais
  (edição de {m['edicao_pink_sheet']}).

> Contém dados do **Banco Mundial**, © The World Bank, licenciados sob
> [**CC BY 4.0**](https://creativecommons.org/licenses/by/4.0/). Os dados foram convertidos para R$ e para saca de
> 60 kg e usados em análises e previsões próprias; o Banco Mundial não endossa estes resultados.
> Catálogo: [datacatalog.worldbank.org/search/dataset/0038238](https://datacatalog.worldbank.org/search/dataset/0038238).

**Por que não há CEPEA nem CONAB aqui**

- **CEPEA/ESALQ** (soja Paranaguá e Paraná, milho ESALQ/B3): sem autorização formal por escrito para redistribuir as
  séries, **não as publicamos**, e o site não permite acesso automatizado por agentes de IA. Elas só entram em execução
  local, a partir de planilhas baixadas manualmente. Há um pedido de autorização em andamento.
- **CONAB** (preços por UF e safra): a licença de redistribuição dos dados **não é declarada**. Há um pedido de
  esclarecimento em andamento (Informa.BR). Enquanto não houver licença, os dados não são lidos nem redistribuídos.

**Metodologia, em resumo:** retornos log mensais; defasagem de 0 a 12 meses (correlação cruzada e Granger, com ajuste de
Benjamini-Hochberg); previsão ARIMA/ETS comparada ao ingênuo em backtest de janela deslizante. Detalhes no README do repositório.
""")


def rodape() -> None:
    m = carga.meta()
    st.divider()
    ui.caption(f"Fontes: {config.FONTE_BCB} (dólar, PTAX venda, R$/US$) · {config.FONTE_WB} (soja e milho, US$/t). "
               f"Pink Sheet de {m['edicao_pink_sheet']}; resultados gerados em {m['gerado_em']} para "
               f"{m['periodo_inicio']} a {m['periodo_fim']}. Previsão ilustrativa. {config.AVISO_INVESTIMENTO}")


def main() -> None:
    st.set_page_config(page_title="Monitor de Commodities", page_icon="🌾", layout="wide")
    ui.title("Monitor de Commodities: dólar × soja e milho")
    aviso_fixo()
    tabs = st.tabs(["Dólar", "Soja e milho", "Dólar × commodities", "Backtest e previsão", "Fontes e licenças"])
    for tab, aba in zip(tabs, (aba_dolar, aba_precos, aba_relacao, aba_previsao, aba_fontes)):
        with tab:
            aba()
    rodape()


main()
