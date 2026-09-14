# fatura-pdf-excel
Ferramenta que converte localmente fatura do cartão do banco Santander de pdf para Excel.

# Fatura PDF → EXCEL

Este é um pequeno script em Python para converter faturas de cartão de crédito em PDF para uma planilha Excel.

Ele surgiu porque o *Banco Santander* deixou de disponibilizar a fatura do cartão de crédito em Excel e passou a oferecê-la apenas em PDF.

PDF é ótimo para ler. Para ordenar, filtrar, conferir compras, somar despesas ou simplesmente trabalhar com os dados, nem tanto.

Então este script faz o caminho de volta, ao passo que lê a fatura, identifica os lançamentos e cria um arquivo `.xlsx`.

Todo o processamento acontece localmente no seu computador.

## O que ele faz

O programa lê uma fatura em PDF e tenta reconstruir uma tabela com estas colunas:

| Data  | Descrição               | Parcela | Valor (US$) | Valor (R$) |
| ----- | ----------------------- | ------- | ----------- | ---------- |
| 06/04 | LOJA EXEMPLO            | 03/10   |             | 47,00      |
| 11/06 | COMERCIO EXEMPLO        |         |             | 320,00     |
| 18/06 | SERVICO DIGITAL EXEMPLO |         | 20,00       | 107,35     |
| 18/06 | IOF DESPESA NO EXTERIOR |         |             | 3,76       |

Todos os exemplos acima são fictícios.

Na versão atual, o parser consegue lidar com:

* PDFs protegidos por senha;
* páginas divididas em duas grandes colunas;
* compras parceladas;
* despesas não parceladas;
* número da parcela;
* valores em reais e dólares;
* compras internacionais;
* IOF associado a compras internacionais;
* continuação de uma seção na coluna seguinte mesmo quando o cabeçalho não é repetido.

## Antes de começar

Este não é um conversor universal de qualquer fatura em PDF.

PDF não é um formato de dados tabular. Dois documentos que parecem iguais na tela podem ter estruturas internas completamente diferentes.

Este parser foi construído para um tipo específico de fatura, com seções equivalentes a:

```text
Parcelamentos
Despesas
```

e com campos equivalentes a:

```text
Compra | Data | Descrição | Parcela | R$ | US$
```

Se o seu banco usar outro layout, provavelmente será necessário adaptar alguma parte do parser.

## Requisitos

Você vai precisar de:

* Python 3.9 ou superior;
* `pdfplumber`;
* `pandas`;
* `openpyxl`;
* `pdfminer.six`.

Instale as dependências com:

```bash
pip install -r requirements.txt
```

Se preferir usar um ambiente virtual:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Como usar

Coloque o `parser.py` no diretório em que você quer trabalhar e execute:

```bash
python parser.py fatura.pdf
```

Como por experiência própria os PDFs deve banco pedem senha para serem abertos, se o seu PDF tiver senha, o programa vai perguntar:

```text
Senha do PDF:
```

A senha não aparece enquanto você digita.

Se o arquivo de entrada for:

```text
fatura.pdf
```

o arquivo de saída será:

```text
fatura.xlsx
```

na mesma pasta.

## Modo de diagnóstico

Se alguma coisa não funcionar, execute:

```bash
python parser.py fatura.pdf --debug
```

**O modo de diagnóstico mostra informações sobre a estrutura que o parser encontrou, mas foi feito para não imprimir descrições de compras, valores, senha ou conteúdo bruto da fatura.**

Isso é importante porque faturas bancárias contêm informação pessoal e financeira.

## Privacidade

Este programa não envia a fatura para nenhum serviço externo.

O PDF é aberto e processado localmente.

A senha é solicitada apenas durante a execução e não é armazenada pelo programa.

O repositório também foi preparado para não versionar, por padrão:

```text
*.pdf
*.xlsx
*.xls
*.csv
*.log
```

Ainda assim, vale a regra mais importante deste projeto:

**não publique uma fatura real no GitHub.**

Também não publique:

* arquivos Excel gerados a partir de faturas reais;
* senhas;
* números de cartão;
* números de conta;
* CPF ou outros identificadores;
* screenshots de faturas;
* logs contendo transações reais.

