"""Estilo do dashboard (cockpit agro, verde escuro): CSS global e tabelas com formatação condicional.

Só CSS e `pandas.Styler` (sem scipy/statsmodels). O layout é `wide` e o Streamlit controla a largura:
nenhum CSS aqui fixa largura de página (sem `max-width`, `100vw` ou margens negativas).
"""

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from monitor import config

LIMAO, VERDE_SUAVE, VERMELHO, AMARELO = "#00FF7F", "#8FB5A0", "#FF6B81", "#FFC21A"
TEXTO_SECUNDARIO = "#B7CCBF"
FUNDO_CARTAO = "#12261C"
FUNDO_KPI = "rgba(11, 20, 16, 0.72)"  # #0B1410 translúcido, para a foto aparecer por trás
CINZA_RODAPE = "#7C8F84"

# Película escura sobre a foto: a imagem dá clima, mas não disputa com os números.
OVERLAY = "linear-gradient(rgba(10, 22, 18, 0.85), rgba(10, 22, 18, 0.95))"


@st.cache_data
def imagem_base64(caminho: str) -> str:
    """Conteúdo do arquivo em base64 ("" se o arquivo não existir)."""
    arquivo = Path(caminho)
    return base64.b64encode(arquivo.read_bytes()).decode("ascii") if arquivo.exists() else ""


def css_fundo(caminho: Path = config.ARQUIVO_FUNDO) -> str:
    """CSS do fundo da página: imagem local (data URI) com `cover` e o overlay escuro por cima."""
    b64 = imagem_base64(str(caminho))
    if not b64:
        return ""
    return (f'.stApp {{ background: {OVERLAY}, url("data:image/jpeg;base64,{b64}") center / cover no-repeat fixed; }}')


CSS = f"""
<style>
/* o cabeçalho do Streamlit tem ~3,75rem; sem esse respiro o selo do aviso fica escondido atrás dele */
.block-container {{ padding-top: 4.5rem; }}
h1 {{ font-size: 2.6rem; font-weight: 800; line-height: 1.15; letter-spacing: -0.02em; }}
h2, h3, h4 {{ letter-spacing: -0.005em; }}

/* Selo do aviso de previsão: discreto, fundo verde escuro e texto âmbar */
.aviso-previsao {{
  display: inline-block; margin: 0 0 1rem 0; padding: 6px 14px; border-radius: 999px;
  background: {FUNDO_CARTAO}; border: 1px solid rgba(255, 194, 26, 0.35);
  color: {AMARELO}; font-size: 0.9rem; font-weight: 600; letter-spacing: 0.01em;
}}

/* Cartões de KPI: fundo bem escuro e brilho neon discreto */
[data-testid="stMetric"], .st-key-kpi_dolar, .st-key-kpi_soja, .st-key-kpi_veredito {{
  background: {FUNDO_KPI}; border: 1px solid rgba(0, 255, 127, 0.3); border-radius: 10px;
  -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
  box-shadow: 0 4px 15px rgba(0, 255, 127, 0.15);
}}
[data-testid="stMetric"] {{ padding: 16px 18px; }}
/* nos cartões do topo, o st.metric fica dentro do cartão (que leva o brilho): sem moldura própria */
.st-key-kpi_dolar, .st-key-kpi_soja, .st-key-kpi_veredito {{ padding: 6px 10px 10px; margin-bottom: 0.9rem; }}
.st-key-kpi_dolar [data-testid="stMetric"], .st-key-kpi_soja [data-testid="stMetric"],
.st-key-kpi_veredito [data-testid="stMetric"] {{ background: transparent; border: 0; box-shadow: none; }}
.st-key-kpi_dolar [data-testid="stCaptionContainer"], .st-key-kpi_soja [data-testid="stCaptionContainer"] {{ padding: 0 18px; }}
[data-testid="stMetricLabel"] p {{
  color: {VERDE_SUAVE}; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
}}
[data-testid="stMetricValue"] {{ font-size: 1.8rem; font-weight: 700; line-height: 1.15; color: #FFFFFF; }}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div, [data-testid="stMetricValue"] p {{ white-space: normal !important; overflow: visible !important; text-overflow: clip !important; overflow-wrap: anywhere; line-height: 1.15 !important; }}
[data-testid="stMetricDelta"] {{
  color: {VERDE_SUAVE} !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em;
}}
[data-testid="stMetricDelta"] svg {{ display: none; }}

/* Legendas, notas de método e rodapé: legíveis, mas discretos */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] li {{
  color: {TEXTO_SECUNDARIO} !important; opacity: 1 !important; font-size: 0.97rem !important; line-height: 1.6;
}}
[data-testid="stCaptionContainer"] strong {{ color: #F0F6FC; }}
[data-testid="stCaptionContainer"] a {{ color: {LIMAO}; }}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{ line-height: 1.6; }}
[data-testid="stAlert"] {{ border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.06); }}
[data-testid="stAlert"] p {{ font-size: 0.97rem; line-height: 1.55; }}
.rodape-fontes {{
  text-align: center; color: {CINZA_RODAPE}; font-size: 0.8rem; line-height: 1.6; margin: 2.5rem auto 1rem;
  padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.06);
}}
.rodape-fontes a {{ color: {CINZA_RODAPE}; text-decoration: underline; }}
button[data-baseweb="tab"] p {{ font-size: 1rem; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: {LIMAO}; }}
</style>
"""


def inject_custom_css() -> None:
    st.markdown(CSS + f"<style>{css_fundo()}</style>", unsafe_allow_html=True)


def selo_aviso(texto: str) -> None:
    """Selo fixo no topo, fora das abas (aparece em todas). O texto vem de `config.AVISO_INVESTIMENTO`."""
    st.markdown(f'<div class="aviso-previsao">{texto}</div>', unsafe_allow_html=True)


def _css(cor: str, fundo: str | None = None, forte: bool = False) -> str:
    return ";".join(p for p in (f"color:{cor}", f"background-color:{fundo}" if fundo else "", "font-weight:700" if forte else "") if p)


def colorir_rmae(dados: pd.DataFrame, rmae) -> pd.DataFrame:
    """Fundo sutil na coluna da rMAE: verde se < 1 (modelo erra menos), vermelho se > 1."""
    estilos = pd.DataFrame("", index=dados.index, columns=dados.columns)
    estilos["rMAE [IC 95%]"] = [
        _css("#F0F6FC", "rgba(0,255,127,0.16)") if r < 1 else _css("#F0F6FC", "rgba(255,107,129,0.16)") for r in rmae
    ]
    return estilos


def colorir_veredito(valor: str) -> str:
    if valor == "ganha do ingênuo":
        return _css(LIMAO, "rgba(0,255,127,0.14)", forte=True)
    if valor == "perde do ingênuo":
        return _css(VERMELHO, "rgba(255,107,129,0.14)", forte=True)
    return _css(AMARELO, forte=True)


def colorir_sinal(valor: float) -> str:
    return _css(LIMAO if valor > 0 else VERMELHO, forte=True)


def colorir_p_bh(valor: float) -> str:
    return _css(LIMAO, "rgba(0,255,127,0.14)", forte=True) if valor < 0.05 else ""
