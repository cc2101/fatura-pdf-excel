"""
Fatura PDF -> XLSX

Conversor local de faturas em PDF para planilhas XLSX.

Privacidade:
- a senha é solicitada em tempo de execução e não é armazenada;
- o modo --debug não imprime descrições, valores ou conteúdo bruto da fatura;
- exemplos no código são inteiramente sintéticos.

Este software não envia dados a serviços externos.
"""

__version__ = "1.0.0"

import argparse
import getpass
import re
from pathlib import Path

import pdfplumber
import pandas as pd
from pdfminer.pdfdocument import PDFPasswordIncorrect


# =========================================================
# PADRÕES BÁSICOS
# =========================================================

PADRAO_DATA = r"\d{2}/\d{2}(?:/\d{2,4})?"

# O (?!\d) é importante:
# impede que "5,3676" (cotação) seja interpretado
# parcialmente como "5,36".
PADRAO_VALOR = (
    r"-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}(?!\d)"
)

PADRAO_PARCELA = r"\d{2}/\d{2}"

PADRAO_SECAO = re.compile(
    r"\b(?P<secao>Parcelamentos|Despesas)\b",
    re.IGNORECASE
)

PADRAO_IOF = re.compile(
    rf"\bIOF\s+DESPESA\s+NO\s+EXTERIOR\s+"
    rf"(?P<valor>{PADRAO_VALOR})",
    re.IGNORECASE
)


# =========================================================
# ARGUMENTOS
# =========================================================

def obter_argumentos():

    parser = argparse.ArgumentParser(
        description="Converte fatura bancária em PDF para Excel."
    )

    parser.add_argument(
        "arquivo",
        help="Arquivo PDF da fatura"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostra informações detalhadas sobre o parsing"
    )

    return parser.parse_args()


# =========================================================
# LEITURA DO PDF EM DUAS GRANDES COLUNAS
# =========================================================

def ler_pdf_em_colunas(arquivo, senha):
    """
    Lê cada página em duas grandes colunas:

        página 1 esquerda
        página 1 direita
        página 2 esquerda
        página 2 direita
        ...

    Isso evita que o pdfplumber misture a ordem de leitura
    entre as duas metades da página.
    """

    blocos = []

    try:

        with pdfplumber.open(
            arquivo,
            password=senha
        ) as pdf:

            print(
                f"Páginas encontradas: {len(pdf.pages)}"
            )

            for numero, pagina in enumerate(
                pdf.pages,
                start=1
            ):

                largura = pagina.width
                altura = pagina.height

                meio = largura / 2

                colunas = [
                    (
                        "esquerda",
                        (0, 0, meio, altura)
                    ),
                    (
                        "direita",
                        (meio, 0, largura, altura)
                    )
                ]

                for nome_coluna, bbox in colunas:

                    recorte = pagina.crop(bbox)

                    texto = recorte.extract_text(
                        x_tolerance=2,
                        y_tolerance=3
                    )

                    if texto and texto.strip():

                        blocos.append({
                            "pagina": numero,
                            "coluna": nome_coluna,
                            "texto": texto
                        })

    except PDFPasswordIncorrect:

        print(
            "\nErro: senha incorreta para o PDF."
        )

        raise SystemExit(1)

    return blocos


# =========================================================
# NORMALIZAÇÃO
# =========================================================

def normalizar_texto(texto):

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


# =========================================================
# SEÇÕES
# =========================================================

def segmentar_coluna_por_secao(
    texto,
    secao_atual=None
):
    """
    Divide uma coluna sempre que encontra:

        Parcelamentos

    ou:

        Despesas

    Se a coluna não tiver cabeçalho, herda a seção
    da coluna anterior.

    Isso é especialmente importante para a coluna
    direita da fatura.
    """

    marcadores = list(
        PADRAO_SECAO.finditer(texto)
    )

    segmentos = []

    posicao = 0
    secao = secao_atual

    for marcador in marcadores:

        # Conteúdo antes do próximo cabeçalho:
        # pode ser continuação da seção anterior.
        antes = texto[
            posicao:marcador.start()
        ].strip()

        if antes and secao:

            segmentos.append({
                "secao": secao,
                "texto": antes
            })

        # Atualiza a seção
        secao = marcador.group(
            "secao"
        )

        posicao = marcador.end()

    # Conteúdo depois do último marcador
    resto = texto[posicao:].strip()

    if resto and secao:

        segmentos.append({
            "secao": secao,
            "texto": resto
        })

    return segmentos, secao


# =========================================================
# DETECÇÃO DE INÍCIO DAS TRANSAÇÕES
# =========================================================

