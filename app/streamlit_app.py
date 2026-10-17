"""Monitor de Commodities: dólar x soja e milho. Só lê arquivos; não recalcula modelos nem baixa dados.

Uso: streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
# `app/` (carga, ui, graficos) e `src/` (pacote monitor) por caminho relativo à raiz: sem `pip install -e .`
for pasta in (RAIZ / "app", RAIZ / "src"):
    sys.path.insert(0, str(pasta))

import carga  # noqa: E402
import ui  # noqa: E402
import estilo  # noqa: E402
import graficos  # noqa: E402
from monitor import config  # noqa: E402
from monitor.analise.conversao import preco_na_porteira, reais_t_para_saca  # noqa: E402
from monitor.config import JANELA_BOLLINGER, JANELA_CORRELACAO, JANELA_VOLATILIDADE, K_BOLLINGER  # noqa: E402

ROTULO_SERIE = {"wb_soja": "Soja", "wb_milho": "Milho", "wb_trigo": "Trigo", "ptax_venda": "Dólar"}
COR = {"wb_soja": graficos.COR_SOJA, "wb_milho": graficos.COR_MILHO, "wb_trigo": graficos.COR_TRIGO}
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
    estilo.selo_aviso(f"Previsão ilustrativa. {config.AVISO_INVESTIMENTO}")


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


def resumo_choques(nome: str, bb: pd.DataFrame, quebras: list[pd.Timestamp]) -> tuple[str, str]:
    """(resumo, aviso): o aviso só existe se algum choque cair num mês de mudança de definição da série."""
    c = bb[bb["choque"]]
    acima, abaixo = int((c["sentido"] == "acima").sum()), int((c["sentido"] == "abaixo").sum())
    resumo = f"{nome}: {len(c)} choques em {len(bb)} meses ({acima} acima da banda, {abaixo} abaixo)."
    coincide = [mes_ano(d) for d in c["data"] if d in quebras]
    aviso = (f"**Atenção:** o choque de {', '.join(coincide)} coincide com uma mudança de definição da série de {nome.lower()}. "
             "Provável efeito da nova definição, não necessariamente um movimento de mercado." if coincide else "")
    return resumo, aviso


def aba_precos() -> None:
    base = carga.base_mensal()
    ui.subheader("Soja, milho e trigo (mensal)")
    unidade = ui.radio("Unidade", UNIDADES, horizontal=True)
    ui.caption(
        "Preços **internacionais** do Banco Mundial (Pink Sheet), mensais, em US$/t nominais. "
        "**R$/t = US$/t × PTAX média do mês** (BCB); **R$/sc 60 kg = R$/t × 60/1000**. "
        f"Período em comum com o dólar: {mes_ano(base.inicio)} a {mes_ano(base.fim)}.")
    bollinger = carga.resultado("bollinger")
    bandas = st.toggle(f"Bandas de Bollinger ({JANELA_BOLLINGER} meses, ±{K_BOLLINGER:.0f} desvios) e choques", value=True)
    for c in config.WB_SERIES:
        df = base.precos[c][unidade]
        titulo = f"{ROTULO_SERIE[c]} — {unidade} (mensal)"
        if bandas:
            bb = bollinger[(bollinger["serie"] == c) & (bollinger["unidade"] == unidade)].reset_index(drop=True)
            fig = graficos.bollinger(bb, titulo, unidade, COR[c])
        else:
            fig = graficos.linha(df, titulo, unidade, COR[c], ROTULO_SERIE[c])
        if c in config.QUEBRAS_DEFINICAO:
            graficos.marcar_quebras(fig, [(pd.Timestamp(d), desc) for d, desc in config.QUEBRAS_DEFINICAO[c]], vertical=True)
            fig.update_xaxes(range=[df["data"].min(), df["data"].max() + pd.DateOffset(months=2)])
        st.plotly_chart(fig, width="stretch")
        if bandas:
            resumo, aviso = resumo_choques(ROTULO_SERIE[c], bb, [pd.Timestamp(d) for d, _ in config.QUEBRAS_DEFINICAO.get(c, [])])
            ui.caption(resumo)
            if aviso:
                ui.warning(aviso, icon="⚠️")
    if bandas:
        ui.caption(f"**Choque** = mês em que o preço fecha fora de ±{K_BOLLINGER:.0f} desvios-padrão da média dos últimos "
                   f"{JANELA_BOLLINGER} meses (a janela inclui o próprio mês; desvio-padrão populacional, como no Bollinger clássico). "
                   "É uma marca descritiva de movimento fora do padrão recente, não um teste estatístico nem um sinal de compra ou venda.")
    ui.info("**Quebras de definição da soja.** Até dez/2020: *U.S. No. 2 yellow, CIF Rotterdam*. De jan/2021 a dez/2024: "
            "*U.S. Gulf Yellow Soybean #2, CIF Rotterdam*. Desde jan/2025: *U.S. Soybeans, FOB U.S. Gulf*. "
            "CIF inclui frete e seguro até a Europa; FOB Golfo não, então a passagem de jan/2025 pode criar um degrau "
            "que não é variação de mercado. **Trigo (HRW):** a definição muda por volta de jul/2020 (de *no. 1 HRW, proteína ordinária* "
            "para *no. 2 HRW*, ambos exportação no Golfo dos EUA). As linhas tracejadas marcam essas datas. O milho não tem quebra registrada.")


def aba_relacao() -> None:
    ui.subheader("Dólar × soja e milho")
    ui.warning("**Análise exploratória.** Associação estatística, não causalidade. A previsão não usa o dólar.", icon="🔎")

    ui.markdown("#### Correlação de retornos mensais")
    cor = carga.resultado("correlacao").copy()
    cor["Commodity"] = cor["serie_y"].map(rotulo)
    cor["Preço em"] = cor["unidade_y"].str.extract(r"\((.*)\)")[0]
    cor["IC 95%"] = [f"{br(a, 3)} a {br(b, 3)}" for a, b in zip(cor["ic95_inf"], cor["ic95_sup"])]
    cor["p"] = cor["p_valor"]
    cor = cor.rename(columns={"n": "n (meses)"})
    estilizada = (cor[["Commodity", "Preço em", "r", "IC 95%", "p", "n (meses)"]].style
                  .format({"r": lambda v: br(v, 3), "p": lambda v: "< 0,0001" if v < 1e-4 else br(v, 4)})
                  .map(estilo.colorir_sinal, subset=["r"]))
    st.dataframe(estilizada, hide_index=True, width="stretch")
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
        resumo = resumo.rename(columns={"teste": "Teste", "serie_y": "Commodity", "variante": "Variante", "p_bh": "Menor p BH"})
        st.dataframe(resumo.style.format({"Menor p BH": lambda v: br(v, 3)}).map(estilo.colorir_p_bh, subset=["Menor p BH"]),
                     hide_index=True, width="stretch")

    secao_risco()


def secao_risco() -> None:
    corr = carga.resultado("correlacao_deslizante")
    vol = carga.resultado("volatilidade")
    r = {"correlacao": {c: g for c, g in corr.groupby("commodity", sort=False)},
         "volatilidade": {k: g for k, g in vol.groupby("ativo", sort=False)}}
    cores = COR
    ui.markdown("#### A relação muda com o tempo? (correlação deslizante)")
    fig = graficos.linhas_suaves(
        [(f"Dólar × {ROTULO_SERIE[c]}", r["correlacao"][c], cores[c]) for c in r["correlacao"]],
        f"Correlação deslizante de {JANELA_CORRELACAO} meses entre os retornos do dólar e dos preços (US$/t)",
        "r de Pearson (adimensional)", formato="r = %{y:+.2f}", faixa_y=(-1, 1))
    graficos.marcar_quebras(fig, [(pd.Timestamp(d), "mudança de definição da soja") for d, _ in config.QUEBRAS_DEFINICAO["wb_soja"]])
    st.plotly_chart(fig, width="stretch")
    ui.caption(" ".join(
        f"{ROTULO_SERIE[c]}: variou de {br(d['valor'].min(), 2)} a {br(d['valor'].max(), 2)}; último valor {br(d['valor'].iloc[-1], 2)}."
        for c, d in r["correlacao"].items()) +
        f" Cada ponto usa os {JANELA_CORRELACAO} meses que terminam nele, então janelas vizinhas compartilham quase todos os dados "
        "e a curva é suave por construção. As janelas que contêm jan/2021 ou jan/2025 (soja) ou jul/2020 (trigo) incluem um retorno entre duas definições da série.")

    ui.markdown("#### O risco do câmbio acompanha o risco da commodity? (volatilidade móvel)")
    fig = graficos.linhas_suaves(
        [(ROTULO_SERIE[k], d, graficos.COR_DOLAR if k == "ptax_venda" else cores[k]) for k, d in r["volatilidade"].items()],
        f"Volatilidade móvel de {JANELA_VOLATILIDADE} meses: desvio-padrão do retorno log mensal",
        "desvio-padrão do retorno log mensal (%)", escala=100, formato="%{y:.1f}%")
    st.plotly_chart(fig, width="stretch")
    ui.caption(" ".join(f"{ROTULO_SERIE[k]}: {br(d['valor'].iloc[-1] * 100, 1)}% no último mês (mediana {br(d['valor'].median() * 100, 1)}%)."
                        for k, d in r["volatilidade"].items()) +
               f" Desvio-padrão amostral dos {JANELA_VOLATILIDADE} retornos mensais que terminam em cada mês; soja e milho em US$/t. "
               "Comparação visual e exploratória: janelas sobrepostas são autocorrelacionadas, então não há teste de significância aqui.")


def grafico_razao() -> None:
    """Razão soja/milho (tabela `resultados_razao_soja_milho`) com a referência em 2,5."""
    r = carga.resultado("razao")
    ref = config.REFERENCIA_RAZAO_SOJA_MILHO
    fig = graficos.razao(r, ref, "Razão soja/milho: preço da soja (US$/t) ÷ preço do milho (US$/t)")
    graficos.marcar_quebras(fig, [(pd.Timestamp(d), "mudança de definição da soja") for d, _ in config.QUEBRAS_DEFINICAO["wb_soja"]],
                            vertical=True)
    fig.update_xaxes(range=[r["data"].min(), r["data"].max() + pd.DateOffset(months=2)])
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch")
    ui.caption(f"Último valor ({mes_ano(r['data'].iloc[-1])}): {br(r['valor'].iloc[-1], 2)}; no período, de {br(r['valor'].min(), 2)} "
               f"a {br(r['valor'].max(), 2)}. A linha tracejada em {br(ref, 1)} é uma **regra prática de mercado**: razões acima "
               "dela costumam favorecer o plantio de soja em relação ao milho. É uma referência visual, não um limiar estimado com "
               "estes dados.")
    ui.warning("**Cuidado com a leitura antes de 2025.** Até dez/2024 o Pink Sheet cota a soja em *CIF Rotterdam* (inclui frete e "
               "seguro até a Europa) e o milho em *FOB Golfo dos EUA*, então a razão desse período fica acima da comparação "
               "entre preços de mesma base. Desde jan/2025 ambos são FOB Golfo, e há ainda a mudança de definição da soja em "
               "jan/2021. Os preços são de exportação, não de campo.", icon="⚠️")


def simulador_stress() -> None:
    """Painel lateral: preço da soja "na porteira" para um dólar, um prêmio de porto e um frete simulados.

    R$/t = (US$/t + prêmio) × dólar − frete interno; R$/sc = R$/t × 60/1000. Premissas do usuário, ceteris paribus.
    """
    base = carga.base_mensal()
    soja_usd = float(base.precos["wb_soja"]["US$/t"]["valor"].iloc[-1])
    mes = base.precos["wb_soja"]["US$/t"]["data"].iloc[-1]
    cambio_mes = round(float(base.ptax["valor"].iloc[-1]), 2)  # mesmo dólar do slider: sem "-0,00" no ponto de partida
    sb = st.sidebar
    sb.markdown("### Simulador de Stress Cambial")
    simulado = ui.slider("Dólar simulado (R$/US$)", 4.0, 7.0, cambio_mes, 0.01, destino=sb)
    premio = ui.slider("Prêmio de Porto (US$/t)", 0, 100, 20, 1, destino=sb)
    frete = ui.slider("Frete Interno (R$/t)", 0, 500, 150, 5, destino=sb)
    reais_t = preco_na_porteira(soja_usd, premio, simulado, frete)
    reais_t_ref = preco_na_porteira(soja_usd, premio, cambio_mes, frete)
    sc, sc_ref = reais_t_para_saca(reais_t), reais_t_para_saca(reais_t_ref)
    ui.metric(sb, "Soja na porteira, R$/sc 60 kg", f"R$ {br(sc)}/sc",
              delta=f"{sc - sc_ref:+.2f} R$/sc ({(sc / sc_ref - 1) * 100:+.1f}%)".replace(".", ","), delta_color="off")
    ui.metric(sb, "Soja na porteira, R$/t", f"R$ {br(reais_t, 0)}/t")
    ui.caption("**R$/t na porteira = (soja em US$/t + prêmio) × dólar − frete interno**; R$/sc = R$/t × 60/1000. "
               f"Variação sobre o mesmo cenário com o dólar de referência: PTAX média de {mes_ano(mes)}, R$ {br(cambio_mes, 2)}/US$ (BCB). "
               f"Soja de {mes_ano(mes)}: {br(soja_usd, 1)} US$/t (Banco Mundial).", destino=sb)
    ui.caption("Prêmio e frete são **premissas suas**: os valores iniciais (20 US$/t e R$ 150/t) são ilustrativos, não dados de mercado. "
               "O resultado não inclui impostos, armazenagem nem outros custos, e o preço realmente recebido varia por região.", destino=sb)
    ui.info("Cálculo mecânico isolado (Ceteris Paribus). Não prevê a reação real do mercado.", destino=sb)


def nomes_modelos(bt: pd.DataFrame, conj: str = "ou") -> str:
    """"ARIMA, ARIMAX ou ETS", a partir dos modelos que estão na tabela do backtest."""
    nomes = sorted(bt["modelo"].unique())
    return f"{', '.join(nomes[:-1])} {conj} {nomes[-1]}" if len(nomes) > 1 else nomes[0]


def aba_previsao() -> None:
    bt = carga.resultado("backtest")
    ui.subheader("Backtest e previsão ingênua")
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
    t = t.sort_values(["serie", "variante", "modelo", "h"], ascending=[False, True, True, True])
    rmae = t["rmae"].to_numpy()
    tabela = t[["Commodity", "Período", "modelo", "Horizonte", "rMAE [IC 95%]", "p (BH)", "Veredito", "Origens"]].rename(
        columns={"modelo": "Modelo"})
    estilizada = (tabela.style.apply(lambda d: estilo.colorir_rmae(d, rmae), axis=None)
                  .map(estilo.colorir_veredito, subset=["Veredito"]))
    st.dataframe(estilizada, hide_index=True, width="stretch", column_config={
        "Commodity": st.column_config.TextColumn(width="small"),
        "Período": st.column_config.TextColumn(width="small"),
        "Modelo": st.column_config.TextColumn(width="small"),
        "Horizonte": st.column_config.TextColumn(width="small"),
        "rMAE [IC 95%]": st.column_config.TextColumn(width="medium"),
        "p (BH)": st.column_config.TextColumn(width="small"),
        "Veredito": st.column_config.TextColumn(width="medium"),
        "Origens": st.column_config.NumberColumn(width="small"),
    })
    ui.caption("Cor da rMAE: verde abaixo de 1 (o modelo erra menos), vermelho acima de 1. Só conta como ganho ou perda "
               "quando o veredito é significativo.")

    contagem = bt["veredito"].value_counts()
    ganha, perde = int(contagem.get("ganha do ingênuo", 0)), int(contagem.get("perde do ingênuo", 0))
    if ganha == 0:
        extra = f" (e em {perde} erra significativamente mais)" if perde else ""
        acima = int((bt["rmae"] > 1).sum())
        ui.success(f"**Veredito honesto:** em nenhum dos {len(bt)} casos {nomes_modelos(bt)} erra significativamente menos que "
                   f"o ingênuo{extra}. Em {acima} dos {len(bt)} a rMAE fica acima de 1. Por isso a previsão exibida é a **ingênua**.")
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


def rodape() -> None:
    """Créditos obrigatórios (BCB e Banco Mundial, CC BY 4.0), em todas as abas."""
    m = carga.meta()
    ui.html(
        '<div class="rodape-fontes">'
        f"Fontes: <strong>{config.FONTE_BCB}</strong>, série 1, {config.BCB_SERIE_1_NOME} (PTAX de fechamento, R$/US$) · "
        "<strong>Banco Mundial</strong>, World Bank Commodity Price Data (The Pink Sheet), mensal, US$/t nominais, licença "
        '<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a> '
        '(<a href="https://datacatalog.worldbank.org/search/dataset/0038238" target="_blank">catálogo</a>).<br>'
        "Dados convertidos para R$ e saca de 60 kg e analisados por este projeto; o Banco Mundial não endossa os resultados. "
        f"Pink Sheet de {m['edicao_pink_sheet']}; resultados gerados em {m['gerado_em']} para {m['periodo_inicio']} a {m['periodo_fim']}."
        "</div>")


def hero_e_kpis() -> None:
    """Conclusão primeiro, de cima para baixo: título, três KPIs lado a lado e os dois gráficos principais em largura total.

    Tudo lido dos arquivos do pipeline; nada é calculado aqui.
    """
    base = carga.base_mensal()
    d = carga.resultado("defasagem")
    bt = carga.resultado("backtest")
    n_sig = int(d[d["defasagem"] >= 1]["significativo_bh"].sum())
    desfecho = "Sem evidência" if n_sig == 0 else f"{n_sig} teste(s) significativo(s)"
    ui.title(f"O dólar antecipa o preço da soja e do milho? {desfecho} em {len(base.ptax)} meses de dados")
    ui.caption(f"Dólar (BCB) e preços internacionais (Banco Mundial), {mes_ano(base.inicio)} a {mes_ano(base.fim)}.")

    with st.container(key="kpis"):
        cartoes_kpi(base, bt, st.columns(3))
    grafico_principal()
    grafico_razao()


def grafico_principal() -> None:
    """Soja em US$/t com média móvel, bandas de Bollinger e choques (tabela `resultados_bollinger`)."""
    bb = carga.resultado("bollinger")
    bb = bb[(bb["serie"] == "wb_soja") & (bb["unidade"] == "US$/t")].reset_index(drop=True)
    fig = graficos.bollinger(bb, "Soja — US$/t: preço, média móvel de 12 meses e bandas de ±2 desvios", "US$/t", COR["wb_soja"])
    graficos.marcar_quebras(fig, [(pd.Timestamp(d), desc) for d, desc in config.QUEBRAS_DEFINICAO["wb_soja"]], vertical=True)
    fig.update_xaxes(range=[bb["data"].min(), bb["data"].max() + pd.DateOffset(months=2)])
    fig.update_layout(height=470)
    st.plotly_chart(fig, width="stretch")
    resumo, aviso = resumo_choques("Soja", bb, [pd.Timestamp(d) for d, _ in config.QUEBRAS_DEFINICAO["wb_soja"]])
    ui.caption(f"{resumo} {aviso}")


def cartoes_kpi(base, bt: pd.DataFrame, colunas) -> None:
    dolar = carga.dolar_diario().iloc[-1]
    soja = base.precos["wb_soja"]["US$/t"].iloc[-1]
    ganha = int((bt["veredito"] == "ganha do ingênuo").sum())
    with colunas[0], st.container(key="kpi_dolar"):
        ui.metric(st, "Último dólar", f"R$ {br(dolar['valor'], 4)}/US$",
                  delta=f"SGS BCB · {dolar['data']:%d/%m/%Y}", delta_color="off", delta_arrow="off")
        st.plotly_chart(graficos.sparkline(base.ptax, 12), width="stretch", config={"staticPlot": True})
        ui.caption("Últimos 12 meses (média mensal)")
    with colunas[1], st.container(key="kpi_soja"):
        ui.metric(st, "Última soja", f"{br(soja['valor'], 1)} US$/t",
                  delta=f"Banco Mundial · {mes_ano(soja['data'])}", delta_color="off", delta_arrow="off")
        st.plotly_chart(graficos.sparkline(base.precos["wb_soja"]["US$/t"], 12), width="stretch", config={"staticPlot": True})
        ui.caption("Últimos 12 meses (US$/t)")
    with colunas[2], st.container(key="kpi_veredito"):
        ui.metric(st, "Veredito do backtest",
                  "Nenhum ganha do ingênuo" if ganha == 0 else f"{ganha} de {len(bt)} casos ganham do ingênuo",
                  delta=f"{nomes_modelos(bt, 'e')} × ingênuo", delta_color="off", delta_arrow="off",
                  help=f"{nomes_modelos(bt, 'e')} contra repetir o último valor, em {len(bt)} casos (modelo × horizonte × série).")


def main() -> None:
    st.set_page_config(page_title="Monitor de Commodities", page_icon="🌾", layout="wide", initial_sidebar_state="expanded")
    estilo.inject_custom_css()
    aviso_fixo()
    hero_e_kpis()
    simulador_stress()
    tabs = st.tabs(["Dólar", "Soja, milho e trigo", "Dólar × commodities", "Backtest e previsão"])
    for tab, aba in zip(tabs, (aba_dolar, aba_precos, aba_relacao, aba_previsao)):
        with tab:
            aba()
    rodape()


main()
