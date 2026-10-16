"""Persiste backtest, previsão, correlação e defasagem em Parquet pequenos (etapa 7).

O dashboard só lê estes arquivos. Eles derivam exclusivamente de BCB e Banco Mundial, então
podem ir para o repositório; `validar_fontes` recusa qualquer menção a CEPEA ou CONAB.

Uso: python -m monitor.resultados   (alguns minutos: refaz o backtest)
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from monitor import config
from monitor.analise.base import correlacoes_de_retornos, montar_base
from monitor.analise.defasagem import analisar
from monitor.previsao.execucao import avaliar_casos, casos, previsoes_ilustrativas

FONTES_PERMITIDAS = f"{config.FONTE_BCB}; {config.FONTE_WB}"
FONTES_PROIBIDAS = ("cepea", "conab", "esalq")
ARQUIVOS = {
    "backtest": "resultados_backtest.parquet",
    "previsao": "resultados_previsao.parquet",
    "correlacao": "resultados_correlacao.parquet",
    "defasagem": "resultados_defasagem.parquet",
    "adf": "resultados_adf.parquet",
}
ARQUIVO_META = "resultados_meta.json"


def tabela_correlacao(base) -> pd.DataFrame:
    return pd.DataFrame([
        {"serie_x": r.serie_x, "unidade_x": r.unidade_x, "serie_y": r.serie_y, "unidade_y": r.unidade_y,
         "r": r.r, "ic95_inf": r.ic95[0], "ic95_sup": r.ic95[1], "p_valor": r.p_valor, "n": r.n,
         "inicio": r.inicio, "fim": r.fim}
        for r in correlacoes_de_retornos(base)
    ])


def validar_fontes(tabelas: dict[str, pd.DataFrame]) -> None:
    """Falha se alguma célula de texto ou nome de coluna citar CEPEA/CONAB."""
    for nome, df in tabelas.items():
        textos = list(map(str, df.columns))
        for col in df.select_dtypes(include=["object", "string"]):
            textos += df[col].dropna().astype(str).unique().tolist()
        for t in textos:
            achado = [p for p in FONTES_PROIBIDAS if p in t.lower()]
            if achado:
                raise ValueError(f"Resultado {nome!r} cita fonte não redistribuível ({achado[0]}): {t!r}")


def gerar(dir_processed: Path = config.DIR_PROCESSED, paralelo: bool = True) -> dict[str, pd.DataFrame]:
    base = montar_base(dir_processed)
    lista = casos(dir_processed)
    adf, defasagem = analisar(base)
    tabelas = {
        "backtest": avaliar_casos(lista, paralelo=paralelo),
        "previsao": previsoes_ilustrativas(lista),
        "correlacao": tabela_correlacao(base),
        "defasagem": defasagem,
        "adf": adf,
    }
    tabelas = {k: v.assign(fonte=FONTES_PERMITIDAS) for k, v in tabelas.items()}
    validar_fontes(tabelas)
    return tabelas


def salvar(tabelas: dict[str, pd.DataFrame], dir_processed: Path = config.DIR_PROCESSED) -> None:
    base = montar_base(dir_processed)
    edicoes = json.loads((dir_processed / "_edicoes.json").read_text(encoding="utf-8"))
    meta = {
        "edicao_pink_sheet": edicoes.get("wb_pink_sheet"),
        "periodo_inicio": f"{base.inicio:%Y-%m}",
        "periodo_fim": f"{base.fim:%Y-%m}",
        "gerado_em": date.today().isoformat(),
        "fontes": FONTES_PERMITIDAS,
    }
    validar_fontes({"meta": pd.DataFrame([meta])})
    for nome, df in tabelas.items():
        df.to_parquet(dir_processed / ARQUIVOS[nome], index=False)
    (dir_processed / ARQUIVO_META).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    tabelas = gerar()
    salvar(tabelas)
    for nome, df in tabelas.items():
        print(f"{ARQUIVOS[nome]}: {len(df)} linhas")
    print(f"{ARQUIVO_META} gravado. Fonte: {FONTES_PERMITIDAS}")


if __name__ == "__main__":
    main()
