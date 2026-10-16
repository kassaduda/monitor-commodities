# Monitor de Commodities

Cruza a cotação do dólar com os preços de soja e milho, analisa a relação entre eles
(incluindo defasagem) e mostra uma previsão semanal ilustrativa em um dashboard Streamlit.

> **Não é recomendação de investimento.** A previsão é ilustrativa.

## Fontes de dados

| Série | Fonte | Licença / termos |
|---|---|---|
| Dólar — PTAX de fechamento, venda (R$/US$), diário | Banco Central do Brasil — SGS, série 1: *Taxa de câmbio - Livre - Dólar americano (venda) - diário* | Dados públicos, com citação da fonte |
| Soja — Indicador CEPEA/ESALQ Paranaguá (principal) e Paraná (opcional) | CEPEA/ESALQ-USP | [CC BY-NC 4.0](https://www.cepea.org.br/br/licenca-de-uso-de-dados.aspx) — uso **não comercial**, com crédito |
| Milho — Indicador ESALQ/B3 (Campinas) | CEPEA/ESALQ-USP | [CC BY-NC 4.0](https://www.cepea.org.br/br/licenca-de-uso-de-dados.aspx) — uso **não comercial**, com crédito |
| Preços por UF e safra (contexto) | CONAB — Portal de Informações | Dados abertos públicos, com citação da fonte |

Os arquivos em `data/processed/` são derivados dessas fontes e redistribuídos nos mesmos
termos. Os dados do CEPEA neste repositório **não podem ser usados para fins comerciais**.

## Período

Desde 2010 ou o máximo disponível em cada fonte. As análises que cruzam séries usam apenas o
período em comum entre elas (detalhado aqui ao final da implementação).

## Como rodar

Requer Python 3.12.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Status

Em construção — ver etapas no histórico de commits.
