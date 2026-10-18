import unittest
from datetime import date
import validators as v


class TestValidators(unittest.TestCase):
    def test_nome_email_telefone_senha(self):
        self.assertIsNone(v.nome("Maria Silva"))
        self.assertIsNotNone(v.nome("Maria"))
        self.assertIsNone(v.email("a@b.com"))
        for ruim in ("", "abc", "a@b", None):
            self.assertIsNotNone(v.email(ruim))
        self.assertIsNone(v.telefone("(75) 98888-7777"))
        self.assertIsNotNone(v.telefone("12345"))
        self.assertIsNone(v.senha("123456"))
        self.assertIsNotNone(v.senha("123"))

    def test_cnpj(self):
        self.assertIsNone(v.cnpj("11.222.333/0001-81"))
        self.assertIsNone(v.cnpj("11222333000181"))
        for ruim in ("11.222.333/0001-82", "00000000000000", "123", "", None):
            self.assertIsNotNone(v.cnpj(ruim), ruim)

    def test_numeros(self):
        self.assertIsNone(v.inteiro_positivo(3, "x"))
        for ruim in (0, -1, 2.5, "3", True, None):
            self.assertIsNotNone(v.inteiro_positivo(ruim, "x"), ruim)
        self.assertIsNone(v.inteiro_nao_negativo(0, "x"))
        self.assertIsNotNone(v.inteiro_nao_negativo(-1, "x"))
        self.assertIsNone(v.preco(0.01, "x"))
        for ruim in (0, -5, "10", None):
            self.assertIsNotNone(v.preco(ruim, "x"), ruim)

    def test_data_e_validade(self):
        self.assertIsNone(v.data("2026-03-15"))
        self.assertIsNotNone(v.data("15/03/2026"))
        hoje = date(2026, 6, 15)
        self.assertIsNone(v.validade_nao_vencida("2026-06-15", hoje))
        self.assertIsNone(v.validade_nao_vencida("2027-01-01", hoje))
        self.assertIsNotNone(v.validade_nao_vencida("2026-06-14", hoje))
        self.assertIsNotNone(v.validade_nao_vencida("abc", hoje))
