# Monitor de Commodities

## Objetivo
Cruzar a cotação do dólar com os preços de soja e milho (CEPEA/CONAB), visualizar a
relação entre eles e gerar uma previsão simples com séries temporais, tudo em um
dashboard público.

## Regras inegociáveis
- Usar SOMENTE dados públicos e sempre citar a fonte (CEPEA, CONAB, Banco Central) no
  dashboard e no README.
- Respeitar os termos de uso de cada fonte. Para o CEPEA, NÃO fazer raspagem agressiva:
  preferir os arquivos/planilhas que o próprio site disponibiliza para download.
- A previsão é ilustrativa. Mostrar na tela o aviso: "Não é recomendação de investimento."
- Nunca commitar chaves de API (.env no .gitignore).
- Cache local dos dados: não baixar tudo de novo a cada execução.

## Fontes de dados (conferir links e formatos antes de implementar)
- Dólar (PTAX/comercial): API de séries temporais do Banco Central (SGS).
- Soja e milho: indicadores CEPEA/ESALQ (planilhas disponibilizadas no site).
- CONAB: portal de dados abertos (safra, preços, custos de produção).
- Plano B se o CEPEA travar: cotações de futuros com API aberta.

## Stack
- Python 3.12, pandas, requests
- Armazenamento: SQLite ou Parquet (decidir no plano)
- Dashboard: Streamlit + Plotly
- Previsão: statsmodels (ARIMA/ETS), Prophet opcional
- Testes: pytest

## Princípios
- Separar em camadas: coleta -> limpeza -> armazenamento -> análise -> previsão -> dashboard.
- Funções pequenas, tipadas e com testes.
- Backtest honesto: comparar o modelo com um modelo ingênuo (repetir o último valor).
  Se o modelo não ganhar do ingênuo, dizer isso no README.
- Analisar defasagem: testar se o dólar de hoje antecipa o preço das commodities.
- Valores em R$ e US$ claramente rotulados.

## Como trabalhar comigo
- Propor plano antes de codar mudanças grandes.
- Fazer uma etapa por vez e rodar os testes ao final de cada uma.
- Sugerir mensagem de commit ao concluir cada etapa.