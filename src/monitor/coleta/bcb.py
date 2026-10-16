"""Coleta de séries do Banco Central do Brasil (SGS) com cache anual em data/raw/.

Comportamento da API (conferido em 14/10/2026):
- consultas diárias com mais de 10 anos retornam HTTP 406;
- período sem valores retorna HTTP 404 ("Value(s) not found");
- erros 5xx transitórios acontecem (ex.: 502 com página HTML).
"""

import json
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

import requests

from monitor import config

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
MAX_ANOS_POR_CONSULTA = 10
STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
USER_AGENT = "monitor-commodities/0.1 (projeto educacional, dados publicos)"

Registro = dict[str, str]


class ErroSGS(RuntimeError):
    """Falha definitiva ao consultar o SGS."""


def formatar_data(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def janelas_de_anos(anos: list[int], max_anos: int = MAX_ANOS_POR_CONSULTA) -> list[tuple[int, int]]:
    """Agrupa anos consecutivos em janelas (ano_inicial, ano_final) de no máximo `max_anos`."""
    janelas: list[tuple[int, int]] = []
    for ano in sorted(set(anos)):
        if janelas and ano == janelas[-1][1] + 1 and ano - janelas[-1][0] < max_anos:
            janelas[-1] = (janelas[-1][0], ano)
        else:
            janelas.append((ano, ano))
    return janelas


def baixar_periodo(
    codigo: int,
    inicio: date,
    fim: date,
    *,
    session: requests.Session,
    tentativas: int = 3,
    espera_inicial: float = 1.0,
    dormir: Callable[[float], None] = time.sleep,
    timeout: float = 30.0,
) -> list[Registro]:
    """Baixa os registros brutos de um período, com nova tentativa em falhas transitórias."""
    params = {"formato": "json", "dataInicial": formatar_data(inicio), "dataFinal": formatar_data(fim)}
    url = URL_SGS.format(codigo=codigo)
    ultimo_erro = ""
    for tentativa in range(tentativas):
        if tentativa:
            dormir(espera_inicial * 2 ** (tentativa - 1))
        try:
            resp = session.get(url, params=params, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            ultimo_erro = f"{type(exc).__name__}: {exc}"
            continue
        if resp.status_code in STATUS_TRANSITORIOS:
            ultimo_erro = f"HTTP {resp.status_code}"
            continue
        if resp.status_code == 404:
            return []
        if not resp.ok:
            raise ErroSGS(f"SGS {codigo} {params}: HTTP {resp.status_code} - {resp.text[:300]}")
        dados = resp.json()
        if not isinstance(dados, list):
            raise ErroSGS(f"SGS {codigo}: resposta inesperada {str(dados)[:300]}")
        return dados
    raise ErroSGS(f"SGS {codigo} {params}: falhou após {tentativas} tentativas ({ultimo_erro})")


def caminho_cache(dir_raw: Path, codigo: int, ano: int) -> Path:
    return dir_raw / "bcb" / f"sgs_{codigo}" / f"{ano}.json"


def cache_valido(caminho: Path, ano: int, hoje: date) -> bool:
    """Ano fechado: válido se baixado depois de 31/12. Ano corrente: válido se baixado hoje."""
    if not caminho.exists():
        return False
    baixado_em = date.fromisoformat(json.loads(caminho.read_text(encoding="utf-8"))["baixado_em"])
    return baixado_em > date(ano, 12, 31) or baixado_em >= hoje


def _salvar_ano(caminho: Path, codigo: int, ano: int, registros: list[Registro], hoje: date) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {"codigo": codigo, "ano": ano, "baixado_em": hoje.isoformat(), "dados": registros}
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    temporario.replace(caminho)


def _ler_ano(caminho: Path) -> list[Registro]:
    return json.loads(caminho.read_text(encoding="utf-8"))["dados"]


def _ano_do_registro(registro: Registro) -> int:
    return int(registro["data"][-4:])  # data no formato dd/mm/aaaa


def coletar_sgs(
    codigo: int,
    inicio: date,
    fim: date | None = None,
    *,
    dir_raw: Path = config.DIR_RAW,
    session: requests.Session | None = None,
    hoje: date | None = None,
    **kwargs_download: object,
) -> list[Registro]:
    """Retorna os registros brutos entre `inicio` e `fim`, baixando só os anos ausentes do cache."""
    hoje = hoje or date.today()
    fim = min(fim or hoje, hoje)
    if inicio > fim:
        return []
    anos = list(range(inicio.year, fim.year + 1))
    faltando = [a for a in anos if not cache_valido(caminho_cache(dir_raw, codigo, a), a, hoje)]

    if faltando:
        if session is None:
            session = requests.Session()
            session.headers["User-Agent"] = USER_AGENT
        for ano_ini, ano_fim in janelas_de_anos(faltando):
            fim_janela = min(date(ano_fim, 12, 31), hoje)
            registros = baixar_periodo(codigo, date(ano_ini, 1, 1), fim_janela, session=session, **kwargs_download)
            for ano in range(ano_ini, ano_fim + 1):
                do_ano = [r for r in registros if _ano_do_registro(r) == ano]
                _salvar_ano(caminho_cache(dir_raw, codigo, ano), codigo, ano, do_ano, hoje)

    ini_txt, fim_txt = inicio.isoformat(), fim.isoformat()
    resultado: list[Registro] = []
    for ano in anos:
        for r in _ler_ano(caminho_cache(dir_raw, codigo, ano)):
            dia, mes, a = r["data"].split("/")
            if ini_txt <= f"{a}-{mes}-{dia}" <= fim_txt:
                resultado.append(r)
    return resultado