def encontrar_inicios_transacoes(texto):
    """
    Reconhece:

        3 11/06 LOJA...
        2 11/06 LOJA...
        11/06 LOJA...

    2 e 3 são opcionais.

    Mas NÃO interpreta:

        03/10 47,00

    como nova compra, porque isso é:

        parcela + valor
    """

    padrao = re.compile(
        rf"""
        (?<!\S)

        (?:
            (?P<tipo>[23])
            \s+
        )?

        (?P<data>{PADRAO_DATA})

        \s+

        # Se imediatamente depois vier um valor,
        # provavelmente é "parcela + valor",
        # não "data + descrição".
        (?!
            {PADRAO_VALOR}
            (?:\s|$)
        )
        """,
        re.VERBOSE
    )

    return list(
        padrao.finditer(texto)
    )


def dividir_em_transacoes(texto):

    inicios = encontrar_inicios_transacoes(
        texto
    )

    blocos = []

    for i, inicio in enumerate(inicios):

        if i + 1 < len(inicios):

            fim = inicios[
                i + 1
            ].start()

        else:

            fim = len(texto)

        conteudo = texto[
            inicio.end():fim
        ].strip()

        blocos.append({
            "tipo": inicio.group("tipo"),
            "data": inicio.group("data"),
            "conteudo": conteudo
        })

    return blocos


# =========================================================
# LANÇAMENTOS AUXILIARES
# =========================================================

def extrair_lancamentos_auxiliares(
    texto,
    data,
    debug=False
):
    """
    Extrai cobranças relacionadas a uma compra,
    mas que aparecem sem data própria.

    Exemplo:

        IOF DESPESA NO EXTERIOR 3,76

    A cobrança herda a data da compra principal.
    """

    transacoes = []

    for resultado in PADRAO_IOF.finditer(
        texto
    ):

        valor = resultado.group(
            "valor"
        )

        transacao = {
            "Data": data,
            "Descrição": "IOF DESPESA NO EXTERIOR",
            "Parcela": "",
            "Valor (US$)": "",
            "Valor (R$)": valor
        }

        transacoes.append(
            transacao
        )

        if debug:

            print(
                "    + lançamento auxiliar de IOF reconhecido "
                "(valor omitido por privacidade)"
            )

    return transacoes


# =========================================================
# DESPESAS NÃO PARCELADAS
# =========================================================

def interpretar_despesa(
    bloco,
    debug=False
):
    """
    Exemplos:

        3 11/06 LOJA EXEMPLO 320,00

        13/06 COMERCIO EXEMPLO 48,35

        18/06 SERVICO DIGITAL EXEMPLO
        107,35
        20,00
        COTAÇÃO DOLAR R$ 5,3676
        IOF DESPESA NO EXTERIOR 3,76
    """

    conteudo = bloco[
        "conteudo"
    ]

    padrao = re.compile(
        rf"""
        ^
        (?P<descricao>.*?)

        \s+

        (?P<real>{PADRAO_VALOR})

        (?:
            \s+
            (?P<dolar>{PADRAO_VALOR})
        )?

        (?P<resto>.*)
        $
        """,
        re.VERBOSE | re.IGNORECASE
    )

    resultado = padrao.match(
        conteudo
    )

    if not resultado:

        if debug:

            print(
                "\n[DESPESA NÃO RECONHECIDA]"
            )

            print(
                "Dados da transação omitidos por privacidade."
            )

        return []

    descricao = resultado.group(
        "descricao"
    ).strip()

    real = resultado.group(
        "real"
    )

    dolar = resultado.group(
        "dolar"
    ) or ""

    resto = resultado.group(
        "resto"
    ).strip()

    transacoes = [
        {
            "Data": bloco["data"],
            "Descrição": descricao,
            "Parcela": "",
            "Valor (US$)": dolar,
            "Valor (R$)": real
        }
    ]

    # Procura IOF ou outros lançamentos auxiliares
    # depois da compra principal.
    transacoes.extend(
        extrair_lancamentos_auxiliares(
            resto,
            bloco["data"],
            debug=debug
        )
    )

    return transacoes


# =========================================================
# PARCELAMENTOS
# =========================================================

def interpretar_parcelamento(
    bloco,
    debug=False
):
    """
    Exemplo:

        3 06/04
        PROFISSIONAL EXEMPLO
        03/10
        47,00
    """

    conteudo = bloco[
        "conteudo"
    ]

    padrao = re.compile(
        rf"""
        ^
        (?P<descricao>.*?)

        \s+

        (?P<parcela>{PADRAO_PARCELA})

        \s+

        (?P<real>{PADRAO_VALOR})

        (?:
            \s+
            (?P<dolar>{PADRAO_VALOR})
        )?

        (?P<resto>.*)
        $
        """,
        re.VERBOSE | re.IGNORECASE
    )

    resultado = padrao.match(
        conteudo
    )

    if not resultado:

        if debug:

            print(
                "\n[PARCELAMENTO NÃO RECONHECIDO]"
            )

            print(
                "Dados da transação omitidos por privacidade."
            )

        return []

    descricao = resultado.group(
        "descricao"
    ).strip()

    transacoes = [
        {
            "Data": bloco["data"],
            "Descrição": descricao,
            "Parcela": resultado.group("parcela"),
            "Valor (US$)": resultado.group("dolar") or "",
            "Valor (R$)": resultado.group("real")
        }
    ]

    resto = resultado.group(
        "resto"
    ).strip()

    transacoes.extend(
        extrair_lancamentos_auxiliares(
            resto,
            bloco["data"],
            debug=debug
        )
    )

    return transacoes