Se você encontrar um erro e quiser abrir uma issue, crie um exemplo fictício que reproduza o problema.

Por exemplo:

```text
Despesas Compra Data Descrição Parcela R$ US$
3 11/06 LOJA EXEMPLO 320,00
13/06 COMERCIO EXEMPLO 48,35
```

Isso já é suficiente para investigar boa parte dos bugs sem expor nenhum dado real.

## Algumas peculiaridades que o parser conhece

Durante o desenvolvimento apareceram alguns casos interessantes.

Uma compra pode vir assim:

```text
3 11/06 LOJA EXEMPLO 320,00
```

ou assim:

```text
11/06 LOJA EXEMPLO 320,00
```

O `2` ou `3` pode aparecer ou não.

Uma compra parcelada pode aparecer como:

```text
3 06/04 PROFISSIONAL EXEMPLO 03/10 47,00
```

e virar:

```text
Data: 06/04
Descrição: PROFISSIONAL EXEMPLO
Parcela: 03/10
Valor (R$): 47,00
```

Compras internacionais também podem trazer linhas adicionais, por exemplo:

```text
18/06 SERVICO DIGITAL EXEMPLO 107,35 20,00
COTAÇÃO DOLAR R$ 5,3676
IOF DESPESA NO EXTERIOR 3,76
```

Nesse caso, o parser mantém a compra principal e cria uma linha separada para o IOF.

## Limitações

Há algumas.

O programa não faz OCR.

Isso significa que ele precisa de um PDF que contenha texto de verdade. Se a fatura for apenas uma imagem digitalizada, o parser não vai conseguir lê-la.

Ele também depende da estrutura do documento.

Se a instituição financeira mudar o layout da fatura, alguma regra pode deixar de funcionar.

A página atualmente é tratada como duas grandes colunas, porque esse é o layout para o qual o parser foi construído.

E, claro, uma boa regra para qualquer parser financeiro:

**confira o resultado com o documento original.**

Este software não deve ser usado como única fonte para auditoria financeira, contábil ou fiscal.

## Por que Excel?

Porque às vezes o problema é só conseguir ter os dados de novo. :)

Uma vez em `.xlsx`, você pode:

* ordenar compras;
* filtrar por descrição;
* localizar parcelas;
* fazer tabelas dinâmicas;
* comparar meses;
* classificar despesas;
* importar os dados em outros programas;
* ou simplesmente guardar uma versão mais prática da fatura. 

## Contribuições

Contribuições são bem-vindas.

Se seu banco produz uma estrutura semelhante, mas alguma coisa não funciona, abra uma issue com um exemplo sintético.

Algo assim é ótimo:

```text
Entrada fictícia:

11/06 LOJA EXEMPLO 25,00

Resultado esperado:

Data = 11/06
Descrição = LOJA EXEMPLO
Valor (R$) = 25,00
```

Não é necessário — nem desejável — enviar a fatura original.

## FAIR

O projeto tenta seguir os princípios FAIR para software na medida em que eles fazem sentido para uma ferramenta pequena como esta.

Em termos práticos, isso significa:

* código e documentação públicos;
* versões identificáveis;
* dependências documentadas;
* licença explícita;
* estrutura de entrada e saída descrita;
* exemplos sintéticos;
* possibilidade de citação;
* registro das limitações conhecidas.

A ideia é que o código deve ser possível de encontrar, entender, executar, reutilizar e adaptar. Use essa recomendação nos seus projetos! :)

## DOI

A versão `v1.0.0` deste software está arquivada no Zenodo.

DOI: 10.5281/zenodo.22755584

## Licença

Este projeto é distribuído sob a licença MIT.

Veja o arquivo `LICENSE`.

## Aviso final

Este é um projeto independente.

Ele não tem vínculo, parceria ou endosso de qualquer banco ou instituição financeira.

O programa surgiu para resolver um problema concreto e foi compartilhado na esperança de que também seja útil para outras pessoas.

Use, adapte, teste, melhore.

E confira a planilha antes de jogar fora o PDF. :)
