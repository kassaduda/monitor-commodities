# Monitor de Commodities

## Objetivo
Cruzar a cotação do dólar com os preços de soja e milho, visualizar a relação entre eles e
gerar uma previsão simples com séries temporais, tudo em um dashboard público.
O dashboard público usa só fontes com redistribuição permitida (BCB + Banco Mundial);
CEPEA e CONAB entram apenas na execução local.

## Regras inegociáveis
- Usar SOMENTE dados públicos e sempre citar a fonte (Banco Central, Banco Mundial, CEPEA,
  CONAB) no dashboard e no README, com a licença de cada uma.
- Respeitar os termos de uso e o robots.txt de cada fonte. Antes de acessar uma fonte nova,
  ler robots.txt e termos de uso e confirmar a licença.
- Só commitar dados (Parquet) de fontes cuja licença permite redistribuição.
- CEPEA: NÃO acessar cepea.org.br por nenhuma ferramenta (o robots.txt bloqueia agentes de IA).
  As planilhas são baixadas manualmente para data/raw/cepea/ e o código só lê arquivos locais.
  Parquet do CEPEA fica no .gitignore até haver autorização formal por escrito.
- CONAB: licença de dados não declarada (pedido em andamento no Informa.BR). Não redistribuir;
  não codar o leitor enquanto não houver licença nem arquivo baixado manualmente.
- A previsão é ilustrativa. Mostrar na tela o aviso: "Não é recomendação de investimento."
- Nunca commitar chaves de API (.env no .gitignore).
- Cache local dos dados: não baixar tudo de novo a cada execução.

## Fontes de dados
Públicas (vão para o repositório e o dashboard público):
- Dólar: BCB SGS série 1, "Taxa de câmbio - Livre - Dólar americano (venda) - diário"
  (PTAX de fechamento, R$/US$). Dados públicos com citação da fonte.
- Soja e milho: Banco Mundial, "World Bank Commodity Price Data (The Pink Sheet)", arquivo
  oficial CMO-Historical-Data-Monthly.xlsx. Mensal, US$/t nominais. Licença CC BY 4.0
  (Data Catalog, dataset 0038238). Atribuição obrigatória ao Banco Mundial.

Apenas locais (não redistribuir):
- CEPEA/ESALQ: soja Paranaguá, soja Paraná, milho ESALQ/B3 (planilhas baixadas manualmente).
- CONAB: preços por UF e safra (quando houver licença e arquivo).

## Stack
- Python 3.12, pandas (<3), requests
- Armazenamento: Parquet em data/processed/ (um arquivo por série, formato padrão
  data, serie, valor, unidade, fonte); cache bruto em data/raw/ (fora do git)
- Dashboard: Streamlit + Plotly (hospedado no Streamlit Community Cloud)
- Previsão: statsmodels (ARIMA/ETS), Prophet opcional
- Testes: pytest

## Princípios
- Separar em camadas: coleta -> limpeza -> armazenamento -> análise -> previsão -> dashboard.
- Funções pequenas, tipadas e com testes.
- Previsão MENSAL (frequência do Pink Sheet). Visualizações diárias para o dólar e mensais
  para o cruzamento dólar x commodities.
- Backtest honesto: comparar o modelo com um modelo ingênuo (repetir o último valor).
  Se o modelo não ganhar do ingênuo, dizer isso no README.
- Analisar defasagem: testar se o dólar antecipa o preço das commodities.
- Valores em R$ e US$ claramente rotulados.
- Documentar quebras de definição das séries (ex.: soja do Pink Sheet muda de CIF Rotterdam
  para FOB US Gulf em jan/2025).

## Como trabalhar comigo
- Propor plano antes de codar mudanças grandes.
- Fazer uma etapa por vez e rodar os testes ao final de cada uma.
- Sugerir mensagem de commit ao concluir cada etapa (título com até 70 caracteres,
  detalhe no corpo) e esperar aprovação antes de commitar.
- Não reimprimir código no chat: mostrar só resumo, caminhos dos arquivos e `pytest -q`.
- Mostrar DataFrames com `head()`/`tail()`, nunca inteiros.
- Não reler arquivos grandes sem necessidade.
- Ao fim de cada etapa, atualizar "Estado atual" e "Próximos passos" no README antes do commit.
