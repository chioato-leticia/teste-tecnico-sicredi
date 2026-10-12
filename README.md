# Processamento de Solicitações — Teste Técnico Sicredi

## Descrição

Automação desenvolvida em Python para processar solicitações de cadastro recebidas em formato JSON.

O programa lê o arquivo `solicitacoes.json`, seleciona os registros aprovados com CPF preenchido, gera o arquivo `aprovados.csv` e registra os resultados e eventuais erros em `processamento.log`.

## Pré-requisitos

- Python 3.9 ou superior (versão testada: 3.12).
- Terminal ou editor de código, como Visual Studio Code.

A solução utiliza somente bibliotecas nativas do Python, sem necessidade de instalar dependências externas.

## Como executar

Abra um terminal na pasta do projeto e execute:

```bash
python main.py
```

Os caminhos dos arquivos são definidos a partir da localização do `main.py`, independentemente do diretório de trabalho.

Após a execução, serão gerados ou atualizados os arquivos `aprovados.csv` e `processamento.log`.

**Resultado esperado com o JSON oficial:** 15 registros lidos, 7 exportados (IDs 1, 4, 6, 9, 12, 13 e 15) e 8 ignorados.

O programa retorna código de saída `0` em caso de sucesso e `1` em caso de falha.

## Regras de processamento

Uma solicitação será exportada quando:

- O status for exatamente `APROVADO`.
- O CPF estiver preenchido e não contiver apenas espaços.
- Os campos obrigatórios `id`, `nome`, `cpf` e `status` estiverem presentes.
- O nome e o ID atenderem às validações adicionais implementadas.

Não é realizada a validação dos dígitos verificadores do CPF, conforme permitido no enunciado.

Registros inválidos são ignorados sem interromper o processamento dos demais.

## Arquivos gerados

**`aprovados.csv`**

Arquivo UTF-8 com separador ponto e vírgula (`;`) e cabeçalho `id;nome;cpf`.

**`processamento.log`**

Registra início e conclusão, totais de registros lidos, exportados e ignorados, motivos das rejeições e eventuais erros. O log é recriado a cada execução.

## Tratamento de erros

A aplicação trata arquivos ausentes, JSON inválido (informando linha e coluna), problemas de codificação UTF-8, estrutura de dados incompatível, registros incompletos e falhas de leitura ou gravação.

O arquivo de entrada aceita UTF-8 com ou sem BOM. Caso a leitura falhe, um CSV gerado anteriormente não é modificado.

## Testes automatizados

Os testes utilizam a biblioteca nativa `unittest` e arquivos temporários, sem modificar os dados originais do projeto.

Para executá-los:

```bash
python -m unittest discover -s tests -v
```

A suíte contempla validação de campos, cenários de erro, leitura de JSON, geração de CSV e execução completa, incluindo conferência do log e dos resultados do arquivo oficial.

## Premissas e decisões técnicas

- Organização: o código foi dividido em funções com responsabilidades específicas, facilitando testes e manutenção.
- Validação: cada registro retorna o primeiro motivo de rejeição identificado, mantendo o log objetivo. Como evolução, a função poderia retornar múltiplas inconsistências por solicitação.
- Integridade dos dados: o CPF é tratado como texto para preservar zeros à esquerda. O CSV utiliza ponto e vírgula como separador.
- Rastreabilidade: o log registra os motivos de rejeição utilizando o ID da solicitação, evitando expor desnecessariamente o CPF completo.
- Tratamento de falhas: problemas de processamento são diferenciados de rejeições por regras de negócio, permitindo que os registros válidos continuem sendo processados.

## Integração com BPM

Em um cenário de BPM (Business Process Management), a automação poderia ser incorporada a um fluxo de cadastro com as seguintes etapas:

1. **Recebimento:** envio da solicitação por formulário eletrônico.
2. **Validação e aprovação:** conferência dos campos obrigatórios e análise pelo responsável.
3. **Acionamento:** após a aprovação, o BPM disponibilizaria os registros em JSON ou por outro mecanismo de integração.
4. **Processamento:** execução da automação Python para validar os registros e gerar o CSV.
5. **Disponibilização e monitoramento:** encaminhamento do arquivo à área responsável, com registro de resultados e tratamento de exceções.

Para utilização em produção, seria importante manter identificadores únicos, histórico de aprovações e controle de registros já processados, evitando duplicidades em eventuais reprocessamentos.

A integração com BPM é uma proposta de evolução. A implementação entregue realiza o processamento local de arquivos JSON.

## Uso de inteligência artificial

Foram utilizadas ferramentas de IA como apoio ao desenvolvimento e à revisão técnica:

- **ChatGPT (OpenAI):** apoio ao uso de Python, estruturação das funções, tratamento de erros, testes automatizados e documentação.
- **Claude (Anthropic):** revisão técnica complementar, identificação de possíveis falhas e apoio à implementação de melhorias de robustez, testes e documentação.

**Decisões técnicas adotadas durante o desenvolvimento**

- **Separador do CSV:** optei pelo ponto e vírgula (`;`) por ser um formato comum em arquivos CSV utilizados em sistemas corporativos no Brasil, inclusive em processos de importação e exportação de dados.
- **CPF como texto:** mantive o CPF como string para preservar zeros à esquerda e evitar que o valor seja tratado como um número utilizado em cálculos.
- **Organização em funções:** dividi o processamento em funções com responsabilidades específicas, facilitando a identificação de erros, a manutenção do código e a criação de testes automatizados.

Durante o desenvolvimento, priorizei o uso de bibliotecas nativas, a separação de responsabilidades entre funções, a rastreabilidade das rejeições e a manutenção de uma solução simples, funcional e adequada aos requisitos.