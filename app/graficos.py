"""Gráficos Plotly do dashboard (funções puras: recebem DataFrames, devolvem figuras). Tema escuro."""

import pandas as pd
import plotly.graph_objects as go

COR_DOLAR = "#00FF7F"   # verde limão (destaque do tema)
COR_SOJA = "#FFC21A"    # amarelo
COR_MILHO = "#FF8C1A"   # laranja
COR_NEUTRA = "#8FB5A0"  # eixos, quebras, pontos não significativos
COR_SIG = "#00FF7F"
COR_TEXTO = "#E6EDF3"
COR_CHOQUE_ALTA = "#FF6B81"   # preço acima da banda
COR_CHOQUE_BAIXA = "#7DD3FC"  # preço abaixo da banda
COR_GRADE = "rgba(255,255,255,0.05)"  # única grade: horizontal e bem suave
LARGURA_LINHA = 2.5
FONTE = dict(color=COR_TEXTO, size=13)
LAYOUT = dict(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=FONTE,
    margin=dict(l=10, r=10, t=56, b=10), hovermode="x unified",
    hoverlabel=dict(bgcolor="#12261C", bordercolor="rgba(255,255,255,0.2)", font=dict(color=COR_TEXTO)),
    legend=dict(orientation="h", y=-0.18, font=dict(color=COR_TEXTO, size=13)),
    title=dict(font=dict(size=16, color="#F0F6FC")),
)


def _rgba(cor_hex: str, alfa: float) -> str:
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def _tema(fig: go.Figure, titulo: str, eixo_y: str, **extra) -> go.Figure:
    """Tema escuro: sem grade vertical, uma grade horizontal suave, eixos legíveis e com unidade."""
    fig.update_layout(**{**LAYOUT, **extra}, title_text=titulo, yaxis_title=eixo_y)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="rgba(255,255,255,0.25)", tickfont=FONTE)
    fig.update_yaxes(showgrid=True, gridcolor=COR_GRADE, zeroline=False, tickfont=FONTE,
                     title_font=dict(color=COR_NEUTRA, size=13))
    return fig


def linha(df: pd.DataFrame, titulo: str, unidade: str, cor: str, nome: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=df["data"], y=df["valor"], mode="lines", line=dict(color=cor, width=LARGURA_LINHA, shape="spline", smoothing=0.6),
                               name=nome, hovertemplate="%{y:,.2f} " + unidade))
    return _tema(fig, titulo, unidade, showlegend=False)


def marcar_quebras(fig: go.Figure, quebras: list[tuple[pd.Timestamp, str]]) -> go.Figure:
    for i, (data, descricao) in enumerate(quebras):
        x = data.strftime("%Y-%m-%d")
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper", line=dict(color=COR_NEUTRA, dash="dash", width=1.2))
        fig.add_annotation(x=x, y=1 - 0.08 * i, yref="paper", text=f"{data:%b/%Y}: {descricao}", showarrow=False,
                           xanchor="left", font=dict(size=12, color=COR_TEXTO))
    return fig


