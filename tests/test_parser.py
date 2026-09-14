import unittest

from parser import (
    dividir_em_transacoes,
    interpretar_despesa,
    interpretar_parcelamento,
)


class TestParser(unittest.TestCase):

    def test_despesa_com_tipo_de_compra(self):
        texto = "3 11/06 LOJA EXEMPLO 320,00"

        blocos = dividir_em_transacoes(texto)

        self.assertEqual(len(blocos), 1)

        transacoes = interpretar_despesa(blocos[0])

        self.assertEqual(len(transacoes), 1)
        self.assertEqual(transacoes[0]["Data"], "11/06")
        self.assertEqual(
            transacoes[0]["Descrição"],
            "LOJA EXEMPLO"
        )
        self.assertEqual(
            transacoes[0]["Parcela"],
            ""
        )
        self.assertEqual(
            transacoes[0]["Valor (US$)"],
            ""
        )
        self.assertEqual(
            transacoes[0]["Valor (R$)"],
            "320,00"
        )

    def test_despesa_sem_tipo_de_compra(self):
        texto = "13/06 COMERCIO EXEMPLO 48,35"

        blocos = dividir_em_transacoes(texto)

        self.assertEqual(len(blocos), 1)

        transacoes = interpretar_despesa(blocos[0])

        self.assertEqual(len(transacoes), 1)
        self.assertEqual(
            transacoes[0]["Data"],
            "13/06"
        )
        self.assertEqual(
            transacoes[0]["Descrição"],
            "COMERCIO EXEMPLO"
        )
        self.assertEqual(
            transacoes[0]["Valor (R$)"],
            "48,35"
        )

    def test_compra_parcelada(self):
        texto = (
            "3 06/04 PROFISSIONAL EXEMPLO "
            "03/10 47,00"
        )

        blocos = dividir_em_transacoes(texto)

        self.assertEqual(len(blocos), 1)

        transacoes = interpretar_parcelamento(
            blocos[0]
        )

        self.assertEqual(len(transacoes), 1)
        self.assertEqual(
            transacoes[0]["Data"],
            "06/04"
        )
        self.assertEqual(
            transacoes[0]["Descrição"],
            "PROFISSIONAL EXEMPLO"
        )
        self.assertEqual(
            transacoes[0]["Parcela"],
            "03/10"
        )
        self.assertEqual(
            transacoes[0]["Valor (R$)"],
            "47,00"
        )

    def test_compra_internacional_com_iof(self):
        texto = (
            "18/06 SERVICO DIGITAL EXEMPLO "
            "107,35 20,00 "
            "COTAÇÃO DOLAR R$ 5,3676 "
            "IOF DESPESA NO EXTERIOR 3,76"
        )

        blocos = dividir_em_transacoes(texto)

        self.assertEqual(len(blocos), 1)

        transacoes = interpretar_despesa(
            blocos[0]
        )

        # Compra principal + IOF
        self.assertEqual(len(transacoes), 2)

        compra = transacoes[0]
        iof = transacoes[1]

        self.assertEqual(
            compra["Data"],
            "18/06"
        )
        self.assertEqual(
            compra["Descrição"],
            "SERVICO DIGITAL EXEMPLO"
        )
        self.assertEqual(
            compra["Valor (US$)"],
            "20,00"
        )
        self.assertEqual(
            compra["Valor (R$)"],
            "107,35"
        )

        self.assertEqual(
            iof["Data"],
            "18/06"
        )
        self.assertEqual(
            iof["Descrição"],
            "IOF DESPESA NO EXTERIOR"
        )
        self.assertEqual(
            iof["Valor (US$)"],
            ""
        )
        self.assertEqual(
            iof["Valor (R$)"],
            "3,76"
        )

    def test_duas_compras_na_mesma_linha(self):
        texto = (
            "3 11/06 LOJA EXEMPLO 320,00 "
            "13/06 COMERCIO EXEMPLO 48,35"
        )

        blocos = dividir_em_transacoes(texto)

        self.assertEqual(len(blocos), 2)

        primeira = interpretar_despesa(
            blocos[0]
        )[0]

        segunda = interpretar_despesa(
            blocos[1]
        )[0]

        self.assertEqual(
            primeira["Data"],
            "11/06"
        )

        self.assertEqual(
            segunda["Data"],
            "13/06"
        )


if __name__ == "__main__":
    unittest.main()
