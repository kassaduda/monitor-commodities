"""Gráficos Plotly do dashboard (funções puras: recebem DataFrames, devolvem figuras)."""

import pandas as pd
import plotly.graph_objects as go

COR_DOLAR = "#2a6f97"
COR_SOJA = "#b08900"
COR_MILHO = "#c2410c"
COR_NEUTRA = "#6b7280"
COR_SIG = "#15803d"
COR_IC = "rgba(107,114,128,0.20)"
COR_MODELO = "#2a6f97"
LAYOUT = dict(margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified", legend=dict(orientation="h", y=-0.15))


def linha(df: pd.DataFrame, titulo: str, unidade: str, cor: str, nome: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=df["data"], y=df["valor"], mode="lines", line=dict(color=cor, width=1.6), name=nome,
                               hovertemplate="%{y:,.2f} " + unidade))
    fig.update_layout(title=titulo, yaxis_title=unidade, xaxis_title=None, showlegend=False, **{**LAYOUT, "legend": {}})
    return fig


def marcar_quebras(fig: go.Figure, quebras: list[tuple[pd.Timestamp, str]]) -> go.Figure:
    for i, (data, descricao) in enumerate(quebras):
        x = data.strftime("%Y-%m-%d")
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper", line=dict(color=COR_NEUTRA, dash="dash", width=1))
        fig.add_annotation(x=x, y=1 - 0.07 * i, yref="paper", text=f"{data:%b/%Y}: {descricao}", showarrow=False,
                           xanchor="left", font=dict(size=10, color=COR_NEUTRA), bgcolor="rgba(255,255,255,0.0)")
    return fig


def correlacao_cruzada(g: pd.DataFrame, titulo: str) -> go.Figure:
    sig = g["p_bh"] < 0.05
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["defasagem"], y=g["ic95_sup"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g["defasagem"], y=g["ic95_inf"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=COR_IC, name="IC 95% (individual)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=g["defasagem"], y=g["estatistica"], mode="lines+markers", line=dict(color=COR_NEUTRA, width=1),
        marker=dict(size=9, color=[COR_SIG if s else COR_NEUTRA for s in sig],
                    symbol=["circle" if s else "circle-open" for s in sig]),
        name="r (cheio = significativo após BH)", customdata=g[["p_valor", "p_bh"]],
        hovertemplate="k = %{x}: r = %{y:+.3f}<br>p = %{customdata[0]:.3f}; p BH = %{customdata[1]:.3f}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=COR_NEUTRA, width=0.8))
    fig.update_layout(title=titulo, xaxis_title="defasagem k (meses: dólar em t−k, preço em t)",
                      yaxis_title="r de Pearson (adimensional)", **{**LAYOUT, "hovermode": "closest"})
    fig.update_xaxes(dtick=1)
    return fig


def previsao_ingenua(hist: pd.DataFrame, prev: pd.DataFrame, titulo: str, cor: str, meses_hist: int = 60) -> go.Figure:
    hist = hist.tail(meses_hist)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["data"], y=hist["valor"], mode="lines", line=dict(color=cor, width=1.6), name="Observado"))
    ligar = pd.concat([hist.tail(1).assign(inf=hist["valor"].iloc[-1], sup=hist["valor"].iloc[-1], previsto=hist["valor"].iloc[-1])[
        ["data", "previsto", "inf", "sup"]], prev[["data", "previsto", "inf", "sup"]]])
    fig.add_trace(go.Scatter(x=ligar["data"], y=ligar["sup"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ligar["data"], y=ligar["inf"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=COR_IC, name="Intervalo de 95%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ligar["data"], y=ligar["previsto"], mode="lines", line=dict(color=cor, dash="dash", width=1.6),
                             name="Previsão ingênua (último valor)"))
    fig.add_trace(go.Scatter(x=prev["data"], y=prev["inf"], mode="markers", marker=dict(size=0), showlegend=False,
                             customdata=prev[["previsto", "sup"]],
                             hovertemplate="IC 95%: %{y:,.1f} a %{customdata[1]:,.1f} US$/t<extra></extra>"))
    fig.update_layout(title=titulo, yaxis_title="US$/t", xaxis_title=None, **LAYOUT)
    return fig