def correlacao_cruzada(g: pd.DataFrame, titulo: str) -> go.Figure:
    sig = g["p_bh"] < 0.05
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["defasagem"], y=g["ic95_sup"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g["defasagem"], y=g["ic95_inf"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_rgba(COR_DOLAR, 0.14), name="IC 95% (individual)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=g["defasagem"], y=g["estatistica"], mode="lines+markers", line=dict(color=COR_DOLAR, width=LARGURA_LINHA),
        marker=dict(size=10, color=[COR_SIG if s else "#0D1B15" for s in sig],
                    line=dict(color=[COR_SIG if s else COR_DOLAR for s in sig], width=2)),
        name="r (cheio = significativo após BH)", customdata=g[["p_valor", "p_bh"]],
        hovertemplate="k = %{x}: r = %{y:+.3f}<br>p = %{customdata[0]:.3f}; p BH = %{customdata[1]:.3f}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=COR_NEUTRA, width=1))
    _tema(fig, titulo, "r de Pearson (adimensional)", hovermode="closest")
    fig.update_xaxes(dtick=1, title_text="defasagem k (meses: dólar em t−k, preço em t)", title_font=dict(color=COR_NEUTRA, size=13))
    return fig


def previsao_ingenua(hist: pd.DataFrame, prev: pd.DataFrame, titulo: str, cor: str, meses_hist: int = 60) -> go.Figure:
    hist = hist.tail(meses_hist)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["data"], y=hist["valor"], mode="lines", line=dict(color=cor, width=LARGURA_LINHA, shape="spline", smoothing=0.6), name="Observado"))
    ligar = pd.concat([hist.tail(1).assign(inf=hist["valor"].iloc[-1], sup=hist["valor"].iloc[-1], previsto=hist["valor"].iloc[-1])[
        ["data", "previsto", "inf", "sup"]], prev[["data", "previsto", "inf", "sup"]]])
    fig.add_trace(go.Scatter(x=ligar["data"], y=ligar["sup"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ligar["data"], y=ligar["inf"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_rgba(cor, 0.18), name="Intervalo de 95%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ligar["data"], y=ligar["previsto"], mode="lines", line=dict(color=cor, dash="dash", width=LARGURA_LINHA),
                             name="Previsão ingênua (último valor)"))
    fig.add_trace(go.Scatter(x=prev["data"], y=prev["inf"], mode="lines", line=dict(width=0), showlegend=False,
                             customdata=prev[["previsto", "sup"]],
                             hovertemplate="IC 95%: %{y:,.1f} a %{customdata[1]:,.1f} US$/t<extra></extra>"))
    return _tema(fig, titulo, "US$/t")


def sparkline(df: pd.DataFrame, meses: int = 24) -> go.Figure:
    """Mini-gráfico de tendência dos últimos `meses` pontos: sem eixos, grade nem margens."""
    d = df.tail(meses)
    margem = (d["valor"].max() - d["valor"].min()) * 0.1 or 1
    fig = go.Figure(go.Scatter(x=d["data"], y=d["valor"], mode="lines", fill="tozeroy",
                               line=dict(color=COR_DOLAR, width=2, shape="spline", smoothing=0.6),
                               fillcolor=_rgba(COR_DOLAR, 0.12), hoverinfo="skip"))
    fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    fig.update_xaxes(visible=False, showgrid=False)
    fig.update_yaxes(visible=False, showgrid=False, range=[d["valor"].min() - margem, d["valor"].max() + margem])
    return fig


def linhas_suaves(series: list[tuple[str, pd.DataFrame, str]], titulo: str, eixo_y: str, escala: float = 1.0,
                  formato: str = "%{y:.2f}", faixa_y: tuple[float, float] | None = None) -> go.Figure:
    """Várias linhas suaves no tempo: (nome, DataFrame com data/valor, cor). `escala` multiplica o valor mostrado."""
    fig = go.Figure()
    for nome, df, cor in series:
        fig.add_trace(go.Scatter(x=df["data"], y=df["valor"] * escala, mode="lines", name=nome, hovertemplate=formato,
                                 line=dict(color=cor, width=LARGURA_LINHA, shape="spline", smoothing=0.6)))
    _tema(fig, titulo, eixo_y)
    if faixa_y:
        fig.update_yaxes(range=list(faixa_y))
        fig.add_hline(y=0, line=dict(color=COR_NEUTRA, width=1))
    return fig


def bollinger(bb: pd.DataFrame, titulo: str, unidade: str, cor: str) -> go.Figure:
    """Preço, média móvel e bandas; os meses fora da banda aparecem como "Choques"."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bb["data"], y=bb["superior"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=bb["data"], y=bb["inferior"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_rgba(cor, 0.13), name="Banda de ±2 desvios (12 meses)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=bb["data"], y=bb["media"], mode="lines", name="Média móvel de 12 meses",
                             line=dict(color=COR_TEXTO, width=1.4, dash="dot"), hovertemplate="%{y:,.2f} " + unidade))
    fig.add_trace(go.Scatter(x=bb["data"], y=bb["valor"], mode="lines", name="Preço",
                             line=dict(color=cor, width=LARGURA_LINHA), hovertemplate="%{y:,.2f} " + unidade))
    for sentido, cor_choque, nome in (("acima", COR_CHOQUE_ALTA, "Choque: acima da banda"),
                                      ("abaixo", COR_CHOQUE_BAIXA, "Choque: abaixo da banda")):
        c = bb[bb["sentido"] == sentido]
        fig.add_trace(go.Scatter(x=c["data"], y=c["valor"], mode="markers", name=nome, customdata=c[["inferior", "superior"]],
                                 marker=dict(size=11, symbol="diamond", color=cor_choque, line=dict(color="#0D1B15", width=1.5)),
                                 hovertemplate="%{y:,.2f} " + unidade + "<br>banda: %{customdata[0]:,.1f} a %{customdata[1]:,.1f}<extra></extra>"))
    return _tema(fig, titulo, unidade)
