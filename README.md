# Monitor de Commodities

Cruza a cotação do dólar com os preços de soja e milho, analisa a relação entre eles
(incluindo defasagem) e mostra uma previsão semanal ilustrativa em um dashboard Streamlit.

> **Não é recomendação de investimento.** A previsão é ilustrativa.

## Fontes de dados

| Série | Fonte | Licença / termos |
|---|---|---|
| Dólar — PTAX de fechamento, venda (R$/US$), diário | Banco Central do Brasil — SGS, série 1: *Taxa de câmbio - Livre - Dólar americano (venda) - diário* | Dados públicos, com citação da fonte |
| Soja e milho — preços internacionais mensais (US$/t), dashboard público | Banco Mundial — *Commodity Price Data (The Pink Sheet)* | [CC BY 4.0](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections) |
| Soja — Indicador CEPEA/ESALQ Paranaguá e Paraná (apenas local) | CEPEA/ESALQ-USP | [CC BY-NC 4.0](https://www.cepea.org.br/br/licenca-de-uso-de-dados.aspx) — ver nota abaixo |
| Milho — Indicador ESALQ/B3 Campinas (apenas local) | CEPEA/ESALQ-USP | [CC BY-NC 4.0](https://www.cepea.org.br/br/licenca-de-uso-de-dados.aspx) — ver nota abaixo |
| Preços por UF e safra (contexto) | CONAB — Preços de Mercado / Portal de Informações | Licença dos dados **não declarada** (em consulta ao SIC da CONAB); páginas gov.br sob CC BY-ND 3.0 |

### Banco Mundial (Pink Sheet)

> Fonte: World Bank, *Commodity Price Data (The Pink Sheet)*, CC BY 4.0. Dados reformatados
> (mensal, US$/t), com conversão para R$ pela PTAX do BCB.

- Arquivo oficial: `CMO-Historical-Data-Monthly.xlsx`, aba "Monthly Prices", séries
  `Soybeans` e `Maize`, em US$ nominais por tonelada métrica. Disponível em
  <https://www.worldbank.org/en/research/commodity-markets>; licença no registro do
  [Data Catalog (dataset 0038238)](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections)
  e nos [termos de uso para datasets](https://www.worldbank.org/ext/en/legal/terms-conditions/datasets).
- "Dados reformatados" significa: período `AAAAMmm` convertido para data (1º dia do mês) e
  colunas padronizadas. Os valores em US$/t não são alterados; a conversão para R$ é feita na
  análise, não nos arquivos de `data/processed/`.
- **Fontes de terceiros:** a aba "Description" do arquivo cita como fontes primárias dos
  preços S&P Global (antiga IHS Markit), Bloomberg Finance L.P., ISTA Mielke GmbH (Oil World)
  e o Departamento de Agricultura dos EUA (USDA). O Banco Mundial publica o conjunto sob
  CC BY 4.0 e os metadados do dataset não indicam restrições adicionais de terceiros.
- O arquivo é atualizado no 2º dia útil de cada mês e baixado **manualmente** para
  `data/raw/worldbank/` (o link muda a cada edição).
- São preços **internacionais** (portos dos EUA/Europa), não preços pagos no Brasil: a
  conversão para R$ não inclui prêmio de porto nem frete interno.

#### Mudança de definição da série de soja

A série `Soybeans` mudou de definição ao longo do tempo (aba "Description"):

| Período | Definição |
|---|---|
| até nov/2007 | origem EUA, *nearest forward* |
| dez/2007 – dez/2020 | U.S. No. 2 yellow, CIF Rotterdam |
| jan/2021 – dez/2024 | U.S. Gulf Yellow Soybean #2, CIF Rotterdam |
| desde jan/2025 | U.S. Soybeans, FOB U.S. Gulf |

CIF Rotterdam inclui frete e seguro até a Europa; FOB Golfo não. Por isso a passagem de
jan/2025 pode criar um degrau que não é variação de mercado. Os gráficos de soja marcam
**jan/2021** e **jan/2025**, e a previsão trata essas datas como quebras estruturais (variável
indicadora e backtest de robustez só com dados após a quebra). A série `Maize` (U.S. No. 2
yellow, FOB US Gulf) não tem mudança de definição registrada.

### Dados do CEPEA não são redistribuídos aqui

A licença de dados do CEPEA (CC BY-NC 4.0) permite uso não comercial com crédito, mas a
[Política de Direitos Autorais](https://www.cepea.org.br/br/politica-de-direitos-autorais-1.aspx)
exige autorização formal para retransmitir conteúdo e diz que "não é permitida [...] a
transmissão de séries de preços". Por isso, até haver autorização por escrito do CEPEA:

- as planilhas são baixadas **manualmente** no site do CEPEA (formulário de download) e salvas
  em `data/raw/cepea/`; o código não acessa o site do CEPEA;
- os arquivos `data/processed/cepea_*.parquet` ficam **fora do repositório** (`.gitignore`);
- o dashboard público não exibe as séries do CEPEA; elas aparecem apenas ao rodar localmente.

Os demais arquivos de `data/processed/` são derivados das fontes públicas acima e
redistribuídos nos termos de cada uma.

## Período

Desde 2010 ou o máximo disponível em cada fonte. As análises que cruzam séries usam apenas o
período em comum entre elas (detalhado aqui ao final da implementação).

## Metodologia da previsão (em implementação)

- Frequência **mensal**; modelos ARIMA/ETS (statsmodels) comparados com o modelo ingênuo
  (repetir o último valor).
- Backtest com janela deslizante (treino de 60 meses, horizontes de 1, 3 e 6 meses).
  Métrica principal: MASE (erro do modelo ÷ erro do ingênuo), com intervalo de confiança.
- **Teste de Diebold-Mariano com a correção de Harvey, Leybourne e Newbold (1997)** para
  decidir se a diferença entre o modelo e o ingênuo é estatisticamente real. Por quê:
  - em previsões de h meses à frente feitas a partir de origens consecutivas, as janelas de
    previsão se **sobrepõem** (a previsão de 6 meses feita em janeiro e a feita em fevereiro
    compartilham 5 meses). Os erros ficam autocorrelacionados até a defasagem h−1 mesmo que o
    modelo seja bom, e a variância "ingênua" da diferença de perdas fica subestimada — o teste
    acusaria diferenças significativas demais;
  - por isso a variância de longo prazo é estimada com **erros padrão robustos (HAC,
    Newey-West)** cobrindo h−1 defasagens;
  - com cerca de 130 origens, a amostra é pequena e o teste original de Diebold-Mariano rejeita
    a hipótese nula com frequência maior que a nominal. A correção de HLN ajusta a estatística
    pelo fator √[(T + 1 − 2h + h(h−1)/T) / T] e usa a distribuição t de Student com T−1 graus
    de liberdade em vez da normal.
- Se o modelo não ganhar do ingênuo, isso será dito aqui.

## Como rodar

Requer Python 3.12.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Atualizar os dados

1. (Mensal, manual) Baixe o arquivo "Monthly prices (XLS)" em
   <https://www.worldbank.org/en/research/commodity-markets> e salve como
   `data/raw/worldbank/CMO-Historical-Data-Monthly.xlsx`. Sem esse arquivo, o pipeline
   atualiza só o dólar e avisa.
2. Rode:

```powershell
python -m monitor.pipeline
```

Os Parquet do Pink Sheet (`wb_soja`, `wb_milho`) guardam todo o histórico do arquivo (desde
1960); as análises usam o período em comum com o dólar (desde jan/2010). Uma nova edição do
arquivo acrescenta os meses novos e aplica as revisões dos meses já salvos.

- `data/raw/` (fora do git): respostas brutas das fontes, em cache. Anos fechados não são
  baixados de novo; o ano corrente, no máximo uma vez por dia.
- `data/processed/` (no git, exceto `cepea_*.parquet`): uma série limpa por arquivo Parquet, nas colunas
  `data, serie, valor, unidade, fonte`. A atualização parte da última data já salva, busca só
  o que falta, nunca duplica datas e não reescreve o arquivo quando não há dados novos.

## Status

Em construção — ver etapas no histórico de commits.
