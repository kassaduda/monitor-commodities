"""Configuração central: caminhos, período e códigos das séries."""

from datetime import date
from pathlib import Path

RAIZ: Path = Path(__file__).resolve().parents[2]
DIR_DADOS: Path = RAIZ / "data"
DIR_RAW: Path = DIR_DADOS / "raw"
DIR_PROCESSED: Path = DIR_DADOS / "processed"

# Imagem de fundo do dashboard (opcional: sem o arquivo, o app usa só a cor do tema).
ARQUIVO_FUNDO: Path = RAIZ / "assets" / "background_agro.jpg"

DATA_INICIO: date = date(2010, 1, 1)

# BCB SGS 1. Desde 01/07/2011 é a PTAX de fechamento (venda); conferido contra a API PTAX/Olinda.
BCB_SERIES: dict[str, int] = {
    "ptax_venda": 1,
}
# Nome exato devolvido pelos metadados do SGS (campo nomeCompleto); usado no README e no dashboard.
BCB_SERIE_1_NOME: str = "Taxa de câmbio - Livre - Dólar americano (venda) - diário"
BCB_SERIE_1_UNIDADE: str = "R$/US$"
FONTE_BCB: str = "Banco Central do Brasil - SGS"

# Banco Mundial - Pink Sheet (CC BY 4.0). Arquivo baixado manualmente para data/raw/worldbank/.
WB_ARQUIVO: str = "CMO-Historical-Data-Monthly.xlsx"
WB_ABA: str = "Monthly Prices"
WB_SERIES: dict[str, str] = {  # série no projeto -> nome da coluna no arquivo
    "wb_soja": "Soybeans",
    "wb_milho": "Maize",
    # O Pink Sheet não tem coluna "Wheat": traz "Wheat, US HRW" (hard red winter) e "Wheat, US SRW" (soft red winter).
    "wb_trigo": "Wheat, US HRW",
}
WB_UNIDADE_ARQUIVO: str = "($/mt)"
WB_UNIDADE: str = "US$/t"
FONTE_WB: str = "World Bank - Commodity Price Data (The Pink Sheet), CC BY 4.0"

# Mudanças de definição registradas na aba "Description" do Pink Sheet; marcadas nos gráficos.
QUEBRAS_DEFINICAO: dict[str, list[tuple[date, str]]] = {
    "wb_soja": [
        (date(2021, 1, 1), "U.S. Gulf Yellow Soybean #2, CIF Rotterdam"),
        (date(2025, 1, 1), "U.S. Soybeans, FOB U.S. Gulf"),
    ],
    # Aba "Description": "no. 2 hard red winter Gulf export price; June 2020 backwards, no. 1, hard red winter, ordinary
    # protein". A data de corte (jul/2020) é lida de "June 2020 backwards"; confirmar no arquivo se a definição importar.
    "wb_trigo": [
        (date(2020, 7, 1), "U.S. no. 2 hard red winter, Gulf"),
    ],
}

# CEPEA e CONAB: apenas locais; identificadores definidos quando houver arquivo baixado manualmente.

# Resultados do backtest e das análises (gerados por monitor.resultados, lidos pelo dashboard).
ARQUIVOS_RESULTADOS: dict[str, str] = {
    "backtest": "resultados_backtest.parquet",
    "previsao": "resultados_previsao.parquet",
    "correlacao": "resultados_correlacao.parquet",
    "defasagem": "resultados_defasagem.parquet",
    "adf": "resultados_adf.parquet",
    "correlacao_deslizante": "resultados_correlacao_deslizante.parquet",
    "volatilidade": "resultados_volatilidade.parquet",
    "bollinger": "resultados_bollinger.parquet",
    "razao": "resultados_razao_soja_milho.parquet",
}
# Janelas (meses) das métricas de risco: correlação deslizante, volatilidade móvel e Bollinger (média ± k desvios).
JANELA_CORRELACAO: int = 36
JANELA_VOLATILIDADE: int = 12
JANELA_BOLLINGER: int = 12
K_BOLLINGER: float = 2.0

# Regra prática de mercado para a razão de preços soja/milho (referência visual, não calculada com estes dados).
REFERENCIA_RAZAO_SOJA_MILHO: float = 2.5

ARQUIVO_RESULTADOS_META: str = "resultados_meta.json"

AVISO_INVESTIMENTO: str = "Não é recomendação de investimento."