# =========================================================
# PROCESSAMENTO DOS BLOCOS DA FATURA
# =========================================================

def identificar_transacoes(
    blocos_pdf,
    debug=False
):
    """
    Processa:

        página 1 esquerda
        página 1 direita
        página 2 esquerda
        página 2 direita

    mantendo memória de qual seção está ativa.
    """

    todas_transacoes = []

    secao_atual = None

    for bloco_pdf in blocos_pdf:

        pagina = bloco_pdf[
            "pagina"
        ]

        coluna = bloco_pdf[
            "coluna"
        ]

        texto = normalizar_texto(
            bloco_pdf["texto"]
        )

        segmentos, secao_atual = (
            segmentar_coluna_por_secao(
                texto,
                secao_atual
            )
        )

        if debug:

            print(
                "\n" + "=" * 60
            )

            print(
                f"Página {pagina} — "
                f"coluna {coluna}"
            )

            print(
                f"Seção atual ao final: "
                f"{secao_atual}"
            )

            print(
                f"Segmentos: {len(segmentos)}"
            )

        for segmento in segmentos:

            nome_secao = segmento[
                "secao"
            ].lower()

            blocos = dividir_em_transacoes(
                segmento["texto"]
            )

            if debug:

                print(
                    f"\n  {segmento['secao']}: "
                    f"{len(blocos)} possíveis compras"
                )

            for bloco in blocos:

                if nome_secao == "despesas":

                    encontradas = interpretar_despesa(
                        bloco,
                        debug=debug
                    )

                elif nome_secao == "parcelamentos":

                    encontradas = interpretar_parcelamento(
                        bloco,
                        debug=debug
                    )

                else:

                    encontradas = []

                todas_transacoes.extend(
                    encontradas
                )

                if debug:

                    for _ in encontradas:
                        print(
                            "  [OK] transação reconhecida "
                            "(dados omitidos por privacidade)"
                        )

    return todas_transacoes


# =========================================================
# EXCEL
# =========================================================

def salvar_excel(
    transacoes,
    arquivo_excel
):

    df = pd.DataFrame(
        transacoes,
        columns=[
            "Data",
            "Descrição",
            "Parcela",
            "Valor (US$)",
            "Valor (R$)"
        ]
    )

    with pd.ExcelWriter(
        arquivo_excel,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Extrato",
            index=False
        )

        planilha = writer.book["Extrato"]

        planilha.column_dimensions["A"].width = 14
        planilha.column_dimensions["B"].width = 55
        planilha.column_dimensions["C"].width = 12
        planilha.column_dimensions["D"].width = 16
        planilha.column_dimensions["E"].width = 16

        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions

        # Mantém Data, Parcela e valores como texto
        for linha in range(
            2,
            planilha.max_row + 1
        ):

            planilha[f"A{linha}"].number_format = "@"
            planilha[f"C{linha}"].number_format = "@"
            planilha[f"D{linha}"].number_format = "@"
            planilha[f"E{linha}"].number_format = "@"


# =========================================================
# MAIN
# =========================================================

def main():

    args = obter_argumentos()

    arquivo_pdf = (
        Path(args.arquivo)
        .expanduser()
        .resolve()
    )

    if not arquivo_pdf.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n"
            f"{arquivo_pdf}"
        )

    if arquivo_pdf.suffix.lower() != ".pdf":

        raise ValueError(
            "O arquivo informado não é um PDF."
        )

    arquivo_excel = (
        arquivo_pdf.with_suffix(".xlsx")
    )

    print("=" * 60)
    print("CONVERSOR DE FATURA PDF → EXCEL")
    print("=" * 60)

    print("\nArquivo selecionado.")

    senha = getpass.getpass(
        "Senha do PDF: "
    )

    # -----------------------------------------
    # PDF -> blocos por coluna
    # -----------------------------------------

    blocos_pdf = ler_pdf_em_colunas(
        arquivo_pdf,
        senha
    )

    if not blocos_pdf:

        print(
            "\nNão foi possível extrair texto do PDF."
        )

        return

    # -----------------------------------------
    # Parsing
    # -----------------------------------------

    transacoes = identificar_transacoes(
        blocos_pdf,
        debug=args.debug
    )

    if not transacoes:

        print(
            "\nNenhuma transação foi reconhecida."
        )

        print(
            "\nExecute novamente com --debug."
        )

        return

    # -----------------------------------------
    # Excel
    # -----------------------------------------

    salvar_excel(
        transacoes,
        arquivo_excel
    )

    print("\n" + "=" * 60)

    print(
        f"Transações encontradas: "
        f"{len(transacoes)}"
    )

    print(
        "\nArquivo Excel criado com sucesso "
        "na mesma pasta do PDF."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
