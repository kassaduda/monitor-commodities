"""Configuração central: caminhos, período e códigos das séries."""

from datetime import date
from pathlib import Path

RAIZ: Path = Path(__file__).resolve().parents[2]
DIR_DADOS: Path = RAIZ / "data"
DIR_RAW: Path = DIR_DADOS / "raw"
DIR_PROCESSED: Path = DIR_DADOS / "processed"

DATA_INICIO: date = date(2010, 1, 1)

# BCB SGS 1: "Taxa de câmbio - Livre - Dólar americano (venda) - diário".
# Desde 01/07/2011 é a PTAX de fechamento (venda); conferido contra a API PTAX/Olinda.
BCB_SERIES: dict[str, int] = {
    "ptax_venda": 1,
}

# CEPEA e CONAB: identificadores definidos nas etapas 3 e 4, após conferir os arquivos.

AVISO_INVESTIMENTO: str = "Não é recomendação de investimento."
